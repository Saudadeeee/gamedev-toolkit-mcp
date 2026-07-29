"""Nine-patch and slice-export helpers layered on top of :mod:`slices`."""

import os
from typing import Dict

from ..core.commands import AsepriteCommand, lua_escape, reject_traversal
from .. import mcp


def _rect_fields(rect: Dict[str, int], label: str) -> tuple[tuple[int, int, int, int] | None, str | None]:
    """Pull x/y/width/height out of a dict, validating types and size."""
    try:
        x = int(rect["x"])
        y = int(rect["y"])
        w = int(rect["width"])
        h = int(rect["height"])
    except (KeyError, TypeError, ValueError):
        return None, f"{label} must be a dict with integer x, y, width, height"
    if w <= 0 or h <= 0:
        return None, f"{label} width and height must be positive"
    return (x, y, w, h), None


@mcp.tool()
async def create_nine_patch_slice(filename: str, name: str, bounds: dict, center: dict) -> str:
    """Create a 9-patch slice in one call (outer bounds plus stretchable center).

    Game engines read the center rectangle to decide which pixels stretch
    when the sprite is scaled — corners stay fixed, edges stretch on one
    axis, the center stretches on both.

    Args:
        filename: Aseprite file to modify
        name: Slice name
        bounds: Outer rectangle: {"x", "y", "width", "height"} (sprite-global)
        center: Stretchable center rectangle: {"x", "y", "width", "height"},
            expressed relative to the slice bounds
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if not name:
        return "Slice name cannot be empty"

    outer, error = _rect_fields(bounds, "bounds")
    if error:
        return error
    inner, error = _rect_fields(center, "center")
    if error:
        return error

    bx, by, bw, bh = outer
    cx, cy, cw, ch = inner
    if cx < 0 or cy < 0 or cx + cw > bw or cy + ch > bh:
        return "center rectangle must fit inside bounds (center is relative to bounds)"

    safe_name = lua_escape(name)

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    for _, slice in ipairs(spr.slices) do
        if slice.name == "{safe_name}" then print("ERROR:Slice already exists") return end
    end

    app.transaction(function()
        local slice = spr:newSlice(Rectangle({bx}, {by}, {bw}, {bh}))
        slice.name = "{safe_name}"
        slice.center = Rectangle({cx}, {cy}, {cw}, {ch})
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Created 9-patch slice '{name}' in {filename}"
    return f"Failed to create 9-patch slice: {output}"


@mcp.tool()
async def export_slices(filename: str, output_folder: str) -> str:
    """Export every slice as a packed sheet plus a JSON slice map.

    Writes ``slices.png`` and ``slices.json`` into the output folder; the
    JSON lists each slice's name and rectangle so an engine can cut them
    back out.

    Args:
        filename: Aseprite file to read
        output_folder: Directory to write into (created if missing)
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    traversal = reject_traversal(output_folder)
    if traversal:
        return traversal

    os.makedirs(output_folder, exist_ok=True)
    abs_folder = os.path.abspath(output_folder).replace("\\", "/")
    safe_folder = lua_escape(abs_folder)

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end
    if #spr.slices == 0 then print("ERROR:Sprite has no slices") return end

    app.command.ExportSpriteSheet{{
        ui = false,
        type = SpriteSheetType.PACKED,
        textureFilename = "{safe_folder}/slices.png",
        dataFilename = "{safe_folder}/slices.json",
        dataFormat = SpriteSheetDataFormat.JSON_HASH,
        listSlices = true
    }}

    print("slices=" .. #spr.slices)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Exported slices from {filename} to {abs_folder} ({output.strip()})"
    return f"Failed to export slices: {output}"
