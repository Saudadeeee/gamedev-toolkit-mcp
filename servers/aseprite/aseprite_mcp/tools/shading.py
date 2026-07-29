"""Palette-constrained shading, palette snapping and antialiasing.

These are the pixel-art techniques that separate a flat silhouette from a
finished sprite, and none of them are expressible with Aseprite's built-in
filters: they need to know the shape's silhouette and a colour ramp.

Feature set adapted from willibrandon/pixel-mcp
(https://github.com/willibrandon/pixel-mcp) -- see CREDITS.md. The
implementations here are original: shading works off a silhouette march,
snapping uses CIELAB rather than RGB distance, and everything runs through
this fork's ERROR:/checked-script protocol.
"""

import json
import os
from typing import List

from ..core.color_space import nearest_palette_index, sort_palette
from ..core.commands import AsepriteCommand, lua_escape
from ..core.colors import parse_hex_color
from ..core.lua import FIND_LAYER, NORMALIZE_CEL
from .. import mcp

# Light direction to a (dx, dy) step, y growing downward as in image space.
LIGHT_DIRECTIONS = {
    "top": (0, -1),
    "top-right": (1, -1),
    "right": (1, 0),
    "bottom-right": (1, 1),
    "bottom": (0, 1),
    "bottom-left": (-1, 1),
    "left": (-1, 0),
    "top-left": (-1, -1),
}

SHADING_STYLES = ("smooth", "hard", "pillow")

# Marching further than this costs time without changing the result on
# sprite-sized art.
_MAX_MARCH = 64


def _cel_preamble(layer_name: str, frame_index: int, create: str = "false") -> str:
    """Lua preamble resolving a layer+frame to a canvas-sized cel image."""
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


def _ramp_lua(ramp: List[tuple]) -> str:
    """Render an (r,g,b,a) ramp as a Lua table literal."""
    return "{" + ", ".join(f"{{{r},{g},{b},{a}}}" for r, g, b, a in ramp) + "}"


def app_key(r: int, g: int, b: int, a: int) -> int:
    """Aseprite's packed RGBA integer, matching app.pixelColor.rgba().

    Verified against the running Aseprite rather than assumed: the byte order
    is what makes a colour-keyed Lua table hit or silently miss.
    """
    return (a << 24) | (b << 16) | (g << 8) | r


