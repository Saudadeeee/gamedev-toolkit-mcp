"""Common utilities for Aseprite operations"""

import os
from typing import Optional

from .constants import BlendMode, ResizeMethod, GradientType, ColorMode, SpriteSheetLayout
from .lua_templates import (
    sprite_operation_template,
    transaction_wrapper,
    find_layer_template,
    create_lua_color,
    create_lua_rectangle
)


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


def validate_color(color: str) -> str:
    """Validate hex color format"""
    if not color.startswith('#') or len(color) not in [7, 9]:
        raise ValidationError(f"Invalid color format '{color}'. Use #RRGGBB or #RRGGBBAA")
    return color


def validate_opacity(opacity: int) -> int:
    """Validate opacity range"""
    if opacity < 0 or opacity > 255:
        raise ValidationError(f"Opacity must be 0-255, got {opacity}")
    return opacity


def validate_dimensions(width: int, height: int) -> tuple[int, int]:
    """Validate dimensions are positive"""
    if width <= 0 or height <= 0:
        raise ValidationError(f"Dimensions must be positive, got {width}x{height}")
    return width, height


def normalize_path(path: str) -> str:
    """Convert Windows paths to forward slashes for Lua"""
    return os.path.abspath(path).replace('\\', '/')


def sanitize_filename(name: str) -> str:
    """Sanitize name for use as filename"""
    return ''.join(c if c.isalnum() or c in '-_' else '_' for c in name)


def safe_execute(func, *args, **kwargs):
    """Execute function with validation error handling"""
    try:
        return func(*args, **kwargs)
    except ValidationError as e:
        return f"Error: {str(e)}"


def validate_blend_mode(blend_mode: str) -> str:
    """Validate blend mode against available modes"""
    from .constants import BlendMode
    valid_modes = [mode.value for mode in BlendMode]
    if blend_mode.lower() not in valid_modes:
        raise ValidationError(f"Invalid blend mode '{blend_mode}'. Valid modes: {', '.join(valid_modes)}")
    return blend_mode.lower()


def validate_non_empty_string(value: str, field_name: str) -> str:
    """Validate that string is not empty"""
    if not value or value.strip() == "":
        raise ValidationError(f"{field_name} cannot be empty")
    return value.strip()


def validate_resize_method(method: str) -> str:
    """Validate resize method against available methods"""
    from .constants import ResizeMethod
    valid_methods = [mode.value for mode in ResizeMethod]
    if method.lower() not in valid_methods:
        raise ValidationError(f"Invalid resize method '{method}'. Valid methods: {', '.join(valid_methods)}")
    return method.lower()