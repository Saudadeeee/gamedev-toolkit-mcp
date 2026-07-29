"""Auto-detect executable paths for every tool in the kit.

Used as the fallback when ASEPRITE_PATH / GODOT_PATH / BLOCKBENCH_PATH /
AUDACITY_PATH are unset or point at a file that no longer exists. Detection is
best-effort: a miss returns None and the caller reports a clear error rather
than crashing.

Where each tool lives is data, not code -- see core/tool_registry.py.
"""

import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .tool_registry import SPECS, TOOL_KEYS, ToolSpec, get_spec

# Depth cap for the recursive fallback sweep. Aseprite source builds land at
# <root>/aseprite/build/bin/aseprite.exe, which is 4 levels below the search
# root, so anything shallower would miss them.
_MAX_SWEEP_DEPTH = 5

_VERSION_TIMEOUT = 5


def _glob(pattern: str) -> List[Path]:
    """Expand a path pattern that may contain `*` in any component.

    `Path(pattern).parent.glob(...)` — the obvious approach — silently returns
    nothing when the wildcard sits in a directory component, because the parent
    itself is then a non-existent literal path. Splitting the pattern at the
    first wildcard segment and globbing the remainder handles both cases.
    """
    path = Path(pattern)
    parts = path.parts
    if not parts:
        return []

    wildcard_at = next((i for i, part in enumerate(parts) if "*" in part), None)
    if wildcard_at is None:
        return [path] if path.exists() else []

    root = Path(*parts[:wildcard_at]) if wildcard_at else Path(parts[0])
    remainder = str(Path(*parts[wildcard_at:]))

    try:
        if not root.exists():
            return []
        return sorted(root.glob(remainder))
    except (OSError, ValueError):
        return []


def _first_existing(candidates: Iterable[str]) -> Optional[str]:
    """Return the first candidate that resolves, expanding wildcards."""
    for candidate in candidates:
        expanded = os.path.expandvars(os.path.expanduser(candidate))
        if "*" in expanded:
            matches = _glob(expanded)
            if matches:
                # Newest wins, so a machine with several installed versions
                # gets the one most recently put there.
                return str(max(matches, key=lambda p: p.stat().st_mtime))
        elif os.path.exists(expanded):
            return expanded
    return None


def _steam_registry_roots() -> List[str]:
    """Steam client folders recorded in the Windows registry."""
    roots: List[str] = []
    if platform.system() != "Windows":
        return roots

    try:
        import winreg
    except ImportError:
        return roots

    for hive, path in (
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
    ):
        try:
            with winreg.OpenKey(hive, path) as key:
                for value in ("SteamPath", "InstallPath"):
                    try:
                        found = winreg.QueryValueEx(key, value)[0]
                    except OSError:
                        continue
                    if found and os.path.isdir(found):
                        roots.append(os.path.normpath(found))
        except OSError:
            continue
    return roots


def _steam_libraries() -> List[str]:
    """Every Steam library folder on this machine.

    Guessing at `C:\\Program Files (x86)\\Steam` and a couple of other
    hard-coded spots misses any non-default install — Steam lets you put the
    client anywhere and add libraries on other drives. The registry knows
    where the client is, and libraryfolders.vdf lists the rest.
    """
    roots: List[str] = list(_steam_registry_roots())

    roots.extend(
        os.path.expanduser(p)
        for p in (
            "~/.local/share/Steam",
            "~/.steam/steam",
            "~/Library/Application Support/Steam",
        )
    )

    # Additional libraries are listed in the client's own config.
    libraries: List[str] = []
    # The registry hands back the same folder in different casings
    # ("d:/games/steam" and "D:\\Games\\Steam"), which would otherwise make
    # every lookup run twice.
    seen: set = set()

    def remember(path: str) -> None:
        if not os.path.isdir(path):
            return
        key = os.path.normcase(os.path.abspath(path))
        if key in seen:
            return
        seen.add(key)
        libraries.append(path)

    for root in roots:
        remember(root)

        vdf = os.path.join(root, "steamapps", "libraryfolders.vdf")
        if not os.path.isfile(vdf):
            continue
        try:
            with open(vdf, encoding="utf-8", errors="replace") as handle:
                contents = handle.read()
        except OSError:
            continue
        for match in re.finditer(r'"path"\s+"([^"]+)"', contents):
            remember(os.path.normpath(match.group(1).replace("\\\\", "\\")))

    return libraries


