"""Environment discovery for the whole toolkit.

The kit drives four applications through three different MCP servers and two
different transports. When something does not respond, the first question is
always "is it installed, and is it reachable the way this server expects" —
these tools answer that without guessing.
"""

import json
import os
import platform
import socket
import sys
import urllib.error
import urllib.request

from ..core.path_resolver import (
    _resolver,
    get_application_info,
    get_tool_path,
)
from ..core.tool_registry import SPECS, TOOL_KEYS, get_spec
from .. import mcp

# Where each MCP server for a tool listens, when it listens at all.
_BLOCKBENCH_DEFAULT_ENDPOINT = "/bb-mcp"
# The plugin reads its port from a Blockbench setting, so the documented
# default is only a first guess. 3456 is the other value seen in the wild.
_BLOCKBENCH_PORT_CANDIDATES = (3000, 3456, 3001, 8080)
_GODOT_BRIDGE_PORT = 9080

# Audacity's mod-script-pipe endpoints. Named pipes on Windows, FIFOs elsewhere.
_AUDACITY_PIPES = {
    "Windows": (r"\\.\pipe\ToSrvPipe", r"\\.\pipe\FromSrvPipe"),
    "Darwin": ("/tmp/audacity_script_pipe.to.{uid}", "/tmp/audacity_script_pipe.from.{uid}"),
    "Linux": ("/tmp/audacity_script_pipe.to.{uid}", "/tmp/audacity_script_pipe.from.{uid}"),
}


