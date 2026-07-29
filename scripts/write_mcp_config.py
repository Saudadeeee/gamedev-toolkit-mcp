"""Generate mcp_config.json for every server in toolkit.json.

Resolves each server's client entry against this machine: absolute repo paths,
the console script inside each virtualenv, detected application paths, and the
port a live bridge is actually on.

    python scripts/write_mcp_config.py              # write mcp_config.json
    python scripts/write_mcp_config.py --print      # to stdout, write nothing
    python scripts/write_mcp_config.py --out PATH   # somewhere else

Secrets already present in mcp_config.json are carried over rather than reset
to their placeholder, so re-running this after an install does not undo
scripts/configure_obsidian.py. mcp_config.json holds absolute local paths and
API keys and is gitignored -- never commit it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _toolkit import (BAD, CONFIG, OK, ROOT, SKIP, detect_applications, heading,
                      load_registry, paint, resolve_bridge_port, server_dir, which,
                      working_venv_script)


def application_paths() -> dict[str, str]:
    """Absolute paths for the applications that were found, keyed by app id.

    This is what a client entry's {app:KEY} placeholder resolves against.
    """
    return {key: str(entry["path"])
            for key, entry in detect_applications().items()
            if entry.get("found") and entry.get("path")}


def previous_env(config_path: Path) -> dict[str, dict[str, str]]:
    """Env values from an existing config, so real secrets survive a rewrite."""
    if not config_path.exists():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {name: (spec.get("env") or {})
            for name, spec in (data.get("mcpServers") or {}).items()}


def substitute(value: str, *, path: Path | None, apps: dict[str, str],
               port: int | None, directory: Path | None) -> str | None:
    """Expand one placeholder. None means it could not be resolved."""
    if "{path}" in value:
        if path is None:
            return None
        value = value.replace("{path}", path.as_posix())

    if "{port}" in value:
        if port is None:
            return None
        value = value.replace("{port}", str(port))

    if value.startswith("{venvScript:") and value.endswith("}"):
        if directory is None:
            return None
        script = working_venv_script(directory, value[len("{venvScript:"):-1])
        return script.as_posix() if script else None

    if value.startswith("{app:") and value.endswith("}"):
        return apps.get(value[len("{app:"):-1])

    return value


def build_entry(name: str, spec: dict, apps: dict[str, str],
                carried: dict[str, str]) -> tuple[dict | None, str]:
    """The mcp client entry for one server, plus a one-line explanation."""
    directory = server_dir(spec)
    port = resolve_bridge_port(spec)

    client = spec.get("client") or {}
    # Fall back to the non-uv client when uv is unavailable; only the aseprite
    # server declares one, and only because `python -m` needs a cwd to work.
    if spec.get("fallbackClient") and client.get("command") == "uv" and which("uv") is None:
        client = spec["fallbackClient"]

    def expand(value: str) -> str | None:
        return substitute(value, path=directory, apps=apps, port=port, directory=directory)

    command = expand(client.get("command", ""))
    if not command:
        if spec.get("origin") == "vendored":
            return None, "not installed -- run scripts/install_vendored.py"
        return None, "could not resolve its command"

    args = []
    for raw in client.get("args", []):
        expanded = expand(raw)
        if expanded is None:
            return None, f"could not resolve {raw}"
        args.append(expanded)

    entry: dict = {"command": command, "args": args}

    if client.get("cwd"):
        resolved_cwd = expand(client["cwd"])
        if resolved_cwd:
            entry["cwd"] = resolved_cwd

    env = {}
    unresolved = []
    for key, raw in (client.get("env") or {}).items():
        # An existing real value always wins: it is either a secret the user
        # pasted in or a path they corrected by hand.
        if carried.get(key) and "REPLACE" not in carried[key]:
            env[key] = carried[key]
            continue
        expanded = expand(raw)
        if expanded is None:
            unresolved.append(key)
            env[key] = raw if "REPLACE" in raw else f"REPLACE_WITH_{key}"
        else:
            env[key] = expanded
    if env:
        entry["env"] = env

    if unresolved:
        return entry, f"written, but set {', '.join(unresolved)} by hand"
    return entry, ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=CONFIG, help="output path")
    parser.add_argument("--print", dest="to_stdout", action="store_true",
                        help="print the config instead of writing it")
    args = parser.parse_args()

    print(paint("Generating MCP client config", "1"))
    print(f"repo: {ROOT}")

    apps = application_paths()
    carried_all = previous_env(args.out)

    heading("Servers")
    entries: dict[str, dict] = {}
    skipped = 0
    for name, spec in load_registry().get("servers", {}).items():
        entry, note = build_entry(name, spec, apps, carried_all.get(name, {}))
        if entry is None:
            print(f"  {SKIP}  {name}  --  {note}")
            skipped += 1
            continue
        entries[name] = entry
        print(f"  {OK}  {name}" + (f"  --  {note}" if note else ""))

    document = json.dumps({"mcpServers": entries}, indent=2) + "\n"

    if args.to_stdout:
        print()
        print(document, end="")
        return 0

    try:
        args.out.write_text(document, encoding="utf-8")
    except OSError as error:
        print(f"\n{BAD} could not write {args.out}: {error}")
        return 1

    heading("Summary")
    print(f"  {len(entries)} configured, {skipped} skipped")
    print(f"  written to {args.out}")
    print("\n  This file holds absolute paths and API keys. It is gitignored -- keep it that way.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
