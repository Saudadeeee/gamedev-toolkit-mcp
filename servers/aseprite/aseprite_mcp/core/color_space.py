"""Perceptual colour maths.

Nearest-colour matching in raw RGB picks visually wrong entries: RGB distance
treats a green shift and a blue shift of equal magnitude as equally different,
while the eye is far more sensitive to green. Converting to CIELAB first makes
"nearest" mean "looks closest", which is what palette snapping and quantization
actually want.

Kept in Python rather than Lua: the conversions are only needed to pick colours
before a script is generated, and Lua has no cbrt.
"""

from typing import Iterable, List, Sequence, Tuple

RGB = Tuple[int, int, int]
LAB = Tuple[float, float, float]

# D65 reference white, the standard illuminant for sRGB.
_WHITE_X = 95.047
_WHITE_Y = 100.0
_WHITE_Z = 108.883

_LINEAR_THRESHOLD = 0.04045
_LAB_EPSILON = 216 / 24389
_LAB_KAPPA = 24389 / 27


def _srgb_to_linear(channel: int) -> float:
    """Undo the sRGB transfer curve for one 0-255 channel."""
    c = channel / 255.0
    if c <= _LINEAR_THRESHOLD:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def rgb_to_xyz(rgb: RGB) -> Tuple[float, float, float]:
    """sRGB (0-255) to CIE XYZ, D65."""
    r, g, b = (_srgb_to_linear(c) * 100.0 for c in rgb)
    return (
        r * 0.4124564 + g * 0.3575761 + b * 0.1804375,
        r * 0.2126729 + g * 0.7151522 + b * 0.0721750,
        r * 0.0193339 + g * 0.1191920 + b * 0.9503041,
    )


def rgb_to_lab(rgb: RGB) -> LAB:
    """sRGB (0-255) to CIELAB."""
    x, y, z = rgb_to_xyz(rgb)

    def f(t: float) -> float:
        return t ** (1 / 3) if t > _LAB_EPSILON else (_LAB_KAPPA * t + 16) / 116

    fx, fy, fz = f(x / _WHITE_X), f(y / _WHITE_Y), f(z / _WHITE_Z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def lab_distance(a: LAB, b: LAB) -> float:
    """CIE76 delta-E. Squared distance would rank identically; the real
    magnitude is kept so callers can apply a perceptual threshold."""
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def nearest_palette_index(rgb: RGB, palette: Sequence[RGB]) -> int:
    """Index of the perceptually closest palette entry."""
    if not palette:
        raise ValueError("palette cannot be empty")
    target = rgb_to_lab(rgb)
    labs = [rgb_to_lab(entry) for entry in palette]
    return min(range(len(labs)), key=lambda i: lab_distance(target, labs[i]))


def relative_luminance(rgb: RGB) -> float:
    """Rec. 709 relative luminance, 0.0-1.0. Green dominates because the eye
    does; a flat (r+g+b)/3 average makes mid-greens read as too dark."""
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def rgb_to_hsl(rgb: RGB) -> Tuple[float, float, float]:
    """sRGB (0-255) to HSL. Hue in degrees, saturation and lightness 0-1."""
    r, g, b = (c / 255.0 for c in rgb)
    high, low = max(r, g, b), min(r, g, b)
    lightness = (high + low) / 2

    if high == low:
        return 0.0, 0.0, lightness

    delta = high - low
    saturation = delta / (2 - high - low) if lightness > 0.5 else delta / (high + low)

    if high == r:
        hue = (g - b) / delta + (6 if g < b else 0)
    elif high == g:
        hue = (b - r) / delta + 2
    else:
        hue = (r - g) / delta + 4

    return hue * 60, saturation, lightness


def sort_palette(palette: Iterable[RGB], key: str = "luminance") -> List[RGB]:
    """Order a palette by a perceptual property.

    A palette sorted dark-to-light is directly usable as a shading ramp, which
    is why this exists as more than a cosmetic tidy-up.

    Args:
        palette: RGB tuples
        key: "luminance", "hue", "saturation", or "lightness"
    """
    entries = list(palette)
    if key == "luminance":
        return sorted(entries, key=relative_luminance)
    if key == "hue":
        # Greys have no meaningful hue; park them at the front ordered by
        # luminance instead of scattering them through the hue wheel.
        def hue_key(rgb: RGB):
            h, s, _ = rgb_to_hsl(rgb)
            return (1, h) if s > 0.05 else (0, relative_luminance(rgb))

        return sorted(entries, key=hue_key)
    if key == "saturation":
        return sorted(entries, key=lambda rgb: rgb_to_hsl(rgb)[1])
    if key == "lightness":
        return sorted(entries, key=lambda rgb: rgb_to_hsl(rgb)[2])
    raise ValueError(f"unknown sort key: {key}")


def build_ramp(palette: Sequence[RGB]) -> List[RGB]:
    """Order a palette dark-to-light so it can be indexed as a shading ramp."""
    return sort_palette(palette, "luminance")
