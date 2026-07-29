"""One command to check the whole toolkit.

Runs every suite that can run unattended, probes every bridge and every server
in toolkit.json, and prints the manual steps still outstanding. Nothing here
mutates a project: it builds, tests and probes.

    python scripts/verify_toolkit.py            # everything runnable
    python scripts/verify_toolkit.py --quick    # skip the slow app-driven suites

Exit code 0 when every automated check passed, 1 otherwise. Pending manual steps
are reported but do not fail the run -- they are your move, not a defect.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from _mcp_probe import audacity_pipes_live, mcp_handshake
from _toolkit import (BAD, CONFIG, OK, ROOT, SKIP, TODO, detect_applications, heading,
                      load_registry, paint, port_open, server_dir, speaks_mcp,
                      venv_can_import, which, working_venv_script)

ASEPRITE_MCP = ROOT / "servers" / "aseprite"
GODOT_SERVER = ROOT / "servers" / "godot" / "server"

# A read-only tool per server whose success proves the application behind it is
# actually reachable. Listing tools alone does not.
LIVENESS_PROBE = {"audacity": "project_get_info"}


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


def run(cmd: list[str], cwd: Path, timeout: int = 900) -> tuple[bool, str]:
    """Run a command, returning (ok, tail-of-output)."""
    resolved = which(cmd[0])
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


def configured_entries() -> dict[str, dict]:
    """The servers as the MCP client will actually see them.

    Probing what mcp_config.json says, rather than re-deriving paths, is what
    catches a config that has drifted from the registry -- a stale entry left
    over from a repo rename looks fine until something tries to launch it.
    """
    if not CONFIG.exists():
        return {}
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8")).get("mcpServers", {}) or {}
    except (OSError, ValueError):
        return {}


def configured_env(name: str, key: str) -> str:
    """One env value from mcp_config.json, which is where the client reads it.

    Checking os.environ instead reported OBSIDIAN_API_KEY missing long after it
    had been set -- the shell running this script has no reason to carry it.
    """
    value = os.environ.get(key, "")
    if value and "REPLACE" not in value:
        return value
    value = (configured_entries().get(name, {}).get("env") or {}).get(key, "")
    return "" if "REPLACE" in value else value


# --------------------------------------------------------------------- #


def check_prerequisites(report: Report) -> None:
    heading("Prerequisites")
    for name, probe in (("uv", ["uv", "--version"]),
                        ("node", ["node", "--version"]),
                        ("npm", ["npm", "--version"])):
        if not which(name):
            report.add(name, BAD, "not on PATH")
            continue
        ok, out = run(probe, ROOT, timeout=30)
        report.add(name, OK if ok else BAD, out)


def check_applications(report: Report) -> dict:
    heading("Applications")
    info = detect_applications()
    if not info:
        report.add("application discovery", BAD,
                   "could not load the aseprite path resolver -- run `uv sync "
                   "--directory servers/aseprite`")
        return {}

    for entry in info.values():
        if entry["found"]:
            report.add(entry["name"], OK, f"{entry['version'][:30]} -- {entry['path']}")
        else:
            report.add(entry["name"], SKIP, f"not found; set {entry['env_var']}")
    return info


def check_installs(report: Report) -> None:
    """Whether each registered server is actually installed on this machine."""
    heading("Installs")
    for name, spec in load_registry().get("servers", {}).items():
        directory = server_dir(spec)

        if directory is None or not directory.exists():
            report.add(name, BAD, f"{spec.get('path')} is missing from the tree")
            continue

        if spec.get("runtime") == "in-app":
            report.add(name, SKIP, "runs inside the application; source vendored")
            continue

        command = (spec.get("client") or {}).get("command", "")
        if command.startswith("{venvScript:"):
            script = command[len("{venvScript:"):-1]
            if not working_venv_script(directory, script):
                report.add(name, BAD, "venv missing or stale (repo moved?)")
                report.manual.append(
                    f"Rebuild it: python scripts/install_vendored.py --force {name}")
                continue

            # A resolvable console script is not proof the venv still works --
            # its dependencies can have been re-resolved out from under it.
            module = (spec.get("install") or {}).get("verifyImport")
            if module:
                importable, message = venv_can_import(directory, module)
                if not importable:
                    report.add(name, BAD, f"cannot import {module}: {message}")
                    report.manual.append(
                        f"Rebuild it: python scripts/install_vendored.py --force {name}")
                    continue

        if name == "godot-mcp" and not (GODOT_SERVER / "dist" / "index.js").exists():
            report.add(name, BAD, "dist/index.js missing -- run npm run build")
            continue

        report.add(name, OK, str(directory.relative_to(ROOT)))


def check_bridges(report: Report) -> None:
    """The application-side half of each server, driven by the registry."""
    heading("Live bridges")

    for name, spec in load_registry().get("servers", {}).items():
        bridge = spec.get("bridge")
        if not bridge:
            continue
        kind = bridge.get("kind")
        label = f"{spec.get('drives', name)} bridge"

        if kind == "audacity-pipe":
            live = audacity_pipes_live()
            report.add(label, OK if live else SKIP,
                       "pipes present" if live else "pipes absent")
        elif kind == "http":
            candidates = bridge.get("portCandidates") or [bridge.get("port")]
            endpoint = bridge.get("endpoint", "/")
            found = next((p for p in candidates
                          if p and port_open(p) and speaks_mcp(p, endpoint)), None)
            report.add(label, OK if found else SKIP,
                       f"serving http://localhost:{found}{endpoint}" if found
                       else f"no MCP server on {candidates}")
        elif kind == "tcp":
            port = bridge.get("port")
            live = port_open(port)
            report.add(label, OK if live else SKIP,
                       f"listening on :{port}" if live else f"nothing on :{port}")
        else:
            continue

        if report.checks[-1].status == SKIP and spec.get("appSetup"):
            report.manual.append(f"{spec.get('drives', name)}: {spec['appSetup']}")


def check_servers(report: Report) -> None:
    """Every configured server, exactly as the MCP client would launch it."""
    heading("MCP servers (stdio handshake)")

    entries = configured_entries()
    if not entries:
        report.add("mcp_config.json", BAD, "missing -- run scripts/write_mcp_config.py")
        return

    for name, entry in entries.items():
        command = entry.get("command", "")
        # mcp-remote proxies an HTTP server that is checked under Live bridges;
        # launching it here would only prove npx works.
        if "mcp-remote" in " ".join(entry.get("args", [])):
            report.add(name, SKIP, "HTTP bridge -- see Live bridges above")
            continue

        cwd = Path(entry.get("cwd") or ROOT)
        if not cwd.exists():
            report.add(name, BAD, f"cwd does not exist: {cwd}")
            continue

        env = dict(entry.get("env") or {})
        probe = LIVENESS_PROBE.get(name)
        if probe and name == "audacity" and not audacity_pipes_live():
            probe = None

        ok, count, message = mcp_handshake(
            [command, *entry.get("args", [])], cwd, env=env, timeout=90, probe_tool=probe)
        detail = f"{count} tools" + (f", {message}" if ok and message else "")
        report.add(name, OK if ok else BAD, detail if ok else message)

    if not configured_env("obsidian", "OBSIDIAN_API_KEY") and "obsidian" in entries:
        report.manual.append(
            "Set OBSIDIAN_API_KEY in mcp_config.json from Obsidian's Local REST API "
            "plugin settings, or run scripts/configure_obsidian.py. The server starts "
            "without it but every call fails."
        )


def check_suites(report: Report, quick: bool, apps: dict) -> None:
    heading("Test suites")

    # `python -m pytest` rather than the `pytest` console script: the script is a
    # shim with an absolute path baked in, so it breaks whenever the venv moves.
    # The module entry point does not care where the venv lives.
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
        demo = GODOT_SERVER / "tests" / "headless_test.mjs"
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
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true",
                        help="skip the suites that drive a real application")
    args = parser.parse_args()

    print(paint("GameDev Toolkit MCP -- verification", "1"))
    print(f"repo: {ROOT}")

    report = Report()
    check_prerequisites(report)
    apps = check_applications(report)
    check_installs(report)
    check_bridges(report)
    check_servers(report)
    check_suites(report, args.quick, apps)

    heading("Summary")
    passed = sum(1 for c in report.checks if c.status == OK)
    skipped = sum(1 for c in report.checks if c.status == SKIP)
    print(f"  {passed} passed, {report.failed} failed, {skipped} skipped")

    if report.manual:
        heading("Still needs you")
        for i, step in enumerate(dict.fromkeys(report.manual), 1):
            print(f"  {TODO} {i}. {step}")

    if report.failed:
        print(f"\n{BAD} -- fix the failures above.")
        return 1
    print(f"\n{OK} -- every automated check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
