---
name: aseprite-animation
description: Building sprite animations with aseprite-mcp — animate cels instead of redrawing frames, propagate static layers, use eased tweens, tag loop ranges, and audit coverage before export. Use for any multi-frame sprite work.
---

# Animating with aseprite-mcp

The single biggest efficiency win: **animate by moving cels, not by redrawing each frame.** An 8-frame walk cycle redrawn frame-by-frame is 8× the drawing work and 8× the opportunities for inconsistency. Draw once, then transform.

## When to activate

- Any sprite with more than one frame
- Walk cycles, idle loops, attack animations, effects
- Parallax or scrolling backgrounds
- Anything that will be exported as a spritesheet with tags

## Workflow

### 1. Block out frames and layers first

```
create_canvas(width, height, filename)
add_layer(filename, "body")
add_layer(filename, "hair")
add_frames(filename, count, duration_ms)
set_frame_duration_all(filename, duration_ms)
```

Separate anything that moves independently onto its own layer. Secondary motion — hair, cape, accessories — is what makes an animation read as alive, and it only works if those parts can move on their own timeline.

### 2. Draw frame 1 only

Use the `*_at` tools with `frame_index=1`. See the `aseprite-pixel-art` skill for drawing specifics.

### 3. Propagate what does not move

```
propagate_cels(filename, layer_names, source_frame, start_frame, end_frame, replace=True)
copy_cel(filename, layer_name, source_frame, target_frame, replace=True)
copy_frame(filename, source_frame, target_frame, overwrite=True)
propagate_frame_to_range(filename, source_frame, start_frame, end_frame, overwrite=True)
duplicate_frame_range(filename, start_frame, end_frame, times=1)
```

A static background or an unchanging torso should be propagated once, not drawn eight times.

### 4. Animate by transforming cels

```
tween_cel_positions_eased(filename, layer_name, start_frame, end_frame,
                          start_x, start_y, end_x, end_y,
                          easing="smoothstep", create_missing_cels=True)
tween_cel_opacity_eased(filename, layer_name, start_frame, end_frame,
                        start_opacity, end_opacity, easing="smoothstep")
tween_cel_scale_eased(filename, layer_name, start_frame, end_frame,
                      start_scale, end_scale, easing="smoothstep", anchor="center")
oscillate_cel_positions(filename, layer_name, start_frame, end_frame,
                        amplitude_x, amplitude_y, cycles=1.0, phase_deg=0.0)
offset_cel_positions(filename, layer_name, start_frame, end_frame, dx, dy)
set_cel_position(filename, layer_name, frame_index, x, y, create_if_missing=False)
```

`oscillate_cel_positions` is the one to reach for on loops — bobbing idle, breathing, hovering, floating. `cycles` controls how many full oscillations fit in the range; `phase_deg` offsets one layer against another so hair lags behind the head.

`create_missing_cels=True` when the layer has no cel yet on the target frames; combine with `source_frame_index` to say which cel to copy from.

Set `create_missing_cels` deliberately. Left False on empty frames, the tween silently affects nothing.

### 5. Tag the loop ranges

```
set_tag(filename, name, from_frame, to_frame, direction="forward")   # or "reverse", "pingpong"
delete_tag(filename, name)
```

Tags are what `export_tag` and Godot's `import_animated_sprite` consume. An untagged multi-animation sprite forces whoever imports it to guess frame boundaries.

### 6. Audit before export

This is the step that catches problems a success string will not:

```
audit_animation(filename, start_frame, end_frame, layer_names,
                overlap_pairs=["body,hair"], layer_frame_ranges=["hair:1-8"])
validate_scene(filename, required_layers, start_frame, end_frame)
ensure_layers_present(filename, layer_names, start_frame, end_frame)
animation_sanitize(filename, ..., out_of_range_action="set_opacity_zero", report_only=True)
```

`audit_animation` returns JSON listing layers missing cels, cels active outside their intended frame range, and unwanted overlaps between layer pairs. `animation_sanitize` can fix what it finds — run it with `report_only=True` first to see what it would change.

`layer_frame_ranges` format is `["layer:1-8,17-24", "clouds:1-12"]`. `overlap_pairs` is `["layerA,layerB"]`.

### 7. Inspect visually

```
render_onion_skin(filename, frame_index, output_filename, before=1, after=1, scale=4, ghost_opacity=100)
compare_frames(filename, frame_a, frame_b)
export_frame(filename, frame_index, output_filename, scale=8)
```

`render_onion_skin` writes a PNG showing neighbouring frames ghosted behind the current one — the standard way to check spacing and arc smoothness. `compare_frames` reports how much actually changed between two frames; near-zero change usually means a propagate or tween silently did nothing.

### 8. Export

```
export_tag(filename, tag_name, output_filename, scale=1)        # .gif animates, .png sequences
export_spritesheet(filename, output_filename, sheet_type="horizontal",
                   data_filename="sheet.json", list_tags=True, data_format="json-array")
export_frames_separately(filename, output_folder, prefix, format, scale)
```

For Godot, export a spritesheet **with** `data_filename` and `list_tags=True` — `import_animated_sprite` needs that JSON to build `SpriteFrames`.

## Timing reference

Frame durations are milliseconds. Common pixel-art rates:

| Feel | ms/frame | ≈ fps |
|---|---|---|
| Snappy action, attacks | 60–80 | 12–16 |
| Standard walk/run | 100–120 | 8–10 |
| Idle, ambient | 150–250 | 4–6 |

Uniform timing reads as mechanical. Hold key poses longer than in-betweens — set the range with `set_frame_duration_all`, then override individual frames with `set_frame_duration`.

## Anti-patterns

| Don't | Do |
|---|---|
| Redraw the sprite each frame | Draw frame 1, then tween/propagate |
| Draw a static background 8 times | `propagate_cels` |
| Linear motion everywhere | `tween_*_eased` with `smoothstep` |
| Hand-place a bobbing loop | `oscillate_cel_positions` |
| Export untagged multi-animation sheets | `set_tag` per animation, `list_tags=True` |
| Assume tweens landed | `audit_animation` + `render_onion_skin` |
| Put everything on one layer | One layer per independently-moving part |
