"""Shading, dither and palette tools verified against a real Aseprite.

Every assertion checks the pixels that landed, not the success string a tool
returned -- a tool reporting "Shaded ..." only means its Lua ran.

    uv run tests/shading_test.py            # keep the scratch files
    uv run tests/shading_test.py --clean    # delete them afterwards

Requires ASEPRITE_PATH to resolve. Exits non-zero on any failure.
"""

import asyncio
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

W = os.path.join(tempfile.gettempdir(), "aseprite_mcp_shading").replace("\\", "/")
shutil.rmtree(W, ignore_errors=True)
os.makedirs(W, exist_ok=True)

from aseprite_mcp.core.commands import AsepriteCommand  # noqa: E402
from aseprite_mcp.tools import canvas, drawing, pixel_read, dither_tools, shading  # noqa: E402

RESULTS = []


def check(label, ok, detail=""):
    RESULTS.append((label, "ok" if ok else "FAIL", detail))
    print(f"{'ok  ' if ok else 'FAIL'} {label:<38} {detail}")


async def distinct_colors(path, x, y, w, h, frame=1):
    raw = await pixel_read.get_composite_rect(path, x, y, w, h, frame)
    px = json.loads(raw)
    return {p["hex"].upper() for p in px if p["a"] > 0}, px


