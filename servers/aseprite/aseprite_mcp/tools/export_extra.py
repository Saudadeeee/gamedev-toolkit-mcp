"""Bulk frame export.

Single frames, tags, layers and packed sheets are handled by :mod:`export`.
What it does not do is dump every frame as its own numbered file, which is
what engines expecting a PNG sequence want.
"""

import os

from ..core.commands import AsepriteCommand, lua_escape, reject_traversal
from .. import mcp


@mcp.tool()
async def export_frames_separately(
    filename: str,
    output_folder: str,
    prefix: str = "frame",
    format: str = "png",
    scale: int = 1,
) -> str:
    """Export every frame as its own numbered file.

    Files are named ``<prefix>_001.<format>`` and up, zero-padded to three
    digits so they sort correctly. Each file is the flattened composite of all
    visible layers at that frame.

    Args:
        filename: Aseprite file to export
        output_folder: Folder to write into (created if missing)
        prefix: Filename prefix before the frame number
        format: Output extension without the dot, e.g. "png"
        scale: Integer nearest-neighbour scale factor
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    traversal = reject_traversal(output_folder)
    if traversal:
        return traversal
    if scale < 1:
        return "scale must be at least 1"

    extension = format.lstrip(".").lower()
    if not extension.isalnum():
        return f"Invalid format: {format}"
    if not prefix or any(c in prefix for c in '\\/:*?"<>|'):
        return f"Invalid prefix: {prefix}"

    os.makedirs(output_folder, exist_ok=True)
    abs_folder = os.path.abspath(output_folder).replace("\\", "/")

    safe_folder = lua_escape(abs_folder)
    safe_prefix = lua_escape(prefix)
    safe_ext = lua_escape(extension)

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local scale = {scale}
    local count = 0

    for i = 1, #spr.frames do
        -- Flatten the frame into a throwaway single-frame sprite: saveCopyAs
        -- always writes the whole sprite, so per-frame output needs its own.
        local flat = Image(spr.width, spr.height, spr.colorMode)
        flat:drawSprite(spr, i)

        local out = Sprite(spr.width, spr.height, spr.colorMode)
        if spr.palettes[1] then out:setPalette(spr.palettes[1]) end
        out.cels[1].image = flat
        if scale > 1 then out:resize(spr.width * scale, spr.height * scale) end

        local path = string.format("%s/%s_%03d.%s", "{safe_folder}", "{safe_prefix}", i, "{safe_ext}")
        out:saveCopyAs(path)
        out:close()
        count = count + 1
    end

    print("frames=" .. count)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Exported {output.strip()} from {filename} to {abs_folder}"
    return f"Failed to export frames: {output}"
