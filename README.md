# Game Asset MCP Toolkit

Five MCP (Model Context Protocol) servers covering the complete game pipeline —
planning, pixel art, 3D models, audio, and the engine that consumes them —
driven entirely through natural language.

Two servers are built and maintained here. Three are integrated from upstream:
cloned into `vendor/` and installed, never copied into this repo's source.

| Server | Drives | Source | Tools |
|---|---|---|---|
| `aseprite` | Aseprite | **this repo** | 165 |
| `godot-mcp` | Godot 4 | **this repo** | 141 |
| `blockbench` | Blockbench | [jasonjgardner/blockbench-mcp-plugin](https://github.com/jasonjgardner/blockbench-mcp-plugin) · GPL-3.0 | 94 |
| `audacity` | Audacity 3.x | [xDarkzx/Audacity-MCP](https://github.com/xDarkzx/Audacity-MCP) · Apache-2.0 | 131 + 9 pipelines |
| `obsidian` | Obsidian | [MarkusPfundstein/mcp-obsidian](https://github.com/MarkusPfundstein/mcp-obsidian) · MIT | 15 |

`get_toolkit_status` reports which applications are installed and which bridges
are currently reachable — all three integrated servers need their app running,
the two local ones mostly do not.

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue)](https://python.org)
[![Node.js 18+](https://img.shields.io/badge/Node.js-18+-green)](https://nodejs.org)
[![Godot 4.x](https://img.shields.io/badge/Godot-4.x-blue)](https://godotengine.org)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-purple)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## What This Is

All configured servers run simultaneously. An AI assistant reads [`AGENTS.md`](./AGENTS.md) to learn which server owns which domain, and routes each task accordingly:

```
User request
     │
     ▼
AI reads AGENTS.md
     ├── plan / design doc / notes     →  obsidian    (15 tools, upstream)
     ├── sprite / texture / animation  →  aseprite    (165 tools, this repo)
     ├── 3D model / UV / rig           →  blockbench  (94 tools, upstream plugin)
     ├── SFX / music / audio cleanup   →  audacity    (131 tools, upstream)
     └── scene / node / script / build →  godot-mcp   (141 tools, this repo)
```

**Combined workflow for a complete game element:**

```
[Aseprite]  create_canvas → add_layer → draw_*_at → tween_cel_positions_eased → export_spritesheet
                                                                              │
[Godot]                                              load_sprite -> create_node -> create_script -> save_scene
```

---

## How This Differs from the Original godot-mcp

This project is **not** a simple tool addition. It is a ground-up architectural overhaul compared to the original subprocess-based [bradypp/godot-mcp](https://github.com/bradypp/godot-mcp):

| Dimension | Original (bradypp/godot-mcp) | This Project |
|---|---|---|
| **Godot Tools** | 16 | 141 |
| **Aseprite Tools** | 0 | 165 |
| **Total MCP Tools** | 16 | 306 in-repo (+ Blockbench and Audacity upstream) |
| **MCP Resources** | None | 10+ resource endpoints |
| **Godot Connection** | Subprocess spawn per command | Persistent WebSocket bridge via Godot plugin |
| **Godot Version** | 3.5+ and 4.x | Godot 4.x only |
| **Aseprite Support** | None | Full Lua injection pipeline |
| **3D Capabilities** | Minimal (MeshLibrary export only) | Full: skeleton IK, navmesh, particles, lights, environment |
| **Animation Systems** | Basic node creation | AnimationPlayer, AnimationTree, Tween — all supported |
| **Project Config Access** | None | Full read/write to project.godot settings |
| **Editor Scripting** | None | Execute arbitrary EditorScript inside running editor |
| **MCP Framework** | @modelcontextprotocol/sdk 0.6.0 | FastMCP 1.20.4 (higher-level, more capable) |
| **AI Routing Guide** | README only | AGENTS.md — machine-readable instruction file |
| **Setup Automation** | Manual | One-click scripts for Windows and macOS/Linux |
| **Monorepo** | No | Yes — Godot + Aseprite as unified pipeline |

### Architecture Change: Subprocess → WebSocket Plugin

The original godot-mcp spawns Godot as a subprocess for each command. This project uses a fundamentally different design:

```
Original:  AI → MCP Server → spawn godot process → parse stdout → return
This fork: AI → MCP Server → WebSocket → Godot Plugin (running inside editor) → real-time response
```

The Godot plugin (`addons/godot_mcp/`) runs a WebSocket server on port 9080 inside the Godot editor. The MCP server communicates with the live editor session, enabling real-time scene manipulation, live resource queries, and persistent state — none of which are possible with subprocess invocation.

---

## Projects

### [Godot-MCP](./Godot-MCP/)

Godot 4 plugin + Node.js MCP server. AI assistants interact with your live Godot editor in real time via WebSocket.

- **Based on:** [ee0pdt/Godot-MCP](https://github.com/ee0pdt/Godot-MCP)
- **Stack:** TypeScript (MCP server) + GDScript (Godot plugin)
- **Tool modules:** 23 TypeScript modules → 141 tools
- **GDScript command modules:** 20 modules handling execution inside the editor
- **MCP Resources:** 10+ live data endpoints (scene tree, scripts, project settings, etc.)

**Extended beyond the ee0pdt base with:**

| Module | Capabilities |
|---|---|
| `animation_tools` | Create animations, add tracks, insert/remove keyframes, query animation data |
| `animation_tree_tools` | Configure AnimationTree, add nodes, connect nodes, get/set parameters |
| `environment_tools` | Configure WorldEnvironment, sky, fog, camera, lights |
| `material_tools` | Create materials, set properties, assign to mesh surfaces |
| `mesh_tools` | Create ArrayMesh, primitive meshes, height map meshes, save to file |
| `navigation_tools` | Configure NavigationRegion, bake navmesh, set agent targets, query paths |
| `particle_tools` | Configure GPUParticles, set emission shapes, materials, restart |
| `path_tools` | Configure PathFollow, add/remove/set path points, clear paths |
| `playback_tools` | Control AnimationPlayer playback, get play status |
| `project_config_tools` | Read/write project.godot settings, import settings, reimport files |
| `skeleton_tools` | Get bone poses, set bone transforms, configure IK, reset bones |
| `theme_tools` | Create themes, set colors/constants/fonts/styleboxes, assign to nodes |
| `tilemap_tools` | Set/erase tile cells, paint areas, clear layers; GridMap support |
| `tween_tools` | Animate node properties via tween, generate tween scripts |
| `editor_tools` | Execute EditorScript, get current scene, play/stop scene |
| `capture_tools` | **Render a scene offscreen and return the image** — visual feedback without running the game |
| `signal_tools` | **Signal wiring** (connect/disconnect/list, persistent) and **node groups** |
| `headless_tools` | **Works with the editor closed**: export builds, validate projects, reimport assets, run GDScript |

### [aseprite-mcp](./aseprite-mcp/)

Python MCP server. Controls Aseprite programmatically via Lua script injection into its CLI (`aseprite --batch`).

- **Merged from:** [diivi/aseprite-mcp](https://github.com/diivi/aseprite-mcp) upstream + this fork's own tools
- **Stack:** Python 3.12+
- **Tool modules:** 34 Python modules → 165 tools

**This fork adds on top of the diivi base:**

| Module | Capabilities |
|---|---|
| `drawing_advanced.py` | Bezier curves, projected linear/radial gradients, thick brush strokes, image-tiled fills |
| `effects.py` | Posterize, pixelate, drop shadow — the effects Aseprite has no native filter for |
| `layer_advanced.py` | Reparent a layer into/out of a group, merge N layers in z-order |
| `cel_operations.py` | Cel linking across a frame range |
| `transform_sprite.py` | Sprite-wide flip/rotate/resize/crop/trim, grid bounds |
| `palette_extra.py` | Palette file import (.gpl/.act/.ase), simple create/get/append |
| `slices_extra.py` | Nine-patch slices, slice export with JSON map |
| `export_extra.py` | Every frame as its own numbered file |
| `file_utils.py` | Batch convert, optimize, backup/restore, cross-file sprite comparison |
| `ai_features.py` | Brightness-ramp recolor, lineart cleanup, structural audit, batch ops, hue variations |
| `shading.py` | Directional shading (8 light directions, smooth/hard/pillow), CIELAB palette snapping, antialias detect + apply |
| `dither_tools.py` | 15 dither patterns, Floyd-Steinberg error diffusion, perceptual palette sorting, ramp suggestion |
| `core/color_space.py` | CIELAB conversion, perceptual nearest-colour matching, Rec. 709 luminance |
| `system_info.py` | Aseprite + Godot path auto-detection — the bridge to `godot-mcp` |

Upstream contributes the animation engine (eased tweens, tags, onion skin), pixel readback, scene validation/audit, native engine filters, dithering and the layer-targeted `*_at` drawing tools.

---

## Quick Start

**Option A — Automated (recommended):**

```bash
# Clone
git clone https://github.com/Saudadeeee/Godot-x-Aseprite-MCP-all.git
cd "Godot-x-Aseprite-MCP-all"

# Windows
.\setup.ps1

# macOS / Linux
chmod +x setup.sh && ./setup.sh
```

The script checks prerequisites, installs dependencies, builds the server, auto-detects Aseprite, and writes a ready-to-use `mcp_config.json`.

**Option B — Manual:**

```bash
# 1. Install Python dependencies (aseprite-mcp)
cd aseprite-mcp && uv sync

# 2. Build Node.js server (Godot-MCP)
cd ../Godot-MCP/server && npm install && npm run build

# 3. Enable Godot plugin
#    Copy addons/godot_mcp/ into your Godot 4 project root
#    Project Settings → Plugins → Godot MCP → Enable

# 4. Configure your MCP client (see section below)
```

**Option C — the three upstream servers:**

Cloned into `vendor/` (gitignored) and installed into their own virtualenvs, so
their source never enters this repo's history or licence surface.

```bash
mkdir -p vendor && cd vendor

# Audacity (Apache-2.0) -- stdio, over Audacity's scripting pipe
git clone --depth 1 https://github.com/xDarkzx/Audacity-MCP
cd Audacity-MCP && uv venv && uv pip install -e . "mcp[cli]>=1.0,<2" && cd ..
#   The <2 pin matters: mcp 2.0 removed mcp.server.fastmcp, which this server
#   imports. Its own dependency is unpinned, so a fresh install picks 2.x and
#   dies at startup with ModuleNotFoundError.
#   Then in Audacity: Edit > Preferences > Modules > mod-script-pipe = Enabled,
#   and restart. Audacity 3.x only -- 4.x is not supported upstream.

# Obsidian (MIT) -- stdio, over the Local REST API plugin
git clone --depth 1 https://github.com/MarkusPfundstein/mcp-obsidian
cd mcp-obsidian && uv venv && uv pip install -e . "mcp>=1.1,<2" && cd ..
#   Install the "Local REST API" community plugin in Obsidian, then copy its
#   API key into OBSIDIAN_API_KEY in mcp_config.json.

# Blockbench (GPL-3.0) -- a plugin inside the app; nothing to install here
#   1. Blockbench > File > Plugins > Load Plugin from URL
#   2. https://jasonjgardner.github.io/blockbench-mcp-plugin/mcp.js
#   3. Grant the network permission it asks for
#   4. Leave Blockbench open; it serves http://localhost:3000/bb-mcp
#   The MCP client reaches it through mcp-remote (already in mcp_config.json).
```

The entry point for Audacity-MCP is the console script `audacity-mcp`, not
`python -m audacity_mcp` — the package has no `__main__.py`.

Verify everything at once with `get_toolkit_status` (on the `aseprite` server).
It reports which applications were found and which bridges are actually
reachable, with the fix for each miss.

For full instructions, troubleshooting, and platform-specific notes: **[SETUP.md](./SETUP.md)**

---

## MCP Client Configuration

```json
{
  "mcpServers": {
    "aseprite": {
      "command": "uv",
      "args": ["--directory", "/path/to/aseprite-mcp", "run", "-m", "aseprite_mcp"],
      "env": { "ASEPRITE_PATH": "/path/to/aseprite" }
    },
    "godot-mcp": {
      "command": "node",
      "args": ["/path/to/Godot-MCP/server/dist/index.js"],
      "env": { "MCP_TRANSPORT": "stdio" }
    }
  }
}
```

Config file locations:
- **Claude Desktop — Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Claude Desktop — macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Claude Code:** `claude mcp add` or project `.mcp.json`

---

## Tool Reference

### Godot-MCP — 141 Tools

| Category | Tools |
|---|---|
| **Node** | create_node, delete_node, update_node_property, get_node_properties, list_nodes, load_sprite, import_animated_sprite |
| **Scene** | create_scene, open_scene, save_scene, create_resource, list_filesystem_files, scan_filesystem |
| **Script** | create_script, get_script, edit_script, create_script_template |
| **Editor** | execute_editor_script, get_current_scene, play_main/custom/current_scene, stop_playing_scene, get_play_status |
| **Project Config** | get_project_info, get/set_project_setting, list_project_settings, get/set_import_settings, reimport_file |
| **TileMap** | set/erase_tile_cell, get_tile_data, get_used_tiles, paint_tile_area, clear_tilemap_layer |
| **GridMap** | set/erase_gridmap_cell, get_gridmap_used_cells |
| **Animation** | create/delete_animation, list_animations, add/remove_animation_track, insert/remove_animation_key, get_animation_data |
| **AnimationTree** | configure_animation_tree, add/connect_animation_tree_nodes, get/set_animation_tree_parameter |
| **Material** | create_material, set_material_property, set_mesh_surface_material, get_material_properties |
| **Mesh** | create_array_mesh, create_primitive_mesh, get_mesh_info, generate_normals, create_from_height_map, save_mesh |
| **Navigation** | configure_navigation_region, bake_navigation_mesh, set_navigation_target, get_navigation_path |
| **Particles** | configure_particles, set_particle_emission_shape/material, restart_particles, get_particle_info |
| **Environment** | configure_environment, set_sky/fog, configure_camera, set_light_property |
| **Skeleton** | get_skeleton_info, get/set_bone_pose, configure_skeleton_ik, start_ik, reset_bone_poses |
| **Theme** | create_theme, set_theme_color/constant/font/font_size/stylebox, assign_theme_to_node, get_theme_items |
| **Tween** | animate_node_property, create_tween_script, create_animation_from_tween |
| **Path** | configure_path_follow, add/remove/set_path_point, get_path_info, clear_path |
| **Playback** | play_animation, stop_animation, get_play_status |
| **Toolkit Status** | get_toolkit_status, get_app_info, get_aseprite_info, get_godot_info, get_blockbench_info, get_audacity_info, get_system_info, resolve_application_path |
| **Visual Feedback** | capture_scene_render, capture_editor_viewport |
| **Signals & Groups** | list_signals, list_connections, connect_signal, disconnect_signal, add/remove_node_to_group, list_nodes_in_group |
| **Headless (no editor)** | godot_headless_info, validate_project_headless, list_export_presets, export_project, import_project_assets, run_headless_script |

### Godot-MCP — 10+ Resource Endpoints

Real-time data queried from the live Godot editor session:

`scene_list` · `scene_structure` · `script_list` · `script` · `script_metadata` · `project_structure` · `project_settings` · `project_resources` · `editor_state` · `selected_node` · `current_script` · `playback_state` · `input_map` · `audio_bus_layout` · `all_project_settings` · `tilemap_data` · `gridmap_data` · `animation_list` · `animation_data` · `import_settings` · `material`

---

### aseprite-mcp — 165 Tools

| Category | Tools |
|---|---|
| **Canvas** | create_canvas, add_layer, add_group, add_frame, set_frame, set_frame_duration, set_layer |
| **Drawing** | draw_pixels, draw_line, draw_rectangle, draw_circle, fill_area — each with a layer-targeted `*_at` variant — plus draw_ellipse_at, draw_polygon, draw_path, apply_gradient_rect |
| **Drawing Advanced** | draw_bezier_curve, draw_gradient, draw_pattern, apply_brush_stroke |
| **Animation** | add_frames, set_frame_duration_all, duplicate_frame_range, copy_frame, delete_frame, set_tag, delete_tag, set_onion_skin, propagate_cels, propagate_frame_to_range |
| **Cel** | create_cel, copy_cel, clear_cel, set_cel_position, set_cel_opacity, offset_cel_positions, link_cels |
| **Tweening** | tween_cel_positions, tween_cel_positions_eased, tween_cel_opacity_eased, tween_cel_scale_eased, oscillate_cel_positions |
| **Layer** | delete_layer, rename_layer, duplicate_layer, reorder_layer, set_layer_visibility/opacity/blend_mode, merge_layer_down, merge_layers, flatten_sprite, move_layer_to_group, copy_layers_between_sprites |
| **Pixel Readback** | get_pixel_color, get_pixels_rect, get_composite_pixel, get_composite_rect |
| **Analysis & QA** | get_sprite_info, get_color_stats, compare_frames, render_onion_skin, validate_scene, audit_animation, animation_sanitize, ensure_layers_present, suggest_improvements |
| **Palette** | get_palette, set_palette, create_palette, add_color_to_palette, get_palette_colors, load_palette_from_file, generate_color_ramp, quantize_to_palette, remap_colors_in_cel_range, list/apply_palette_preset, set_color_mode |
| **Effects** | outline_native, outline_cel, adjust_hsl, adjust_hsl_native, adjust_brightness_contrast, invert_colors, apply_convolution, replace_color, apply_dither_gradient, apply_dither_pattern, posterize, pixelate, drop_shadow |
| **Regions** | move_region, copy_region, erase_region, erase_color |
| **Transform** | flip_layer, rotate_layer, resize_canvas, crop_canvas, flip_horizontal/vertical, rotate, resize_sprite, crop_sprite, trim_sprite, set_sprite_grid |
| **Tilemap** | create_tilemap_layer, draw_on_tile, set_tiles, get_tile_at, get_tilemap_info |
| **Slices** | create_slice, create_nine_patch_slice, set_slice_center/pivot, list_slices, delete_slice, export_slices |
| **Export** | export_sprite, export_frame, export_tag, export_layers, export_spritesheet, export_frames_separately, copy_sprite, import_image_as_layer |
| **File Utils** | batch_convert, batch_process_sprites, backup_sprite, restore_sprite, compare_sprites, optimize_file_size, generate_sprite_variations |
| **System Info** | get_app_info, get_aseprite_info, get_godot_info, get_system_info, resolve_application_path |
| **Shading** | shade_directional, suggest_shading_ramp, snap_to_palette, detect_antialias_candidates, apply_antialias |
| **Dithering** | list_dither_patterns, apply_dither_texture, apply_dither_gradient_pattern, apply_floyd_steinberg, sort_sprite_palette |
| **Escape Hatches** | run_lua_script, start/stop_preview_server, animation_workflow_guide |

---

## Example Prompts

```
Create a 16x16 player sprite with idle and walk animations,
export it as a spritesheet with JSON metadata, then set it up
in Godot as a CharacterBody2D with AnimatedSprite2D, imported SpriteFrames, and CollisionShape2D.
```

```
Draw a 128x128 tileset with grass, dirt, and stone tiles at 16x16px,
then create a TileMap level in Godot and paint a 20x15 map using those tiles.
```

```
Make an enemy sprite with a hit-flash effect, export it, then create an
enemy scene in Godot with AnimationPlayer, health system, patrol AI script,
and a died signal connected to the game manager.
```

```
Build a complete HUD: draw health bar and coin counter assets in Aseprite,
import them into Godot, set up a CanvasLayer with Control nodes, and write
a GDScript that updates the HUD when the player's stats change.
```

---

## Repository Structure

```
Godot x Aseprite MCP/
├── AGENTS.md                       # AI routing instructions (auto-loaded by Claude)
├── SETUP.md                        # Full setup guide with troubleshooting
├── setup.sh                        # One-click setup (Linux/macOS)
├── setup.ps1                       # One-click setup (Windows)
├── claude_desktop_config.json      # MCP config template
│
├── Godot-MCP/
│   ├── addons/godot_mcp/           # Godot 4 plugin — copy into your project
│   │   ├── commands/               # 20 GDScript command handler modules
│   │   ├── ui/                     # Editor panel (dock)
│   │   └── utils/                  # WebSocket server, connection manager
│   ├── server/
│   │   └── src/
│   │       ├── tools/              # 19 TypeScript MCP tool modules
│   │       ├── resources/          # 10+ MCP resource endpoint definitions
│   │       └── utils/              # WebSocket client, connection utilities
│   └── docs/
│
└── aseprite-mcp/
    ├── aseprite_mcp/
    │   ├── core/                   # MCP server core, Lua injector, command runner
    │   ├── tools/                  # 31 Python tool modules
    │   └── utils/                  # Lua script templates, constants
    └── tests/
```

---

## Requirements

| Component | Version | Purpose |
|---|---|---|
| Python | 3.12+ | aseprite-mcp server |
| uv | latest | Python dependency manager |
| Node.js | 18+ | Godot-MCP server |
| Godot Engine | 4.x | Target game engine (plugin required) |
| Aseprite | 1.3+ | Pixel art tool (CLI scripting required) |

---

## Credits

| Project | Original Author | Repository |
|---|---|---|
| Godot-MCP | [@ee0pdt](https://github.com/ee0pdt) | [ee0pdt/Godot-MCP](https://github.com/ee0pdt/Godot-MCP) |
| aseprite-mcp | [@diivi](https://github.com/diivi) | [diivi/aseprite-mcp](https://github.com/diivi/aseprite-mcp) |

Both original projects are MIT licensed. This fork extends both without altering their core architecture, while combining them into a unified game-development pipeline.

---

## Credits

This project merges and extends several open-source MCP servers. See [CREDITS.md](./CREDITS.md) for exactly what came from where.

## License

MIT — Copyright (c) 2026 Saudade. See [LICENSE](./LICENSE).

The two merged upstreams keep their own copyright notices in
`aseprite-mcp/LICENSE` and `Godot-MCP/LICENSE`. The three integrated servers
are installed from their own projects under their own licences and are not
redistributed here — see [CREDITS.md](./CREDITS.md).

**Maintainer:** Saudade
