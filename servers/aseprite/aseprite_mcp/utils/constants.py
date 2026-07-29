"""Constants for Aseprite operations"""

from enum import Enum


class BlendMode(Enum):
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    DARKEN = "darken"
    LIGHTEN = "lighten"
    COLOR_DODGE = "color_dodge"
    COLOR_BURN = "color_burn"
    HARD_LIGHT = "hard_light"
    SOFT_LIGHT = "soft_light"
    DIFFERENCE = "difference"
    EXCLUSION = "exclusion"
    HUE = "hue"
    SATURATION = "saturation"
    COLOR = "color"
    LUMINOSITY = "luminosity"
    ADDITION = "addition"
    SUBTRACT = "subtract"
    DIVIDE = "divide"


class ResizeMethod(Enum):
    NEAREST = "nearest"
    BILINEAR = "bilinear"
    ROTSPRITE = "rotsprite"


class GradientType(Enum):
    LINEAR = "linear"
    RADIAL = "radial"


class ColorMode(Enum):
    RGB = "rgb"
    GRAYSCALE = "grayscale"
    INDEXED = "indexed"


class SpriteSheetLayout(Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    PACKED = "packed"
    ROWS = "rows"
    COLUMNS = "columns"


# Validation ranges
OPACITY_RANGE = (0, 255)
MAX_PALETTE_COLORS = 256
DEFAULT_GRID_SIZE = 16