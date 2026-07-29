# Aseprite MCP

A Python MCP (Model Context Protocol) server that gives an AI agent programmatic control of Aseprite for pixel art, animation and game-asset workflows. **162 tools.**

[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io/)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-green)](https://python.org/)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-blue)](https://docker.com/)

---

## Credits

Based on **[aseprite-mcp](https://github.com/diivi/aseprite-mcp)** by [@diivi](https://github.com/diivi), which pioneered MCP integration with Aseprite via Lua script injection. This fork merges upstream's full tool set with its own additions.

---

## How it works

Every tool builds a Lua script and runs it through `aseprite --batch <file> --script <tmp>`. Three properties make that reliable:

**Errors are never silent.** Aseprite's batch runner discards a top-level `return "message"` and always exits 0, so a failing script looks identical to a succeeding one. Scripts here print `ERROR:<message>` and go through `AsepriteCommand.execute_lua_script_checked`, which scans stdout and turns that into a failed tool call.

**Strings are escaped.** Filenames and layer names pass through `lua_escape` before interpolation, so a name containing a quote or backslash cannot break out of the Lua literal. Paths that would escape upward are rejected by `reject_traversal`.

**Coordinates are sprite-global.** Aseprite's `cel.image:putPixel` works in cel-local space, so drawing at (10, 10) lands somewhere else once a cel has been moved. Tools call `normalize_cel` first, which replaces the cel image with a canvas-sized one anchored at (0, 0).

Layer lookup (`FIND_LAYER`) searches inside groups and accepts `group/child` paths, backtracking correctly when a layer's own name contains a slash.

---

## Tools by area

| Area | Module | What it covers |
|---|---|---|
| Canvas & layers | `canvas`, `layers`, `layer_advanced`, `scene` | Create canvas, layers, groups, frames; rename/delete/duplicate/reorder; blend modes; merge down; **merge N layers**; **reparent a layer into a group**; copy layers between sprites |
| Drawing | `drawing`, `drawing_advanced` | Pixels, lines, rects, circles, ellipses, polygons, freehand paths, rectangular gradients; layer-targeted `*_at` variants; **Bezier curves**, **projected linear/radial gradients**, **thick brush strokes**, **image-tiled fills** |
| Animation | `animation`, `cel_operations` | Frames, durations, tags, onion skin, cel copy/clear/position, propagation, eased tweens (position, opacity, scale), oscillation; **cel linking** |
| Color | `palette`, `palette_extra`, `fx`, `native_fx`, `effects`, `dither_tools`, `shading` | Get/set palette, presets, color ramps, quantize, remap, color mode; HSL, replace color; native engine filters (outline, convolution, brightness/contrast, invert, palette extraction); **palette file import**, **posterize**, **pixelate**, **drop shadow**, **directional shading**, **15 dither patterns + Floyd-Steinberg**, **CIELAB palette snapping**, **antialiasing**, **perceptual palette sort** |
| Reading back | `pixel_read`, `analysis`, `quality` | Per-pixel and per-region reads (layer or composite), color stats, frame diffing, onion-skin render; scene validation, animation audit and sanitize |
| Regions & geometry | `selection`, `slices`, `slices_extra`, `tilemap`, `transform`, `transform_sprite` | Move/copy/erase regions, erase by color; slices and pivots, **9-patch slices**, **slice export**; tilemap layers and tiles; per-layer flip/rotate/resize/crop, **sprite-wide flip/rotate/resize/crop/trim**, **grid bounds** |
| Export | `export`, `export_extra` | PNG/GIF/etc, single frames, tags, per-layer files, sprite sheets with JSON data, image import; **every frame as a numbered file** |
| Environment | `system_info`, `file_utils`, `preview`, `script`, `guide`, `ai_features` | **Aseprite/Godot path detection**, **batch convert**, **backup/restore**, **sprite comparison**, preview HTTP server, raw Lua escape hatch, workflow guide; **brightness-ramp recolor**, **lineart cleanup**, **structural audit**, **batch ops**, **hue variations** |

**Bold** entries are this fork's additions; the rest come from upstream.

### Pixel-art specific techniques

Aseprite has no filter for these; they need the silhouette and a colour ramp.

```python
# Build a ramp from colours already in the sprite, then light it
ramp = await suggest_shading_ramp("hero.aseprite", steps=5)
await shade_directional("hero.aseprite", "body", ramp, 1,
                        light_direction="top-left", style="smooth")

# Dither instead of blending: a smooth gradient would add hundreds of colours
await list_dither_patterns()          # bayer2x2/4x4/8x8, grass, water, stone, ...
await apply_dither_texture("rock.aseprite", "surface", 0, 0, 32, 32,
                           "#4A4A55", "#6E6E7A", pattern="stone", only_opaque=True)

# Force imported art onto a fixed palette, matched perceptually not in RGB
await snap_to_palette("import.aseprite", "art", PICO8_COLORS)

# Smooth staircase diagonals -- inspect first, it costs palette entries
await detect_antialias_candidates("hero.aseprite", "outline")
```

### Getting visual feedback

The agent is not blind. `export_frame(..., scale=8)` writes a magnified PNG to look at, and `get_composite_rect` / `get_pixels_rect` return the actual pixel values as JSON. Use them to check work instead of assuming a draw call landed.

---

## Installation

### Prerequisites
- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv)
- Aseprite 1.3+ with scripting support

### Setup

```bash
uv sync
```

Point `ASEPRITE_PATH` at the executable, either in a `.env` file next to `pyproject.toml` or in the environment:

```bash
# .env
ASEPRITE_PATH=D:/Games/Aseprite/aseprite/build/bin/aseprite.exe
```

If `ASEPRITE_PATH` is unset or points at a missing file, `core/path_resolver.py` searches the usual install locations (Program Files, Steam, `%LOCALAPPDATA%`, `/Applications`, `$PATH`) for both Aseprite and Godot. Call `get_app_info` to see what it found.

### Claude Desktop / Claude Code config

```json
{
  "mcpServers": {
    "aseprite": {
      "command": "uv",
      "args": ["--directory", "/path/to/aseprite-mcp", "run", "-m", "aseprite_mcp"],
      "env": { "ASEPRITE_PATH": "/path/to/aseprite" }
    }
  }
}
```

---

## Docker

```bash
docker build -t aseprite-mcp:latest .
docker run -it --rm aseprite-mcp:latest
```

Or use `build-docker.sh` / `build-docker.ps1`, or `docker-compose up aseprite-mcp`. See [DOCKER.md](DOCKER.md).

---

## Usage examples

### Draw and verify

```python
await create_canvas(64, 64, "sprite.aseprite")
await add_layer("sprite.aseprite", "body")
await draw_rectangle_at("sprite.aseprite", "body", 1, 10, 10, 40, 40, "#FF0000FF", True)

# Look at what actually landed
await get_composite_rect("sprite.aseprite", 10, 10, 4, 4, 1)
await export_frame("sprite.aseprite", 1, "preview.png", scale=8)
```

### Animation

```python
await create_canvas(32, 32, "anim.aseprite")
await add_layer("anim.aseprite", "ball")
await add_frames("anim.aseprite", 7)

# Animate by moving the cel, not by redrawing each frame
await draw_circle_at("anim.aseprite", "ball", 1, 8, 8, 6, "#FFCC00FF", True)
await tween_cel_positions_eased("anim.aseprite", "ball", 1, 8, 0, 0, 20, 0,
                                easing="smoothstep", create_missing_cels=True)
await set_tag("anim.aseprite", "roll", 1, 8)
await export_tag("anim.aseprite", "roll", "roll.gif")

# Check layer coverage and overlaps before shipping
await audit_animation("anim.aseprite")
```

### Tileset and slices

```python
await create_canvas(128, 128, "tiles.aseprite")
await create_tilemap_layer("tiles.aseprite", "ground", 16, 16)
await set_sprite_grid("tiles.aseprite", 0, 0, 16, 16)
await create_nine_patch_slice("tiles.aseprite", "panel",
                              {"x": 0, "y": 0, "width": 48, "height": 48},
                              {"x": 16, "y": 16, "width": 16, "height": 16})
await export_spritesheet("tiles.aseprite", "tiles.png",
                         data_filename="tiles.json", list_tags=True)
```

`animation_workflow_guide("character")` returns a short workflow summary if you want the agent to orient itself first.

---

## Troubleshooting

**Aseprite not found** — Tools return `Cannot run Aseprite at '<path>'` rather than crashing the server. Check `get_aseprite_info`, then set `ASEPRITE_PATH`. Verify the binary runs headless: `aseprite --batch --version`.

**A tool reports failure with an empty message** — Aseprite crashed rather than erroring. Usually a Lua API misuse; reproduce the script with `run_lua_script` to see where it stops.

**"Unsupported chunk type 0" warnings on open** — the .aseprite file is damaged. Restore from `backup_sprite` output; `restore_sprite` takes the timestamp from the backup filename.

**Layer not found** — Names are matched exactly, groups included. Use `get_sprite_info` to list the real names; nested layers can be addressed as `group/child`.

---

## License

MIT — see [LICENSE](LICENSE). Original project by [@diivi](https://github.com/diivi), MIT.
