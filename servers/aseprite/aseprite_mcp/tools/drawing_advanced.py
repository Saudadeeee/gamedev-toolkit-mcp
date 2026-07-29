"""Drawing primitives Aseprite has no native command for.

Lines, rectangles, circles, ellipses, polygons, freehand paths and rectangular
gradients live in :mod:`drawing`. What is added here are curves, projected
gradients, thick brush strokes and image-tiled fills.

Every tool targets an explicit layer + frame and normalizes the cel to canvas
size first, so all coordinates are sprite-global.
"""

import os
from typing import List

from ..core.commands import AsepriteCommand, lua_escape, reject_traversal
from ..core.lua import FIND_LAYER, NORMALIZE_CEL, PSET
from ..core.colors import parse_hex_color
from .. import mcp


def _points_to_lua(points: List) -> tuple[str, str | None]:
    """Render a list of [x, y] pairs as a Lua table literal."""
    parts = []
    for point in points:
        try:
            x, y = int(point[0]), int(point[1])
        except (TypeError, ValueError, IndexError):
            return "", f"Invalid point: {point!r} (expected [x, y])"
        parts.append(f"{{x={x}, y={y}}}")
    return ", ".join(parts), None


def _target_preamble(layer_name: str, frame_index: int) -> str:
    """Lua preamble activating a layer+frame with a canvas-sized cel."""
    safe_layer = lua_escape(layer_name)
    return f"""
    {FIND_LAYER}
    {NORMALIZE_CEL}
    {PSET}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local target = find_layer(spr, "{safe_layer}")
    if not target then print("ERROR:Layer not found") return end
    if target.isGroup then print("ERROR:Layer is a group") return end

    local cel = normalize_cel(spr, target, idx, true)
    if not cel then print("ERROR:Could not resolve cel") return end
    local img = cel.image
    """


