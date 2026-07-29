"""Build an animated sprite in Aseprite and export it for Godot.

Runs the pipeline the way the skills describe it: draw one frame, shade it
with a palette ramp, animate by moving cels, tag the ranges, audit, export a
spritesheet with tag metadata. Every stage asserts on pixels or JSON, not on
the success strings the tools return.

The output feeds servers/godot/server/tests/editor_test.mjs.

    uv run tests/pipeline_demo.py <path-to-a-godot-project>
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if len(sys.argv) < 2:
    sys.exit("usage: uv run tests/pipeline_demo.py <path-to-a-godot-project>")
DEMO = sys.argv[1].replace("\\", "/")
ART = f"{DEMO}/art"
SPRITES = f"{DEMO}/assets/sprites"
os.makedirs(ART, exist_ok=True)
os.makedirs(SPRITES, exist_ok=True)

from aseprite_mcp.tools import (  # noqa: E402
    analysis,
    animation,
    canvas,
    dither_tools,
    drawing,
    export,
    pixel_read,
    quality,
    shading,
)

HERO = f"{ART}/hero.aseprite"
SHEET = f"{SPRITES}/hero_sheet.png"
SHEET_JSON = f"{SPRITES}/hero_sheet.json"

steps = []


def step(label, result):
    text = str(result)
    bad = text.lower().startswith(("failed", "error", "invalid")) or "ERROR:" in text
    steps.append((label, not bad))
    print(f"{'ok  ' if not bad else 'FAIL'} {label:<34} {text[:100].replace(chr(10), ' | ')}")
    return result


async def main():
    print("=== Aseprite: build the sprite ===")
    step("create_canvas 24x24", await canvas.create_canvas(24, 24, HERO))
    step("add_layer body", await canvas.add_layer(HERO, "body"))
    step("add_layer eye", await canvas.add_layer(HERO, "eye"))
    step("add_frames (8 total)", await animation.add_frames(HERO, 7))

    # Frame 1 only: everything else is derived.
    step("draw body", await drawing.draw_circle_at(HERO, "body", 1, 12, 13, 8, "#C08050FF", True))
    step("draw eye", await drawing.draw_rectangle_at(HERO, "eye", 1, 9, 10, 2, 2, "#201810FF", True))

    print("\n=== Aseprite: shade with a palette ramp ===")
    ramp_json = step("suggest_shading_ramp", await dither_tools.suggest_shading_ramp(HERO, 1, 4))
    ramp = ["#3A2416", "#8A5A32", "#C08050", "#E8B888"]
    step("shade_directional", await shading.shade_directional(
        HERO, "body", ramp, 1, light_direction="top-left", style="smooth"))

    px = json.loads(await pixel_read.get_pixels_rect(HERO, 4, 5, 16, 16, "body", 1))
    used = {p["hex"].upper() for p in px if p["a"] > 0}
    on_palette = used <= {c.upper() for c in ramp}
    steps.append(("shading stayed on the ramp", on_palette))
    print(f"{'ok  ' if on_palette else 'FAIL'} {'shading stayed on the ramp':<34} {sorted(used)}")

    print("\n=== Aseprite: animate by moving cels ===")
    step("propagate body", await animation.propagate_cels(HERO, ["body"], 1, 2, 8, True))
    step("propagate eye", await animation.propagate_cels(HERO, ["eye"], 1, 2, 8, True))
    # Idle bob: the body rises and falls twice across 8 frames.
    step("oscillate body", await animation.oscillate_cel_positions(
        HERO, "body", 1, 8, amplitude_x=0, amplitude_y=2, cycles=1.0))
    step("oscillate eye", await animation.oscillate_cel_positions(
        HERO, "eye", 1, 8, amplitude_x=0, amplitude_y=2, cycles=1.0))
    step("tag idle 1-4", await animation.set_tag(HERO, "idle", 1, 4))
    step("tag blink 5-8", await animation.set_tag(HERO, "blink", 5, 8))
    step("frame durations", await animation.set_frame_duration_all(HERO, 120))

    print("\n=== Aseprite: audit before export ===")
    audit = step("audit_animation", await quality.audit_animation(HERO, 1, 8, ["body", "eye"]))
    validated = step("validate_scene", await quality.validate_scene(HERO, ["body", "eye"], 1, 8))
    diff = step("compare_frames 1 vs 3", await analysis.compare_frames(HERO, 1, 3))

    print("\n=== Aseprite: export for Godot ===")
    step("export_spritesheet", await export.export_spritesheet(
        HERO, SHEET, sheet_type="horizontal", data_filename=SHEET_JSON,
        list_tags=True, data_format="json-array"))
    step("export preview x8", await export.export_frame(HERO, 1, f"{ART}/preview.png", scale=8))

    ok_sheet = os.path.exists(SHEET) and os.path.exists(SHEET_JSON)
    steps.append(("sheet + json on disk", ok_sheet))
    print(f"{'ok  ' if ok_sheet else 'FAIL'} {'sheet + json on disk':<34} "
          f"{os.path.getsize(SHEET) if ok_sheet else 0} bytes png")

    data = json.load(open(SHEET_JSON, encoding="utf-8"))
    tags = data["meta"].get("frameTags", [])
    has_tags = [t["name"] for t in tags] == ["idle", "blink"]
    steps.append(("json carries both tags", has_tags))
    print(f"{'ok  ' if has_tags else 'FAIL'} {'json carries both tags':<34} "
          f"{[(t['name'], t['from'], t['to']) for t in tags]}")

    durations = {f["duration"] for f in data["frames"]}
    steps.append(("json carries durations", durations == {120}))
    print(f"{'ok  ' if durations == {120} else 'FAIL'} {'json carries durations':<34} {durations}")


asyncio.run(main())

failed = sum(1 for _, ok in steps if not ok)
print(f"\n{len(steps) - failed}/{len(steps)} passed")
sys.exit(1 if failed else 0)
