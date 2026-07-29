"""File-level utilities: batch conversion, resaving, comparison and backups.

Sprite introspection lives in :mod:`animation` (``get_sprite_info``), colour
mode conversion in :mod:`palette` (``set_color_mode``) and grid bounds in
:mod:`transform_sprite` (``set_sprite_grid``).
"""

import json
import os
import shutil
from datetime import datetime
from typing import Optional

from ..core.commands import AsepriteCommand, lua_escape, reject_traversal
from .. import mcp

_SPRITE_EXTENSIONS = (".aseprite", ".ase")
_DEFAULT_BACKUP_FOLDER = "backups"
_BACKUP_STAMP = "%Y%m%d_%H%M%S"


@mcp.tool()
async def batch_convert(input_folder: str, output_folder: str, format: str) -> str:
    """Convert every .aseprite/.ase file in a folder to another format.

    Args:
        input_folder: Folder to read sprites from (not recursive)
        output_folder: Folder to write converted files into (created if missing)
        format: Target extension without the dot, e.g. "png", "gif", "webp"
    """
    for path in (input_folder, output_folder):
        traversal = reject_traversal(path)
        if traversal:
            return traversal

    if not os.path.isdir(input_folder):
        return f"Input folder {input_folder} not found"

    target = format.lstrip(".").lower()
    if not target.isalnum():
        return f"Invalid format: {format}"

    os.makedirs(output_folder, exist_ok=True)

    files = [f for f in os.listdir(input_folder) if f.lower().endswith(_SPRITE_EXTENSIONS)]
    if not files:
        return f"No .aseprite or .ase files found in {input_folder}"

    converted: list[str] = []
    failed: list[str] = []

    for name in files:
        abs_input = os.path.abspath(os.path.join(input_folder, name)).replace("\\", "/")
        out_name = f"{os.path.splitext(name)[0]}.{target}"
        abs_output = os.path.abspath(os.path.join(output_folder, out_name)).replace("\\", "/")

        script = f"""
        local spr = app.open("{lua_escape(abs_input)}")
        if not spr then print("ERROR:Failed to open sprite") return end
        spr:saveCopyAs("{lua_escape(abs_output)}")
        spr:close()
        print("OK")
        """

        success, output = AsepriteCommand.execute_lua_script_checked(script)
        if success:
            converted.append(out_name)
        else:
            failed.append(f"{name}: {output.strip()}")

    summary = f"Converted {len(converted)}/{len(files)} files to .{target} in {output_folder}"
    if failed:
        summary += "\nFailed:\n" + "\n".join(f"  - {f}" for f in failed)
    return summary


@mcp.tool()
async def optimize_file_size(filename: str) -> str:
    """Re-save the sprite so Aseprite rewrites it with current compression.

    This drops orphaned data left behind by earlier edits. It never changes
    pixels. Reports the byte delta so you can tell whether it was worth it.

    Args:
        filename: Aseprite file to rewrite in place
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"

    original_size = os.path.getsize(filename)

    script = """
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end
    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if not success:
        return f"Failed to optimize: {output}"

    new_size = os.path.getsize(filename)
    saved = original_size - new_size
    percent = (saved / original_size * 100) if original_size > 0 else 0.0
    return (
        f"Re-saved {filename}: {original_size} -> {new_size} bytes "
        f"({saved:+d} bytes, {percent:+.1f}%)"
    )


