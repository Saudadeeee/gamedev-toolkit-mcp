"""Cel linking.

Position, opacity, copy, clear and creation of cels live in :mod:`animation`.
What is not covered there is *linking*: making a frame range share one image
so editing any frame edits them all, which keeps file size down for held
poses. Aseprite exposes no direct Lua constructor for a linked cel, so this
goes through ``app.command.LinkCels`` with an explicit frame range.
"""

import os

from ..core.commands import AsepriteCommand, lua_escape
from ..core.lua import FIND_LAYER
from .. import mcp


@mcp.tool()
async def link_cels(filename: str, layer_name: str, start_frame: int, end_frame: int) -> str:
    """Link a layer's cels across a frame range so they share one image.

    Every frame in the range ends up referencing the image of the first
    frame in the range. Editing one edits all of them.

    Args:
        filename: Aseprite file to modify
        layer_name: Layer whose cels should be linked
        start_frame: First frame of the range, 1-based
        end_frame: Last frame of the range, 1-based and inclusive
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if start_frame < 1 or end_frame < start_frame:
        return "Invalid frame range: require 1 <= start_frame <= end_frame"

    safe_layer = lua_escape(layer_name)

    script = f"""
    {FIND_LAYER}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local target = find_layer(spr, "{safe_layer}")
    if not target then print("ERROR:Layer not found") return end
    if target.isGroup then print("ERROR:Layer is a group") return end

    local first, last = {start_frame}, {end_frame}
    if last > #spr.frames then print("ERROR:Frame range exceeds sprite length") return end
    if not target:cel(first) then print("ERROR:No cel at start_frame") return end

    app.activeLayer = target
    app.range.layers = {{ target }}
    local frames = {{}}
    for i = first, last do frames[#frames + 1] = spr.frames[i] end
    app.range.frames = frames

    app.transaction(function()
        app.command.LinkCels{{ ui = false }}
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Linked cels {start_frame}-{end_frame} on layer '{layer_name}' in {filename}"
    return f"Failed to link cels: {output}"
