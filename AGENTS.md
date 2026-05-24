# CLAUDE.md — Godot x Aseprite MCP

This workspace contains two MCP servers that work together as a unified 2D game development pipeline:

- **`aseprite`** — controls Aseprite for all pixel art, sprite, and animation work
- **`godot-mcp`** — controls Godot Engine for all scene, node, and game logic work

Both servers are always active. You have full access to tools from both at the same time.

---

## Core Rule: Which Tool to Use

| Task | Use |
|---|---|
| Create or edit a sprite, texture, icon, tile | `aseprite` |
| Draw pixels, shapes, gradients on a canvas | `aseprite` |
| Manage layers, blend modes, opacity | `aseprite` |
| Create or edit animation frames/cels | `aseprite` |
| Export PNG, spritesheet, JSON metadata | `aseprite` |
| Apply image effects (blur, outline, HSL) | `aseprite` |
| Work with palettes and colors | `aseprite` |
| Create or open a Godot scene | `godot-mcp` |
| Add, edit, or remove a node | `godot-mcp` |
| Write or modify a GDScript | `godot-mcp` |
| Configure physics, collision, navigation | `godot-mcp` |
| Set up animations in AnimationPlayer | `godot-mcp` |
| Configure materials, environment, lighting | `godot-mcp` |
| Run or stop the Godot project | `godot-mcp` |
| Load a sprite/texture into a Godot node | `godot-mcp` (`load_sprite`) |

**Never use Godot tools to create art. Never use Aseprite tools to build scenes.**

---

## Standard Combined Workflow

When a user asks to create a game element (character, enemy, tile, UI element), follow this order:

### Step 1 — Create the art in Aseprite
```
create_canvas → add_layer → draw_* / fill_area → add_frame (if animated) → export_sprite
```

### Step 2 — Import into Godot
```
load_sprite (path to exported PNG) → add_node (Sprite2D / AnimatedSprite2D / TextureRect)
```

### Step 3 — Build the scene structure in Godot
```
create_scene → add_node (CharacterBody2D, CollisionShape2D, etc.) → edit_node (set properties)
```

### Step 4 — Wire up logic
```
godot-mcp script tools → create or modify GDScript on nodes
```

Always complete Aseprite work (and export) before referencing the file in Godot. Godot cannot use an `.aseprite` file directly — always export to PNG first.

---

## Aseprite Tool Reference

### Canvas & File
- `create_canvas(width, height, filename)` — create a new sprite file
- `export_sprite(filename, output_path)` — export to PNG

### Drawing
- `draw_pixels(filename, pixels)` — place individual pixels `[{x, y, color}]`
- `draw_line(filename, x1, y1, x2, y2, color)` — draw a line
- `draw_rectangle(filename, x1, y1, x2, y2, color, filled)` — draw a rectangle
- `draw_circle(filename, cx, cy, radius, color, filled)` — draw a circle
- `fill_area(filename, x, y, color)` — flood fill

### Layers & Frames
- `add_layer(filename, layer_name)` — add a new layer
- `add_frame(filename)` — add an animation frame

### Advanced (extended tools)
- Advanced drawing: polygons, Bezier curves, gradients, patterns
- Effects: blur, outline, drop shadow, HSL, posterize, pixelate
- Transform: flip, rotate, resize, crop
- Spritesheet export with JSON metadata
- Tilemap and tileset creation
- AI-assisted colorization and upscaling
- Batch file processing

---

## Godot Tool Reference

### Project & Editor
- `get_project_info()` — read project metadata
- `list_projects()` — list Godot projects
- `launch_editor()` — open Godot editor
- `run_project()` / `stop_project()` — run/stop the game
- `get_debug_output()` — read console output

### Scenes & Nodes
- `create_scene(path, root_type)` — create a new `.tscn` file
- `save_scene()` — save current scene
- `add_node(parent_path, node_type, node_name)` — add a node
- `edit_node(node_path, properties)` — set node properties
- `remove_node(node_path)` — delete a node
- `load_sprite(node_path, texture_path)` — assign a texture to a node

### Extended (added modules)
- **Animation**: AnimationPlayer tracks, keyframes, playback
- **Animation Tree**: state machines, blend trees
- **Environment**: sky, ambient light, fog, tone mapping
- **Material**: StandardMaterial3D, ShaderMaterial
- **Mesh**: MeshInstance, MeshLibrary, export
- **Navigation**: NavigationRegion, navmesh baking
- **Particles**: GPUParticles2D/3D configuration
- **Path**: Path3D, PathFollow, curve editing
- **Playback**: AudioStreamPlayer, VideoStreamPlayer
- **Project Config**: read/write project.godot settings
- **Skeleton**: Skeleton3D, bones, IK
- **Theme**: UI Theme creation
- **TileMap**: tile placement, TileSet configuration
- **Tween**: property and method tweens
- **Editor Script**: run arbitrary EditorScript in-editor

---

## File Path Convention

Aseprite saves files wherever you specify. Godot expects paths in its `res://` format for internal resources.

- Export Aseprite art to Godot's project folder so Godot can reference it:
  - Example: export to `res://assets/sprites/player.png`
- When using `load_sprite` or referencing textures in Godot, always use the `res://` path.

---

## Common Patterns

### Pixel art character with physics
```
1. create_canvas(16, 16, "player.aseprite")
2. add_layer → draw body pixels on separate layers
3. add_frame × N for walk animation
4. export_sprite_sheet → player_sheet.png + player_sheet.json
5. create_scene("res://scenes/player.tscn", "CharacterBody2D")
6. add_node → CollisionShape2D, AnimatedSprite2D
7. load_sprite(AnimatedSprite2D path, "res://assets/player_sheet.png")
8. edit_node → set animation frames from JSON metadata
```

### Tilemap level
```
1. create_canvas(128, 128, "tileset.aseprite") — 8×8 tiles at 16×16px
2. Draw individual tiles on separate layers or frames
3. export_sprite_sheet → tileset.png + tileset.json
4. create_scene("res://scenes/level.tscn", "Node2D")
5. add_node → TileMap
6. godot-mcp tilemap tools → configure TileSet, place tiles
```

### UI element
```
1. Aseprite → draw button/icon art, export PNG
2. Godot → add_node(TextureButton or TextureRect)
3. load_sprite → assign exported texture
4. edit_node → set size, position, anchor
```

---

## Error Handling

- If an Aseprite export fails, check that `ASEPRITE_PATH` is set correctly and Aseprite supports `--batch` mode.
- If a Godot command fails with "not connected", the Godot editor must be open with the plugin enabled and the WebSocket server running on port 9080.
- Always verify an exported file exists before referencing it in Godot.
- If a node path is wrong in Godot, use `get_project_info()` or inspect the scene tree first.

---

## Setup Checklist (for new users)

- [ ] Aseprite installed, `ASEPRITE_PATH` set in environment
- [ ] Python 3.12+ and `uv` installed
- [ ] `cd aseprite-mcp && uv sync` completed
- [ ] Node.js 18+ installed
- [ ] `cd Godot-MCP/server && npm install && npm run build` completed
- [ ] Godot 4.x installed
- [ ] Godot project open in editor with `godot_mcp` plugin enabled
- [ ] Both MCP servers registered in Claude config (see `claude_desktop_config.json`)
