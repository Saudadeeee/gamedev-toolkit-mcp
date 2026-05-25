# CLAUDE.md - Godot x Aseprite MCP

This workspace contains two MCP servers that work together as a unified 2D game development pipeline:

- **`aseprite`** - controls Aseprite for all pixel art, sprite, and animation work
- **`godot-mcp`** - controls Godot Engine for all scene, node, and game logic work

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
| Load a sprite or texture into a Godot node | `godot-mcp` (`load_sprite`) |
| Import spritesheet animation into `AnimatedSprite2D` | `godot-mcp` (`import_animated_sprite`) |

**Never use Godot tools to create art. Never use Aseprite tools to build scenes.**

---

## Standard Combined Workflow

When a user asks to create a game element such as a character, enemy, tile, or UI element, follow this order:

### Step 1 - Create the art in Aseprite

```text
create_canvas -> add_layer -> draw_* / fill_area -> add_frame (if animated) -> export_sprite
```

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

## Aseprite Tool Reference

### Canvas and File

- `create_canvas(width, height, filename)` - create a new sprite file
- `export_sprite(filename, output_path)` - export to PNG

### Drawing

- `draw_pixels(filename, pixels)` - place individual pixels `[{x, y, color}]`
- `draw_line(filename, x1, y1, x2, y2, color)` - draw a line
- `draw_rectangle(filename, x1, y1, x2, y2, color, filled)` - draw a rectangle
- `draw_circle(filename, cx, cy, radius, color, filled)` - draw a circle
- `fill_area(filename, x, y, color)` - flood fill

### Layers and Frames

- `add_layer(filename, layer_name)` - add a new layer
- `add_frame(filename)` - add an animation frame

### Advanced

- Advanced drawing: polygons, Bezier curves, gradients, patterns
- Effects: blur, outline, drop shadow, HSL, posterize, pixelate
- Transform: flip, rotate, resize, crop
- Spritesheet export with JSON metadata
- Tilemap and tileset creation
- AI-assisted colorization and upscaling
- Batch file processing

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
4. export_sprite_sheet -> player_sheet.png + player_sheet.json
5. create_scene("res://scenes/player.tscn", "CharacterBody2D")
6. create_node -> CollisionShape2D, AnimatedSprite2D
7. import_animated_sprite(AnimatedSprite2D path, "res://assets/player_sheet.png", "res://assets/player_sheet.json")
8. update_node_property -> set extra playback or transform properties if needed
```

### Tilemap level

```text
1. create_canvas(128, 128, "tileset.aseprite") - 8x8 tiles at 16x16px
2. draw tiles on separate layers or frames
3. export_sprite_sheet -> tileset.png + tileset.json
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

- [ ] Aseprite installed and `ASEPRITE_PATH` configured
- [ ] Python 3.12+ and `uv` installed
- [ ] `cd aseprite-mcp && uv sync` completed
- [ ] Node.js 18+ installed
- [ ] `cd Godot-MCP/server && npm install && npm run build` completed
- [ ] Godot 4.x installed
- [ ] Godot project open in editor with `godot_mcp` plugin enabled
- [ ] Both MCP servers registered in Claude config
