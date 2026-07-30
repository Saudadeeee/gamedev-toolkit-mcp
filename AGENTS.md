# GameDev Toolkit MCP — Agent Instructions

Seven MCP servers covering the whole 2D/low-poly game pipeline: planning, art,
models, audio and the engine that consumes them.

| Server | Drives | Owns |
|---|---|---|
| **`obsidian`** | Obsidian | Design docs, task lists, notes — planning before building |
| **`aseprite`** | Aseprite | Pixel art, sprites, spritesheets, palettes |
| **`blockbench`** | Blockbench | 3D models, UV maps, model textures, bone rigs |
| **`rfxgen`** | rfxgen | Retro SFX synthesis — presets, parametric design, variations |
| **`audacity`** | Audacity | Sound effects, music, recording, mastering |
| **`ffmpeg`** | ffmpeg | Format glue — ogg for Godot, GIF/webm from captures, media inspection |
| **`godot-mcp`** | Godot 4 | Scenes, nodes, scripts, gameplay, builds |

Whichever are configured are active at once. `get_toolkit_status` (on the
`aseprite` server) reports which are installed and currently reachable — run it
first when a tool does not respond.

---

## Core Rule: Which Server to Use

| Task | Use |
|---|---|
| Read or write a design doc, plan, or task list | `obsidian` |
| Search notes for a prior decision | `obsidian` |
| Record what was built, as a note | `obsidian` |
| Create or edit a sprite, texture, icon, tile | `aseprite` |
| Draw pixels, shapes, gradients on a canvas | `aseprite` |
| Manage layers, blend modes, opacity | `aseprite` |
| Create or edit animation frames/cels | `aseprite` |
| Shade, dither, snap to a palette | `aseprite` |
| Export PNG, spritesheet, JSON metadata | `aseprite` |
| Create or edit a 3D model, cube, mesh | `blockbench` |
| UV map, texture a model, paint on a model | `blockbench` |
| Rig bones, animate a model | `blockbench` |
| Export glTF/OBJ/Minecraft model formats | `blockbench` |
| Generate a retro/8-bit SFX from scratch (coin, laser, jump…) | `rfxgen` |
| Design an SFX by synthesis parameters, or make variations | `rfxgen` |
| Record, trim, or mix audio | `audacity` |
| Apply audio effects (reverb, EQ, pitch, compression) | `audacity` |
| Generate tones, noise, or chiptune-style SFX | `audacity` |
| Clean up noise, normalise, master a track | `audacity` |
| Export WAV/OGG/MP3 | `audacity` |
| Convert audio to .ogg for Godot music | `ffmpeg` (`convert_audio`) |
| Make a devlog GIF or trailer clip from captures | `ffmpeg` (`make_gif`, `make_video`) |
| Extract video frames as reference for pixel art | `ffmpeg` (`extract_frames`) |
| Create or open a Godot scene | `godot-mcp` |
| Add, edit, or remove a node | `godot-mcp` |
| Write or modify a GDScript | `godot-mcp` |
| Wire a signal between nodes | `godot-mcp` (`connect_signal`) |
| Configure physics, collision, navigation | `godot-mcp` |
| Configure materials, environment, lighting | `godot-mcp` |
| Run, stop, or export the project | `godot-mcp` |
| Load a texture into a Godot node | `godot-mcp` (`load_sprite`) |
| Import spritesheet animation into `AnimatedSprite2D` | `godot-mcp` (`import_animated_sprite`) |
| See what a scene actually looks like | `godot-mcp` (`capture_scene_render`) |

**Each server owns its domain.** Do not build scenes with art tools, do not
author art in the engine, and do not try to make one server do another's job —
the handoff is always a file on disk.

---

## Prerequisites Differ Per Server

This trips up more calls than anything else:

| Server | Needs the app running? | Extra setup |
|---|---|---|
| `aseprite` | **No** — spawns `aseprite --batch` per call | none |
| `godot-mcp` scene tools | **Yes** — editor open, `godot_mcp` plugin enabled | WebSocket on port 9080 |
| `godot-mcp` headless tools | **No** — drives the binary directly | none |
| `blockbench` | **Yes** — app open with the MCP plugin loaded | HTTP, usually port 3000 (the plugin picks it) |
| `rfxgen` | **No** — spawns the rfxgen CLI per call | binary via `RFXGEN_PATH` or standard paths |
| `audacity` | **Yes** — app open with `mod-script-pipe` enabled | Audacity 3.x only |
| `ffmpeg` | **No** — spawns ffmpeg per call | binary via `FFMPEG_PATH` or standard paths |
| `obsidian` | **Yes** — app open with the Local REST API plugin | `OBSIDIAN_API_KEY` from that plugin |

When a call fails with a connection error, check `get_toolkit_status` before
assuming the tool is broken.

---

## Standard Combined Workflow

When a user asks to create a game element such as a character, enemy, tile, or UI element, follow this order:

### Step 0 - Plan, then check what is reachable

