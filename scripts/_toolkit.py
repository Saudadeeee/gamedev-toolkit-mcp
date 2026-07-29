"""Shared access to toolkit.json.

Every script that needs to know which servers exist reads them through here, so
the list lives in exactly one place. See toolkit.json for the schema.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "toolkit.json"
CONFIG = ROOT / "mcp_config.json"


def load_registry() -> dict[str, Any]:
    """The parsed toolkit.json, with $comment keys left in place."""
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except OSError as error:
        raise SystemExit(f"cannot read {REGISTRY}: {error}") from error
    except ValueError as error:
        raise SystemExit(f"{REGISTRY} is not valid JSON: {error}") from error


def servers(origin: str | None = None) -> dict[str, dict]:
    """Registered servers, optionally narrowed to one origin.

    origin is "first-party" or "vendored" -- where the code came from, which is
    what decides who fixes its bugs and how an update is pulled in. It is not
    where the code lives; everything lives under servers/ now.
    """
    entries = load_registry().get("servers", {})
    if origin is None:
        return entries
    return {name: spec for name, spec in entries.items() if spec.get("origin") == origin}


def server_dir(spec: dict) -> Path | None:
    """Absolute path to a server's directory in the tree."""
    path = spec.get("path")
    return (ROOT / path) if path else None


def venv_script(directory: Path, name: str) -> Path | None:
    """A console script inside `directory/.venv`, on either platform layout.

    Returns None when it is absent, which is how callers tell "not installed"
    apart from "installed but broken".
    """
    for candidate in (directory / ".venv" / "Scripts" / f"{name}.exe",
                      directory / ".venv" / "bin" / name):
        if candidate.exists():
            return candidate
    return None


def working_venv_script(directory: Path, name: str) -> Path | None:
    """A console script that exists *and* still points at a live interpreter."""
    script = venv_script(directory, name)
    return script if script and script_is_live(script) else None


def script_interpreter(script: Path) -> str | None:
    """The interpreter path baked into a console script, if it has one.

    Both layouts embed it: a POSIX `bin/foo` as a leading shebang, a Windows
    `Scripts/foo.exe` as a `#!` line between the launcher stub and the zipped
    payload. rfind covers both without caring which.
    """
    try:
        blob = script.read_bytes()
    except OSError:
        return None
    marker = blob.rfind(b"#!")
    if marker == -1:
        return None
    end = blob.find(b"\n", marker)
    line = blob[marker + 2:end if end != -1 else len(blob)]
    return line.decode("utf-8", "replace").strip().strip('"')


def script_is_live(script: Path) -> bool:
    """Whether a console script's interpreter still exists.

    Console scripts bake in an absolute interpreter path, so moving or renaming
    the repo breaks every one of them while leaving the files in place. Testing
    for existence alone reports those as installed; this is what catches them.
    """
    interpreter = script_interpreter(script)
    if interpreter is None or not Path(interpreter).is_absolute():
        return True  # nothing to invalidate
    return Path(interpreter).exists()


def detect_applications() -> dict[str, dict]:
    """Which of Aseprite, Godot, Blockbench and Audacity are installed.

    Delegates to the aseprite server's path resolver -- the same code its tools
    use, so discovery cannot disagree with itself. It runs through `uv run`
    because that resolver imports `mcp`, which lives in the server's virtualenv
    and not in whatever interpreter is running this script.
    """
    server = ROOT / "servers" / "aseprite"
    program = (
        "import json;"
        "from aseprite_mcp.core.path_resolver import get_application_info;"
        "print(json.dumps(get_application_info(), default=str))"
    )

    uv = which("uv")
    if uv:
        try:
            proc = subprocess.run(
                [uv, "run", "python", "-c", program], cwd=server,
                capture_output=True, text=True, timeout=120,
                encoding="utf-8", errors="replace",
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return json.loads(proc.stdout.strip().splitlines()[-1])
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass

    # No uv, or it failed: try this interpreter, which works when the server was
    # installed with pip into the same environment.
    sys.path.insert(0, str(server))
    try:
        from aseprite_mcp.core.path_resolver import get_application_info
        return get_application_info()
    except ImportError:
        return {}
    finally:
        sys.path.remove(str(server))


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def speaks_mcp(port: int, endpoint: str, timeout: float = 1.5) -> bool:
    """A JSON-RPC reply proves it is an MCP server, not just an open port."""
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{endpoint}",
        data=b'{"jsonrpc":"2.0","id":1,"method":"ping"}',
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return b"jsonrpc" in response.read(512)
    except urllib.error.HTTPError as error:
        try:
            return b"jsonrpc" in error.read(512)
        except OSError:
            return False
    except (OSError, ValueError):
        return False


def resolve_bridge_port(spec: dict) -> int | None:
    """The port a bridge is actually on, preferring one that answers MCP.

    Falls back to the declared default so a config can still be written with
    the application closed.
    """
    bridge = spec.get("bridge") or {}
    default = bridge.get("port")
    candidates = bridge.get("portCandidates") or ([default] if default else [])
    endpoint = bridge.get("endpoint", "/")
    for port in candidates:
        if port_open(port) and speaks_mcp(port, endpoint):
            return port
    return default


# --------------------------------------------------------------------- #
# ANSI output, shared so every script prints the same way.

_COLOR = os.environ.get("NO_COLOR") is None


def paint(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


OK = paint("PASS", "32")
BAD = paint("FAIL", "31")
SKIP = paint("SKIP", "33")
TODO = paint("TODO", "36")


def heading(text: str) -> None:
    print(f"\n{paint(text, '1')}")


def which(program: str) -> str | None:
    """Absolute path for a program.

    Needed on Windows, where npm/npx/uv can be `.CMD` shims: shutil.which finds
    them, but subprocess without a shell cannot execute the bare name.
    """
    return shutil.which(program)
