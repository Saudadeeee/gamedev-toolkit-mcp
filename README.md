# Godot x Aseprite MCP

A monorepo combining two fully-extended MCP (Model Context Protocol) servers that cover the complete 2D game asset pipeline — pixel art creation in **Aseprite** and scene/logic building in **Godot Engine** — controlled entirely through natural language via AI assistants.

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue)](https://python.org)
[![Node.js 18+](https://img.shields.io/badge/Node.js-18+-green)](https://nodejs.org)
[![Godot 4.x](https://img.shields.io/badge/Godot-4.x-blue)](https://godotengine.org)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-purple)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## What This Is

Two MCP servers run simultaneously. An AI assistant reads [`AGENTS.md`](./AGENTS.md) to understand when to use Aseprite (art) vs Godot (scenes/logic), and routes each task automatically:

```
User request
     │
     ▼
AI reads AGENTS.md
     ├── art / sprite / animation task  →  aseprite-mcp tools (70+ tools)
     └── scene / node / script task    →  godot-mcp tools (100+ tools)
```

**Combined workflow for a complete game element:**

```
[Aseprite]  create_canvas → add_layer → draw_pixels → apply_effects → export_sprite_sheet
                                                                              │
[Godot]                                              load_sprite -> create_node -> create_script -> save_scene
```

---

## How This Differs from the Original godot-mcp

This project is **not** a simple tool addition. It is a ground-up architectural overhaul compared to the original subprocess-based [bradypp/godot-mcp](https://github.com/bradypp/godot-mcp):

| Dimension | Original (bradypp/godot-mcp) | This Project |
|---|---|---|
| **Godot Tools** | 16 | 100+ |
| **Aseprite Tools** | 0 | 70+ |
| **Total MCP Tools** | 16 | 170+ |
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
- **Tool modules:** 19 TypeScript modules → 100+ tools
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

### [aseprite-mcp](./aseprite-mcp/)

Python MCP server. Controls Aseprite programmatically via Lua script injection into its CLI (`aseprite --batch`).

- **Based on:** [diivi/aseprite-mcp](https://github.com/diivi/aseprite-mcp)
- **Stack:** Python 3.12+
- **Tool modules:** 17 Python modules → 70+ tools

**Extended beyond the diivi base with:**

| Module | Capabilities |
|---|---|
| `drawing_advanced.py` | Polygons, Bezier curves, gradients, patterns, brush strokes, text |
| `layer_advanced.py` | Layer groups, blend modes, opacity control, layer moving/merging |
| `cel_operations.py` | Copy/move/clear/link cels, set cel opacity, tile get/set |
| `effects.py` | Blur, HSL adjust, brightness/contrast, posterize, pixelate, outline, drop shadow, invert |
| `transform.py` | Flip, rotate, crop, resize, scale, expand canvas, trim |
| `selection.py` | Select all/rectangle, deselect, invert, delete selection |
| `clipboard.py` | Copy/cut/paste, paste as new layer, merge layers |
| `spritesheet.py` | Export spritesheets with JSON metadata, extract color palettes, generate variations |
| `tilemap.py` | Create tilesets, tilemap layers, import tileset from image, setup tileset |
| `slices.py` | List/create slices, nine-patch slices, export slices |
| `file_utils.py` | Batch convert, optimize, backup/restore, compare sprites, convert color mode |
| `ai_features.py` | Auto colorization, AI-guided upscaling, auto outline, lineart cleanup |

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

### Godot-MCP — 100+ Tools

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
| **System Info** | get_application_info, get_godot_info, get_aseprite_info, get_system_info, resolve_application_path |

### Godot-MCP — 10+ Resource Endpoints

Real-time data queried from the live Godot editor session:

`scene_list` · `scene_structure` · `script_list` · `script` · `script_metadata` · `project_structure` · `project_settings` · `project_resources` · `editor_state` · `selected_node` · `current_script` · `playback_state` · `input_map` · `audio_bus_layout` · `all_project_settings` · `tilemap_data` · `gridmap_data` · `animation_list` · `animation_data` · `import_settings` · `material`

---

### aseprite-mcp — 70+ Tools

| Category | Tools |
|---|---|
| **Canvas** | create_canvas, add_layer, add_frame |
| **Drawing** | draw_pixels, draw_line, draw_rectangle, draw_circle, fill_area, erase_area |
| **System Info** | get_app_info, get_aseprite_info, get_godot_info, get_system_info, resolve_application_path |
| **Drawing Advanced** | draw_polygon, draw_bezier_curve, draw_gradient, draw_pattern, draw_text, apply_brush_stroke |
| **Layer** | (basic layer management from original) |
| **Layer Advanced** | create_layer_group, copy/rename_layer, toggle_visibility, move_to_group, merge_layers, set_blend_mode/opacity |
| **Cel Operations** | copy/move/clear/link_cel, set_cel_opacity, get/set_tile |
| **Selection** | select_all, select_rectangle, deselect, invert_selection, delete_selection |
| **Effects** | apply_blur, adjust_hue_saturation, adjust_brightness_contrast, posterize, pixelate, outline, drop_shadow, invert_colors |
| **Transform** | flip_horizontal/vertical, rotate_image, crop_sprite, resize_sprite, scale_sprite, expand_canvas, trim_sprite |
| **Clipboard** | copy/cut/paste_to_clipboard, paste_as_new_layer, merge_layers |
| **Export** | export_sprite, export_sprite_sheet, export_sprite_sheet_with_json, export_frames_separately, export_layers_separately, export_tileset |
| **Spritesheet** | export_sprite_sheet_with_json, extract_color_palette_smart, generate_sprite_variations |
| **Palette** | create_palette, load_palette_from_file, add_color_to_palette, get_palette_colors |
| **Brush** | list_brushes, create_custom_brush, set_brush_size/angle/pattern |
| **Tilemap** | create_tileset, create_tilemap_layer, import_tileset_from_image, setup_tileset |
| **Slices** | list_slices, create_slice, create_nine_patch_slice, export_slices |
| **File Utils** | batch_convert, batch_process_sprites, backup/restore_sprite, compare_sprites, optimize_file_size, convert_color_mode, get_sprite_info |
| **AI Features** | auto_color_sprite, upscale_sprite_ai, auto_outline_sprite, auto_cleanup_lineart, suggest_improvements |

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
    │   ├── tools/                  # 17 Python tool modules
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

## License

MIT — see individual `LICENSE` files in each subdirectory.
