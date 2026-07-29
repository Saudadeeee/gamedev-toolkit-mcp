"""Convenience palette tools layered on top of :mod:`palette`.

``palette.get_palette`` / ``palette.set_palette`` are the JSON-oriented
primitives. The tools here are the simpler, human-readable variants plus
palette-file import, which the primitives do not cover.
"""

import os

from ..core.commands import AsepriteCommand, lua_escape, reject_traversal
from ..core.colors import parse_hex_color
from .. import mcp


def _normalize_colors(colors: list) -> tuple[list[tuple[int, int, int, int]], str | None]:
    """Validate hex colors and return them as (r, g, b, a) tuples.

    Channels are passed to Lua numerically rather than as hex strings:
    Aseprite's ``Color{fromString=...}`` only understands #RRGGBB, and
    silently yields transparent black for an 8-digit value.
    """
    normalized: list[tuple[int, int, int, int]] = []
    for color in colors:
        rgba = parse_hex_color(color)
        if rgba is None:
            return [], f"Invalid color value: {color}"
        normalized.append(rgba)
    return normalized, None


@mcp.tool()
async def create_palette(filename: str, colors: list) -> str:
    """Replace the sprite palette with a list of hex colors.

    Args:
        filename: Aseprite file to modify
        colors: Hex colors (#RGB, #RGBA, #RRGGBB or #RRGGBBAA)
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if not colors:
        return "Colors list cannot be empty"

    normalized, error = _normalize_colors(colors)
    if error:
        return error

    colors_lua = ", ".join(f"{{{r}, {g}, {b}, {a}}}" for r, g, b, a in normalized)

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local colors = {{{colors_lua}}}
    local palette = Palette(#colors)
    for i, c in ipairs(colors) do
        palette:setColor(i - 1, Color(c[1], c[2], c[3], c[4]))
    end

    app.transaction(function()
        spr:setPalette(palette)
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Created palette with {len(normalized)} colors in {filename}"
    return f"Failed to create palette: {output}"


@mcp.tool()
async def get_palette_colors(filename: str) -> str:
    """List the sprite palette as a comma-separated hex string.

    Use ``get_palette`` instead when structured JSON is needed.

    Args:
        filename: Aseprite file to read
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"

    script = """
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local palette = spr.palettes[1]
    if not palette then print("ERROR:Sprite has no palette") return end

    local out = {}
    for i = 0, #palette - 1 do
        local c = palette:getColor(i)
        out[#out + 1] = string.format("#%02X%02X%02X%02X", c.red, c.green, c.blue, c.alpha)
    end
    print(table.concat(out, ", "))
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    return output if success else f"Failed to read palette: {output}"


@mcp.tool()
async def add_color_to_palette(filename: str, color: str) -> str:
    """Append one color to the end of the sprite palette.

    Args:
        filename: Aseprite file to modify
        color: Hex color (#RGB, #RGBA, #RRGGBB or #RRGGBBAA)
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"

    rgba = parse_hex_color(color)
    if rgba is None:
        return f"Invalid color value: {color}"
    r, g, b, a = rgba

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local palette = spr.palettes[1]
    if not palette then print("ERROR:Sprite has no palette") return end

    app.transaction(function()
        local size = #palette + 1
        palette:resize(size)
        palette:setColor(size - 1, Color({r}, {g}, {b}, {a}))
    end)

    spr:saveAs(spr.filename)
    print("index=" .. (#palette - 1))
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Added {color} to palette of {filename} ({output.strip()})"
    return f"Failed to add color: {output}"


@mcp.tool()
async def load_palette_from_file(filename: str, palette_file: str) -> str:
    """Load a palette from an external file (.gpl, .ase, .aseprite, .act, .png).

    Args:
        filename: Aseprite file to modify
        palette_file: Path to the palette source file
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    traversal = reject_traversal(palette_file)
    if traversal:
        return traversal
    if not os.path.exists(palette_file):
        return f"Palette file {palette_file} not found"

    safe_palette = lua_escape(os.path.abspath(palette_file).replace("\\", "/"))

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local ok, palette = pcall(function()
        return Palette{{ fromFile = "{safe_palette}" }}
    end)
    if not ok or not palette then print("ERROR:Failed to load palette file") return end
    -- Assigning an empty palette corrupts the sprite on save, so refuse it
    -- rather than trusting the loader to have understood the file.
    if #palette == 0 then print("ERROR:Palette file parsed to zero colors") return end

    app.transaction(function()
        spr:setPalette(palette)
    end)

    spr:saveAs(spr.filename)
    print("colors=" .. #palette)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Loaded palette from {palette_file} into {filename} ({output.strip()})"
    return f"Failed to load palette: {output}"