@mcp.tool()
async def compare_sprites(file1: str, file2: str) -> str:
    """Compare the structure of two sprite files.

    Returns JSON describing canvas size, frame count, layer count, colour
    mode and layer names for both files, plus which of those match. Use
    ``compare_frames`` instead to diff pixels within a single sprite.

    Args:
        file1: First Aseprite file
        file2: Second Aseprite file
    """
    for path in (file1, file2):
        if not os.path.exists(path):
            return f"File {path} not found"

    abs1 = os.path.abspath(file1).replace("\\", "/")
    abs2 = os.path.abspath(file2).replace("\\", "/")

    script = f"""
    -- Layer names are user text and may contain quotes or backslashes;
    -- escape them or the emitted JSON is unparseable on the Python side.
    local function json_string(s)
        return '"' .. s:gsub('[\\\\"]', '\\\\%0'):gsub('%c', ' ') .. '"'
    end

    local function describe(path)
        local spr = app.open(path)
        if not spr then return nil end
        local names = {{}}
        local function walk(layers)
            for _, l in ipairs(layers) do
                names[#names + 1] = json_string(l.name)
                if l.isGroup then walk(l.layers) end
            end
        end
        walk(spr.layers)
        local desc = string.format(
            '{{"width":%d,"height":%d,"frames":%d,"layers":%d,"color_mode":%d,"layer_names":[%s]}}',
            spr.width, spr.height, #spr.frames, #spr.layers, spr.colorMode,
            table.concat(names, ","))
        spr:close()
        return desc
    end

    local a = describe("{lua_escape(abs1)}")
    if not a then print("ERROR:Failed to open first sprite") return end
    local b = describe("{lua_escape(abs2)}")
    if not b then print("ERROR:Failed to open second sprite") return end

    print('{{"file1":' .. a .. ',"file2":' .. b .. '}}')
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script)
    if not success:
        return f"Failed to compare sprites: {output}"

    try:
        data = json.loads(output.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return f"Failed to parse comparison output: {output}"

    a, b = data["file1"], data["file2"]
    data["matches"] = {
        "size": a["width"] == b["width"] and a["height"] == b["height"],
        "frames": a["frames"] == b["frames"],
        "layers": a["layers"] == b["layers"],
        "color_mode": a["color_mode"] == b["color_mode"],
        "layer_names": a["layer_names"] == b["layer_names"],
    }
    return json.dumps(data, indent=2)


@mcp.tool()
async def backup_sprite(filename: str, backup_folder: Optional[str] = None) -> str:
    """Copy a sprite to a timestamped backup file.

    The timestamp in the returned path is what ``restore_sprite`` takes.

    Args:
        filename: Aseprite file to back up
        backup_folder: Destination folder (default: "backups")
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"

    folder = backup_folder or _DEFAULT_BACKUP_FOLDER
    traversal = reject_traversal(folder)
    if traversal:
        return traversal

    os.makedirs(folder, exist_ok=True)

    timestamp = datetime.now().strftime(_BACKUP_STAMP)
    basename, extension = os.path.splitext(os.path.basename(filename))
    backup_path = os.path.join(folder, f"{basename}_{timestamp}{extension}")

    shutil.copy2(filename, backup_path)
    return f"Backup created: {backup_path} (timestamp {timestamp})"


@mcp.tool()
async def restore_sprite(
    filename: str,
    backup_timestamp: str,
    backup_folder: Optional[str] = None,
) -> str:
    """Restore a sprite from a backup made by ``backup_sprite``.

    Overwrites the target file. Call ``backup_sprite`` on the current state
    first if you might want to come back to it.

    Args:
        filename: File to overwrite with the backup
        backup_timestamp: Timestamp part of the backup name, e.g. "20260727_143000"
        backup_folder: Folder holding the backups (default: "backups")
    """
    folder = backup_folder or _DEFAULT_BACKUP_FOLDER
    for path in (folder, backup_timestamp):
        traversal = reject_traversal(path)
        if traversal:
            return traversal

    basename, extension = os.path.splitext(os.path.basename(filename))
    backup_path = os.path.join(folder, f"{basename}_{backup_timestamp}{extension}")

    if not os.path.exists(backup_path):
        available = sorted(
            f for f in os.listdir(folder) if f.startswith(f"{basename}_")
        ) if os.path.isdir(folder) else []
        hint = f" Available: {', '.join(available)}" if available else ""
        return f"Backup {backup_path} not found.{hint}"

    shutil.copy2(backup_path, filename)
    return f"Restored {filename} from {backup_path}"
