"""Tools for querying system and application information."""

from .. import mcp
from ..core.path_resolver import get_application_info, get_aseprite_path, get_godot_path, PathResolver
import os


@mcp.tool()
async def get_app_info() -> str:
    """Get information about detected game development applications.

    Returns:
        JSON string with application paths and versions.
    """
    info = get_application_info()

    # Format as readable output
    output = []
    output.append("=== Game Development Tools Detected ===")
    output.append("")

    for app_name, details in info.items():
        status = "✓" if details["found"] else "✗"
        output.append(f"{status} {app_name.title()}:")
        output.append(f"  Path: {details['path']}")
        output.append(f"  Version: {details['version']}")
        output.append("")

    return "\n".join(output)


@mcp.tool()
async def get_aseprite_info() -> str:
    """Get Aseprite executable path and version.

    Returns:
        String with Aseprite path and version info.
    """
    path = get_aseprite_path()
    env_path = os.getenv('ASEPRITE_PATH')

    output = []
    output.append("=== Aseprite Information ===")

    if env_path:
        output.append(f"ASEPRITE_PATH (env): {env_path}")
        if os.path.exists(env_path):
            output.append(f"  ✓ File exists")
        else:
            output.append(f"  ✗ File not found")
        output.append("")

    if path and os.path.exists(path):
        output.append(f"Detected path: {path}")
        from ..core.path_resolver import PathResolver
        version = PathResolver().get_version(path)
        if version:
            output.append(f"Version: {version}")
        output.append("  ✓ Ready to use")
    else:
        output.append("Aseprite not found in common locations.")
        output.append("  Install from: https://aseprite.org")
        output.append("  Or set ASEPRITE_PATH environment variable.")

    return "\n".join(output)


@mcp.tool()
async def get_godot_info() -> str:
    """Get Godot executable path and version.

    Returns:
        String with Godot path and version info.
    """
    path = get_godot_path()
    env_path = os.getenv('GODOT_PATH')

    output = []
    output.append("=== Godot Information ===")

    if env_path:
        output.append(f"GODOT_PATH (env): {env_path}")
        if os.path.exists(env_path):
            output.append(f"  ✓ File exists")
        else:
            output.append(f"  ✗ File not found")
        output.append("")

    if path and os.path.exists(path):
        output.append(f"Detected path: {path}")
        from ..core.path_resolver import PathResolver
        version = PathResolver().get_version(path)
        if version:
            output.append(f"Version: {version}")
        output.append("  ✓ Ready to use")
    else:
        output.append("Godot 4.x not found in common locations.")
        output.append("  Download from: https://godotengine.org/download")
        output.append("  Or set GODOT_PATH environment variable.")

    return "\n".join(output)


@mcp.tool()
async def get_system_info() -> str:
    """Get system information for troubleshooting.

    Returns:
        String with platform and environment info.
    """
    import platform
    import sys

    output = []
    output.append("=== System Information ===")
    output.append(f"Platform: {platform.system()} {platform.release()}")
    output.append(f"Python: {sys.version.split()[0]}")
    output.append(f"Architecture: {platform.machine()}")
    output.append("")
    output.append("=== Environment Variables ===")

    env_vars = {
        "ASEPRITE_PATH": os.getenv('ASEPRITE_PATH', "Not set"),
        "GODOT_PATH": os.getenv('GODOT_PATH', "Not set"),
        "PATH": os.getenv('PATH', "")[:100] + "..." if len(os.getenv('PATH', "")) > 100 else os.getenv('PATH', ""),
    }

    for var, value in env_vars.items():
        output.append(f"{var}: {value}")

    return "\n".join(output)


@mcp.tool()
async def resolve_application_path(application: str) -> str:
    """Resolve the full path to a game development application.

    Args:
        application: The application name ('aseprite' or 'godot')

    Returns:
        String with the resolved path or error message.
    """
    app_lower = application.lower().strip()

    if app_lower in ("aseprite", "aseprite.exe"):
        path = get_aseprite_path()
        if path and os.path.exists(path):
            return f"Aseprite found at: {path}"
        return "Aseprite not found. Install from https://aseprite.org or set ASEPRITE_PATH."

    elif app_lower in ("godot", "godot4", "godot.exe"):
        path = get_godot_path()
        if path and os.path.exists(path):
            return f"Godot 4.x found at: {path}"
        return "Godot 4.x not found. Download from https://godotengine.org/download or set GODOT_PATH."

    else:
        return f"Unknown application: {application}. Supported: 'aseprite', 'godot'"