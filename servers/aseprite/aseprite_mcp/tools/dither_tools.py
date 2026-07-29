"""Pattern dithering and palette ordering.

:mod:`fx` carries the original two dither tools, both hardcoded to a Bayer 4x4
matrix. These add the full pattern library — ordered matrices, line screens
and material textures — plus Floyd-Steinberg error diffusion, which is not a
threshold map and needs its own implementation.

Pattern taxonomy adapted from willibrandon/pixel-mcp
(https://github.com/willibrandon/pixel-mcp) — see CREDITS.md.
"""

import json
import os
from typing import List

from ..core.color_space import sort_palette
from ..core.commands import AsepriteCommand, lua_escape
from ..core.colors import parse_hex_color
from ..core.dither import PATTERN_NAMES, pattern_lua
from ..core.lua import FIND_LAYER, NORMALIZE_CEL, PSET
from .. import mcp


def _cel_preamble(layer_name: str, frame_index: int, create: str = "true") -> str:
    """Lua preamble resolving a layer+frame to a canvas-sized cel image."""
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

    local cel = normalize_cel(spr, target, idx, {create})
    if not cel then print("ERROR:No cel at that layer/frame") return end
    local img = cel.image
    """


@mcp.tool()
async def list_dither_patterns() -> str:
    """List every dither pattern name, grouped by what it is good for."""
    return json.dumps(
        {
            "ordered": {
                "names": ["bayer2x2", "bayer4x4", "bayer8x8"],
                "use": "Even gradients. Larger matrices give smoother ramps but a "
                       "more visible grid at small sizes.",
            },
            "screens": {
                "names": ["checker", "lines-horizontal", "lines-vertical", "diagonal", "cross"],
                "use": "Uniform 50%-ish blends, cloth and metal shading.",
            },
            "textures": {
                "names": ["grass", "water", "stone", "cloud", "brick", "dots", "noise"],
                "use": "Material surfaces. Apply over a flat fill rather than as a gradient.",
            },
            "error_diffusion": {
                "names": ["floyd-steinberg"],
                "use": "Photographic reduction to two colours via apply_floyd_steinberg. "
                       "Produces an irregular pattern, which reads as noise in pixel art.",
                "note": "Not usable with apply_dither_texture; it has its own tool.",
            },
            "all_pattern_names": PATTERN_NAMES,
        },
        indent=2,
    )


@mcp.tool()
async def apply_dither_texture(
    filename: str,
    layer_name: str,
    x: int,
    y: int,
    width: int,
    height: int,
    color_a: str,
    color_b: str,
    pattern: str = "bayer4x4",
    frame_index: int = 1,
    density: float = 0.5,
    only_opaque: bool = False,
) -> str:
    """Fill a rectangle with a two-colour dither using a named pattern.

    Unlike a smooth gradient, this only ever writes ``color_a`` or ``color_b``,
    so the result stays on-palette. Call ``list_dither_patterns`` for the
    catalogue.

    Args:
        filename: Aseprite file to modify
        layer_name: Layer to draw on
        x: Left edge of the region (sprite-global)
        y: Top edge of the region (sprite-global)
        width: Region width in pixels
        height: Region height in pixels
        color_a: Colour used below the threshold
        color_b: Colour used at or above the threshold
        pattern: Pattern name from list_dither_patterns
        frame_index: Frame index starting at 1
        density: 0.0 = all color_a, 1.0 = all color_b
        only_opaque: Dither only over existing opaque pixels, leaving
            transparent areas untouched. Use when texturing a drawn shape.
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "width and height must be positive"
    if not 0.0 <= density <= 1.0:
        return "density must be between 0.0 and 1.0"
    if pattern not in PATTERN_NAMES:
        return f"Unknown pattern '{pattern}'. Valid: {', '.join(PATTERN_NAMES)}"

    a = parse_hex_color(color_a)
    b = parse_hex_color(color_b)
    if a is None:
        return f"Invalid color value: {color_a}"
    if b is None:
        return f"Invalid color value: {color_b}"

    matrix_lua, mat_w, mat_h, divisor = pattern_lua(pattern)
    gate = "true" if only_opaque else "false"

    script = f"""
    {_cel_preamble(layer_name, frame_index)}

    local matrix = {matrix_lua}
    local mat_w, mat_h, divisor = {mat_w}, {mat_h}, {divisor}
    local ca = app.pixelColor.rgba({a[0]}, {a[1]}, {a[2]}, {a[3]})
    local cb = app.pixelColor.rgba({b[0]}, {b[1]}, {b[2]}, {b[3]})
    local density = {density}
    local only_opaque = {gate}
    local painted = 0

    app.transaction(function()
        for py = {y}, {y} + {height} - 1 do
            for px = {x}, {x} + {width} - 1 do
                local draw = true
                if only_opaque then
                    if px < 0 or py < 0 or px >= img.width or py >= img.height then
                        draw = false
                    else
                        draw = app.pixelColor.rgbaA(img:getPixel(px, py)) > 0
                    end
                end
                if draw then
                    -- Modulo on the absolute coordinate keeps the pattern
                    -- aligned to the canvas, so adjacent fills tile seamlessly.
                    local threshold = (matrix[(py % mat_h) + 1][(px % mat_w) + 1] + 0.5) / divisor
                    if density >= threshold then
                        pset(img, px, py, cb)
                    else
                        pset(img, px, py, ca)
                    end
                    painted = painted + 1
                end
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("painted=" .. painted)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return (
            f"Applied '{pattern}' dither {color_a}/{color_b} at ({x},{y}) {width}x{height} "
            f"on '{layer_name}' frame {frame_index} ({output.strip()})"
        )
    return f"Failed to apply dither texture: {output}"


@mcp.tool()
async def apply_dither_gradient_pattern(
    filename: str,
    layer_name: str,
    x: int,
    y: int,
    width: int,
    height: int,
    color_a: str,
    color_b: str,
    pattern: str = "bayer8x8",
    frame_index: int = 1,
    horizontal: bool = True,
    only_opaque: bool = False,
) -> str:
    """Dither a two-colour gradient across a rectangle using a named pattern.

    The blend ratio varies across the axis while the pattern decides which of
    the two colours each pixel takes. ``bayer8x8`` gives the smoothest ramp.

    Args:
        filename: Aseprite file to modify
        layer_name: Layer to draw on
        x: Left edge of the region (sprite-global)
        y: Top edge of the region (sprite-global)
        width: Region width in pixels
        height: Region height in pixels
        color_a: Colour at the start of the gradient
        color_b: Colour at the end of the gradient
        pattern: Pattern name from list_dither_patterns
        frame_index: Frame index starting at 1
        horizontal: Gradient runs left-to-right; False runs top-to-bottom
        only_opaque: Restrict to existing opaque pixels
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "width and height must be positive"
    if pattern not in PATTERN_NAMES:
        return f"Unknown pattern '{pattern}'. Valid: {', '.join(PATTERN_NAMES)}"

    a = parse_hex_color(color_a)
    b = parse_hex_color(color_b)
    if a is None:
        return f"Invalid color value: {color_a}"
    if b is None:
        return f"Invalid color value: {color_b}"

    matrix_lua, mat_w, mat_h, divisor = pattern_lua(pattern)
    axis = f"px - {x}" if horizontal else f"py - {y}"
    span = width if horizontal else height
    gate = "true" if only_opaque else "false"

    script = f"""
    {_cel_preamble(layer_name, frame_index)}

    local matrix = {matrix_lua}
    local mat_w, mat_h, divisor = {mat_w}, {mat_h}, {divisor}
    local ca = app.pixelColor.rgba({a[0]}, {a[1]}, {a[2]}, {a[3]})
    local cb = app.pixelColor.rgba({b[0]}, {b[1]}, {b[2]}, {b[3]})
    local only_opaque = {gate}
    local painted = 0

    app.transaction(function()
        for py = {y}, {y} + {height} - 1 do
            for px = {x}, {x} + {width} - 1 do
                local draw = true
                if only_opaque then
                    if px < 0 or py < 0 or px >= img.width or py >= img.height then
                        draw = false
                    else
                        draw = app.pixelColor.rgbaA(img:getPixel(px, py)) > 0
                    end
                end
                if draw then
                    local f = ({axis}) / math.max(1, {span} - 1)
                    local threshold = (matrix[(py % mat_h) + 1][(px % mat_w) + 1] + 0.5) / divisor
                    if f >= threshold then
                        pset(img, px, py, cb)
                    else
                        pset(img, px, py, ca)
                    end
                    painted = painted + 1
                end
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("painted=" .. painted)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        direction = "horizontal" if horizontal else "vertical"
        return (
            f"Applied '{pattern}' {direction} gradient {color_a} -> {color_b} at "
            f"({x},{y}) {width}x{height} on '{layer_name}' frame {frame_index} "
            f"({output.strip()})"
        )
    return f"Failed to apply dither gradient: {output}"


@mcp.tool()
async def apply_floyd_steinberg(
    filename: str,
    layer_name: str,
    color_a: str,
    color_b: str,
    frame_index: int = 1,
    x: int = 0,
    y: int = 0,
    width: int = 0,
    height: int = 0,
) -> str:
    """Reduce a region to two colours using Floyd-Steinberg error diffusion.

    Error diffusion pushes each pixel's quantization error onto its unprocessed
    neighbours, producing an irregular pattern that preserves detail far better
    than an ordered matrix. That irregularity reads as noise at sprite sizes,
    so this suits photographic sources and large areas rather than icons.

    Args:
        filename: Aseprite file to modify
        layer_name: Layer to process
        color_a: The darker of the two output colours
        color_b: The lighter of the two output colours
        frame_index: Frame index starting at 1
        x: Left edge of the region; 0 with width 0 means the whole cel
        y: Top edge of the region
        width: Region width; 0 means to the right edge
        height: Region height; 0 means to the bottom edge
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"

    a = parse_hex_color(color_a)
    b = parse_hex_color(color_b)
    if a is None:
        return f"Invalid color value: {color_a}"
    if b is None:
        return f"Invalid color value: {color_b}"

    script = f"""
    {_cel_preamble(layer_name, frame_index, create="false")}

    local x0, y0 = {x}, {y}
    local w = {width} > 0 and {width} or (img.width - x0)
    local h = {height} > 0 and {height} or (img.height - y0)
    if w <= 0 or h <= 0 then print("ERROR:Region is empty") return end

    local ar, ag, ab, aa = {a[0]}, {a[1]}, {a[2]}, {a[3]}
    local br, bg, bb, ba = {b[0]}, {b[1]}, {b[2]}, {b[3]}

    -- Luminance of the two targets decides which one a pixel snaps to.
    local function luma(r, g, b) return 0.2126 * r + 0.7152 * g + 0.0722 * b end
    local la, lb = luma(ar, ag, ab), luma(br, bg, bb)

    -- Error accumulates in a float buffer, not in the image: writing rounded
    -- values back and re-reading them would discard the very error this
    -- algorithm exists to carry forward.
    local buf = {{}}
    for j = 0, h - 1 do
        buf[j] = {{}}
        for i = 0, w - 1 do
            local px = img:getPixel(x0 + i, y0 + j)
            if app.pixelColor.rgbaA(px) > 0 then
                buf[j][i] = luma(app.pixelColor.rgbaR(px),
                                 app.pixelColor.rgbaG(px),
                                 app.pixelColor.rgbaB(px))
            else
                buf[j][i] = nil
            end
        end
    end

    local ca = app.pixelColor.rgba(ar, ag, ab, aa)
    local cb = app.pixelColor.rgba(br, bg, bb, ba)
    local painted = 0

    app.transaction(function()
        for j = 0, h - 1 do
            for i = 0, w - 1 do
                local old = buf[j][i]
                if old ~= nil then
                    local pick_b = math.abs(old - lb) < math.abs(old - la)
                    local new_luma = pick_b and lb or la
                    img:drawPixel(x0 + i, y0 + j, pick_b and cb or ca)
                    painted = painted + 1

                    local err = old - new_luma
                    -- Standard Floyd-Steinberg kernel: 7/16 right, then
                    -- 3/16, 5/16, 1/16 across the row below.
                    local spread = {{{{1, 0, 7/16}}, {{-1, 1, 3/16}}, {{0, 1, 5/16}}, {{1, 1, 1/16}}}}
                    for _, s in ipairs(spread) do
                        local ni, nj = i + s[1], j + s[2]
                        if ni >= 0 and ni < w and nj >= 0 and nj < h and buf[nj][ni] ~= nil then
                            buf[nj][ni] = buf[nj][ni] + err * s[3]
                        end
                    end
                end
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("painted=" .. painted)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return (
            f"Floyd-Steinberg dithered '{layer_name}' frame {frame_index} to "
            f"{color_a}/{color_b} ({output.strip()})"
        )
    return f"Failed to apply Floyd-Steinberg dither: {output}"


@mcp.tool()
async def sort_sprite_palette(filename: str, key: str = "luminance") -> str:
    """Reorder the sprite palette by a perceptual property.

    A palette sorted by luminance is directly usable as a shading ramp, which
    is what ``shade_directional`` wants. Sorting by hue groups colour families
    together for manual work.

    Indexed sprites are refused: reordering the palette would remap every
    pixel, silently changing the image.

    Args:
        filename: Aseprite file to modify
        key: "luminance", "hue", "saturation" or "lightness"
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if key not in ("luminance", "hue", "saturation", "lightness"):
        return "key must be luminance, hue, saturation or lightness"

    read = """
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end
    if spr.colorMode == ColorMode.INDEXED then
        print("ERROR:Refusing to sort an indexed sprite's palette; pixel indices reference it")
        return
    end
    local pal = spr.palettes[1]
    if not pal then print("ERROR:Sprite has no palette") return end
    local out = {}
    for i = 0, #pal - 1 do
        local c = pal:getColor(i)
        out[#out + 1] = string.format('[%d,%d,%d,%d]', c.red, c.green, c.blue, c.alpha)
    end
    print('[' .. table.concat(out, ',') .. ']')
    """

    success, output = AsepriteCommand.execute_lua_script_checked(read, filename)
    if not success:
        return f"Failed to read palette: {output}"

    try:
        entries = json.loads(output.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return f"Failed to parse palette: {output}"

    if not entries:
        return f"{filename} has an empty palette"

    alpha_by_rgb = {(r, g, b): a for r, g, b, a in entries}
    ordered = sort_palette([(r, g, b) for r, g, b, _ in entries], key)
    colors_lua = ", ".join(
        f"{{{r},{g},{b},{alpha_by_rgb[(r, g, b)]}}}" for r, g, b in ordered
    )

    write = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local colors = {{{colors_lua}}}
    local pal = Palette(#colors)
    for i, c in ipairs(colors) do
        pal:setColor(i - 1, Color(c[1], c[2], c[3], c[4]))
    end

    app.transaction(function()
        spr:setPalette(pal)
    end)

    spr:saveAs(spr.filename)
    print("sorted=" .. #colors)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(write, filename)
    if success:
        preview = ", ".join("#%02X%02X%02X" % rgb for rgb in ordered[:6])
        suffix = ", ..." if len(ordered) > 6 else ""
        return f"Sorted {len(ordered)} palette colours by {key} in {filename}: {preview}{suffix}"
    return f"Failed to write sorted palette: {output}"


@mcp.tool()
async def suggest_shading_ramp(
    filename: str,
    frame_index: int = 1,
    steps: int = 5,
) -> str:
    """Propose a shading ramp built from the colours already in the sprite.

    Reads the sprite's own colours, orders them by perceptual luminance and
    picks evenly spaced entries. Feed the result straight to
    ``shade_directional`` to shade without introducing new colours.

    Args:
        filename: Aseprite file to inspect
        frame_index: Frame index starting at 1
        steps: How many ramp entries to return
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if steps < 2:
        return "steps must be at least 2"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local seen, out = {{}}, {{}}
    for _, cel in ipairs(spr.cels) do
        if cel.frameNumber == idx then
            local im = cel.image
            for yy = 0, im.height - 1 do
                for xx = 0, im.width - 1 do
                    local px = im:getPixel(xx, yy)
                    if app.pixelColor.rgbaA(px) > 0 and not seen[px] then
                        seen[px] = true
                        out[#out + 1] = string.format('[%d,%d,%d]',
                            app.pixelColor.rgbaR(px), app.pixelColor.rgbaG(px),
                            app.pixelColor.rgbaB(px))
                    end
                end
            end
        end
    end
    print('[' .. table.concat(out, ',') .. ']')
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if not success:
        return f"Failed to read sprite colours: {output}"

    try:
        colors = [tuple(c) for c in json.loads(output.strip().splitlines()[-1])]
    except (ValueError, IndexError):
        return f"Failed to parse sprite colours: {output}"

    if len(colors) < 2:
        return json.dumps(
            {
                "ramp": ["#%02X%02X%02X" % c for c in colors],
                "note": "Fewer than 2 distinct colours found; generate_color_ramp "
                        "will synthesise a ramp from a single base colour instead.",
            },
            indent=2,
        )

    ordered = sort_palette(colors, "luminance")
    if steps >= len(ordered):
        picked = ordered
    else:
        # Even spacing including both endpoints, so the ramp spans the full
        # tonal range rather than clustering in the middle.
        picked = [ordered[round(i * (len(ordered) - 1) / (steps - 1))] for i in range(steps)]

    return json.dumps(
        {
            "ramp": ["#%02X%02X%02X" % c for c in picked],
            "distinct_colors_found": len(ordered),
            "note": "Ordered dark to light. Pass straight to shade_directional.",
        },
        indent=2,
    )
