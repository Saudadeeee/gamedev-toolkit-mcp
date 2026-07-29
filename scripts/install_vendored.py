"""Build the virtualenvs for the vendored MCP servers listed in toolkit.json.

The source is already in the tree -- these servers are vendored, not cloned --
so this only creates each one's virtualenv and installs it. Nothing touches the
network except the package index.

    python scripts/install_vendored.py            # install or repair all
    python scripts/install_vendored.py obsidian   # just one
    python scripts/install_vendored.py --check    # report, change nothing
    python scripts/install_vendored.py --force    # rebuild the venvs from scratch

Safe to re-run. A venv whose console script points at an interpreter that no
longer exists -- which is what happens when the repo is moved or renamed, since
the shims bake in absolute paths -- is rebuilt automatically.

To pull a newer upstream into a vendored server, see docs/licensing.md; it is a
licensing operation as much as a technical one.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from _toolkit import (BAD, OK, ROOT, SKIP, heading, load_registry, paint,
                      venv_can_import, working_venv_script, which)


def run(cmd: list[str], cwd: Path, timeout: int = 900) -> tuple[bool, str]:
    """Run a command, returning (ok, last-line-of-output)."""
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

    output = ((proc.stdout or "") + (proc.stderr or "")).strip()
    lines = [line for line in output.splitlines() if line.strip()]
    return proc.returncode == 0, (lines[-1] if lines else "")


def entry_point(spec: dict) -> str:
    """The console script a uv-venv server is invoked through.

    Taken from the client command's {venvScript:NAME} placeholder rather than
    guessed, so the registry stays the only place that names it.
    """
    command = (spec.get("client") or {}).get("command", "")
    if command.startswith("{venvScript:") and command.endswith("}"):
        return command[len("{venvScript:"):-1]
    return ""


def install(name: str, spec: dict, *, force: bool, check: bool) -> str:
    """Install one vendored server. Returns a status constant."""
    target = ROOT / spec["path"]
    script_name = entry_point(spec)

    if not target.exists():
        print(f"  {BAD}  {name}  --  {spec['path']} is missing from the tree")
        return BAD

    installed = working_venv_script(target, script_name) if script_name else None
    module = (spec.get("install") or {}).get("verifyImport")

    # The console script resolving is necessary but not sufficient: the venv's
    # dependencies can have been re-resolved out from under it. Both have to
    # hold before an install counts as healthy.
    importable, import_error = (True, "")
    if installed and module:
        importable, import_error = venv_can_import(target, module)

    if check:
        if installed and importable:
            print(f"  {OK}  {name}  --  {installed}")
            return OK
        if not installed:
            print(f"  {BAD}  {name}  --  venv missing or stale (repo moved?)")
        else:
            print(f"  {BAD}  {name}  --  cannot import {module}: {import_error}")
        return BAD

    if installed and importable and not force:
        print(f"  {OK}  {name}  --  {installed}")
        return OK

    venv = target / ".venv"

    # A console script whose interpreter no longer exists is one the repo was
    # moved out from under. uv pip install alone will not repoint it -- the venv
    # has to go.
    if force or venv.exists():
        shutil.rmtree(venv, ignore_errors=True)

    ok, message = run(["uv", "venv"], target, timeout=300)
    if not ok:
        print(f"  {BAD}  {name}  --  uv venv failed: {message}")
        return BAD

    packages = (spec.get("install") or {}).get("packages") or []
    ok, message = run(["uv", "pip", "install", *packages], target, timeout=900)
    if not ok:
        print(f"  {BAD}  {name}  --  install failed: {message}")
        return BAD

    final = working_venv_script(target, script_name) if script_name else None
    if script_name and final is None:
        print(f"  {BAD}  {name}  --  installed but `{script_name}` is missing")
        return BAD

    if module:
        ok, message = venv_can_import(target, module)
        if not ok:
            print(f"  {BAD}  {name}  --  installed but cannot import {module}: {message}")
            return BAD

    print(f"  {OK}  {name}  --  {final or target}")
    return OK


def report_manual(name: str, spec: dict) -> None:
    print(f"  {SKIP}  {name}  --  runs inside the application; source vendored for reference")
    for step in (spec.get("install") or {}).get("steps") or []:
        print(f"          {step}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="*", help="server names; default is all vendored")
    parser.add_argument("--check", action="store_true", help="report status, change nothing")
    parser.add_argument("--force", action="store_true", help="delete and rebuild each venv")
    args = parser.parse_args()

    if not args.check and which("uv") is None:
        print(f"{BAD} uv is not on PATH -- see https://astral.sh/uv")
        return 1

    registry = load_registry()
    all_servers = registry.get("servers", {})
    wanted = set(args.names)

    unknown = wanted - set(all_servers)
    if unknown:
        print(f"{BAD} unknown server(s): {', '.join(sorted(unknown))}")
        return 1

    selected = {name: spec for name, spec in all_servers.items()
                if spec.get("origin") == "vendored" and (not wanted or name in wanted)}

    print(paint("Vendored MCP servers", "1"))
    print(f"tree: {ROOT / registry.get('serversDir', 'servers')}")
    heading("Installing")

    statuses = []
    for name, spec in selected.items():
        if (spec.get("install") or {}).get("type") == "manual":
            report_manual(name, spec)
            continue
        statuses.append(install(name, spec, force=args.force, check=args.check))

    failed = statuses.count(BAD)
    heading("Summary")
    print(f"  {statuses.count(OK)} ready, {failed} need attention")

    if failed:
        print(f"\n{BAD} -- see the failures above.")
        return 1
    print(f"\n{OK} -- run `python scripts/write_mcp_config.py` to pick these up.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
