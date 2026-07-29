"""Probing an MCP server and the application bridges behind them.

Split out of verify_toolkit.py so the fiddly parts -- speaking MCP over stdio,
and the Win32 named-pipe check -- stay readable on their own.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import threading
from pathlib import Path

from _toolkit import which


def windows_pipe_present(name: str) -> bool:
    """Whether a Win32 named pipe exists.

    os.path.exists under-reports here: Windows does not reliably enumerate the
    named-pipe namespace, so a live pipe can look absent. WaitNamedPipe asks the
    object manager directly.
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


def mcp_handshake(command: list[str], cwd: Path, env: dict | None = None,
                  timeout: int = 90, probe_tool: str | None = None) -> tuple[bool, int, str]:
    """Speak MCP over stdio and return (ok, tool_count, message).

    Responses are read as they arrive and the process is killed once the answers
    are in. An MCP server is not supposed to exit when stdin closes -- waiting
    for it to would hang until the timeout on every healthy server.

    probe_tool names a read-only tool to call afterwards. A server can list tools
    perfectly while the application behind it is unreachable, so for those
    servers listing alone is not evidence the chain works. On success the message
    reports the probe; on failure it says what broke.
    """
    resolved = which(command[0]) or (command[0] if Path(command[0]).exists() else None)
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
            [str(resolved), *command[1:]], cwd=cwd,
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
