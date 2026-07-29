"""Per-cel image effects not covered by Aseprite's native filters.

Brightness/contrast, HSL, invert, outline and convolution go through
:mod:`native_fx`, which drives the real engine filters. What is left here are
effects Aseprite has no command for, implemented pixel-by-pixel: posterize,
pixelate and drop shadow.

All three target an explicit layer + frame rather than the active cel, and
normalize the cel to canvas size first so sprite-global coordinates apply.
"""

import os

from ..core.commands import AsepriteCommand, lua_escape
from ..core.lua import FIND_LAYER, NORMALIZE_CEL
from ..core.colors import parse_hex_color
from .. import mcp


def _resolve_target(layer_name: str, frame_index: int, create: str = "false") -> str:
    """Lua preamble that activates a layer+frame and normalizes its cel."""
    safe_layer = lua_escape(layer_name)
    return f"""
    {FIND_LAYER}
    {NORMALIZE_CEL}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local target = find_layer(spr, "{safe_layer}")
    if not target then print("ERROR:Layer not found") return end
    if target.isGroup then print("ERROR:Layer is a group") return end

    local cel = normalize_cel(spr, target, idx, {create})
    if not cel then print("ERROR:No cel at that layer/frame") return end
    local img = cel.image
    """


@mcp.tool()
async def posterize(filename: str, layer_name: str, frame_index: int = 1, levels: int = 4) -> str:
    """Reduce each RGB channel to a fixed number of levels (banding effect).

    Args:
        filename: Aseprite file to modify
        layer_name: Layer to affect
        frame_index: Frame index starting at 1
        levels: Levels per channel, 2-255. Lower means harsher banding.
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if levels < 2 or levels > 255:
        return "levels must be between 2 and 255"

    script = f"""
    {_resolve_target(layer_name, frame_index)}

    local levels = {levels}
    local step = 255 / (levels - 1)

    app.transaction(function()
        for y = 0, img.height - 1 do
            for x = 0, img.width - 1 do
                local c = Color(img:getPixel(x, y))
                if c.alpha > 0 then
                    local r = math.floor(math.floor(c.red / step + 0.5) * step + 0.5)
                    local g = math.floor(math.floor(c.green / step + 0.5) * step + 0.5)
                    local b = math.floor(math.floor(c.blue / step + 0.5) * step + 0.5)
                    img:drawPixel(x, y, Color(
                        math.min(255, r), math.min(255, g), math.min(255, b), c.alpha))
                end
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Posterized '{layer_name}' frame {frame_index} to {levels} levels in {filename}"
    return f"Failed to posterize: {output}"


@mcp.tool()
async def pixelate(filename: str, layer_name: str, frame_index: int = 1, pixel_size: int = 2) -> str:
    """Snap the cel to a coarser pixel grid (mosaic effect).

    Each block takes the color of its top-left pixel, so the result stays on
    the original palette instead of introducing averaged in-between colors.

    Args:
        filename: Aseprite file to modify
        layer_name: Layer to affect
        frame_index: Frame index starting at 1
        pixel_size: Block edge length in pixels, 2 or more
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if pixel_size < 2:
        return "pixel_size must be 2 or more"

    script = f"""
    {_resolve_target(layer_name, frame_index)}

    local block = {pixel_size}
    local out = Image(img.width, img.height, img.colorMode)

    app.transaction(function()
        local by = 0
        while by < img.height do
            local bx = 0
            while bx < img.width do
                local sample = img:getPixel(bx, by)
                for y = by, math.min(by + block - 1, img.height - 1) do
                    for x = bx, math.min(bx + block - 1, img.width - 1) do
                        out:drawPixel(x, y, sample)
                    end
                end
                bx = bx + block
            end
            by = by + block
        end
        cel.image = out
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Pixelated '{layer_name}' frame {frame_index} at {pixel_size}px in {filename}"
    return f"Failed to pixelate: {output}"


@mcp.tool()
async def drop_shadow(
    filename: str,
    layer_name: str,
    frame_index: int = 1,
    offset_x: int = 2,
    offset_y: int = 2,
    color: str = "#00000080",
    to_layer: str = "",
) -> str:
    """Add a hard-edged drop shadow behind the cel's opaque pixels.

    The shadow is a solid silhouette offset by (offset_x, offset_y) — the
    pixel-art convention, not a blurred gaussian. Shadow pixels that fall
    outside the canvas are clipped.

    Args:
        filename: Aseprite file to modify
        layer_name: Layer to read the silhouette from
        frame_index: Frame index starting at 1
        offset_x: Horizontal shadow offset in pixels, may be negative
        offset_y: Vertical shadow offset in pixels, may be negative
        color: Shadow color, alpha respected (#RRGGBBAA)
        to_layer: Existing layer to draw the shadow onto. Leave empty to
            composite the shadow into the source layer itself.
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if offset_x == 0 and offset_y == 0:
        return "offset_x and offset_y cannot both be zero"

    rgba = parse_hex_color(color)
    if rgba is None:
        return f"Invalid color value: {color}"
    r, g, b, a = rgba

    safe_dest = lua_escape(to_layer)

    script = f"""
    {_resolve_target(layer_name, frame_index)}

    local dest_img = img
    local dest_cel = cel
    if "{safe_dest}" ~= "" then
        local dest_layer = find_layer(spr, "{safe_dest}")
        if not dest_layer then print("ERROR:Destination layer not found") return end
        if dest_layer.isGroup then print("ERROR:Destination layer is a group") return end
        dest_cel = normalize_cel(spr, dest_layer, idx, true)
        if not dest_cel then print("ERROR:Could not create destination cel") return end
        dest_img = dest_cel.image
    end

    local shadow = Color({r}, {g}, {b}, {a})
    local dx, dy = {offset_x}, {offset_y}
    local painted = 0

    app.transaction(function()
        local out = Image(dest_img.width, dest_img.height, dest_img.colorMode)
        for y = 0, img.height - 1 do
            for x = 0, img.width - 1 do
                if Color(img:getPixel(x, y)).alpha > 0 then
                    local sx, sy = x + dx, y + dy
                    if sx >= 0 and sy >= 0 and sx < out.width and sy < out.height then
                        out:drawPixel(sx, sy, shadow)
                        painted = painted + 1
                    end
                end
            end
        end
        out:drawImage(dest_img, Point(0, 0))
        dest_cel.image = out
    end)

    spr:saveAs(spr.filename)
    print("shadow_pixels=" .. painted)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        where = f"'{to_layer}'" if to_layer else f"'{layer_name}'"
        return f"Drop shadow ({offset_x}, {offset_y}) drawn onto {where} in {filename} ({output.strip()})"
    return f"Failed to add drop shadow: {output}"