def _steam_app_candidates(*relative_paths: str) -> List[str]:
    """Expand app-relative paths against every Steam library."""
    return [
        os.path.join(library, "steamapps", "common", relative)
        for library in _steam_libraries()
        for relative in relative_paths
    ]


def _windows_file_version(exe_path: str) -> Optional[str]:
    """Version from a Windows executable's own resource block.

    Costs nothing and cannot start the program, unlike shelling out to
    `--version`. Returns None on any other platform or when the file carries
    no version resource.
    """
    if platform.system() != "Windows":
        return None

    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return None

    try:
        version_dll = ctypes.WinDLL("version", use_last_error=True)
        size = version_dll.GetFileVersionInfoSizeW(exe_path, None)
        if not size:
            return None

        buffer = ctypes.create_string_buffer(size)
        if not version_dll.GetFileVersionInfoW(exe_path, 0, size, buffer):
            return None

        block = ctypes.c_void_p()
        length = wintypes.UINT()
        if not version_dll.VerQueryValueW(
            buffer, "\\", ctypes.byref(block), ctypes.byref(length)
        ):
            return None

        class FixedFileInfo(ctypes.Structure):
            _fields_ = [
                ("dwSignature", wintypes.DWORD),
                ("dwStrucVersion", wintypes.DWORD),
                ("dwFileVersionMS", wintypes.DWORD),
                ("dwFileVersionLS", wintypes.DWORD),
                ("dwProductVersionMS", wintypes.DWORD),
                ("dwProductVersionLS", wintypes.DWORD),
            ]

        info = ctypes.cast(block, ctypes.POINTER(FixedFileInfo)).contents
        parts = (
            info.dwProductVersionMS >> 16,
            info.dwProductVersionMS & 0xFFFF,
            info.dwProductVersionLS >> 16,
            info.dwProductVersionLS & 0xFFFF,
        )
        if not any(parts):
            return None
        # Trailing zeros are padding in the resource, not meaningful digits.
        while len(parts) > 2 and parts[-1] == 0:
            parts = parts[:-1]
        return ".".join(str(p) for p in parts)
    except (OSError, ValueError, AttributeError):
        return None


def _sweep(roots: Iterable[str], exe_names: Iterable[str]) -> Optional[str]:
    """Bounded recursive search for any of `exe_names` under `roots`."""
    wanted = {name.lower() for name in exe_names}
    for root in roots:
        if not os.path.isdir(root):
            continue
        root_depth = root.rstrip(os.sep).count(os.sep)
        for current, dirs, files in os.walk(root):
            # Prune instead of breaking: `break` on a deep directory would
            # abandon the entire sweep, including shallow branches not yet
            # visited.
            if current.count(os.sep) - root_depth >= _MAX_SWEEP_DEPTH:
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for name in files:
                if name.lower() in wanted:
                    return os.path.join(current, name)
    return None