```text
obsidian_simple_search / obsidian_get_file_contents  -> prior decisions, the plan
get_toolkit_status                                   -> what is installed and up
```

Read the plan before building and write the outcome back to it. A note in
Obsidian is the only part of this pipeline that survives between sessions.

### Step 1 - Create the art in Aseprite

```text
create_canvas -> add_layer (one per concern) -> draw_*_at / fill_area_at
             -> add_frames + tween/propagate (if animated) -> set_tag -> export_spritesheet
```

Verify with `get_composite_rect` or `export_frame(scale=8)` before moving on. A tool returning "drawn successfully" only means the Lua ran.

### Step 2 - Import into Godot

```text
load_sprite or import_animated_sprite -> create_node -> save_scene
```

### Step 3 - Build the scene structure in Godot

```text
create_scene -> create_node (CharacterBody2D, CollisionShape2D, etc.) -> update_node_property
```

### Step 4 - Wire up logic

```text
godot-mcp script tools -> create or modify GDScript on nodes
```

Always complete Aseprite work and export before referencing the file in Godot. Godot cannot use an `.aseprite` file directly. Export PNG and, for animations, JSON metadata.

---

## Skills

Detailed guidance lives in [`.claude/skills/`](./.claude/skills/). Load the one that matches the task rather than working from this summary alone:

| Skill | Covers |
|---|---|
| `aseprite-pixel-art` | Drawing: layer discipline, the `*_at` tools, shading, dithering, verifying by reading pixels back |
| `aseprite-animation` | Multi-frame work: propagate, eased tweens, tags, audit before export |
| `blockbench-modeling` | 3D models: box modelling, UV layout, texturing from Aseprite art, export formats |
| `audacity-audio` | Game audio: SFX design, loops, mastering, export settings that suit an engine |
| `game-asset-pipeline` | Orchestration across all four: who owns what, handoff formats, folder layout |
| `aseprite-godot-pipeline` | The 2D handoff in detail: `res://` paths, spritesheet JSON, pixel-art import settings |
| `aseprite-mcp-dev` | Editing the `aseprite` server itself (`servers/aseprite/`) |

---

## Aseprite Tool Reference

165 tools total. The ones that matter most:

### Canvas, layers, frames

- `create_canvas(width, height, filename)` - new sprite file
- `add_layer(filename, layer_name, group)` - new layer, optionally inside a group
- `add_group(filename, group_name, parent_group)` - new layer group
- `add_frames(filename, count, duration_ms)` - append animation frames
- `get_sprite_info(filename)` - dimensions, frames, layer tree, tags — call this before guessing names

### Drawing — always use the `*_at` variants

Each tool call spawns its own Aseprite process, so "active layer" is not stable across calls. The `*_at` tools take the target explicitly and use sprite-global coordinates.

- `draw_pixels_at(filename, layer_name, frame_index, pixels)` - pixels are `[{x, y, color}]`
- `draw_line_at(filename, layer_name, frame_index, x1, y1, x2, y2, color, thickness)`
- `draw_rectangle_at(filename, layer_name, frame_index, x, y, width, height, color, fill)`
- `draw_circle_at(filename, layer_name, frame_index, center_x, center_y, radius, color, fill)`
- `draw_ellipse_at`, `fill_area_at`, `draw_polygon`, `draw_path`, `apply_gradient_rect`

Colours accept `#RGB`, `#RGBA`, `#RRGGBB`, `#RRGGBBAA`.

### Verify the result

A success string means the script ran, not that the art is right.

- `get_composite_rect(filename, x, y, width, height, frame_index)` - flattened pixels as JSON
- `export_frame(filename, frame_index, output_filename, scale=8)` - magnified PNG to look at
- `audit_animation(filename, ...)` - missing cels, out-of-range layers, overlaps
- `validate_scene(filename, required_layers, ...)`

### Animation

- `propagate_cels(filename, layer_names, source_frame, start_frame, end_frame)` - static layers across a range
- `tween_cel_positions_eased(...)`, `tween_cel_opacity_eased(...)`, `tween_cel_scale_eased(...)`
- `oscillate_cel_positions(...)` - bobbing/hovering loops
- `set_tag(filename, name, from_frame, to_frame, direction)` - required for spritesheet tag export

### Colour

- `apply_palette_preset(filename, preset)` - gameboy, pico8, c64, dawnbringer16, ...
- `generate_color_ramp(base_color, steps, hue_shift_degrees, lightness_range)`
- `quantize_to_palette(...)`, `remap_colors_in_cel_range(...)`, `get_color_stats(...)`
- `outline_native(...)`, `apply_dither_gradient(...)`, `apply_convolution(...)`

### Export

- `export_sprite(filename, output_filename, format)` - single image
- `export_frame(filename, frame_index, output_filename, scale)`
- `export_spritesheet(filename, output_filename, data_filename, list_tags=True)` - **use `list_tags=True` for Godot**
- `export_tag(filename, tag_name, output_filename)` - `.gif` animates, `.png` sequences
- `export_layers(filename, output_directory)` - one PNG per layer

