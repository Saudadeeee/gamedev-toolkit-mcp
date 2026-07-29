"""End-to-end smoke test against a real Aseprite install.

Runs every tool this fork added or rewrote against a scratch sprite, then
checks that a set of deliberately invalid calls fail loudly rather than
silently succeeding — the failure mode Aseprite's batch runner makes easy.

    uv run tests/smoke_test.py            # keep the scratch files
    uv run tests/smoke_test.py --clean    # delete them afterwards

Requires ASEPRITE_PATH to resolve (see get_aseprite_info). Exits non-zero on
the first sign of trouble, so it works as a CI gate.
"""

import asyncio
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aseprite_mcp.core.commands import AsepriteCommand  # noqa: E402
from aseprite_mcp.tools import (  # noqa: E402
    ai_features,
    animation,
    canvas,
    cel_operations,
    drawing,
    drawing_advanced,
    effects,
    export,
    export_extra,
    file_utils,
    layer_advanced,
    palette_extra,
    pixel_read,
    slices_extra,
    transform_sprite,
)

WORK = os.path.join(tempfile.gettempdir(), "aseprite_mcp_smoke")
SPRITE = os.path.join(WORK, "smoke.aseprite").replace("\\", "/")

# A tool reports failure in its return string; there are no exceptions to
# catch. These prefixes and markers are what a failed call looks like.
FAILURE_PREFIXES = ("failed", "error", "invalid")
FAILURE_MARKERS = ("ERROR:", "Unsupported chunk")

results: list[tuple[str, str, str]] = []


def _looks_failed(text: str) -> bool:
    return text.lower().startswith(FAILURE_PREFIXES) or any(
        marker in text for marker in FAILURE_MARKERS
    )


async def expect_ok(label, coro):
    """Run a tool call that must succeed."""
    try:
        out = await coro
    except Exception as exc:  # noqa: BLE001 - a raised exception is itself the failure
        results.append((label, "FAIL", f"{type(exc).__name__}: {exc}"))
        return None
    text = str(out)
    failed = _looks_failed(text)
    results.append((label, "FAIL" if failed else "ok", (text if failed else text[:120]).replace("\n", " | ")))
    return out


async def expect_failure(label, coro, expected):
    """Run a tool call that must be rejected with a specific message.

    Matching the message, not just "something went wrong", is what catches a
    tool that fails for the wrong reason — the failure mode that makes a
    rejection test pass while proving nothing.
    """
    try:
        text = str(await coro)
    except Exception as exc:  # noqa: BLE001
        results.append((label, "FAIL", f"raised instead of returning: {exc}"))
        return
    if expected.lower() in text.lower():
        results.append((label, "ok", text[:120].replace("\n", " | ")))
    else:
        results.append((label, "FAIL", f"expected {expected!r}, got: {text[:120]}"))


