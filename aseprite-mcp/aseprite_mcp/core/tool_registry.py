"""Where each supported creative tool lives, and how to recognise it.

One table instead of one hand-written finder per application. Adding a fifth
tool is a new entry here, not another near-copy of the previous four.

Each spec lists candidate paths per platform. Patterns may contain `*` in any
component; `%VAR%` and `~` are expanded. Steam entries are filled in from the
real library list rather than guessed, because Steam can be installed
anywhere.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class ToolSpec:
    """How to find one application and decide whether the copy found is usable."""

    key: str
    display_name: str
    # Candidate paths, in priority order, per platform.
    windows: List[str] = field(default_factory=list)
    darwin: List[str] = field(default_factory=list)
    linux: List[str] = field(default_factory=list)
    # Paths relative to <steam library>/steamapps/common/, per platform.
    steam_windows: List[str] = field(default_factory=list)
    steam_darwin: List[str] = field(default_factory=list)
    steam_linux: List[str] = field(default_factory=list)
    # Names to try on PATH.
    on_path: List[str] = field(default_factory=list)
    # Directories to sweep recursively as a last resort, per platform.
    sweep_windows: List[str] = field(default_factory=list)
    sweep_names: List[str] = field(default_factory=list)
    # Substring searched for in the Windows uninstall registry.
    registry_needle: str = ""
    registry_exe: str = ""
    # Whether `<exe> --version` prints a version and exits. GUI apps often
    # print something unrelated, or worse, open a window -- a read-only probe
    # must not launch the application it is asking about.
    supports_version_flag: bool = True
    # Optional gate on `<exe> --version` output. Return True to accept.
    version_gate: Optional[Callable[[str], bool]] = None
    # Why the gate exists, surfaced when it rejects every candidate.
    version_requirement: str = ""
    # How this tool is reached over MCP, for the health report.
    mcp_transport: str = ""
    mcp_notes: str = ""


def _is_godot_4(version: str) -> bool:
    """Godot 3 and 4 share a filename in Steam and several distro packages."""
    return version.startswith("4.")


SPECS: Dict[str, ToolSpec] = {
    "aseprite": ToolSpec(
        key="aseprite",
        display_name="Aseprite",
        windows=[
            r"C:\Program Files\Aseprite\Aseprite.exe",
            r"C:\Program Files (x86)\Aseprite\Aseprite.exe",
            r"D:\Program Files\Aseprite\Aseprite.exe",
            r"%LOCALAPPDATA%\Programs\Aseprite\Aseprite.exe",
            r"C:\Games\Aseprite*\Aseprite.exe",
            r"D:\Games\Aseprite*\Aseprite.exe",
            # Source builds sit several levels below an installer copy.
            r"C:\Games\Aseprite*\*\build\bin\aseprite.exe",
            r"D:\Games\Aseprite*\*\build\bin\aseprite.exe",
            r"D:\Apps\Aseprite\Aseprite.exe",
        ],
        darwin=[
            "/Applications/Aseprite.app/Contents/MacOS/aseprite",
            "~/Applications/Aseprite.app/Contents/MacOS/aseprite",
        ],
        linux=[
            "/usr/bin/aseprite",
            "/usr/local/bin/aseprite",
            "~/.var/app/org.aseprite.Aseprite/aseprite",
        ],
        steam_windows=[r"Aseprite\Aseprite.exe"],
        steam_darwin=["Aseprite/Aseprite.app/Contents/MacOS/aseprite"],
        steam_linux=["Aseprite/aseprite"],
        on_path=["aseprite"],
        sweep_windows=[r"C:\Games", r"D:\Games", r"C:\Aseprite", r"D:\Aseprite"],
        sweep_names=["aseprite.exe"],
        registry_needle="aseprite",
        registry_exe="Aseprite.exe",
        mcp_transport="stdio (this repo's aseprite-mcp)",
        mcp_notes="Driven by `aseprite --batch --script`; no running instance needed.",
    ),
    "godot": ToolSpec(
        key="godot",
        display_name="Godot Engine",
        windows=[
            r"C:\Program Files\Godot\Godot_v4*.exe",
            r"C:\Program Files (x86)\Godot\Godot_v4*.exe",
            r"D:\Program Files\Godot\Godot_v4*.exe",
            r"C:\Godot\Godot_v4*.exe",
            r"D:\Godot\Godot_v4*.exe",
            r"C:\Games\Godot*\Godot_v4*.exe",
            r"D:\Games\Godot*\Godot_v4*.exe",
            r"D:\Apps\Godot*\Godot_v4*.exe",
            r"%LOCALAPPDATA%\Programs\Godot\Godot_v4*.exe",
        ],
        darwin=[
            "/Applications/Godot.app/Contents/MacOS/Godot",
            "/Applications/Godot_mono.app/Contents/MacOS/Godot",
            "~/Applications/Godot.app/Contents/MacOS/Godot",
        ],
        linux=["/usr/bin/godot4", "/usr/local/bin/godot4", "~/.local/bin/godot4"],
        # Steam names the editor nothing like the official downloads do.
        steam_windows=[
            r"Godot Engine\godot.windows.opt.tools.64.exe",
            r"Godot Engine\godot.windows.opt.tools.*.exe",
            r"Godot Engine\Godot*.exe",
        ],
        steam_darwin=["Godot Engine/Godot.app/Contents/MacOS/Godot"],
        steam_linux=[
            "Godot Engine/godot.x11.opt.tools.64",
            "Godot Engine/godot.linuxbsd.opt.tools.*",
        ],
        on_path=["godot4", "godot"],
        version_gate=_is_godot_4,
        version_requirement="Godot 4.x (this toolkit does not support Godot 3)",
        mcp_transport="stdio -> WebSocket :9080 (this repo's Godot-MCP)",
        mcp_notes=(
            "Scene tools need the editor open with the godot_mcp plugin enabled. "
            "Headless tools drive the binary directly and need no editor."
        ),
    ),
    "blockbench": ToolSpec(
        key="blockbench",
        display_name="Blockbench",
        windows=[
            r"%LOCALAPPDATA%\Programs\Blockbench\Blockbench.exe",
            r"C:\Program Files\Blockbench\Blockbench.exe",
            r"C:\Program Files (x86)\Blockbench\Blockbench.exe",
            r"D:\Program Files\Blockbench\Blockbench.exe",
            r"C:\Apps\Blockbench\Blockbench.exe",
            r"D:\Apps\Blockbench\Blockbench.exe",
            r"C:\Games\Blockbench*\Blockbench.exe",
            r"D:\Games\Blockbench*\Blockbench.exe",
        ],
        darwin=[
            "/Applications/Blockbench.app/Contents/MacOS/Blockbench",
            "~/Applications/Blockbench.app/Contents/MacOS/Blockbench",
        ],
        linux=[
            "/usr/bin/blockbench",
            "/usr/local/bin/blockbench",
            "/opt/Blockbench/blockbench",
            "~/.var/app/net.blockbench.Blockbench/blockbench",
        ],
        on_path=["blockbench"],
        supports_version_flag=False,
        sweep_windows=[r"C:\Apps", r"D:\Apps", r"C:\Games", r"D:\Games"],
        sweep_names=["blockbench.exe"],
        registry_needle="blockbench",
        registry_exe="Blockbench.exe",
        mcp_transport="HTTP /bb-mcp (blockbench-mcp-plugin, runs inside Blockbench)",
        mcp_notes=(
            "Blockbench must be running with the MCP plugin installed. The server "
            "lives in the app, so nothing to launch separately. The port is a "
            "Blockbench setting (default 3000); get_blockbench_info probes for it."
        ),
    ),
    "obsidian": ToolSpec(
        key="obsidian",
        display_name="Obsidian",
        windows=[
            r"%LOCALAPPDATA%\Obsidian\Obsidian.exe",
            r"%LOCALAPPDATA%\Programs\Obsidian\Obsidian.exe",
            r"C:\Program Files\Obsidian\Obsidian.exe",
            r"D:\Apps\Obsidian\Obsidian.exe",
        ],
        darwin=[
            "/Applications/Obsidian.app/Contents/MacOS/Obsidian",
            "~/Applications/Obsidian.app/Contents/MacOS/Obsidian",
        ],
        linux=[
            "/usr/bin/obsidian",
            "/opt/Obsidian/obsidian",
            "~/.var/app/md.obsidian.Obsidian/obsidian",
        ],
        on_path=["obsidian"],
        supports_version_flag=False,
        registry_needle="obsidian",
        registry_exe="Obsidian.exe",
        mcp_transport="stdio -> Obsidian Local REST API (mcp-obsidian)",
        mcp_notes=(
            "Obsidian must be running with the Local REST API community plugin "
            "enabled. OBSIDIAN_API_KEY comes from that plugin's settings; the "
            "default endpoint is https://127.0.0.1:27124."
        ),
    ),
    "audacity": ToolSpec(
        key="audacity",
        display_name="Audacity",
        windows=[
            r"C:\Program Files\Audacity\Audacity.exe",
            r"C:\Program Files (x86)\Audacity\Audacity.exe",
            r"D:\Program Files\Audacity\Audacity.exe",
            r"%LOCALAPPDATA%\Programs\Audacity\Audacity.exe",
            r"C:\Apps\Audacity\Audacity.exe",
            r"D:\Apps\Audacity\Audacity.exe",
        ],
        darwin=[
            "/Applications/Audacity.app/Contents/MacOS/Audacity",
            "~/Applications/Audacity.app/Contents/MacOS/Audacity",
        ],
        linux=[
            "/usr/bin/audacity",
            "/usr/local/bin/audacity",
            "~/.var/app/org.audacityteam.Audacity/audacity",
        ],
        on_path=["audacity"],
        supports_version_flag=False,
        registry_needle="audacity",
        registry_exe="Audacity.exe",
        mcp_transport="stdio -> mod-script-pipe named pipe (Audacity-MCP)",
        mcp_notes=(
            "Audacity must be running with mod-script-pipe enabled "
            "(Preferences > Modules). Audacity 3.x only."
        ),
    ),
}

TOOL_KEYS = list(SPECS)


def get_spec(key: str) -> Optional[ToolSpec]:
    """Look a spec up by key, accepting a few common aliases."""
    normalized = key.lower().strip().removesuffix(".exe").removesuffix(".app")
    aliases = {
        "godot4": "godot",
        "godot-engine": "godot",
        "godot_engine": "godot",
        "aseprite-mcp": "aseprite",
        "bb": "blockbench",
        "block-bench": "blockbench",
    }
    return SPECS.get(aliases.get(normalized, normalized))
