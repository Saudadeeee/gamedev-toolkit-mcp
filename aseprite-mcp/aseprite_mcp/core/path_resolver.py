"""Auto-detect application paths for Godot and Aseprite."""

import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import Optional, Dict


class PathResolver:
    """Auto-detect paths for game development tools."""

    def __init__(self):
        self.platform = platform.system()
        self._cache: Dict[str, Optional[str]] = {}

    def get_all_paths(self) -> Dict[str, str]:
        """Get all detected tool paths."""
        return {
            "aseprite": self.find_aseprite(),
            "godot": self.find_godot(),
            "godot4": self.find_godot4(),
        }

    def find_aseprite(self) -> Optional[str]:
        """Find Aseprite executable path."""
        if "aseprite" in self._cache:
            return self._cache["aseprite"]

        exe_name = "Aseprite.exe" if self.platform == "Windows" else "aseprite"
        result = None

        if self.platform == "Windows":
            # Check common locations
            candidates = [
                r"C:\Program Files\Aseprite\Aseprite.exe",
                r"C:\Program Files (x86)\Steam\steamapps\common\Aseprite\Aseprite.exe",
                r"D:\Program Files\Aseprite\Aseprite.exe",
                r"D:\Games\Aseprite*\Aseprite.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Aseprite\Aseprite.exe"),
            ]

            # Check direct paths
            for path in candidates:
                if "*" in path:
                    # Glob for wildcard - match full pattern
                    parent_dir = Path(path).parent
                    pattern = path.split("\\")[-1].replace("*", ".*")
                    if parent_dir.exists():
                        for exe in parent_dir.glob("Aseprite.exe"):
                            result = str(exe)
                            break
                        if result:
                            break
                elif os.path.exists(path):
                    result = path
                    break

            # If still not found, search D:\Games more broadly
            if not result and os.path.exists("D:\\Games"):
                for root, dirs, files in os.walk("D:\\Games"):
                    if "Aseprite.exe" in files:
                        result = os.path.join(root, "Aseprite.exe")
                        break
                    # Limit depth to avoid searching too deep
                    level = root.count(os.sep)
                    if level > 4:
                        break

            # Check registry
            if not result:
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        subkey_name = winreg.EnumKey(key, i)
                        if "aseprite" in subkey_name.lower():
                            subkey = winreg.OpenKey(key, subkey_name)
                            install_loc = winreg.QueryValueEx(subkey, "InstallLocation")
                            if install_loc and install_loc[0]:
                                exe_path = os.path.join(install_loc[0], "Aseprite.exe")
                                if os.path.exists(exe_path):
                                    result = exe_path
                                    break
                            winreg.CloseKey(subkey)
                    winreg.CloseKey(key)
                except Exception:
                    pass

            # Check Steam registry
            if not result:
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
                    steam_path = winreg.QueryValueEx(key, "SteamPath")[0]
                    library_folders = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
                    if os.path.exists(library_folders):
                        # Parse library folders and search for Aseprite
                        pass
                    winreg.CloseKey(key)
                except Exception:
                    pass

        elif self.platform == "Darwin":  # macOS
            candidates = [
                "/Applications/Aseprite.app/Contents/MacOS/aseprite",
                "/Applications/Aseprite.app/Contents/MacOS/Aseprite",
            ]
            for path in candidates:
                if os.path.exists(path):
                    result = path
                    break

        elif self.platform == "Linux":
            # Check PATH
            result = self._which("aseprite")

            # Check Steam installation
            if not result:
                steam_dirs = [
                    os.path.expanduser("~/.local/share/Steam/steamapps/common/Aseprite/aseprite"),
                    os.path.expanduser("~/.steam/steam/steamapps/common/Aseprite/aseprite"),
                    "/usr/local/bin/aseprite",
                ]
                for path in steam_dirs:
                    if os.path.exists(path):
                        result = path
                        break

        self._cache["aseprite"] = result
        return result

    def find_godot(self, fallback_to_v4: bool = True) -> Optional[str]:
        """Find Godot executable path (any version)."""
        return self.find_godot4() if fallback_to_v4 else self._find_godot_any()

    def find_godot4(self) -> Optional[str]:
        """Find Godot 4.x executable path."""
        if "godot4" in self._cache:
            return self._cache["godot4"]

        exe_name = "Godot_v4.exe" if self.platform == "Windows" else "Godot"
        result = None

        if self.platform == "Windows":
            candidates = [
                r"C:\Program Files\Godot\Godot_v*.exe",
                r"C:\Program Files (x86)\Godot\Godot_v*.exe",
                r"D:\Program Files\Godot\Godot_v*.exe",
                r"C:\Godot\Godot_v*.exe",
                r"D:\Godot\Godot_v*.exe",
            ]

            for pattern in candidates:
                matches = list(Path(pattern).parent.glob("Godot_v4*.exe"))
                if matches:
                    result = str(max(matches, key=os.path.getmtime))
                    break

            # Check PATH
            if not result:
                result = self._which("godot4.exe") or self._which("godot.exe")

            # Check registry
            if not result:
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\godotfile\shell\open\command")
                    cmd = winreg.QueryValue(key, "")
                    # Extract path from command like '"C:\Godot\Godot_v4.3.exe" "%1"'
                    if cmd:
                        import re
                        match = re.search(r'"([^"]+\.exe)"', cmd)
                        if match and os.path.exists(match.group(1)):
                            result = match.group(1)
                    winreg.CloseKey(key)
                except Exception:
                    pass

        elif self.platform == "Darwin":
            candidates = [
                "/Applications/Godot_mono.app/Contents/MacOS/Godot",
                "/Applications/Godot.app/Contents/MacOS/Godot",
            ]
            for path in candidates:
                if os.path.exists(path):
                    result = path
                    break

        elif self.platform == "Linux":
            result = self._which("godot4") or self._which("godot")

        self._cache["godot4"] = result
        return result

    def _find_godot_any(self) -> Optional[str]:
        """Find any Godot version."""
        if self.platform == "Windows":
            candidates = [
                r"C:\Godot\*.exe",
                r"D:\Godot\*.exe",
                r"C:\Program Files\Godot\*.exe",
            ]
            for pattern in candidates:
                matches = list(Path(pattern).parent.glob("Godot*.exe"))
                if matches:
                    return str(max(matches, key=os.path.getmtime))
        return self._which("godot")

    def _which(self, name: str) -> Optional[str]:
        """Find executable in PATH."""
        try:
            result = subprocess.run(
                ["where", name] if self.platform == "Windows" else ["which", name],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0]
        except Exception:
            pass
        return None

    def get_version(self, exe_path: str) -> Optional[str]:
        """Get version of executable."""
        if not exe_path or not os.path.exists(exe_path):
            return None

        try:
            if self.platform == "Windows":
                result = subprocess.run(
                    [exe_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return result.stdout.strip().split("\n")[0]
        except Exception:
            pass
        return None


# Singleton instance
_resolver = PathResolver()


def get_aseprite_path() -> Optional[str]:
    """Get Aseprite path with auto-detection."""
    env_path = os.environ.get("ASEPRITE_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    return _resolver.find_aseprite()


def get_godot_path() -> Optional[str]:
    """Get Godot path with auto-detection."""
    env_path = os.environ.get("GODOT_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    return _resolver.find_godot4()


def get_application_info() -> Dict[str, Dict[str, str]]:
    """Get information about all detected applications."""
    resolver = PathResolver()
    paths = resolver.get_all_paths()

    info = {}
    for app_name, path in paths.items():
        if path and os.path.exists(path):
            version = resolver.get_version(path)
            info[app_name] = {
                "path": path,
                "version": version or "unknown",
                "found": True
            }
        else:
            info[app_name] = {
                "path": "Not found",
                "version": "N/A",
                "found": False
            }

    return info