@mcp.tool()
async def shade_directional(
    filename: str,
    layer_name: str,
    ramp_colors: List[str],
    frame_index: int = 1,
    light_direction: str = "top-left",
    style: str = "smooth",
    intensity: float = 1.0,
) -> str:
    """Shade a cel's opaque pixels using a colour ramp and a light direction.

    Every pixel is replaced by an entry from ``ramp_colors``, so the result
    cannot drift off-palette the way a brightness filter would. Shading is
    derived from the silhouette: each pixel marches toward the light until it
    leaves the shape, and the distance it covers decides how lit it is.

    Args:
        filename: Aseprite file to modify
        layer_name: Layer holding the silhouette to shade
        ramp_colors: Hex colours forming the ramp. Order does not matter --
            they are sorted dark to light by perceptual luminance.
        frame_index: Frame index starting at 1
        light_direction: One of top, top-right, right, bottom-right, bottom,
            bottom-left, left, top-left
        style: "smooth" for a gradual ramp, "hard" for a two-tone terminator,
            "pillow" for shading that radiates from the centre outward
        intensity: 0.0-1.0. Below 1.0 compresses the range toward the lit end,
            leaving the form flatter.
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if light_direction not in LIGHT_DIRECTIONS:
        return f"light_direction must be one of: {', '.join(sorted(LIGHT_DIRECTIONS))}"
    if style not in SHADING_STYLES:
        return f"style must be one of: {', '.join(SHADING_STYLES)}"
    if not ramp_colors or len(ramp_colors) < 2:
        return "ramp_colors needs at least 2 colours"
    if not 0.0 <= intensity <= 1.0:
        return "intensity must be between 0.0 and 1.0"

    parsed = []
    for color in ramp_colors:
        rgba = parse_hex_color(color)
        if rgba is None:
            return f"Invalid color value: {color}"
        parsed.append(rgba)

    # Sort dark to light so ramp[1] is shadow and ramp[#ramp] is highlight,
    # regardless of the order the caller supplied.
    ordered_rgb = sort_palette([(r, g, b) for r, g, b, _ in parsed], "luminance")
    alpha_by_rgb = {(r, g, b): a for r, g, b, a in parsed}
    ramp = [(r, g, b, alpha_by_rgb[(r, g, b)]) for r, g, b in ordered_rgb]

    dx, dy = LIGHT_DIRECTIONS[light_direction]

    script = f"""
    {_cel_preamble(layer_name, frame_index)}

    local ramp = {_ramp_lua(ramp)}
    local steps = #ramp
    local dx, dy = {dx}, {dy}
    local max_march = {_MAX_MARCH}
    local style = "{style}"
    local intensity = {intensity}

    local function opaque(x, y)
        if x < 0 or y < 0 or x >= img.width or y >= img.height then return false end
        return app.pixelColor.rgbaA(img:getPixel(x, y)) > 0
    end

    -- Distance from (x,y) to the silhouette edge along (sx,sy).
    local function march(x, y, sx, sy)
        local d = 0
        local cx, cy = x, y
        while d < max_march do
            cx = cx + sx
            cy = cy + sy
            if not opaque(cx, cy) then return d end
            d = d + 1
        end
        return max_march
    end

    -- Collect depths first: writing while measuring would sample pixels that
    -- have already been recoloured and skew every later reading.
    local depths = {{}}
    local max_depth = 0
    for y = 0, img.height - 1 do
        for x = 0, img.width - 1 do
            if opaque(x, y) then
                local d
                if style == "pillow" then
                    -- Distance to the nearest edge in any of 8 directions:
                    -- the centre of the form ends up brightest.
                    d = max_march
                    local dirs = {{{{1,0}},{{-1,0}},{{0,1}},{{0,-1}},{{1,1}},{{1,-1}},{{-1,1}},{{-1,-1}}}}
                    for _, dir in ipairs(dirs) do
                        local m = march(x, y, dir[1], dir[2])
                        if m < d then d = m end
                    end
                else
                    -- March toward the light: a pixel that leaves the shape
                    -- quickly is facing the light and should be bright.
                    d = march(x, y, dx, dy)
                end
                depths[y * img.width + x] = d
                if d > max_depth then max_depth = d end
            end
        end
    end

    if max_depth == 0 then max_depth = 1 end

    app.transaction(function()
        for y = 0, img.height - 1 do
            for x = 0, img.width - 1 do
                local d = depths[y * img.width + x]
                if d ~= nil then
                    local t
                    if style == "pillow" then
                        -- Deeper inside == more lit.
                        t = d / max_depth
                    else
                        -- Further to march == deeper in shadow.
                        t = 1 - (d / max_depth)
                    end

                    if style == "hard" then
                        t = t >= 0.5 and 1 or 0
                    end

                    -- Compress toward the lit end as intensity drops.
                    t = 1 - (1 - t) * intensity

                    local slot = math.floor(t * (steps - 1) + 0.5) + 1
                    if slot < 1 then slot = 1 end
                    if slot > steps then slot = steps end

                    local c = ramp[slot]
                    local existing_alpha = app.pixelColor.rgbaA(img:getPixel(x, y))
                    local alpha = c[4]
                    if existing_alpha < alpha then alpha = existing_alpha end
                    img:drawPixel(x, y, app.pixelColor.rgba(c[1], c[2], c[3], alpha))
                end
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("shaded=" .. max_depth)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return (
            f"Shaded '{layer_name}' frame {frame_index} with a {len(ramp)}-step ramp, "
            f"{style} style, light from {light_direction}"
        )
    return f"Failed to shade: {output}"


@mcp.tool()
async def snap_to_palette(
    filename: str,
    layer_name: str,
    palette_colors: List[str],
    frame_index: int = 1,
) -> str:
    """Replace every colour in a cel with its perceptually nearest palette entry.

    Matching runs in CIELAB, not RGB. RGB distance treats an equal shift in
    red and in green as equally different, so it regularly snaps a colour to
    an entry that looks wrong; LAB matches what the eye reports.

    Use this to force imported or hand-picked art onto a fixed palette.

    Args:
        filename: Aseprite file to modify
        layer_name: Layer to recolour
        palette_colors: Hex colours to snap to
        frame_index: Frame index starting at 1
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if not palette_colors:
        return "palette_colors cannot be empty"

    palette = []
    for color in palette_colors:
        rgba = parse_hex_color(color)
        if rgba is None:
            return f"Invalid color value: {color}"
        palette.append(rgba)

    # Pass 1: what colours are actually in the cel.
    inspect = f"""
    {_cel_preamble(layer_name, frame_index)}

    local seen = {{}}
    local out = {{}}
    for y = 0, img.height - 1 do
        for x = 0, img.width - 1 do
            local px = img:getPixel(x, y)
            if app.pixelColor.rgbaA(px) > 0 and not seen[px] then
                seen[px] = true
                out[#out + 1] = string.format('[%d,%d,%d,%d]',
                    app.pixelColor.rgbaR(px), app.pixelColor.rgbaG(px),
                    app.pixelColor.rgbaB(px), app.pixelColor.rgbaA(px))
            end
        end
    end
    print('[' .. table.concat(out, ',') .. ']')
    """

    success, output = AsepriteCommand.execute_lua_script_checked(inspect, filename)
    if not success:
        return f"Failed to read cel colours: {output}"

    try:
        source_colors = json.loads(output.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return f"Failed to parse cel colours: {output}"

    if not source_colors:
        return f"Layer '{layer_name}' frame {frame_index} has no opaque pixels"

    # Pass 2: map each source colour to its nearest palette entry, in LAB.
    palette_rgb = [(r, g, b) for r, g, b, _ in palette]
    mappings = []
    unchanged = 0
    for r, g, b, a in source_colors:
        index = nearest_palette_index((r, g, b), palette_rgb)
        tr, tg, tb, _ = palette[index]
        if (r, g, b) == (tr, tg, tb):
            unchanged += 1
            continue
        mappings.append((r, g, b, a, tr, tg, tb))

    if not mappings:
        return (
            f"Layer '{layer_name}' frame {frame_index} already uses only palette "
            f"colours ({unchanged} distinct)"
        )

    lua_map = ", ".join(
        f"[{app_key(r, g, b, a)}]={{{tr},{tg},{tb}}}" for r, g, b, a, tr, tg, tb in mappings
    )

    apply = f"""
    {_cel_preamble(layer_name, frame_index)}

    local map = {{{lua_map}}}
    local changed = 0

    app.transaction(function()
        for y = 0, img.height - 1 do
            for x = 0, img.width - 1 do
                local px = img:getPixel(x, y)
                local t = map[px]
                if t ~= nil then
                    img:drawPixel(x, y, app.pixelColor.rgba(
                        t[1], t[2], t[3], app.pixelColor.rgbaA(px)))
                    changed = changed + 1
                end
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("changed=" .. changed)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(apply, filename)
    if success:
        return (
            f"Snapped '{layer_name}' frame {frame_index} to {len(palette)} palette "
            f"colours: {len(mappings)} of {len(source_colors)} distinct colours remapped "
            f"({output.strip()})"
        )
    return f"Failed to snap to palette: {output}"


@mcp.tool()
async def detect_antialias_candidates(
    filename: str,
    layer_name: str,
    frame_index: int = 1,
    max_results: int = 200,
) -> str:
    """Find staircase corners on diagonal edges that would benefit from antialiasing.

    Returns JSON listing each corner pixel, the two edge colours meeting there
    and a suggested midpoint colour. Nothing is modified -- feed the result to
    ``apply_antialias`` or draw the suggestions selectively.

    Args:
        filename: Aseprite file to inspect
        layer_name: Layer to analyse
        frame_index: Frame index starting at 1
        max_results: Cap on reported corners
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if max_results < 1:
        return "max_results must be at least 1"

    script = f"""
    {_cel_preamble(layer_name, frame_index)}

    local function at(x, y)
        if x < 0 or y < 0 or x >= img.width or y >= img.height then return 0 end
        return img:getPixel(x, y)
    end
    local function alpha(px) return app.pixelColor.rgbaA(px) end

    local out = {{}}
    local total = 0

    -- A staircase corner: an opaque pixel whose two orthogonal neighbours in
    -- one quadrant are transparent, with the diagonal opaque. That is the
    -- shape a 1px jagged edge makes.
    for y = 0, img.height - 1 do
        for x = 0, img.width - 1 do
            local px = at(x, y)
            if alpha(px) > 0 then
                local quads = {{{{1,1}},{{1,-1}},{{-1,1}},{{-1,-1}}}}
                for _, q in ipairs(quads) do
                    local ox, oy = q[1], q[2]
                    local side_a = at(x + ox, y)
                    local side_b = at(x, y + oy)
                    local diag = at(x + ox, y + oy)
                    if alpha(side_a) == 0 and alpha(side_b) == 0 and alpha(diag) > 0 then
                        total = total + 1
                        if #out < {max_results} then
                            out[#out + 1] = string.format(
                                '{{"x":%d,"y":%d,"dx":%d,"dy":%d,"edge":[%d,%d,%d],"diagonal":[%d,%d,%d]}}',
                                x, y, ox, oy,
                                app.pixelColor.rgbaR(px), app.pixelColor.rgbaG(px), app.pixelColor.rgbaB(px),
                                app.pixelColor.rgbaR(diag), app.pixelColor.rgbaG(diag), app.pixelColor.rgbaB(diag))
                        end
                        break
                    end
                end
            end
        end
    end

    print(string.format('{{"total":%d,"reported":%d,"corners":[%s]}}',
        total, #out, table.concat(out, ',')))
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if not success:
        return f"Failed to detect antialias candidates: {output}"

    try:
        data = json.loads(output.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return f"Failed to parse detection output: {output}"

    # Suggest the midpoint of the two colours meeting at each corner. Kept as
    # a suggestion rather than applied: over-antialiasing is what makes pixel
    # art look blurry, so the choice stays with the caller.
    for corner in data.get("corners", []):
        edge = corner["edge"]
        diagonal = corner["diagonal"]
        corner["suggested"] = "#%02X%02X%02X" % tuple(
            (e + d) // 2 for e, d in zip(edge, diagonal)
        )

    data["note"] = (
        "Antialias sparingly: it costs palette entries and reads as blur at small "
        "sizes. Apply to long diagonals and curves, not to every corner."
    )
    return json.dumps(data, indent=2)


@mcp.tool()
async def apply_antialias(
    filename: str,
    layer_name: str,
    frame_index: int = 1,
    max_pixels: int = 500,
) -> str:
    """Soften staircase corners by placing midpoint colours in the notches.

    Adds one pixel per detected corner, coloured halfway between the two edge
    colours. Run ``detect_antialias_candidates`` first to see how many corners
    exist -- on dense lineart this can add a lot of colours.

    Args:
        filename: Aseprite file to modify
        layer_name: Layer to smooth
        frame_index: Frame index starting at 1
        max_pixels: Safety cap on how many pixels may be added
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if max_pixels < 1:
        return "max_pixels must be at least 1"

    script = f"""
    {_cel_preamble(layer_name, frame_index)}

    local function at(x, y)
        if x < 0 or y < 0 or x >= img.width or y >= img.height then return 0 end
        return img:getPixel(x, y)
    end
    local function alpha(px) return app.pixelColor.rgbaA(px) end

    -- Collected before drawing: writing during the scan would create corners
    -- that the scan then "detects", cascading across the image.
    local writes = {{}}
    for y = 0, img.height - 1 do
        for x = 0, img.width - 1 do
            local px = at(x, y)
            if alpha(px) > 0 and #writes < {max_pixels} then
                local quads = {{{{1,1}},{{1,-1}},{{-1,1}},{{-1,-1}}}}
                for _, q in ipairs(quads) do
                    local ox, oy = q[1], q[2]
                    local diag = at(x + ox, y + oy)
                    if alpha(at(x + ox, y)) == 0 and alpha(at(x, y + oy)) == 0
                       and alpha(diag) > 0 then
                        local mid = app.pixelColor.rgba(
                            math.floor((app.pixelColor.rgbaR(px) + app.pixelColor.rgbaR(diag)) / 2),
                            math.floor((app.pixelColor.rgbaG(px) + app.pixelColor.rgbaG(diag)) / 2),
                            math.floor((app.pixelColor.rgbaB(px) + app.pixelColor.rgbaB(diag)) / 2),
                            math.floor((alpha(px) + alpha(diag)) / 2))
                        writes[#writes + 1] = {{x + ox, y, mid}}
                        break
                    end
                end
            end
        end
    end

    app.transaction(function()
        for _, w in ipairs(writes) do
            if w[1] >= 0 and w[2] >= 0 and w[1] < img.width and w[2] < img.height then
                img:drawPixel(w[1], w[2], w[3])
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("added=" .. #writes)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Antialiased '{layer_name}' frame {frame_index} in {filename} ({output.strip()})"
    return f"Failed to apply antialias: {output}"