def _port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.4) -> bool:
    """Whether something is listening locally on a port."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _windows_pipe_present(name: str) -> bool:
    """Whether a Win32 named pipe exists.

    `os.path.exists` and `os.listdir` both under-report here: Windows does not
    reliably enumerate the named-pipe namespace through FindFirstFile, so a
    live pipe can look absent. WaitNamedPipe asks the object manager directly,
    and its error code distinguishes "not there" from "there but busy".
    """
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.WaitNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
    kernel32.WaitNamedPipeW.restype = wintypes.BOOL

    if kernel32.WaitNamedPipeW(name, 200):
        return True

    error_sem_timeout, error_pipe_busy = 121, 231
    # Busy means every instance is taken -- the pipe is there, which is what
    # this check is about.
    return ctypes.get_last_error() in (error_sem_timeout, error_pipe_busy)


def _audacity_pipe_state() -> dict:
    """Whether Audacity's scripting pipes exist right now.

    The pipes are created by a *running* Audacity that has mod-script-pipe
    enabled. Their absence is the single most common reason an Audacity MCP
    call fails, and it is invisible from the tool's own error message.
    """
    system = platform.system()
    names = _AUDACITY_PIPES.get(system)
    if not names:
        return {"supported": False, "reason": f"Unknown platform: {system}"}

    if system == "Windows":
        to_pipe, from_pipe = names
        exists = _windows_pipe_present(to_pipe) and _windows_pipe_present(from_pipe)
    else:
        uid = os.getuid() if hasattr(os, "getuid") else 0
        to_pipe = names[0].format(uid=uid)
        from_pipe = names[1].format(uid=uid)
        exists = os.path.exists(to_pipe) and os.path.exists(from_pipe)

    return {
        "supported": True,
        "to_pipe": to_pipe,
        "from_pipe": from_pipe,
        "ready": exists,
        "reason": None
        if exists
        else (
            "Pipes not present. Audacity must be running with mod-script-pipe "
            "enabled: Edit > Preferences > Modules > mod-script-pipe = Enabled, "
            "then restart Audacity. Audacity 3.x only."
        ),
    }


def _speaks_mcp(port: int, endpoint: str, timeout: float = 1.5) -> bool:
    """Whether an MCP server answers at this port and endpoint.

    An open port is not proof: the plugin's port is a Blockbench setting, so
    whatever else the user runs could hold it. A POST without a session header
    gets a JSON-RPC error from the real server, which is enough to identify it
    without opening a session.
    """
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}{endpoint}",
            data=b'{"jsonrpc":"2.0","id":1,"method":"ping"}',
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return b"jsonrpc" in response.read(512)
    except urllib.error.HTTPError as error:
        # 400 "Mcp-Session-Id header is required" is the server identifying
        # itself; anything with a JSON-RPC envelope counts.
        try:
            return b"jsonrpc" in error.read(512)
        except OSError:
            return False
    except (OSError, ValueError):
        return False


def _blockbench_state() -> dict:
    """Whether the Blockbench MCP plugin is serving, and on which port.

    The port is a Blockbench setting, not a constant -- the plugin reads
    `Settings.get("mcp_port")`. Probing only the documented default reports a
    perfectly healthy install as down, so the candidates are searched.
    """
    endpoint = os.environ.get("BLOCKBENCH_MCP_ENDPOINT", _BLOCKBENCH_DEFAULT_ENDPOINT)

    candidates: list[int] = []
    override = os.environ.get("BLOCKBENCH_MCP_PORT")
    if override and override.isdigit():
        candidates.append(int(override))
    candidates.extend(p for p in _BLOCKBENCH_PORT_CANDIDATES if p not in candidates)

    for port in candidates:
        if _port_open(port) and _speaks_mcp(port, endpoint):
            return {
                "port": port,
                "endpoint": endpoint,
                "url": f"http://localhost:{port}{endpoint}",
                "ready": True,
                "reason": None,
            }

    return {
        "port": None,
        "endpoint": endpoint,
        "searched_ports": candidates,
        "ready": False,
        "reason": (
            f"No MCP server answered on ports {candidates} at {endpoint}. Blockbench "
            "must be running with the MCP plugin installed (File > Plugins > Load "
            "from URL: https://jasonjgardner.github.io/blockbench-mcp-plugin/mcp.js) "
            "and the network permission granted. If it uses a different port, check "
            "the plugin's settings and set BLOCKBENCH_MCP_PORT."
        ),
    }


def _godot_bridge_state() -> dict:
    """Whether the Godot editor plugin's WebSocket bridge is up."""
    listening = _port_open(_GODOT_BRIDGE_PORT)
    return {
        "port": _GODOT_BRIDGE_PORT,
        "ready": listening,
        "reason": None
        if listening
        else (
            f"Nothing listening on port {_GODOT_BRIDGE_PORT}. Scene tools need the Godot "
            "editor open with the godot_mcp plugin enabled. Headless tools work without it."
        ),
    }


@mcp.tool()
async def get_app_info() -> str:
    """Report every creative tool in the kit: path, version, and how it is reached.

    Start here when a tool in any of the MCP servers is not responding.
    """
    info = get_application_info()

    lines = ["=== Toolkit applications ==="]
    for key in TOOL_KEYS:
        entry = info[key]
        mark = "OK " if entry["found"] else "-- "
        lines.append(f"{mark} {entry['name']}")
        lines.append(f"      path      : {entry['path']}")
        lines.append(f"      version   : {entry['version']}")
        lines.append(f"      transport : {entry['mcp_transport']}")
        if entry["notes"]:
            lines.append(f"      note      : {entry['notes']}")
        if not entry["found"] and entry["env_var"]:
            lines.append(f"      override  : set {entry['env_var']} to the executable")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def get_toolkit_status() -> str:
    """Full readiness report: what is installed AND what is currently reachable.

    Installation and reachability are different questions. Blockbench and
    Audacity both need to be *running* — with a plugin and a module enabled
    respectively — before their MCP servers answer anything. Returns JSON.
    """
    info = get_application_info()
    report = {
        "system": {
            "platform": f"{platform.system()} {platform.release()}",
            "python": sys.version.split()[0],
            "architecture": platform.machine(),
        },
        "applications": info,
        "bridges": {
            "godot_editor": _godot_bridge_state(),
            "blockbench_plugin": _blockbench_state(),
            "audacity_pipe": _audacity_pipe_state(),
        },
    }

    blockers = []
    for key, entry in info.items():
        if not entry["found"]:
            blockers.append(f"{entry['name']} not installed or not found")
    for name, state in report["bridges"].items():
        if state.get("reason"):
            blockers.append(f"{name}: {state['reason']}")

    report["ready"] = not blockers
    report["blockers"] = blockers
    return json.dumps(report, indent=2)


