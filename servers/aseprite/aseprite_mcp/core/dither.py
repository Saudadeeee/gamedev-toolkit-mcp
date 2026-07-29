"""Dither matrices and texture masks.

Pixel art gradients are dithered rather than blended: a smooth blend
introduces hundreds of intermediate colours and destroys the palette. An
ordered matrix decides, per pixel, which of two colours to place, so the
result stays on-palette while reading as a gradient.

Matrices are threshold maps normalised by `divisor`; masks are literal
on/off stencils. Both are emitted into Lua as plain tables.

Pattern set adapted from the taxonomy used by willibrandon/pixel-mcp
(https://github.com/willibrandon/pixel-mcp); the Bayer matrices themselves are
the standard recursive construction and the textures are original.
"""

from typing import Dict, List, Tuple

Matrix = List[List[int]]

# --- Ordered (Bayer) matrices ------------------------------------------- #
# Each is the standard recursive construction: M(2n) = 4*M(n) + offsets.

BAYER_2X2: Matrix = [
    [0, 2],
    [3, 1],
]

BAYER_4X4: Matrix = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]

BAYER_8X8: Matrix = [
    [0, 32, 8, 40, 2, 34, 10, 42],
    [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44, 4, 36, 14, 46, 6, 38],
    [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43, 1, 33, 9, 41],
    [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47, 7, 39, 13, 45, 5, 37],
    [63, 31, 55, 23, 61, 29, 53, 21],
]

# A 50% checkerboard: the classic hard two-tone blend.
CHECKER: Matrix = [
    [0, 1],
    [1, 0],
]

# Horizontal and vertical line screens, useful for cloth and metal.
LINES_H: Matrix = [
    [0, 0],
    [1, 1],
]

LINES_V: Matrix = [
    [0, 1],
    [0, 1],
]

DIAGONAL: Matrix = [
    [0, 1, 2, 3],
    [1, 2, 3, 0],
    [2, 3, 0, 1],
    [3, 0, 1, 2],
]

CROSS: Matrix = [
    [0, 2, 1, 2],
    [2, 3, 2, 3],
    [1, 2, 0, 2],
    [2, 3, 2, 3],
]

# --- Texture stencils ---------------------------------------------------- #
# Hand-authored 8x8 masks. Values are thresholds like the matrices above, but
# tuned to read as a material rather than as an even gradient.

GRASS: Matrix = [
    [7, 2, 6, 1, 7, 3, 6, 0],
    [1, 5, 0, 4, 2, 6, 1, 5],
    [6, 0, 7, 2, 5, 1, 7, 3],
    [2, 4, 1, 6, 0, 4, 2, 6],
    [7, 1, 5, 0, 7, 2, 5, 1],
    [0, 6, 2, 4, 1, 6, 0, 4],
    [5, 2, 7, 1, 6, 0, 7, 2],
    [1, 4, 0, 5, 3, 4, 1, 5],
]

WATER: Matrix = [
    [0, 1, 2, 3, 3, 2, 1, 0],
    [1, 2, 3, 4, 4, 3, 2, 1],
    [2, 3, 4, 5, 5, 4, 3, 2],
    [3, 4, 5, 6, 6, 5, 4, 3],
    [3, 4, 5, 6, 6, 5, 4, 3],
    [2, 3, 4, 5, 5, 4, 3, 2],
    [1, 2, 3, 4, 4, 3, 2, 1],
    [0, 1, 2, 3, 3, 2, 1, 0],
]

STONE: Matrix = [
    [0, 5, 2, 7, 1, 6, 3, 4],
    [6, 3, 7, 1, 5, 2, 7, 0],
    [2, 7, 0, 4, 3, 7, 1, 6],
    [7, 1, 6, 3, 7, 0, 5, 2],
    [1, 6, 3, 7, 0, 5, 2, 7],
    [5, 2, 7, 0, 6, 3, 7, 1],
    [3, 7, 1, 6, 2, 7, 0, 5],
    [7, 0, 5, 2, 7, 1, 6, 3],
]

