"""Image transformation operations for Aseprite MCP"""

from aseprite_mcp import mcp
from aseprite_mcp.utils.lua_templates import transform_operation_template, execute_lua_with_template
from typing import Optional


@mcp.tool()
async def flip_horizontal(filename: str, layer_name: Optional[str] = None) -> str:
    """Flip image or layer horizontally"""
    transform_code = 'app.command.Flip{ target="mask", orientation="horizontal" }'
    success_message = "flipped horizontally"
    return execute_lua_with_template(transform_operation_template, filename, layer_name, transform_code, success_message)


@mcp.tool()
async def flip_vertical(filename: str, layer_name: Optional[str] = None) -> str:
    """Flip image or layer vertically"""
    transform_code = 'app.command.Flip{ target="mask", orientation="vertical" }'
    success_message = "flipped vertically"
    return execute_lua_with_template(transform_operation_template, filename, layer_name, transform_code, success_message)


@mcp.tool()
async def rotate(filename: str, angle: int, layer_name: Optional[str] = None) -> str:
    """Rotate image or layer by angle (90, 180, 270)"""
    if angle not in [90, 180, 270]:
        return "Error: Angle must be 90, 180, or 270"
    
    # Map 270 to -90 for Aseprite command if needed, but RotateSprite takes 90, 180, 270
    transform_code = f'app.command.Rotate{{ angle="{angle}" }}'
    success_message = f"rotated {angle} degrees"
    return execute_lua_with_template(transform_operation_template, filename, layer_name, transform_code, success_message)


@mcp.tool()
async def resize_sprite(filename: str, width: int, height: int) -> str:
    """Resize the entire sprite to new dimensions"""
    if width <= 0 or height <= 0:
        return "Error: Width and height must be positive"
    
    transform_code = f'sprite:resize({width}, {height})'
    success_message = f"resized to {width}x{height}"
    return execute_lua_with_template(transform_operation_template, filename, None, transform_code, success_message)


@mcp.tool()
async def crop_sprite(filename: str, x: int, y: int, width: int, height: int) -> str:
    """Crop the sprite to the specified rectangle"""
    if width <= 0 or height <= 0:
        return "Error: Width and height must be positive"
    
    transform_code = f'sprite:crop(Rectangle({x}, {y}, {width}, {height}))'
    success_message = f"cropped to {width}x{height} at ({x}, {y})"
    return execute_lua_with_template(transform_operation_template, filename, None, transform_code, success_message)


@mcp.tool()
async def trim_sprite(filename: str) -> str:
    """Automatically trim transparent borders around the sprite"""
    transform_code = 'app.command.AutocropSprite()'
    success_message = "trimmed"
    return execute_lua_with_template(transform_operation_template, filename, None, transform_code, success_message)
