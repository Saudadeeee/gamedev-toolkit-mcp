"""Lua script templates and utilities.

Every template here follows the ERROR:/OK protocol used by
``AsepriteCommand.execute_lua_script_checked``: a script signals failure by
printing a line starting with ``ERROR:``. A bare ``return "message"`` at Lua
top level is discarded by Aseprite's batch runner, so failures reported that
way are invisible to the caller.

All interpolated strings go through ``lua_escape`` — user-supplied filenames
and layer names would otherwise break out of the Lua string literal.
"""

from typing import Optional

from ..core.commands import lua_escape
from ..core.lua import FIND_LAYER


def sprite_operation_template(filename: str, operation_code: str) -> str:
    """Template for basic sprite operations with error handling."""
    safe_file = lua_escape(filename)
    return f"""
local sprite = app.open("{safe_file}")
if not sprite then
    print("ERROR:Failed to open sprite")
    return
end

{operation_code}

sprite:saveAs("{safe_file}")
sprite:close()
"""


def transaction_wrapper(code: str) -> str:
    """Wrap code in an Aseprite transaction."""
    return f"""
app.transaction(function()
    {code}
end)
"""


def find_layer_template(layer_name: str, action_code: str) -> str:
    """Template for finding a layer (searching inside groups) and acting on it."""
    safe_layer = lua_escape(layer_name)
    return f"""
{FIND_LAYER}
local layer = find_layer(sprite, "{safe_layer}")

if not layer then
    print("ERROR:Layer '{safe_layer}' not found")
    sprite:close()
    return
end

{action_code}
"""


def create_lua_color(hex_color: str) -> str:
    """Convert a hex color to a Lua Color constructor."""
    return f'Color{{fromString="{lua_escape(hex_color)}"}}'


def create_lua_rectangle(x: int, y: int, width: int, height: int) -> str:
    """Create a Lua Rectangle constructor."""
    return f'Rectangle({x}, {y}, {width}, {height})'


def layer_operation_template(filename: str, layer_name: str, action_code: str) -> str:
    """Template for operations that require finding a specific layer."""
    operation = find_layer_template(layer_name, action_code)
    return sprite_operation_template(filename, operation)


def execute_lua_with_template(template_func, *args, **kwargs):
    """Execute a Lua script template, surfacing in-script ERROR: lines."""
    from ..core.commands import AsepriteCommand

    lua_script = template_func(*args, **kwargs)
    success, output = AsepriteCommand.execute_lua_script_checked(lua_script)
    return output if success else f"Error: {output}"


def transform_operation_template(
    filename: str,
    layer_name: Optional[str],
    transform_code: str,
    success_message: str,
) -> str:
    """Template for transforms that target a layer or the entire sprite."""
    safe_message = lua_escape(success_message)
    if layer_name:
        safe_layer = lua_escape(layer_name)
        operation = find_layer_template(layer_name, f"""
        app.activeLayer = layer
        {transform_code}
        print("Success: Layer '{safe_layer}' {safe_message}")
        """)
    else:
        operation = f"""
        {transform_code}
        print("Success: Sprite {safe_message}")
        """

    return sprite_operation_template(filename, operation)