CLOUD: Matrix = [
    [7, 6, 5, 4, 4, 5, 6, 7],
    [6, 4, 3, 2, 2, 3, 4, 6],
    [5, 3, 1, 0, 0, 1, 3, 5],
    [4, 2, 0, 0, 0, 0, 2, 4],
    [4, 2, 0, 0, 0, 0, 2, 4],
    [5, 3, 1, 0, 0, 1, 3, 5],
    [6, 4, 3, 2, 2, 3, 4, 6],
    [7, 6, 5, 4, 4, 5, 6, 7],
]

BRICK: Matrix = [
    [0, 0, 0, 0, 0, 0, 0, 7],
    [0, 1, 1, 1, 1, 1, 1, 7],
    [0, 1, 1, 1, 1, 1, 1, 7],
    [7, 7, 7, 7, 7, 7, 7, 7],
    [0, 0, 0, 7, 0, 0, 0, 0],
    [1, 1, 1, 7, 1, 1, 1, 1],
    [1, 1, 1, 7, 1, 1, 1, 1],
    [7, 7, 7, 7, 7, 7, 7, 7],
]

DOTS: Matrix = [
    [0, 3, 3, 3, 0, 3, 3, 3],
    [3, 3, 3, 3, 3, 3, 3, 3],
    [3, 3, 0, 3, 3, 3, 0, 3],
    [3, 3, 3, 3, 3, 3, 3, 3],
    [0, 3, 3, 3, 0, 3, 3, 3],
    [3, 3, 3, 3, 3, 3, 3, 3],
    [3, 3, 0, 3, 3, 3, 0, 3],
    [3, 3, 3, 3, 3, 3, 3, 3],
]

NOISE: Matrix = [
    [5, 1, 7, 3, 0, 6, 2, 4],
    [2, 6, 0, 4, 7, 3, 5, 1],
    [7, 3, 5, 1, 2, 4, 0, 6],
    [0, 4, 2, 6, 5, 1, 7, 3],
    [6, 2, 4, 0, 3, 7, 1, 5],
    [3, 7, 1, 5, 4, 0, 6, 2],
    [4, 0, 6, 2, 1, 5, 3, 7],
    [1, 5, 3, 7, 6, 2, 4, 0],
]


def _divisor(matrix: Matrix) -> int:
    """Threshold ceiling: one past the largest value in the matrix."""
    return max(max(row) for row in matrix) + 1


PATTERNS: Dict[str, Matrix] = {
    "bayer2x2": BAYER_2X2,
    "bayer4x4": BAYER_4X4,
    "bayer8x8": BAYER_8X8,
    "checker": CHECKER,
    "lines-horizontal": LINES_H,
    "lines-vertical": LINES_V,
    "diagonal": DIAGONAL,
    "cross": CROSS,
    "grass": GRASS,
    "water": WATER,
    "stone": STONE,
    "cloud": CLOUD,
    "brick": BRICK,
    "dots": DOTS,
    "noise": NOISE,
}

PATTERN_NAMES = sorted(PATTERNS)

# Floyd-Steinberg is an error-diffusion kernel, not a threshold map, so it
# cannot live in PATTERNS. Offsets are (dx, dy, weight/16).
FLOYD_STEINBERG = [
    (1, 0, 7 / 16),
    (-1, 1, 3 / 16),
    (0, 1, 5 / 16),
    (1, 1, 1 / 16),
]


def get_pattern(name: str) -> Matrix:
    """Look up a dither matrix by name."""
    try:
        return PATTERNS[name]
    except KeyError:
        raise ValueError(
            f"unknown dither pattern '{name}'; valid names: {', '.join(PATTERN_NAMES)}"
        ) from None


def to_lua_table(matrix: Matrix) -> str:
    """Render a matrix as a Lua table literal."""
    rows = ", ".join("{" + ", ".join(str(v) for v in row) + "}" for row in matrix)
    return "{" + rows + "}"


def pattern_lua(name: str) -> Tuple[str, int, int, int]:
    """Lua literal plus (width, height, divisor) for a named pattern."""
    matrix = get_pattern(name)
    return to_lua_table(matrix), len(matrix[0]), len(matrix), _divisor(matrix)
