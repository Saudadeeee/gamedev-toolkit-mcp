"""Repository-level checks: the registry, the scripts, and the setup scripts.

These used to live in a GitHub Actions workflow. They are cheap, they catch
things no runtime probe can, and there is no reason they need a server to run
on -- so they run here, as part of scripts/verify_toolkit.py.

Each check returns (ok, detail). Nothing here touches the network or mutates a
file.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from _toolkit import (REGISTRY, ROOT, load_registry, venv_can_import, which,
                      working_venv_script)

SCRIPT_MODULES = ("_toolkit", "_mcp_probe", "_repo_checks",
                  "install_vendored", "write_mcp_config", "verify_toolkit",
                  # scripts/checks/ -- run by CI and the full verify; a syntax
                  # error there fails just as silently.
                  "checks.gdcheck", "checks.test_vendored",
                  "checks.check_upstream_drift")

# Tab, LF and CR are line endings, which .gitattributes governs. What this is
# looking for is the BEL that once turned "servers\aseprite" into an
# unopenable path and broke setup.ps1 on every Windows machine.
ALLOWED_CONTROL_BYTES = {0x09, 0x0A, 0x0D}
BYTE_SENSITIVE_FILES = ("setup.ps1", "setup.sh", "toolkit.json")

ORIGINS = {"first-party", "vendored"}
RUNTIMES = {"stdio", "in-app"}


def _run_full(cmd: list[str], cwd: Path = ROOT, timeout: int = 300) -> tuple[bool, str]:
    """Run a command and return (ok, complete combined output)."""
    resolved = which(cmd[0]) if not Path(cmd[0]).exists() else cmd[0]
    if resolved is None:
        return False, f"{cmd[0]} not found on PATH"
    try:
        proc = subprocess.run([str(resolved), *cmd[1:]], cwd=cwd, capture_output=True,
                              text=True, timeout=timeout, encoding="utf-8", errors="replace")
    except OSError as error:
        return False, str(error)
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    return proc.returncode == 0, ((proc.stdout or "") + (proc.stderr or "")).strip()


def _run(cmd: list[str], cwd: Path = ROOT, timeout: int = 300) -> tuple[bool, str]:
    """Run a command and return (ok, last meaningful line) -- for status messages."""
    ok, out = _run_full(cmd, cwd, timeout)
    lines = [ln for ln in out.splitlines() if ln.strip()]
    return ok, (lines[-1] if lines else "")


def check_registry() -> tuple[bool, str]:
    """toolkit.json is what every script reads; a typo here breaks a fresh clone."""
    try:
        servers = load_registry().get("servers") or {}
    except SystemExit as error:
        return False, str(error)
    if not servers:
        return False, f"{REGISTRY.name} declares no servers"

    for name, spec in servers.items():
        origin = spec.get("origin")
        if origin not in ORIGINS:
            return False, f"{name}: origin {origin!r} not in {sorted(ORIGINS)}"
        if spec.get("runtime") not in RUNTIMES:
            return False, f"{name}: runtime {spec.get('runtime')!r} not in {sorted(RUNTIMES)}"
        if not (spec.get("client") or {}).get("command"):
            return False, f"{name}: no client.command"
        if not spec.get("license"):
            return False, f"{name}: no license recorded -- see COPYRIGHT"

        path = spec.get("path")
        if not path or not (ROOT / path).is_dir():
            return False, f"{name}: path {path!r} does not exist"

        if origin == "vendored":
            if not spec.get("repo"):
                return False, f"{name}: vendored servers must record their upstream repo"
            if not (ROOT / path / "LICENSE").is_file():
                return False, f"{name}: vendored server is missing its LICENSE file"
            if spec.get("modified") is None:
                return False, f"{name}: vendored servers must declare `modified`"

        install = spec.get("install") or {}
        if install.get("type") == "uv-venv" and not install.get("verifyImport"):
            return False, f"{name}: uv-venv servers must declare install.verifyImport"

    return True, f"{len(servers)} servers, all well-formed"


def check_scripts_import() -> tuple[bool, str]:
    """Every helper imports cleanly -- a syntax error here breaks setup silently."""
    broken = []
    for module in SCRIPT_MODULES:
        ok, detail = _run([sys.executable, "-c",
                           f"import sys; sys.path.insert(0, r'{ROOT / 'scripts'}'); import {module}"],
                          timeout=120)
        if not ok:
            broken.append(f"{module} ({detail[:60]})")
    if broken:
        return False, "; ".join(broken)
    return True, f"{len(SCRIPT_MODULES)} modules"


def check_control_bytes() -> tuple[bool, str]:
    """No stray control bytes in the files where one would be invisible."""
    bad = []
    for name in BYTE_SENSITIVE_FILES:
        path = ROOT / name
        if not path.is_file():
            continue
        found = sorted({b for b in path.read_bytes()
                        if b < 0x20 and b not in ALLOWED_CONTROL_BYTES})
        if found:
            bad.append(f"{name}: {[hex(b) for b in found]}")
    if bad:
        return False, "; ".join(bad)
    return True, f"{len(BYTE_SENSITIVE_FILES)} files clean"


def check_setup_syntax() -> tuple[bool, str]:
    """Both setup scripts parse, on whichever interpreters this machine has."""
    results = []

    if which("bash"):
        ok, detail = _run(["bash", "-n", "setup.sh"], timeout=120)
        if not ok:
            return False, f"setup.sh: {detail[:80]}"
        results.append("setup.sh")

    shell = which("pwsh") or which("powershell")
    if shell:
        probe = (
            "$e=$null;"
            "[System.Management.Automation.Language.Parser]::ParseFile("
            "(Resolve-Path setup.ps1),[ref]$null,[ref]$e)|Out-Null;"
            "if($e){$e|ForEach-Object{$_.Message};exit 1}"
        )
        ok, detail = _run([shell, "-NoProfile", "-Command", probe], timeout=180)
        if not ok:
            return False, f"setup.ps1: {detail[:80]}"
        results.append("setup.ps1")

    if not results:
        return True, "no bash or powershell on PATH -- nothing to parse"
    return True, " + ".join(results) + " parse"


def check_duplicate_tool_names() -> tuple[bool, str]:
    """FastMCP keeps whichever tool registers last and reports nothing.

    A duplicated name therefore shadows a working tool in silence. This is the
    only thing that catches it.
    """
    server = ROOT / "servers" / "aseprite"
    program = (
        "import asyncio, collections, json;"
        "from aseprite_mcp import mcp;"
        "import aseprite_mcp.tools;"
        "names=[t.name for t in asyncio.run(mcp.list_tools())];"
        "dupes=[n for n,c in collections.Counter(names).items() if c>1];"
        "print(json.dumps({'total':len(names),'duplicates':dupes}))"
    )
    if which("uv") is None:
        return True, "uv not on PATH -- skipped"
    ok, detail = _run(["uv", "run", "python", "-c", program], cwd=server, timeout=300)
    if not ok:
        return False, detail[:100]
    try:
        result = json.loads(detail)
    except ValueError:
        return False, detail[:100]
    if result["duplicates"]:
        return False, f"duplicate tool names: {result['duplicates']}"
    return True, f"{result['total']} tools, no duplicates"


def check_config_generator() -> tuple[bool, str]:
    """The generator must cover every server that is actually installed.

    This is what caught the config drifting from the registry: setup used to
    emit two servers while the docs described five.
    """
    # The whole document is needed here, not just its last line -- `--print`
    # writes a status banner and then multi-line JSON.
    ok, output = _run_full([sys.executable, str(ROOT / "scripts" / "write_mcp_config.py"),
                            "--print"], timeout=600)
    if not ok:
        return False, output.splitlines()[-1][:100] if output else "generator failed"
    try:
        document = json.loads(output[output.index("{"):])
    except (ValueError, KeyError):
        return False, "could not parse the generated config"

    written = set(document.get("mcpServers") or {})
    expected = set()
    for name, spec in (load_registry().get("servers") or {}).items():
        command = (spec.get("client") or {}).get("command", "")
        if command.startswith("{venvScript:"):
            # Only expect a server whose venv is genuinely usable.
            directory = ROOT / spec["path"]
            script = command[len("{venvScript:"):-1]
            module = (spec.get("install") or {}).get("verifyImport")
            if not working_venv_script(directory, script):
                continue
            if module and not venv_can_import(directory, module)[0]:
                continue
        expected.add(name)

    missing = expected - written
    if missing:
        return False, f"generator dropped: {sorted(missing)}"
    return True, f"{len(written)} servers configured"


REPO_CHECKS = (
    ("toolkit.json registry", check_registry),
    ("helper scripts import", check_scripts_import),
    ("no stray control bytes", check_control_bytes),
    ("setup script syntax", check_setup_syntax),
    ("no duplicate tool names", check_duplicate_tool_names),
    ("config generator coverage", check_config_generator),
)
