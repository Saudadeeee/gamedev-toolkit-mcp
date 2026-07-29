"""Sprite-wide transforms.

:mod:`transform` operates on a single layer+frame cel. The tools here act on
the whole sprite (all layers, all frames), which is what you want for canvas
resizing, cropping and whole-sheet rotation.
"""

import os
from typing import Optional

from ..core.commands import AsepriteCommand
from ..utils.lua_templates import (
    transform_operation_template,
    execute_lua_with_template,
)
from .. import mcp


@mcp.tool()
async def flip_horizontal(filename: str, layer_name: Optional[str] = None) -> str:
    """Flip the whole sprite (or one layer) horizontally.

    Args:
        filename: Aseprite file to modify
        layer_name: Optional layer to flip instead of the entire sprite
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    target = "mask" if layer_name else "sprite"
    code = f'app.command.Flip{{ ui=false, target="{target}", orientation="horizontal" }}'
    return execute_lua_with_template(
        transform_operation_template, filename, layer_name, code, "flipped horizontally"
    )


@mcp.tool()
async def flip_vertical(filename: str, layer_name: Optional[str] = None) -> str:
    """Flip the whole sprite (or one layer) vertically.

    Args:
        filename: Aseprite file to modify
        layer_name: Optional layer to flip instead of the entire sprite
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    target = "mask" if layer_name else "sprite"
    code = f'app.command.Flip{{ ui=false, target="{target}", orientation="vertical" }}'
    return execute_lua_with_template(
        transform_operation_template, filename, layer_name, code, "flipped vertically"
    )


@mcp.tool()
async def rotate(filename: str, angle: int, layer_name: Optional[str] = None) -> str:
    """Rotate the whole sprite (or one layer) by 90, 180 or 270 degrees.

    Args:
        filename: Aseprite file to modify
        angle: 90, 180 or 270
        layer_name: Optional layer to rotate instead of the entire sprite
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if angle not in (90, 180, 270):
        return "angle must be 90, 180 or 270"

    target = "mask" if layer_name else "sprite"
    code = f'app.command.Rotate{{ ui=false, target="{target}", angle="{angle}" }}'
    return execute_lua_with_template(
        transform_operation_template, filename, layer_name, code, f"rotated {angle} degrees"
    )


@mcp.tool()
async def resize_sprite(filename: str, width: int, height: int) -> str:
    """Resize the entire sprite to new pixel dimensions (nearest-neighbour).

    Args:
        filename: Aseprite file to modify
        width: New width in pixels
        height: New height in pixels
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "width and height must be positive"

    code = f"sprite:resize({width}, {height})"
    return execute_lua_with_template(
        transform_operation_template, filename, None, code, f"resized to {width}x{height}"
    )


@mcp.tool()
async def crop_sprite(filename: str, x: int, y: int, width: int, height: int) -> str:
    """Crop the sprite to a rectangle, keeping all layers and frames.

    Args:
        filename: Aseprite file to modify
        x: Left edge of the crop rectangle
        y: Top edge of the crop rectangle
        width: Crop width in pixels
        height: Crop height in pixels
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "width and height must be positive"

    code = f"sprite:crop(Rectangle({x}, {y}, {width}, {height}))"
    return execute_lua_with_template(
        transform_operation_template,
        filename,
        None,
        code,
        f"cropped to {width}x{height} at ({x}, {y})",
    )


@mcp.tool()
async def trim_sprite(filename: str) -> str:
    """Trim fully transparent borders from the sprite.

    Args:
        filename: Aseprite file to modify
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"

    script = """
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    app.transaction(function()
        app.command.AutocropSprite{ ui = false }
    end)

    spr:saveAs(spr.filename)
    print("size=" .. spr.width .. "x" .. spr.height)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Trimmed {filename} ({output.strip()})"
    return f"Failed to trim sprite: {output}"


@mcp.tool()
async def set_sprite_grid(filename: str, x: int, y: int, width: int, height: int) -> str:
    """Set the sprite's grid bounds (used by tilemap tools and the UI grid).

    Args:
        filename: Aseprite file to modify
        x: Grid origin x
        y: Grid origin y
        width: Grid cell width
        height: Grid cell height
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "width and height must be positive"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    app.transaction(function()
        spr.gridBounds = Rectangle({x}, {y}, {width}, {height})
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Grid set to {width}x{height} at ({x}, {y}) in {filename}"
    return f"Failed to set grid: {output}"
