"""Heuristic assist tools: palette mapping, lineart cleanup, batch runs, audits.

None of these call an external model — the "AI" here is ordinary image
heuristics run inside Aseprite. Anything better handled by a real engine
filter (outline, palette extraction, upscaling) lives in :mod:`native_fx`,
:mod:`palette` and :mod:`transform_sprite` instead.
"""

import json
import os
import shutil
from typing import List

from ..core.commands import AsepriteCommand, lua_escape, reject_traversal
from ..core.lua import FIND_LAYER, NORMALIZE_CEL
from ..core.colors import parse_hex_color
from .. import mcp

_SPRITE_EXTENSIONS = (".aseprite", ".ase")


def _cel_preamble(layer_name: str, frame_index: int) -> str:
    """Lua preamble resolving a layer+frame to a canvas-sized cel image."""
    safe_layer = lua_escape(layer_name)
    return f"""
    {FIND_LAYER}
    {NORMALIZE_CEL}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local target = find_layer(spr, "{safe_layer}")
    if not target then print("ERROR:Layer not found") return end
    if target.isGroup then print("ERROR:Layer is a group") return end

    local cel = normalize_cel(spr, target, idx, false)
    if not cel then print("ERROR:No cel at that layer/frame") return end
    local img = cel.image
    """


@mcp.tool()
async def auto_color_sprite(
    filename: str,
    layer_name: str,
    color_palette: list,
    frame_index: int = 1,
) -> str:
    """Recolor a cel by mapping pixel brightness onto a ramp of palette colors.

    Darkest pixels take the first color, brightest the last. This is the fast
    way to turn a greyscale sketch or a flat silhouette into a shaded sprite:
    pass the palette dark-to-light.

    Args:
        filename: Aseprite file to modify
        layer_name: Layer to recolor
        color_palette: Hex colors ordered dark to light, at least 2
        frame_index: Frame index starting at 1
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if not color_palette or len(color_palette) < 2:
        return "color_palette needs at least 2 colors"

    entries = []
    for color in color_palette:
        rgba = parse_hex_color(color)
        if rgba is None:
            return f"Invalid color value: {color}"
        r, g, b, _ = rgba
        entries.append(f"{{{r}, {g}, {b}}}")

    palette_lua = ", ".join(entries)

    script = f"""
    {_cel_preamble(layer_name, frame_index)}

    local ramp = {{{palette_lua}}}
    local changed = 0

    app.transaction(function()
        for y = 0, img.height - 1 do
            for x = 0, img.width - 1 do
                local c = Color(img:getPixel(x, y))
                if c.alpha > 0 then
                    -- Rec. 601 luma, so mid-greens do not read as brighter
                    -- than mid-reds the way a flat average makes them.
                    local luma = 0.299 * c.red + 0.587 * c.green + 0.114 * c.blue
                    local slot = math.floor(luma / 256 * #ramp) + 1
                    slot = math.max(1, math.min(#ramp, slot))
                    local t = ramp[slot]
                    img:drawPixel(x, y, Color(t[1], t[2], t[3], c.alpha))
                    changed = changed + 1
                end
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("pixels=" .. changed)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return (
            f"Recolored '{layer_name}' frame {frame_index} with "
            f"{len(color_palette)} ramp colors ({output.strip()})"
        )
    return f"Failed to auto-color: {output}"


@mcp.tool()
async def auto_cleanup_lineart(
    filename: str,
    layer_name: str,
    frame_index: int = 1,
    min_neighbors: int = 1,
    dry_run: bool = False,
) -> str:
    """Remove stray pixels that have too few opaque neighbours.

    Scanning and photo-traced lineart leaves single-pixel noise that reads as
    dirt at sprite scale. Raise ``min_neighbors`` to strip thin dangling ends
    too, but check with ``dry_run`` first — 2 or more will eat legitimate
    single-pixel detail.

    Args:
        filename: Aseprite file to modify
        layer_name: Layer to clean
        frame_index: Frame index starting at 1
        min_neighbors: Keep a pixel only if it has at least this many opaque
            neighbours in its 8-neighbourhood
        dry_run: Report how many pixels would be removed without touching them
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if min_neighbors < 1 or min_neighbors > 8:
        return "min_neighbors must be between 1 and 8"

    apply_changes = "false" if dry_run else "true"

    script = f"""
    {_cel_preamble(layer_name, frame_index)}

    local threshold = {min_neighbors}
    local doomed = {{}}

    for y = 0, img.height - 1 do
        for x = 0, img.width - 1 do
            if Color(img:getPixel(x, y)).alpha > 0 then
                local neighbors = 0
                for dy = -1, 1 do
                    for dx = -1, 1 do
                        if dx ~= 0 or dy ~= 0 then
                            local nx, ny = x + dx, y + dy
                            if nx >= 0 and ny >= 0 and nx < img.width and ny < img.height then
                                if Color(img:getPixel(nx, ny)).alpha > 0 then
                                    neighbors = neighbors + 1
                                end
                            end
                        end
                    end
                end
                if neighbors < threshold then doomed[#doomed + 1] = {{x, y}} end
            end
        end
    end

    -- Collected first, cleared second: clearing during the scan would change
    -- the neighbour counts of pixels not yet visited.
    if {apply_changes} and #doomed > 0 then
        app.transaction(function()
            for _, p in ipairs(doomed) do
                img:drawPixel(p[1], p[2], Color(0, 0, 0, 0))
            end
        end)
        spr:saveAs(spr.filename)
    end

    print("stray=" .. #doomed)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if not success:
        return f"Failed to clean lineart: {output}"

    verb = "would remove" if dry_run else "removed"
    return f"Lineart cleanup on '{layer_name}' frame {frame_index}: {verb} {output.strip()}"


@mcp.tool()
async def suggest_improvements(filename: str) -> str:
    """Audit a sprite for common pixel-art and game-asset problems.

    Returns JSON with the metrics it measured plus a list of suggestions, so
    the findings can be acted on directly rather than re-derived.

    Args:
        filename: Aseprite file to inspect
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"

    script = """
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local layer_count, group_count, empty_cels = 0, 0, 0
    local function walk(layers)
        for _, l in ipairs(layers) do
            if l.isGroup then
                group_count = group_count + 1
                walk(l.layers)
            else
                layer_count = layer_count + 1
                for f = 1, #spr.frames do
                    local cel = l:cel(f)
                    if cel and cel.bounds.width == 0 then empty_cels = empty_cels + 1 end
                end
            end
        end
    end
    walk(spr.layers)

    local unique = {}
    local unique_count, opaque = 0, 0
    for _, cel in ipairs(spr.cels) do
        local img = cel.image
        for y = 0, img.height - 1 do
            for x = 0, img.width - 1 do
                local px = img:getPixel(x, y)
                if Color(px).alpha > 0 then
                    opaque = opaque + 1
                    if not unique[px] then
                        unique[px] = true
                        unique_count = unique_count + 1
                    end
                end
            end
        end
    end

    local palette_size = 0
    if spr.palettes[1] then palette_size = #spr.palettes[1] end

    print(string.format(
        '{"width":%d,"height":%d,"frames":%d,"layers":%d,"groups":%d,' ..
        '"empty_cels":%d,"unique_colors":%d,"opaque_pixels":%d,' ..
        '"palette_size":%d,"color_mode":%d,"tags":%d}',
        spr.width, spr.height, #spr.frames, layer_count, group_count,
        empty_cels, unique_count, opaque, palette_size, spr.colorMode, #spr.tags))
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if not success:
        return f"Failed to analyze sprite: {output}"

    try:
        metrics = json.loads(output.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return f"Failed to parse analysis output: {output}"

    suggestions: List[str] = []
    if metrics["width"] % 8 or metrics["height"] % 8:
        suggestions.append(
            f"Canvas is {metrics['width']}x{metrics['height']}; multiples of 8 "
            "pack more cleanly into atlases and tile grids."
        )
    if metrics["layers"] > 10 and metrics["groups"] == 0:
        suggestions.append(
            f"{metrics['layers']} layers and no groups — group them so layer-targeted "
            "tools stay unambiguous."
        )
    if metrics["unique_colors"] > 64:
        suggestions.append(
            f"{metrics['unique_colors']} distinct colors is high for pixel art; "
            "quantize_to_palette will tighten it."
        )
    if metrics["palette_size"] > 64 and metrics["color_mode"] == 1:
        suggestions.append(
            f"Indexed sprite carries a {metrics['palette_size']}-entry palette; "
            "trim unused entries."
        )
    if metrics["empty_cels"]:
        suggestions.append(
            f"{metrics['empty_cels']} empty cels take up space; clear_cel or "
            "animation_sanitize will drop them."
        )
    if metrics["frames"] > 1 and metrics["tags"] == 0:
        suggestions.append(
            f"{metrics['frames']} frames with no tags — set_tag names the loop ranges "
            "so export_tag can pull them out."
        )
    if metrics["opaque_pixels"] == 0:
        suggestions.append("Sprite is fully transparent — nothing has been drawn yet.")
    if not suggestions:
        suggestions.append("No structural issues found.")

    return json.dumps({"metrics": metrics, "suggestions": suggestions}, indent=2)


@mcp.tool()
async def batch_process_sprites(folder: str, operations: list, recursive: bool = False) -> str:
    """Run a fixed set of maintenance operations over every sprite in a folder.

    Supported operations: "trim" (crop transparent borders), "optimize"
    (re-save to shrink the file), "cleanup" (remove stray single pixels on
    every layer and frame).

    Args:
        folder: Folder containing .aseprite/.ase files
        operations: Operation names to apply, in order
        recursive: Descend into subfolders
    """
    traversal = reject_traversal(folder)
    if traversal:
        return traversal
    if not os.path.isdir(folder):
        return f"Folder {folder} not found"

    supported = {"trim", "optimize", "cleanup"}
    unknown = [op for op in operations if op not in supported]
    if unknown:
        return f"Unsupported operations: {', '.join(unknown)}. Supported: {', '.join(sorted(supported))}"
    if not operations:
        return "operations cannot be empty"

    paths: List[str] = []
    if recursive:
        for root, _, names in os.walk(folder):
            paths.extend(
                os.path.join(root, n) for n in names if n.lower().endswith(_SPRITE_EXTENSIONS)
            )
    else:
        paths = [
            os.path.join(folder, n)
            for n in os.listdir(folder)
            if n.lower().endswith(_SPRITE_EXTENSIONS)
        ]

    if not paths:
        return f"No .aseprite or .ase files found in {folder}"

    steps = []
    if "trim" in operations:
        steps.append("app.command.AutocropSprite{ ui = false }")
    if "cleanup" in operations:
        steps.append("""
        for _, cel in ipairs(spr.cels) do
            local img = cel.image
            local doomed = {}
            for y = 0, img.height - 1 do
                for x = 0, img.width - 1 do
                    if Color(img:getPixel(x, y)).alpha > 0 then
                        local n = 0
                        for dy = -1, 1 do
                            for dx = -1, 1 do
                                if dx ~= 0 or dy ~= 0 then
                                    local nx, ny = x + dx, y + dy
                                    if nx >= 0 and ny >= 0 and nx < img.width and ny < img.height
                                       and Color(img:getPixel(nx, ny)).alpha > 0 then
                                        n = n + 1
                                    end
                                end
                            end
                        end
                        if n == 0 then doomed[#doomed + 1] = {x, y} end
                    end
                end
            end
            for _, p in ipairs(doomed) do img:drawPixel(p[1], p[2], Color(0, 0, 0, 0)) end
        end
        """)

    body = "\n".join(steps)
    processed: List[str] = []
    failed: List[str] = []

    for path in paths:
        script = f"""
        local spr = app.activeSprite
        if not spr then print("ERROR:No active sprite") return end
        app.transaction(function()
        {body}
        end)
        spr:saveAs(spr.filename)
        print("OK")
        """
        success, output = AsepriteCommand.execute_lua_script_checked(script, path)
        if success:
            processed.append(os.path.basename(path))
        else:
            failed.append(f"{os.path.basename(path)}: {output.strip()}")

    summary = (
        f"Applied [{', '.join(operations)}] to {len(processed)}/{len(paths)} sprites in {folder}"
    )
    if failed:
        summary += "\nFailed:\n" + "\n".join(f"  - {f}" for f in failed)
    return summary


@mcp.tool()
async def generate_sprite_variations(
    filename: str,
    output_folder: str,
    hue_steps: list | None = None,
) -> str:
    """Produce recolored copies of a sprite, one per hue shift.

    Each variation is a full .aseprite copy with the whole sprite hue-rotated,
    which is the usual way to get palette-swap enemy or team variants.

    Args:
        filename: Source Aseprite file
        output_folder: Folder to write variations into (created if missing)
        hue_steps: Hue rotations in degrees, e.g. [60, 120, 180, 240, 300].
            Defaults to five evenly spaced shifts.
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    traversal = reject_traversal(output_folder)
    if traversal:
        return traversal

    steps = hue_steps if hue_steps else [60, 120, 180, 240, 300]
    try:
        steps = [int(s) for s in steps]
    except (TypeError, ValueError):
        return "hue_steps must be a list of integers"
    if not steps:
        return "hue_steps cannot be empty"

    os.makedirs(output_folder, exist_ok=True)
    basename, extension = os.path.splitext(os.path.basename(filename))

    created: List[str] = []
    failed: List[str] = []

    for shift in steps:
        out_name = f"{basename}_hue{shift:+d}{extension}"
        out_path = os.path.join(output_folder, out_name)
        shutil.copy2(filename, out_path)

        script = f"""
        local spr = app.activeSprite
        if not spr then print("ERROR:No active sprite") return end
        app.command.HueSaturation{{ ui = false, hue = {shift}, target = "sprite" }}
        spr:saveAs(spr.filename)
        print("OK")
        """
        success, output = AsepriteCommand.execute_lua_script_checked(script, out_path)
        if success:
            created.append(out_name)
        else:
            failed.append(f"{out_name}: {output.strip()}")
            os.remove(out_path)

    summary = f"Generated {len(created)}/{len(steps)} variations in {output_folder}"
    if created:
        summary += "\n" + "\n".join(f"  - {name}" for name in created)
    if failed:
        summary += "\nFailed:\n" + "\n".join(f"  - {f}" for f in failed)
    return summary