async def run():
    await expect_ok("create_canvas", canvas.create_canvas(64, 64, SPRITE))
    await expect_ok("add_layer:body", canvas.add_layer(SPRITE, "body"))
    await expect_ok("add_layer:fx", canvas.add_layer(SPRITE, "fx"))
    await expect_ok("add_frames", animation.add_frames(SPRITE, 3))
    await expect_ok(
        "draw_rectangle_at",
        drawing.draw_rectangle_at(SPRITE, "body", 1, 10, 10, 30, 30, "#3366CCFF", True),
    )

    # palette_extra
    await expect_ok("create_palette", palette_extra.create_palette(SPRITE, ["#000", "#F00", "#FFFFFF80"]))
    await expect_ok("get_palette_colors", palette_extra.get_palette_colors(SPRITE))
    await expect_ok("add_color_to_palette", palette_extra.add_color_to_palette(SPRITE, "#00FF00"))

    gpl = os.path.join(WORK, "pal.gpl").replace("\\", "/")
    with open(gpl, "w", encoding="utf-8") as f:
        f.write(
            "GIMP Palette\nName: smoke\nColumns: 4\n#\n"
            "  0   0   0\tBlack\n255   0 255\tMagenta\n 17  34  51\tNavy\n"
        )
    await expect_ok("load_palette_from_file", palette_extra.load_palette_from_file(SPRITE, gpl))

    # drawing_advanced
    await expect_ok(
        "draw_bezier_curve",
        drawing_advanced.draw_bezier_curve(
            SPRITE, "fx", [[2, 2], [20, 0], [40, 60], [60, 60]], "#FF00FF", 1, 2
        ),
    )
    await expect_ok(
        "draw_gradient:linear",
        drawing_advanced.draw_gradient(SPRITE, "fx", 0, 0, 63, 0, "#FF0000", "#0000FF", 2, "linear"),
    )
    await expect_ok(
        "draw_gradient:radial",
        drawing_advanced.draw_gradient(SPRITE, "fx", 0, 0, 63, 63, "#FFFFFF", "#000000", 3, "radial"),
    )
    await expect_ok(
        "apply_brush_stroke",
        drawing_advanced.apply_brush_stroke(SPRITE, "fx", [[5, 5], [30, 40], [55, 10]], "#00FFAA", 4, 3),
    )

    pattern = os.path.join(WORK, "pattern.png").replace("\\", "/")
    await expect_ok("export_frame", export.export_frame(SPRITE, 1, pattern))
    await expect_ok(
        "draw_pattern",
        drawing_advanced.draw_pattern(SPRITE, "fx", 0, 0, 32, 32, pattern, 1, True),
    )

    # effects
    await expect_ok("posterize", effects.posterize(SPRITE, "body", 1, 3))
    await expect_ok("pixelate", effects.pixelate(SPRITE, "body", 1, 4))
    await expect_ok("drop_shadow", effects.drop_shadow(SPRITE, "body", 1, 3, 3, "#00000080"))
    await expect_ok("drop_shadow:to_layer", effects.drop_shadow(SPRITE, "body", 1, 2, 2, "#000000FF", "fx"))

    # cels and layers
    await expect_ok("link_cels", cel_operations.link_cels(SPRITE, "body", 1, 3))
    await expect_ok("add_group", canvas.add_group(SPRITE, "grp"))
    await expect_ok("move_layer_to_group", layer_advanced.move_layer_to_group(SPRITE, "fx", "grp"))
    await expect_ok("move_layer_to_root", layer_advanced.move_layer_to_group(SPRITE, "fx", ""))
    await expect_ok("merge_layers", layer_advanced.merge_layers(SPRITE, ["body", "fx"], "merged"))

    # transform_sprite
    await expect_ok("set_sprite_grid", transform_sprite.set_sprite_grid(SPRITE, 0, 0, 16, 16))
    await expect_ok("flip_horizontal", transform_sprite.flip_horizontal(SPRITE))
    await expect_ok("flip_vertical:layer", transform_sprite.flip_vertical(SPRITE, "merged"))
    await expect_ok("rotate", transform_sprite.rotate(SPRITE, 90))
    await expect_ok("resize_sprite", transform_sprite.resize_sprite(SPRITE, 32, 32))
    await expect_ok("crop_sprite", transform_sprite.crop_sprite(SPRITE, 0, 0, 24, 24))
    await expect_ok("trim_sprite", transform_sprite.trim_sprite(SPRITE))

    # slices_extra
    await expect_ok(
        "create_nine_patch_slice",
        slices_extra.create_nine_patch_slice(
            SPRITE, "panel",
            {"x": 0, "y": 0, "width": 16, "height": 16},
            {"x": 4, "y": 4, "width": 8, "height": 8},
        ),
    )
    await expect_ok("export_slices", slices_extra.export_slices(SPRITE, os.path.join(WORK, "slices")))

    # export_extra
    await expect_ok(
        "export_frames_separately",
        export_extra.export_frames_separately(SPRITE, os.path.join(WORK, "frames"), "f", "png", 2),
    )

    # ai_features
    await expect_ok(
        "auto_color_sprite",
        ai_features.auto_color_sprite(SPRITE, "merged", ["#221100", "#886644", "#FFDDBB"], 1),
    )
    await expect_ok("auto_cleanup_lineart:dry", ai_features.auto_cleanup_lineart(SPRITE, "merged", 1, 1, True))
    await expect_ok("auto_cleanup_lineart", ai_features.auto_cleanup_lineart(SPRITE, "merged", 1, 1, False))
    audit = await expect_ok("suggest_improvements", ai_features.suggest_improvements(SPRITE))
    if audit:
        json.loads(str(audit))  # must be valid JSON

    # file_utils
    batch_in = os.path.join(WORK, "batch_in")
    os.makedirs(batch_in, exist_ok=True)
    for name in ("a.aseprite", "b.aseprite"):
        shutil.copy2(SPRITE, os.path.join(batch_in, name))
    await expect_ok("batch_convert", file_utils.batch_convert(batch_in, os.path.join(WORK, "batch_out"), "png"))
    await expect_ok("batch_process_sprites", ai_features.batch_process_sprites(batch_in, ["trim", "optimize"]))
    await expect_ok(
        "generate_sprite_variations",
        ai_features.generate_sprite_variations(SPRITE, os.path.join(WORK, "vars"), [60, 180]),
    )
    await expect_ok("optimize_file_size", file_utils.optimize_file_size(SPRITE))

    comparison = await expect_ok(
        "compare_sprites", file_utils.compare_sprites(SPRITE, os.path.join(batch_in, "a.aseprite"))
    )
    if comparison:
        json.loads(str(comparison))  # layer names must not break the JSON

    backup = await expect_ok("backup_sprite", file_utils.backup_sprite(SPRITE, os.path.join(WORK, "bak")))
    if backup and "timestamp " in str(backup):
        stamp = str(backup).rsplit("timestamp ", 1)[1].rstrip(")")
        await expect_ok("restore_sprite", file_utils.restore_sprite(SPRITE, stamp, os.path.join(WORK, "bak")))

    # Readback: proves the pixels actually landed rather than trusting the
    # success strings above.
    await expect_ok("get_composite_rect", pixel_read.get_composite_rect(SPRITE, 0, 0, 8, 8, 1))

    # Invalid input must be rejected, and rejected for the stated reason.
    await expect_failure(
        "reject:missing layer",
        effects.posterize(SPRITE, "does_not_exist", 1, 3),
        "Layer not found",
    )
    await expect_failure(
        "reject:frame out of range",
        effects.pixelate(SPRITE, "merged", 999, 2),
        "Frame index out of range",
    )
    await expect_failure(
        "reject:bad color",
        drawing_advanced.draw_gradient(SPRITE, "merged", 0, 0, 10, 10, "not-a-color", "#FFF", 1),
        "Invalid color value",
    )
    await expect_failure(
        "reject:path traversal",
        palette_extra.load_palette_from_file(SPRITE, "../../etc/passwd"),
        "parent directory traversal not allowed",
    )
    await expect_failure(
        "reject:missing file",
        effects.posterize(os.path.join(WORK, "nope.aseprite"), "merged", 1, 3),
        "not found",
    )
    await expect_failure(
        "reject:empty palette",
        palette_extra.create_palette(SPRITE, []),
        "cannot be empty",
    )

    # A layer name crafted to close the Lua string literal and inject a
    # statement must be treated as an ordinary (missing) name.
    await expect_failure(
        "reject:lua injection",
        layer_advanced.move_layer_to_group(SPRITE, 'x" print("ERROR:pwned") --', ""),
        "Layer not found",
    )


def main():
    ok, version = AsepriteCommand.run_command(["--version"])
    if not ok:
        print(f"Cannot reach Aseprite: {version}")
        print("Set ASEPRITE_PATH in .env or the environment, then retry.")
        return 2
    print(f"Using {AsepriteCommand.get_aseprite_executable()} ({version})\n")

    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK, exist_ok=True)

    asyncio.run(run())

    width = max(len(label) for label, _, _ in results)
    failed = sum(1 for _, status, _ in results if status != "ok")
    for label, status, detail in results:
        print(f"{status:<5} {label:<{width}}  {detail}")
    print(f"\n{len(results) - failed}/{len(results)} passed")

    if "--clean" in sys.argv:
        shutil.rmtree(WORK, ignore_errors=True)
    else:
        print(f"Scratch files kept in {WORK}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
