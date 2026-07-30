# GameDev Toolkit MCP

Five MCP (Model Context Protocol) servers covering the complete game pipeline —
planning, pixel art, 3D models, audio, and the engine that consumes them —
driven entirely through natural language.

All five live under [`servers/`](./servers/) and are tracked here: two built and
maintained in this repo, three vendored verbatim from upstream.
[`toolkit.json`](./toolkit.json) is the single registry that says which is which —
setup, config generation and verification all read it, so nothing hardcodes the list.

| Server | Drives | Source | Tools |
|---|---|---|---|
| `aseprite` | Aseprite | **this repo** · MIT | 165 |
| `godot-mcp` | Godot 4 | **this repo** · MIT | 141 |
| `blockbench` | Blockbench | vendored — [jasonjgardner/blockbench-mcp-plugin](https://github.com/jasonjgardner/blockbench-mcp-plugin) · GPL-3.0 | 94 |
| `audacity` | Audacity 3.x | vendored — [xDarkzx/Audacity-MCP](https://github.com/xDarkzx/Audacity-MCP) · Apache-2.0 | 131 + 9 pipelines |
| `obsidian` | Obsidian | vendored — [MarkusPfundstein/mcp-obsidian](https://github.com/MarkusPfundstein/mcp-obsidian) · MIT | 15 |

`get_toolkit_status` reports which applications are installed and which bridges
are currently reachable — all three vendored servers need their app running, the
two first-party ones mostly do not.

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue)](https://python.org)
[![Node.js 18+](https://img.shields.io/badge/Node.js-18+-green)](https://nodejs.org)
[![Godot 4.x](https://img.shields.io/badge/Godot-4.x-blue)](https://godotengine.org)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-purple)](https://modelcontextprotocol.io)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue)](LICENSE)

---

## What This Is

All configured servers run simultaneously. An AI assistant reads [`AGENTS.md`](./AGENTS.md) to learn which server owns which domain, and routes each task accordingly:

```
User request
     │
     ▼
AI reads AGENTS.md
     ├── plan / design doc / notes     →  obsidian    (15 tools, vendored)
     ├── sprite / texture / animation  →  aseprite    (165 tools, first-party)
     ├── 3D model / UV / rig           →  blockbench  (94 tools, vendored)
     ├── SFX / music / audio cleanup   →  audacity    (131 tools, vendored)
     └── scene / node / script / build →  godot-mcp   (141 tools, first-party)
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
| **Total MCP Tools** | 16 | 306 first-party, 546 with the vendored servers |
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

### [godot-mcp](./servers/godot/)

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

### [aseprite](./servers/aseprite/)

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
git clone https://github.com/Saudadeeee/gamedev-toolkit-mcp.git
cd gamedev-toolkit-mcp

.\setup.ps1                          # Windows
chmod +x setup.sh && ./setup.sh      # macOS / Linux
```

One script does the lot: checks prerequisites, installs the two first-party
servers, builds the vendored ones' virtualenvs, auto-detects your applications,
and writes an `mcp_config.json` covering **all five** servers.

**Option B — Manual**, from the repository root:

```bash
# 1. The aseprite server (Python)
uv sync --directory servers/aseprite

# 2. The godot-mcp server (TypeScript)
npm --prefix servers/godot/server install
npm --prefix servers/godot/server run build

# 3. The vendored servers -- builds each one's venv from the in-tree source
python scripts/install_vendored.py

# 4. The Godot plugin, into your game project
python scripts/install_godot_plugin.py /path/to/your/godot/project

# 5. Obsidian's key (after installing its Local REST API plugin)
python scripts/configure_obsidian.py

# 6. Generate mcp_config.json for every server
python scripts/write_mcp_config.py
```

Blockbench needs no build here — its source is vendored for reference and
licence compliance, but the plugin is loaded by the app itself:
`File > Plugins > Load Plugin from URL` →
`https://jasonjgardner.github.io/blockbench-mcp-plugin/mcp.js`, grant the
network permission, and leave Blockbench open.

**Check it all:**

```bash
python scripts/verify_toolkit.py --quick
```

Probes every prerequisite, application, install, live bridge and MCP handshake,
then lists the manual steps still outstanding. `get_toolkit_status` (on the
`aseprite` server) reports the same state from inside an MCP session.

For full instructions, troubleshooting, and platform-specific notes: **[docs/setup.md](./docs/setup.md)**

---

## MCP Client Configuration

Do not write this by hand — generate it:

```bash
python scripts/write_mcp_config.py            # writes mcp_config.json
python scripts/write_mcp_config.py --print    # preview, write nothing
```

It resolves every entry in `toolkit.json` against this machine: absolute repo
paths, the console script inside each virtualenv, detected application paths,
and the port a live bridge is actually on. Re-running is safe — API keys and
hand-corrected values already in `mcp_config.json` are carried over rather than
reset to placeholders.

```json
{
  "mcpServers": {
    "aseprite": {
      "command": "uv",
      "args": ["--directory", "/abs/path/to/servers/aseprite", "run", "-m", "aseprite_mcp"],
      "cwd": "/abs/path/to/servers/aseprite",
      "env": { "ASEPRITE_PATH": "/abs/path/to/aseprite" }
    },
    "godot-mcp": {
      "command": "node",
      "args": ["/abs/path/to/servers/godot/server/dist/index.js"],
      "env": { "MCP_TRANSPORT": "stdio" }
    }
  }
}
```

`mcp_config.json` holds absolute local paths and API keys. It is gitignored —
keep it that way.

Config file locations:
- **Claude Desktop — Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Claude Desktop — macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Claude Code:** `claude mcp add` or project `.mcp.json`

---

## Tool Reference

### godot-mcp — 141 Tools

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

### godot-mcp — 10+ Resource Endpoints

Real-time data queried from the live Godot editor session:

`scene_list` · `scene_structure` · `script_list` · `script` · `script_metadata` · `project_structure` · `project_settings` · `project_resources` · `editor_state` · `selected_node` · `current_script` · `playback_state` · `input_map` · `audio_bus_layout` · `all_project_settings` · `tilemap_data` · `gridmap_data` · `animation_list` · `animation_data` · `import_settings` · `material`

---

### aseprite — 165 Tools

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
gamedev-toolkit-mcp/
├── toolkit.json                # THE REGISTRY — every server, how it installs,
│                               #   how it is configured, how it is probed.
│                               #   Everything below reads it; nothing hardcodes
│                               #   the server list.
├── AGENTS.md                   # AI routing instructions (auto-loaded by Claude)
├── CREDITS.md                  # what came from where
├── LICENSE                     # GPL-3.0, verbatim
├── COPYRIGHT                   # per-component licence inventory, modification
│                               #   status, and what the licence asks of you
├── setup.sh / setup.ps1        # one-click setup; sequences the scripts below
│
├── docs/setup.md               # setup, troubleshooting, updating a vendored server
│
├── .claude/skills/             # task playbooks the assistant loads on demand
│
├── servers/                    # every MCP server, all tracked
│   ├── aseprite/               # first-party · Python — Aseprite over Lua batch
│   │   ├── aseprite_mcp/
│   │   │   ├── core/           # command runner, Lua injector, path resolver
│   │   │   ├── tools/          # tool modules, one per domain
│   │   │   └── utils/          # shared Lua snippets and constants
│   │   └── tests/
│   │
│   ├── godot/                  # first-party · TypeScript server + editor plugin
│   │   ├── addons/godot_mcp/   # installed into your Godot project
│   │   │   ├── commands/       # GDScript command handlers
│   │   │   ├── ui/             # editor dock
│   │   │   └── utils/          # WebSocket server, connection manager
│   │   ├── server/src/
│   │   │   ├── tools/          # TypeScript MCP tool modules
│   │   │   ├── resources/      # MCP resource endpoints
│   │   │   └── utils/          # WebSocket client, Godot CLI wrapper
│   │   └── docs/
│   │
│   ├── audacity/               # vendored · Apache-2.0 — verbatim upstream
│   ├── obsidian/               # vendored · MIT        — verbatim upstream
│   └── blockbench/             # vendored · GPL-3.0    — verbatim upstream
│                               #   (runs inside the app; not built here)
│
└── scripts/
    ├── _toolkit.py             # shared registry access + probes
    ├── _mcp_probe.py           # MCP stdio handshake, application bridges
    ├── install_vendored.py     # build the vendored servers' virtualenvs
    ├── write_mcp_config.py     # generate mcp_config.json for all five
    ├── verify_toolkit.py       # one command to check everything
    ├── _repo_checks.py         # registry, script and setup-script checks
    ├── install_godot_plugin.py
    ├── configure_obsidian.py
    └── checks/
        ├── test_vendored.py         # the vendored servers' own upstream suites
        ├── check_upstream_drift.py  # vendored trees vs upstream HEAD
        ├── probe_mcp_server.mjs
        └── gdcheck.py
```

Every check lives in `scripts/` and runs locally through
`scripts/verify_toolkit.py` — the single gate. CI is a thin wrapper over the
same scripts, on both Windows and Linux: the two worst bugs in this repo's
history were platform divergences (a BEL byte that broke only Windows setup, a
hardcoded path separator that failed only on Linux), and one platform cannot
see either class. A monthly workflow also diffs each vendored server against
its upstream HEAD, since vendored fixes stop arriving on their own.

### `first-party` vs `vendored`

All five are tracked in the same place. `toolkit.json` records an `origin` per
server, which decides only **who fixes its bugs** and how an update arrives:

| | `first-party` | `vendored` |
|---|---|---|
| Servers | `aseprite`, `godot-mcp` | `audacity`, `obsidian`, `blockbench` |
| Who fixes bugs | this repo | upstream |
| How to change it | edit it | send it upstream; see [docs/setup.md](./docs/setup.md#pulling-a-newer-upstream-into-a-vendored-server) |
| Modified here | yes, extensively | no — verbatim copies |

Until the GPL-3.0 relicense, the upstream servers were cloned into a gitignored
`external/` to keep GPL code out of an MIT repo. That constraint is gone, and
with it the two-tier layout. [COPYRIGHT](./COPYRIGHT) records what each
component is and whether it was modified.

---

## Requirements

| Component | Version | Purpose |
|---|---|---|
| Python | 3.12+ | `aseprite` server |
| uv | latest | Python dependency manager |
| Node.js | 18+ | `godot-mcp` server |
| Godot Engine | 4.x | Target game engine (plugin required) |
| Aseprite | 1.3+ | Pixel art tool (CLI scripting required) |

---

## Credits

The two first-party servers started as forks:

| Server | Original Author | Repository | Licence |
|---|---|---|---|
| `godot-mcp` | [@ee0pdt](https://github.com/ee0pdt) | [ee0pdt/Godot-MCP](https://github.com/ee0pdt/Godot-MCP) | MIT |
| `aseprite` | [@diivi](https://github.com/diivi) | [diivi/aseprite-mcp](https://github.com/diivi/aseprite-mcp) | MIT |

The other three are vendored verbatim, each keeping its own licence:

| Server | Author | Repository | Licence |
|---|---|---|---|
| `audacity` | [@xDarkzx](https://github.com/xDarkzx) | [xDarkzx/Audacity-MCP](https://github.com/xDarkzx/Audacity-MCP) | Apache-2.0 |
| `obsidian` | [@MarkusPfundstein](https://github.com/MarkusPfundstein) | [MarkusPfundstein/mcp-obsidian](https://github.com/MarkusPfundstein/mcp-obsidian) | MIT |
| `blockbench` | [@jasonjgardner](https://github.com/jasonjgardner) | [jasonjgardner/blockbench-mcp-plugin](https://github.com/jasonjgardner/blockbench-mcp-plugin) | GPL-3.0 |

[CREDITS.md](./CREDITS.md) records exactly what came from where, including
features adapted rather than copied.

## License

**GPL-3.0-or-later** — Copyright (C) 2026 Saudade. See [LICENSE](./LICENSE).

This project was MIT through commit `c5f32f4`. It became GPL-3.0 when the
Blockbench plugin was vendored: GPL-3.0 code cannot be redistributed under a
more permissive licence, and every other component (MIT, Apache-2.0) flows
one-way into GPL-3.0.

What that means in practice:

- **Using it changes nothing.** GPL obligations attach to distribution, not use.
- **Art, audio, models and code it produces are yours.** GPL-3.0 covers the
  program, not its output. Licence your game however you like.
- **Forking and distributing** requires releasing your source under GPL-3.0,
  keeping the notices, and stating what you changed.

Every component keeps its own copyright notice and licence file in its
directory. [COPYRIGHT](./COPYRIGHT) is the full inventory, and covers the
details — modification status per component, and the Godot addon you copy into
your own project.

**Maintainer:** Saudade