async def main():
    S = f"{W}/t.aseprite"
    await canvas.create_canvas(48, 48, S)
    await canvas.add_layer(S, "blob")
    # A filled circle: gives a silhouette with a real interior to shade.
    await drawing.draw_circle_at(S, "blob", 1, 24, 24, 14, "#808080FF", True)

    RAMP = ["#2A1B3D", "#5B4B7A", "#8C7AA8", "#BDAFD1", "#EFE7F5"]

    # --- shade_directional -------------------------------------------- #
    r = await shading.shade_directional(S, "blob", RAMP, 1, "top-left", "smooth", 1.0)
    check("shade_directional runs", not r.lower().startswith(("failed", "invalid")), r[:70])

    colors, _ = await distinct_colors(S, 10, 10, 28, 28)
    ramp_set = {c.upper() for c in RAMP}
    check("shading stayed on-palette", colors <= ramp_set, f"{len(colors)} colors: {sorted(colors)}")
    check("shading used multiple ramp steps", len(colors) >= 3, f"{len(colors)} distinct")

    # Light from top-left => top-left should be lighter than bottom-right.
    def lum(hexstr):
        h = hexstr.lstrip("#")
        r_, g_, b_ = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return 0.2126 * r_ + 0.7152 * g_ + 0.0722 * b_

    tl_raw = json.loads(await pixel_read.get_composite_rect(S, 16, 16, 4, 4, 1))
    br_raw = json.loads(await pixel_read.get_composite_rect(S, 28, 28, 4, 4, 1))
    tl = [lum(p["hex"]) for p in tl_raw if p["a"] > 0]
    br = [lum(p["hex"]) for p in br_raw if p["a"] > 0]
    ok = tl and br and (sum(tl) / len(tl)) > (sum(br) / len(br))
    check("light direction respected", ok,
          f"top-left avg {sum(tl)/len(tl):.0f} > bottom-right avg {sum(br)/len(br):.0f}")

    # hard style => exactly two tones
    await canvas.add_layer(S, "hard")
    await drawing.draw_circle_at(S, "hard", 1, 24, 24, 10, "#808080FF", True)
    await shading.shade_directional(S, "hard", RAMP, 1, "right", "hard", 1.0)
    # Read the layer, not the composite: the smooth-shaded "blob" sits under
    # this one and would contribute its own ramp entries.
    hard_px = json.loads(await pixel_read.get_pixels_rect(S, 12, 12, 24, 24, "hard", 1))
    hard_colors = {p["hex"].upper() for p in hard_px if p["a"] > 0}
    check("hard style is two-tone", len(hard_colors) == 2, f"{sorted(hard_colors)}")

    # --- snap_to_palette ---------------------------------------------- #
    await canvas.add_layer(S, "snap")
    for i, c in enumerate(["#FF0102", "#00FE01", "#0201FF"]):
        await drawing.draw_rectangle_at(S, "snap", 1, i * 12, 40, 10, 6, c, True)
    PAL = ["#FF0000", "#00FF00", "#0000FF"]
    r = await shading.snap_to_palette(S, "snap", PAL, 1)
    check("snap_to_palette runs", not r.lower().startswith(("failed", "invalid")), r[:70])
    snapped = json.loads(await pixel_read.get_pixels_rect(S, 0, 40, 34, 6, "snap", 1))
    got = {p["hex"].upper() for p in snapped if p["a"] > 0}
    check("snapped exactly onto palette", got <= {c.upper() for c in PAL}, f"{sorted(got)}")

    # --- dither patterns ---------------------------------------------- #
    listing = json.loads(await dither_tools.list_dither_patterns())
    check("list_dither_patterns", len(listing["all_pattern_names"]) >= 15,
          f"{len(listing['all_pattern_names'])} patterns")

    await canvas.add_layer(S, "dith")
    tested = 0
    for pattern in listing["all_pattern_names"]:
        r = await dither_tools.apply_dither_texture(
            S, "dith", 0, 0, 16, 16, "#000000", "#FFFFFF", pattern, 1, 0.5)
        if r.lower().startswith(("failed", "unknown", "invalid")):
            check(f"dither {pattern}", False, r[:70])
            continue
        cols, _ = await distinct_colors(S, 0, 0, 16, 16)
        both = {"#000000", "#FFFFFF"} <= cols
        if not both:
            check(f"dither {pattern}", False, f"only {sorted(cols)}")
        tested += 1
    check("all dither patterns produce both colors", tested == len(listing["all_pattern_names"]),
          f"{tested}/{len(listing['all_pattern_names'])}")

    r = await dither_tools.apply_dither_texture(S, "dith", 0, 0, 8, 8, "#000", "#FFF", "nope", 1)
    check("unknown pattern rejected", "Unknown pattern" in r, r[:60])

    # --- gradient pattern --------------------------------------------- #
    await canvas.add_layer(S, "grad")
    r = await dither_tools.apply_dither_gradient_pattern(
        S, "grad", 0, 0, 48, 8, "#000000", "#FFFFFF", "bayer8x8", 1, True)
    check("dither gradient runs", not r.lower().startswith("failed"), r[:60])
    left = json.loads(await pixel_read.get_pixels_rect(S, 0, 0, 6, 8, "grad", 1))
    right = json.loads(await pixel_read.get_pixels_rect(S, 42, 0, 6, 8, "grad", 1))
    lw = sum(1 for p in left if p["hex"].upper() == "#FFFFFF")
    rw = sum(1 for p in right if p["hex"].upper() == "#FFFFFF")
    check("gradient actually ramps", rw > lw, f"white px: left {lw} -> right {rw}")

    # --- floyd-steinberg ----------------------------------------------- #
    await canvas.add_layer(S, "fs")
    await dither_tools.apply_dither_gradient_pattern(
        S, "fs", 0, 0, 48, 12, "#111111", "#EEEEEE", "bayer8x8", 1, True)
    r = await dither_tools.apply_floyd_steinberg(S, "fs", "#000000", "#FFFFFF", 1, 0, 0, 48, 12)
    check("floyd_steinberg runs", not r.lower().startswith("failed"), r[:60])
    fs = json.loads(await pixel_read.get_pixels_rect(S, 0, 0, 48, 12, "fs", 1))
    fs_cols = {p["hex"].upper() for p in fs if p["a"] > 0}
    check("floyd_steinberg two-tone", fs_cols <= {"#000000", "#FFFFFF"} and len(fs_cols) == 2,
          f"{sorted(fs_cols)}")
    fs_white = sum(1 for p in fs if p["hex"].upper() == "#FFFFFF")
    check("floyd_steinberg preserved gradient", 0 < fs_white < len(fs),
          f"{fs_white}/{len(fs)} white")

    # --- palette sort -------------------------------------------------- #
    from aseprite_mcp.tools import palette_extra, palette as pal_mod
    await palette_extra.create_palette(S, ["#FFFFFF", "#000000", "#808080", "#FF0000"])
    r = await dither_tools.sort_sprite_palette(S, "luminance")
    check("sort_sprite_palette runs", not r.lower().startswith("failed"), r[:80])
    pal = json.loads(await pal_mod.get_palette(S))
    def L(h):
        h = h.lstrip("#")
        return 0.2126 * int(h[0:2], 16) + 0.7152 * int(h[2:4], 16) + 0.0722 * int(h[4:6], 16)
    lums = [L(c) for c in pal]
    check("palette sorted dark->light", lums == sorted(lums), f"{pal}")

    # --- ramp suggestion ------------------------------------------------ #
    r = json.loads(await dither_tools.suggest_shading_ramp(S, 1, 4))
    check("suggest_shading_ramp", len(r["ramp"]) == 4, f"{r['ramp']}")
    rl = [L(c) for c in r["ramp"]]
    check("suggested ramp ordered", rl == sorted(rl), f"{[round(x) for x in rl]}")

    # --- antialias ------------------------------------------------------ #
    await canvas.add_layer(S, "aa")
    # A staircase diagonal: guaranteed corners.
    for i in range(8):
        await drawing.draw_rectangle_at(S, "aa", 1, i * 2, i * 2, 2, 2, "#FF0000FF", True)
    det = json.loads(await shading.detect_antialias_candidates(S, "aa", 1))
    check("detect_antialias found corners", det["total"] > 0, f"total={det['total']}")
    check("detection suggests colors",
          all("suggested" in c for c in det["corners"]), f"{len(det['corners'])} corners")
    before = json.loads(await pixel_read.get_pixels_rect(S, 0, 0, 20, 20, "aa", 1))
    before_n = sum(1 for p in before if p["a"] > 0)
    r = await shading.apply_antialias(S, "aa", 1, 500)
    check("apply_antialias runs", not r.lower().startswith("failed"), r[:60])
    after = json.loads(await pixel_read.get_pixels_rect(S, 0, 0, 20, 20, "aa", 1))
    after_n = sum(1 for p in after if p["a"] > 0)
    check("antialias added pixels", after_n > before_n, f"{before_n} -> {after_n}")

    # --- rejections ------------------------------------------------------ #
    for label, coro, expect in [
        ("reject bad light dir",
         shading.shade_directional(S, "blob", RAMP, 1, "sideways"), "light_direction must be"),
        ("reject bad style",
         shading.shade_directional(S, "blob", RAMP, 1, "top", "glossy"), "style must be"),
        ("reject 1-color ramp",
         shading.shade_directional(S, "blob", ["#FFF"], 1), "at least 2"),
        ("reject bad ramp color",
         shading.shade_directional(S, "blob", ["#FFF", "zzz"], 1), "Invalid color"),
        ("reject empty palette snap",
         shading.snap_to_palette(S, "snap", [], 1), "cannot be empty"),
        ("reject bad sort key",
         dither_tools.sort_sprite_palette(S, "vibes"), "key must be"),
        ("reject missing layer",
         shading.shade_directional(S, "ghost", RAMP, 1), "Layer not found"),
    ]:
        out = str(await coro)
        check(label, expect.lower() in out.lower(), out[:70])


asyncio.run(main())

fails = sum(1 for _, s, _ in RESULTS if s != "ok")
print(f"\n{len(RESULTS) - fails}/{len(RESULTS)} passed")
sys.exit(1 if fails else 0)