class PathResolver:
    """Locate the creative tools this kit drives."""

    def __init__(self):
        self.platform = platform.system()
        self._cache: Dict[str, Optional[str]] = {}

    # ------------------------------------------------------------------ #
    # Generic lookup
    # ------------------------------------------------------------------ #

    def _candidates(self, spec: ToolSpec) -> List[str]:
        """Every path worth trying for this tool on this platform, in order."""
        if self.platform == "Windows":
            direct, steam = spec.windows, spec.steam_windows
        elif self.platform == "Darwin":
            direct, steam = spec.darwin, spec.steam_darwin
        else:
            direct, steam = spec.linux, spec.steam_linux

        return [*direct, *_steam_app_candidates(*steam)] if steam else list(direct)

    def find(self, key: str) -> Optional[str]:
        """Locate one tool by registry key, or None."""
        spec = get_spec(key)
        if spec is None:
            return None
        if spec.key in self._cache:
            return self._cache[spec.key]

        result = self._first_acceptable(spec, self._candidates(spec))

        if not result:
            for name in spec.on_path:
                exe = f"{name}.exe" if self.platform == "Windows" else name
                found = self._which(exe) or self._which(name)
                if found and self._version_ok(spec, found):
                    result = found
                    break

        if not result and self.platform == "Windows" and spec.registry_needle:
            found = self._from_uninstall_registry(spec.registry_needle, spec.registry_exe)
            if found and self._version_ok(spec, found):
                result = found

        if not result and self.platform == "Windows" and spec.sweep_windows:
            found = _sweep(spec.sweep_windows, spec.sweep_names)
            if found and self._version_ok(spec, found):
                result = found

        self._cache[spec.key] = result
        return result

    def _version_ok(self, spec: ToolSpec, exe_path: str) -> bool:
        """Apply the spec's version gate, if it has one."""
        if spec.version_gate is None:
            return True
        version = self.get_version(exe_path, spec)
        # An unreadable version is not proof of the wrong major release;
        # rejecting on it would lose working installs on locked-down machines.
        return version is None or spec.version_gate(version)

    def _first_acceptable(self, spec: ToolSpec, candidates: Iterable[str]) -> Optional[str]:
        """First candidate that resolves and passes the version gate.

        Steam and several distro packages use one filename across major
        versions, so the path alone cannot decide. A rejected candidate is
        dropped and the search continues rather than giving up.
        """
        remaining = list(candidates)
        while remaining:
            found = _first_existing(remaining)
            if not found:
                return None
            if self._version_ok(spec, found):
                return found
            remaining = [c for c in remaining if _first_existing([c]) != found]
        return None

    # ------------------------------------------------------------------ #
    # Named accessors, kept for readability at call sites
    # ------------------------------------------------------------------ #

    def find_aseprite(self) -> Optional[str]:
        """Locate the Aseprite executable, or None."""
        return self.find("aseprite")

    def find_godot(self) -> Optional[str]:
        """Locate a Godot 4.x executable, or None."""
        return self.find("godot")

    def find_godot4(self) -> Optional[str]:
        """Alias of :meth:`find_godot`."""
        return self.find("godot")

    def find_blockbench(self) -> Optional[str]:
        """Locate the Blockbench executable, or None."""
        return self.find("blockbench")

    def find_audacity(self) -> Optional[str]:
        """Locate the Audacity executable, or None."""
        return self.find("audacity")

    def find_obsidian(self) -> Optional[str]:
        """Locate the Obsidian executable, or None."""
        return self.find("obsidian")

    def get_all_paths(self) -> Dict[str, Optional[str]]:
        """Detected paths for every tool in the registry."""
        return {key: self.find(key) for key in TOOL_KEYS}

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _which(self, name: str) -> Optional[str]:
        """Find an executable on PATH."""
        try:
            result = subprocess.run(
                ["where", name] if self.platform == "Windows" else ["which", name],
                capture_output=True,
                text=True,
                timeout=_VERSION_TIMEOUT,
            )
            if result.returncode == 0:
                first = result.stdout.strip().splitlines()
                if first and os.path.exists(first[0]):
                    return first[0]
        except (OSError, subprocess.SubprocessError):
            pass
        return None

    def _from_uninstall_registry(self, needle: str, exe_name: str) -> Optional[str]:
        """Look the program up in the Windows uninstall registry."""
        if self.platform != "Windows" or not exe_name:
            return None
        try:
            import winreg
        except ImportError:
            return None

        subpath = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        for hive, access in (
            (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_READ | winreg.KEY_WOW64_64KEY),
            (winreg.HKEY_CURRENT_USER, winreg.KEY_READ),
        ):
            try:
                with winreg.OpenKey(hive, subpath, 0, access) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            name = winreg.EnumKey(key, i)
                        except OSError:
                            continue
                        if needle not in name.lower():
                            continue
                        try:
                            with winreg.OpenKey(key, name) as sub:
                                location = winreg.QueryValueEx(sub, "InstallLocation")[0]
                        except OSError:
                            continue
                        if location:
                            candidate = os.path.join(location, exe_name)
                            if os.path.exists(candidate):
                                return candidate
            except OSError:
                continue
        return None

    def get_version(self, exe_path: str, spec: Optional[ToolSpec] = None) -> Optional[str]:
        """Version of an executable.

        File metadata is preferred on Windows because it is free and cannot
        have side effects. `--version` is only run for tools that declare they
        support it: on a GUI application it either prints something unrelated
        (Audacity answers "Obtaining pipe", Blockbench reports its bundled Node
        version) or opens a window, which a read-only probe must never do.
        """
        if not exe_path or not os.path.exists(exe_path):
            return None

        if self.platform == "Windows":
            from_file = _windows_file_version(exe_path)
            if from_file:
                return from_file

        if spec is not None and not spec.supports_version_flag:
            return None

        try:
            result = subprocess.run(
                [exe_path, "--version"],
                capture_output=True,
                text=True,
                timeout=_VERSION_TIMEOUT,
            )
        except (OSError, subprocess.SubprocessError):
            return None

        output = (result.stdout or "").strip() or (result.stderr or "").strip()
        return output.splitlines()[0] if output else None