@mcp.tool()
async def draw_bezier_curve(
    filename: str,
    layer_name: str,
    points: list,
    color: str,
    frame_index: int = 1,
    thickness: int = 1,
) -> str:
    """Draw a cubic Bezier curve through four control points.

    Args:
        filename: Aseprite file to modify
        layer_name: Layer to draw on
        points: Exactly four [x, y] control points: start, handle 1, handle 2, end
        color: Hex color (#RGB, #RGBA, #RRGGBB or #RRGGBBAA)
        frame_index: Frame index starting at 1
        thickness: Stroke width in pixels
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if not points or len(points) != 4:
        return "points must contain exactly 4 control points"
    if thickness < 1:
        return "thickness must be at least 1"

    rgba = parse_hex_color(color)
    if rgba is None:
        return f"Invalid color value: {color}"
    r, g, b, a = rgba

    points_lua, error = _points_to_lua(points)
    if error:
        return error

    script = f"""
    {_target_preamble(layer_name, frame_index)}

    local col = Color({r}, {g}, {b}, {a})
    local pts = {{{points_lua}}}
    local radius = math.floor(({thickness} - 1) / 2)

    local function bezier(t, p0, p1, p2, p3)
        local mt = 1 - t
        return mt*mt*mt*p0 + 3*mt*mt*t*p1 + 3*mt*t*t*p2 + t*t*t*p3
    end

    local function stamp(cx, cy)
        for dy = -radius, radius do
            for dx = -radius, radius do
                if dx*dx + dy*dy <= radius*radius then pset(img, cx + dx, cy + dy, col) end
            end
        end
    end

    app.transaction(function()
        -- Step count scales with curve extent so no gaps appear on long curves.
        local span = math.abs(pts[4].x - pts[1].x) + math.abs(pts[4].y - pts[1].y)
                   + math.abs(pts[2].x - pts[1].x) + math.abs(pts[3].y - pts[1].y)
        local steps = math.max(32, span * 2)
        local px, py
        for i = 0, steps do
            local t = i / steps
            local x = math.floor(bezier(t, pts[1].x, pts[2].x, pts[3].x, pts[4].x) + 0.5)
            local y = math.floor(bezier(t, pts[1].y, pts[2].y, pts[3].y, pts[4].y) + 0.5)
            if x ~= px or y ~= py then stamp(x, y) end
            px, py = x, y
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Drew Bezier curve on '{layer_name}' frame {frame_index} in {filename}"
    return f"Failed to draw Bezier curve: {output}"


@mcp.tool()
async def draw_gradient(
    filename: str,
    layer_name: str,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color1: str,
    color2: str,
    frame_index: int = 1,
    gradient_type: str = "linear",
) -> str:
    """Fill the whole cel with a gradient defined by two points.

    A linear gradient runs along the (x1,y1)->(x2,y2) axis; a radial gradient
    is centred on the midpoint with that distance as its radius. Use
    ``apply_gradient_rect`` instead when the gradient should be confined to a
    rectangle or dithered.

    Args:
        filename: Aseprite file to modify
        layer_name: Layer to fill
        x1: Gradient start x
        y1: Gradient start y
        x2: Gradient end x
        y2: Gradient end y
        color1: Color at the start point
        color2: Color at the end point
        frame_index: Frame index starting at 1
        gradient_type: "linear" or "radial"
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if gradient_type not in ("linear", "radial"):
        return "gradient_type must be 'linear' or 'radial'"
    if x1 == x2 and y1 == y2:
        return "gradient start and end points must differ"

    start = parse_hex_color(color1)
    end = parse_hex_color(color2)
    if start is None:
        return f"Invalid color value: {color1}"
    if end is None:
        return f"Invalid color value: {color2}"

    r1, g1, b1, a1 = start
    r2, g2, b2, a2 = end

    script = f"""
    {_target_preamble(layer_name, frame_index)}

    local function lerp(a, b, t) return a + (b - a) * t end

    app.transaction(function()
        local x1, y1, x2, y2 = {x1}, {y1}, {x2}, {y2}
        local dx, dy = x2 - x1, y2 - y1
        local len2 = dx*dx + dy*dy
        local cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        local max_r = math.sqrt(len2) / 2
        local radial = "{gradient_type}" == "radial"

        for y = 0, img.height - 1 do
            for x = 0, img.width - 1 do
                local t
                if radial then
                    local ox, oy = x - cx, y - cy
                    t = math.min(1, math.sqrt(ox*ox + oy*oy) / max_r)
                else
                    t = ((x - x1) * dx + (y - y1) * dy) / len2
                    t = math.max(0, math.min(1, t))
                end
                img:drawPixel(x, y, Color(
                    math.floor(lerp({r1}, {r2}, t) + 0.5),
                    math.floor(lerp({g1}, {g2}, t) + 0.5),
                    math.floor(lerp({b1}, {b2}, t) + 0.5),
                    math.floor(lerp({a1}, {a2}, t) + 0.5)))
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Drew {gradient_type} gradient on '{layer_name}' frame {frame_index} in {filename}"
    return f"Failed to draw gradient: {output}"


@mcp.tool()
async def apply_brush_stroke(
    filename: str,
    layer_name: str,
    points: list,
    color: str = "#000000",
    frame_index: int = 1,
    brush_size: int = 1,
) -> str:
    """Draw a round-brush stroke through a series of points.

    Unlike ``draw_path``, which is always one pixel wide, this stamps a filled
    circle of ``brush_size`` diameter along the interpolated path.

    Args:
        filename: Aseprite file to modify
        layer_name: Layer to draw on
        points: At least two [x, y] path points, in order
        color: Hex color (#RGB, #RGBA, #RRGGBB or #RRGGBBAA)
        frame_index: Frame index starting at 1
        brush_size: Brush diameter in pixels
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if not points or len(points) < 2:
        return "points must contain at least 2 entries"
    if brush_size < 1:
        return "brush_size must be at least 1"

    rgba = parse_hex_color(color)
    if rgba is None:
        return f"Invalid color value: {color}"
    r, g, b, a = rgba

    points_lua, error = _points_to_lua(points)
    if error:
        return error

    script = f"""
    {_target_preamble(layer_name, frame_index)}

    local col = Color({r}, {g}, {b}, {a})
    local pts = {{{points_lua}}}
    local radius = math.floor(({brush_size} - 1) / 2)

    local function stamp(cx, cy)
        for dy = -radius, radius do
            for dx = -radius, radius do
                if dx*dx + dy*dy <= radius*radius then pset(img, cx + dx, cy + dy, col) end
            end
        end
    end

    app.transaction(function()
        for i = 1, #pts - 1 do
            local p1, p2 = pts[i], pts[i + 1]
            local dx, dy = p2.x - p1.x, p2.y - p1.y
            local steps = math.max(1, math.floor(math.sqrt(dx*dx + dy*dy)))
            for step = 0, steps do
                local t = step / steps
                stamp(math.floor(p1.x + dx * t + 0.5), math.floor(p1.y + dy * t + 0.5))
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Drew brush stroke ({len(points)} points) on '{layer_name}' frame {frame_index}"
    return f"Failed to draw brush stroke: {output}"


@mcp.tool()
async def draw_pattern(
    filename: str,
    layer_name: str,
    x: int,
    y: int,
    width: int,
    height: int,
    pattern_image: str,
    frame_index: int = 1,
    skip_transparent: bool = True,
) -> str:
    """Tile an external image across a rectangular region.

    Args:
        filename: Aseprite file to modify
        layer_name: Layer to draw on
        x: Left edge of the region (sprite-global)
        y: Top edge of the region (sprite-global)
        width: Region width in pixels
        height: Region height in pixels
        pattern_image: Path to the image to tile (any format Aseprite opens)
        frame_index: Frame index starting at 1
        skip_transparent: Leave existing pixels untouched where the pattern is
            transparent, instead of erasing them
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "width and height must be positive"

    traversal = reject_traversal(pattern_image)
    if traversal:
        return traversal
    if not os.path.exists(pattern_image):
        return f"Pattern image {pattern_image} not found"

    safe_pattern = lua_escape(os.path.abspath(pattern_image).replace("\\", "/"))
    skip = "true" if skip_transparent else "false"

    script = f"""
    {_target_preamble(layer_name, frame_index)}

    local pat_spr = app.open("{safe_pattern}")
    if not pat_spr then print("ERROR:Failed to open pattern image") return end
    local pat_cel = pat_spr.layers[1]:cel(1)
    if not pat_cel then pat_spr:close() print("ERROR:Pattern image has no pixels") return end
    local pat = Image(pat_spr.width, pat_spr.height, pat_spr.colorMode)
    pat:drawImage(pat_cel.image, pat_cel.position)

    -- The pattern may be indexed/grayscale while the target is RGB; go via
    -- Color so the pixel value is converted rather than reinterpreted.
    app.transaction(function()
        for py = 0, {height} - 1 do
            for px = 0, {width} - 1 do
                local c = Color(pat:getPixel(px % pat.width, py % pat.height))
                if c.alpha > 0 or not {skip} then
                    pset(img, {x} + px, {y} + py, c)
                end
            end
        end
    end)

    -- Closed only after the loop: closing the source sprite frees images
    -- derived from it, and reading `pat` afterwards crashes Aseprite.
    pat_spr:close()

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Tiled {pattern_image} over ({x}, {y}) {width}x{height} on '{layer_name}'"
    return f"Failed to draw pattern: {output}"