@mcp.tool()
async def get_aseprite_info() -> str:
    """Aseprite executable path and version."""
    return _tool_report("aseprite")


@mcp.tool()
async def get_godot_info() -> str:
    """Godot executable path and version, plus whether the editor bridge is up."""
    base = _tool_report("godot")
    bridge = _godot_bridge_state()
    status = "reachable" if bridge["ready"] else "not reachable"
    extra = f"\nEditor bridge (port {bridge['port']}): {status}"
    if bridge["reason"]:
        extra += f"\n  {bridge['reason']}"
    return base + extra


@mcp.tool()
async def get_blockbench_info() -> str:
    """Blockbench path and version, plus whether its MCP plugin is serving."""
    base = _tool_report("blockbench")
    state = _blockbench_state()
    status = "serving" if state["ready"] else "not serving"
    extra = f"\nMCP plugin ({state['url']}): {status}"
    if state["reason"]:
        extra += f"\n  {state['reason']}"
    return base + extra


@mcp.tool()
async def get_audacity_info() -> str:
    """Audacity path and version, plus whether mod-script-pipe is available."""
    base = _tool_report("audacity")
    state = _audacity_pipe_state()
    if not state["supported"]:
        return base + f"\nScripting pipe: {state['reason']}"
    status = "ready" if state["ready"] else "not ready"
    extra = f"\nmod-script-pipe: {status}\n  to  : {state['to_pipe']}\n  from: {state['from_pipe']}"
    if state["reason"]:
        extra += f"\n  {state['reason']}"
    return base + extra


@mcp.tool()
async def get_system_info() -> str:
    """Platform, Python version, and the toolkit's environment variables."""
    lines = [
        "=== System ===",
        f"Platform     : {platform.system()} {platform.release()}",
        f"Python       : {sys.version.split()[0]}",
        f"Architecture : {platform.machine()}",
        "",
        "=== Environment overrides ===",
    ]
    for key in TOOL_KEYS:
        spec = SPECS[key]
        env_name = f"{key.upper()}_PATH"
        value = os.environ.get(env_name)
        if value:
            state = "exists" if os.path.exists(value) else "MISSING - will be ignored"
            lines.append(f"{env_name:<16} = {value}  ({state})")
        else:
            lines.append(f"{env_name:<16} = (not set, using auto-detection)")
        del spec
    return "\n".join(lines)


@mcp.tool()
async def resolve_application_path(application: str) -> str:
    """Resolve one application to its executable path.

    Args:
        application: "aseprite", "godot", "blockbench" or "audacity"
    """
    spec = get_spec(application)
    if spec is None:
        return (
            f"Unknown application: {application}. "
            f"Supported: {', '.join(TOOL_KEYS)}"
        )
    return _tool_report(spec.key)


def _tool_report(key: str) -> str:
    """Human-readable path/version block for one tool."""
    spec = SPECS[key]
    path = get_tool_path(key)

    if path and os.path.exists(path):
        version = _resolver.get_version(path, spec) or "unknown"
        return (
            f"=== {spec.display_name} ===\n"
            f"Path      : {path}\n"
            f"Version   : {version}\n"
            f"Transport : {spec.mcp_transport}"
        )

    hint = spec.version_requirement or spec.mcp_notes
    return (
        f"=== {spec.display_name} ===\n"
        f"Not found.\n"
        f"Set {key.upper()}_PATH to the executable, or install it where the "
        f"resolver looks (Program Files, Steam libraries, /Applications, $PATH).\n"
        + (f"Requirement: {hint}" if hint else "")
    )