### Also available

Slices and nine-patch, tilemaps, per-layer and sprite-wide transforms, region move/copy/erase, batch conversion, backup/restore, pixel readback, a preview HTTP server, and `run_lua_script` as an escape hatch.

---

## Godot Tool Reference

### Project and Editor

- `get_project_info()` - read project metadata
- `list_projects()` - list Godot projects
- `launch_editor()` - open Godot editor
- `run_project()` / `stop_project()` - run or stop the game
- `get_debug_output()` - read console output

### Scenes and Nodes

- `create_scene(path, root_type)` - create a new `.tscn` file
- `save_scene()` - save current scene
- `create_node(parent_path, node_type, node_name)` - add a node
- `update_node_property(node_path, property, value)` - set one node property
- `delete_node(node_path)` - delete a node
- `load_sprite(node_path, texture_path)` - assign a texture to a `Sprite2D` or `TextureRect`
- `import_animated_sprite(node_path, texture_path, metadata_path, animation_name, fps, autoplay)` - build `SpriteFrames` for an `AnimatedSprite2D` from Aseprite JSON metadata

### Extended

- **Animation**: AnimationPlayer tracks, keyframes, playback
- **Animation Tree**: state machines, blend trees
- **Environment**: sky, ambient light, fog, tone mapping
- **Material**: StandardMaterial3D, ShaderMaterial
- **Mesh**: MeshInstance, MeshLibrary, export
- **Navigation**: NavigationRegion, navmesh baking
- **Particles**: GPUParticles2D and GPUParticles3D configuration
- **Path**: Path3D, PathFollow, curve editing
- **Playback**: AudioStreamPlayer, VideoStreamPlayer
- **Project Config**: read and write `project.godot` settings
- **Skeleton**: Skeleton3D, bones, IK
- **Theme**: UI theme creation
- **TileMap**: tile placement, TileSet configuration
- **Tween**: property and method tweens
- **Editor Script**: run arbitrary `EditorScript` in-editor

---

## File Path Convention

Aseprite saves files wherever you specify. Godot expects `res://` paths for internal resources.

- Export Aseprite art into the Godot project folder if Godot needs to use it.
- Example texture path: `res://assets/sprites/player.png`
- Example metadata path: `res://assets/sprites/player_sheet.json`

---

## Common Patterns

### Pixel art character with physics

```text
1. create_canvas(16, 16, "player.aseprite")
2. add_layer -> draw body pixels on separate layers
3. add_frame x N for walk animation
4. export_spritesheet -> player_sheet.png + player_sheet.json
5. create_scene("res://scenes/player.tscn", "CharacterBody2D")
6. create_node -> CollisionShape2D, AnimatedSprite2D
7. import_animated_sprite(AnimatedSprite2D path, "res://assets/player_sheet.png", "res://assets/player_sheet.json")
8. update_node_property -> set extra playback or transform properties if needed
```

### Tilemap level

```text
1. create_canvas(128, 128, "tileset.aseprite") - 8x8 tiles at 16x16px
2. draw tiles on separate layers or frames
3. export_spritesheet -> tileset.png + tileset.json
4. create_scene("res://scenes/level.tscn", "Node2D")
5. create_node -> TileMap
6. use godot-mcp tilemap tools to configure TileSet and place tiles
```

### UI element

```text
1. Aseprite -> draw button or icon art, export PNG
2. Godot -> create_node(TextureRect or TextureButton)
3. load_sprite -> assign exported texture
4. update_node_property -> set size, position, anchor
```

---

## Error Handling

- If an Aseprite export fails, check that `ASEPRITE_PATH` is set correctly and Aseprite supports `--batch` mode.
- If a Godot command fails with `not connected`, the Godot editor must be open with the plugin enabled and the WebSocket server running on port `9080`.
- Always verify an exported file exists before referencing it in Godot.
- If a node path is wrong in Godot, inspect the current scene tree or call `get_project_info()`.

---

## Setup Checklist

Run `python scripts/verify_toolkit.py --quick` rather than checking these by
hand — it probes every one of them and prints what is still missing.

- [ ] Python 3.12+, `uv`, Node.js 18+, and `git` installed
- [ ] `uv sync --directory servers/aseprite` completed
- [ ] `npm --prefix servers/godot/server run build` completed
- [ ] `python scripts/install_vendored.py` completed (venvs for the vendored servers)
- [ ] `python scripts/write_mcp_config.py` completed (writes `mcp_config.json`)
- [ ] Aseprite installed and `ASEPRITE_PATH` configured
- [ ] Godot 4.x installed, project open in the editor with `godot_mcp` enabled
- [ ] `OBSIDIAN_API_KEY` set — `python scripts/configure_obsidian.py`
- [ ] All seven servers registered in the MCP client config

Which servers exist and how each is installed comes from
[`toolkit.json`](toolkit.json). Nothing else hardcodes that list — if a server
is missing everywhere, that file is the place to look.
