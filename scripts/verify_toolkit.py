"""One command to check the whole toolkit.

Runs every suite that can run unattended, probes every bridge, and prints the
manual steps still outstanding. Nothing here mutates a project: it builds,
tests and probes.

    python scripts/verify_toolkit.py            # everything runnable
    python scripts/verify_toolkit.py --quick    # skip the slow app-driven suites

Exit code 0 when every automated check passed, 1 otherwise. Pending manual
steps are reported but do not fail the run -- they are your move, not a defect.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASEPRITE_MCP = ROOT / "servers" / "aseprite"
GODOT_SERVER = ROOT / "servers" / "godot" / "server"
VENDOR = ROOT / "vendor"

GODOT_BRIDGE_PORT = 9080
BLOCKBENCH_PORTS = (3000, 3456, 3001, 8080)
BLOCKBENCH_ENDPOINT = "/bb-mcp"

# ANSI is fine on modern Windows terminals; strip it when piped to a file.
_COLOR = sys.stdout.isatty()


def _paint(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


OK = _paint("PASS", "32")
BAD = _paint("FAIL", "31")
SKIP = _paint("SKIP", "33")
TODO = _paint("TODO", "36")


@dataclass
class Result:
    name: str
    status: str
    detail: str = ""


@dataclass
class Report:
    checks: list[Result] = field(default_factory=list)
    manual: list[str] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.checks.append(Result(name, status, detail))
        line = f"  {status}  {name}"
        if detail:
            line += f"  --  {detail}"
        print(line, flush=True)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status == BAD)


def heading(text: str) -> None:
    print(f"\n{_paint(text, '1')}")


def resolve(program: str) -> str | None:
    """Absolute path for a program.

    Needed on Windows, where npm and npx are `.CMD` shims: shutil.which finds
    them, but subprocess without a shell cannot execute the bare name.
    """
    return shutil.which(program)


def run(cmd: list[str], cwd: Path, timeout: int = 900) -> tuple[bool, str]:
    """Run a command, returning (ok, tail-of-output)."""
    resolved = resolve(cmd[0])
    if resolved is None:
        return False, f"{cmd[0]} not found on PATH"

    try:
        proc = subprocess.run(
            [resolved, *cmd[1:]], cwd=cwd, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
    except OSError as error:
        return False, f"could not run {cmd[0]}: {error}"
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"

    output = (proc.stdout or "") + (proc.stderr or "")
    tail = [line for line in output.strip().splitlines() if line.strip()]
    return proc.returncode == 0, (tail[-1] if tail else "")


def windows_pipe_present(name: str) -> bool:
    """Whether a Win32 named pipe exists.

    os.path.exists under-reports here: Windows does not reliably enumerate the
    named-pipe namespace, so a live pipe can look absent. WaitNamedPipe asks
    the object manager directly.
    """
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.WaitNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
    kernel32.WaitNamedPipeW.restype = wintypes.BOOL
    if kernel32.WaitNamedPipeW(name, 200):
        return True
    # Busy means the pipe is there with every instance taken.
    return ctypes.get_last_error() in (121, 231)


def audacity_pipes_live() -> bool:
    """Whether Audacity is running with mod-script-pipe listening."""
    if platform.system() == "Windows":
        return all(windows_pipe_present(name) for name in
                   (r"\\.\pipe\ToSrvPipe", r"\\.\pipe\FromSrvPipe"))

    uid = os.getuid() if hasattr(os, "getuid") else 0
    return all(os.path.exists(path) for path in
               (f"/tmp/audacity_script_pipe.to.{uid}",
                f"/tmp/audacity_script_pipe.from.{uid}"))


def configured_obsidian_key() -> str:
    """The Obsidian API key as the MCP client will actually see it.

    It is set in mcp_config.json, which is where the client reads it from --
    the shell running this script has no reason to carry it.
    """
    env_key = os.environ.get("OBSIDIAN_API_KEY", "")
    if env_key and "REPLACE" not in env_key:
        return env_key

    config = ROOT / "mcp_config.json"
    if not config.exists():
        return ""
    try:
        servers = json.loads(config.read_text(encoding="utf-8")).get("mcpServers", {})
    except (OSError, ValueError):
        return ""
    key = servers.get("obsidian", {}).get("env", {}).get("OBSIDIAN_API_KEY", "")
    return "" if "REPLACE" in key else key


def port_open(port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def speaks_mcp(port: int, endpoint: str) -> bool:
    """A JSON-RPC reply proves it is an MCP server, not just an open port."""
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{endpoint}",
        data=b'{"jsonrpc":"2.0","id":1,"method":"ping"}',
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=1.5) as response:
            return b"jsonrpc" in response.read(512)
    except urllib.error.HTTPError as error:
        try:
            return b"jsonrpc" in error.read(512)
        except OSError:
            return False
    except (OSError, ValueError):
        return False


def mcp_handshake(command: list[str], cwd: Path, env: dict | None = None,
                  timeout: int = 90, probe_tool: str | None = None) -> tuple[bool, int, str]:
    """Speak MCP over stdio and return (ok, tool_count, message).

    Responses are read as they arrive and the process is killed once the
    answers are in. An MCP server is not supposed to exit when stdin closes --
    waiting for it to would hang until the timeout on every healthy server.

    probe_tool names a read-only tool to call afterwards. A server can list
    tools perfectly while the application behind it is unreachable, so for
    those servers listing alone is not evidence the chain works. On success
    the message reports the probe; on failure it says what broke.
    """
    resolved = resolve(command[0])
    if resolved is None:
        return False, 0, f"{command[0]} not found on PATH"

    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "verify", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    if probe_tool:
        requests.append({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                         "params": {"name": probe_tool, "arguments": {}}})
    wanted = {1, 2, 3} if probe_tool else {1, 2}

    try:
        proc = subprocess.Popen(
            [resolved, *command[1:]], cwd=cwd,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            env={**os.environ, **(env or {})},
        )
    except OSError as error:
        return False, 0, f"could not start: {error}"

    seen: dict = {}

    def reader() -> None:
        for line in proc.stdout:  # type: ignore[union-attr]
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if "id" in message:
                seen[message["id"]] = message
                if wanted <= seen.keys():
                    return

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()

    try:
        proc.stdin.write("\n".join(json.dumps(r) for r in requests) + "\n")  # type: ignore[union-attr]
        proc.stdin.flush()  # type: ignore[union-attr]
    except OSError:
        pass

    thread.join(timeout)
    stderr_tail = ""
    proc.kill()
    try:
        _, stderr = proc.communicate(timeout=10)
        stderr_tail = ((stderr or "").strip().splitlines() or [""])[-1]
    except (subprocess.TimeoutExpired, ValueError):
        pass

    if 1 not in seen or "result" not in seen[1]:
        return False, 0, f"initialize failed: {stderr_tail[:120] or 'no response'}"
    if 2 not in seen or "result" not in seen[2]:
        return False, 0, "tools/list failed"

    count = len(seen[2]["result"]["tools"])
    if not probe_tool:
        return True, count, ""

    if 3 not in seen or "result" not in seen[3]:
        return False, count, f"{probe_tool} never answered -- application unreachable"

    result = seen[3]["result"]
    text = "".join(part.get("text", "") for part in result.get("content", [])
                   if part.get("type") == "text")
    if result.get("isError") or '"success": false' in text:
        return False, count, f"{probe_tool}: {text.strip().splitlines()[0][:90]}"

    return True, count, "application reachable"


# --------------------------------------------------------------------- #


def check_prerequisites(report: Report) -> dict:
    heading("Prerequisites")
    tools = {}
    for name, probe in (("uv", ["uv", "--version"]),
                        ("node", ["node", "--version"]),
                        ("npm", ["npm", "--version"])):
        path = shutil.which(name)
        tools[name] = path
        if not path:
            report.add(name, BAD, "not on PATH")
            continue
        ok, out = run(probe, ROOT, timeout=30)
        report.add(name, OK if ok else BAD, out)
    return tools


def check_applications(report: Report) -> dict:
    heading("Applications")
    sys.path.insert(0, str(ASEPRITE_MCP))
    try:
        from aseprite_mcp.core.path_resolver import get_application_info
    except ImportError as error:
        report.add("application discovery", BAD, str(error))
        return {}

    info = get_application_info()
    for key, entry in info.items():
        if entry["found"]:
            report.add(entry["name"], OK, f"{entry['version'][:30]} -- {entry['path']}")
        else:
            report.add(entry["name"], SKIP, f"not found; set {entry['env_var']}")
    return info


def check_bridges(report: Report) -> None:
    heading("Live bridges")

    if port_open(GODOT_BRIDGE_PORT):
        report.add("Godot editor bridge", OK, f"listening on :{GODOT_BRIDGE_PORT}")
    else:
        report.add("Godot editor bridge", SKIP, f"nothing on :{GODOT_BRIDGE_PORT}")
        report.manual.append(
            "Open a Godot project with the godot_mcp plugin enabled "
            "(Project > Project Settings > Plugins). Only the scene tools need "
            "this; the headless tools do not."
        )

    found_port = next(
        (p for p in BLOCKBENCH_PORTS if port_open(p) and speaks_mcp(p, BLOCKBENCH_ENDPOINT)),
        None,
    )
    if found_port:
        report.add("Blockbench MCP plugin", OK,
                   f"serving http://localhost:{found_port}{BLOCKBENCH_ENDPOINT}")
    else:
        report.add("Blockbench MCP plugin", SKIP, f"no MCP server on {list(BLOCKBENCH_PORTS)}")
        report.manual.append(
            "Open Blockbench with the MCP plugin loaded (File > Plugins > Load "
            "from URL: https://jasonjgardner.github.io/blockbench-mcp-plugin/mcp.js) "
            "and grant the network permission."
        )

    if audacity_pipes_live():
        report.add("Audacity mod-script-pipe", OK, "pipes present")
    else:
        report.add("Audacity mod-script-pipe", SKIP, "pipes absent")
        report.manual.append(
            "Open Audacity 3.x, enable Edit > Preferences > Modules > "
            "mod-script-pipe, then restart Audacity."
        )


def check_servers(report: Report) -> None:
    heading("MCP servers (stdio handshake)")

    ok, count, message = mcp_handshake(["uv", "run", "-m", "aseprite_mcp"], ASEPRITE_MCP)
    report.add("aseprite", OK if ok else BAD, f"{count} tools" if ok else message)

    dist = GODOT_SERVER / "dist" / "index.js"
    if dist.exists():
        ok, count, message = mcp_handshake(["node", str(dist)], GODOT_SERVER)
        report.add("godot-mcp", OK if ok else BAD, f"{count} tools" if ok else message)
    else:
        report.add("godot-mcp", BAD, "dist/index.js missing — run npm run build")

    audacity = VENDOR / "Audacity-MCP" / ".venv" / "Scripts" / "audacity-mcp.exe"
    if not audacity.exists():
        audacity = VENDOR / "Audacity-MCP" / ".venv" / "bin" / "audacity-mcp"
    if audacity.exists():
        # With Audacity running, go one step further than listing tools and
        # make a read-only call, which is the only thing that proves the
        # server actually reaches the application over mod-script-pipe.
        probe = "project_get_info" if audacity_pipes_live() else None
        ok, count, message = mcp_handshake(
            [str(audacity)], VENDOR / "Audacity-MCP", timeout=45, probe_tool=probe)
        detail = f"{count} tools" + (f", {message}" if ok and message else "")
        report.add("audacity", OK if ok else BAD, detail if ok else message)
    else:
        report.add("audacity", SKIP, "not installed under vendor/")
        report.manual.append(
            "Install it: git clone https://github.com/xDarkzx/Audacity-MCP vendor/Audacity-MCP "
            'then uv venv && uv pip install -e . "mcp[cli]>=1.0,<2"'
        )

    obsidian = VENDOR / "mcp-obsidian" / ".venv" / "Scripts" / "mcp-obsidian.exe"
    if not obsidian.exists():
        obsidian = VENDOR / "mcp-obsidian" / ".venv" / "bin" / "mcp-obsidian"
    if obsidian.exists():
        ok, count, message = mcp_handshake(
            [str(obsidian)], VENDOR / "mcp-obsidian",
            env={"OBSIDIAN_API_KEY": configured_obsidian_key() or "verify-probe"},
        )
        report.add("obsidian", OK if ok else BAD, f"{count} tools" if ok else message)
        # The key lives in mcp_config.json, not this shell's environment --
        # checking os.environ reported it missing long after it was set.
        if not configured_obsidian_key():
            report.manual.append(
                "Set OBSIDIAN_API_KEY in mcp_config.json from Obsidian's Local REST "
                "API plugin settings, or run scripts/configure_obsidian.py. The "
                "server starts without it but every call fails."
            )
    else:
        report.add("obsidian", SKIP, "not installed under vendor/")


def check_suites(report: Report, quick: bool, apps: dict) -> None:
    heading("Test suites")

    # `python -m pytest` rather than the `pytest` console script: the script is
    # a shim with an absolute path baked in, so it breaks whenever the venv is
    # moved. The module entry point does not care where the venv lives.
    ok, out = run(["uv", "run", "python", "-m", "pytest", "-q"], ASEPRITE_MCP, timeout=300)
    report.add("aseprite unit tests", OK if ok else BAD, out)

    ok, out = run(["npm", "run", "build"], GODOT_SERVER, timeout=600)
    report.add("godot-mcp TypeScript build", OK if ok else BAD, out if not ok else "tsc clean")

    ok, out = run([sys.executable, str(ROOT / "scripts" / "ci" / "gdcheck.py"),
                   str(ROOT / "servers" / "godot" / "addons")], ROOT, timeout=120)
    report.add("GDScript structure", OK if ok else BAD, out)

    if quick:
        report.add("app-driven suites", SKIP, "--quick given")
        return

    if apps.get("aseprite", {}).get("found"):
        for label, script in (("aseprite smoke", "tests/smoke_test.py"),
                              ("aseprite shading", "tests/shading_test.py")):
            ok, out = run(["uv", "run", script, "--clean"], ASEPRITE_MCP, timeout=1800)
            report.add(label, OK if ok else BAD, out)
    else:
        report.add("aseprite smoke + shading", SKIP, "Aseprite not found")

    if apps.get("godot", {}).get("found"):
        demo = ROOT / "servers" / "godot" / "server" / "tests" / "headless_test.mjs"
        project = os.environ.get("GODOT_TEST_PROJECT")
        if project and Path(project).exists():
            ok, out = run(["node", str(demo), project], GODOT_SERVER, timeout=1800)
            report.add("Godot headless suite", OK if ok else BAD, out)
        else:
            report.add("Godot headless suite", SKIP,
                       "set GODOT_TEST_PROJECT to a Godot project path")
            report.manual.append(
                "To run the Godot headless suite, set GODOT_TEST_PROJECT to any "
                "Godot 4 project folder, then re-run this script."
            )
    else:
        report.add("Godot headless suite", SKIP, "Godot not found")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true",
                        help="skip the suites that drive a real application")
    args = parser.parse_args()

    print(_paint("GameDev Toolkit MCP -- verification", "1"))
    print(f"repo: {ROOT}")

    report = Report()
    check_prerequisites(report)
    apps = check_applications(report)
    check_bridges(report)
    check_servers(report)
    check_suites(report, args.quick, apps)

    heading("Summary")
    passed = sum(1 for c in report.checks if c.status == OK)
    skipped = sum(1 for c in report.checks if c.status == SKIP)
    print(f"  {passed} passed, {report.failed} failed, {skipped} skipped")

    if report.manual:
        heading("Still needs you")
        for i, step in enumerate(report.manual, 1):
            print(f"  {TODO} {i}. {step}")

    if report.failed:
        print(f"\n{BAD} — fix the failures above.")
        return 1
    print(f"\n{OK} — every automated check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