# Singleton -- the cache is what keeps repeated lookups off the filesystem.
_resolver = PathResolver()

# Environment variable consulted before auto-detection, per tool.
_ENV_OVERRIDES = {
    "aseprite": "ASEPRITE_PATH",
    "godot": "GODOT_PATH",
    "blockbench": "BLOCKBENCH_PATH",
    "audacity": "AUDACITY_PATH",
    "obsidian": "OBSIDIAN_PATH",
}


def get_tool_path(key: str) -> Optional[str]:
    """Path for one tool: its env override if that resolves, else detection."""
    spec = get_spec(key)
    if spec is None:
        return None

    env_name = _ENV_OVERRIDES.get(spec.key)
    if env_name:
        env_path = os.environ.get(env_name)
        # A stale override is skipped rather than raised: it usually means the
        # app moved, and detection can still find it.
        if env_path and os.path.exists(env_path):
            return env_path
    return _resolver.find(spec.key)


def get_aseprite_path() -> Optional[str]:
    """Aseprite path: ASEPRITE_PATH if it resolves, else auto-detection."""
    return get_tool_path("aseprite")


def get_godot_path() -> Optional[str]:
    """Godot path: GODOT_PATH if it resolves, else auto-detection."""
    return get_tool_path("godot")


def get_blockbench_path() -> Optional[str]:
    """Blockbench path: BLOCKBENCH_PATH if it resolves, else auto-detection."""
    return get_tool_path("blockbench")


def get_audacity_path() -> Optional[str]:
    """Audacity path: AUDACITY_PATH if it resolves, else auto-detection."""
    return get_tool_path("audacity")


def get_obsidian_path() -> Optional[str]:
    """Obsidian path: OBSIDIAN_PATH if it resolves, else auto-detection."""
    return get_tool_path("obsidian")


def get_application_info() -> Dict[str, Dict[str, str]]:
    """Path, version and found-state for every tool in the registry."""
    info: Dict[str, Dict[str, str]] = {}
    for key, spec in SPECS.items():
        path = get_tool_path(key)
        if path and os.path.exists(path):
            info[key] = {
                "name": spec.display_name,
                "path": path,
                "version": _resolver.get_version(path, spec) or "unknown",
                "found": True,
                "env_var": _ENV_OVERRIDES.get(key, ""),
                "mcp_transport": spec.mcp_transport,
                "notes": spec.mcp_notes,
            }
        else:
            info[key] = {
                "name": spec.display_name,
                "path": "Not found",
                "version": "N/A",
                "found": False,
                "env_var": _ENV_OVERRIDES.get(key, ""),
                "mcp_transport": spec.mcp_transport,
                "notes": spec.version_requirement or spec.mcp_notes,
            }
    return info


