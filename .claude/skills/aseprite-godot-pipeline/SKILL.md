---
name: aseprite-godot-pipeline
description: Handing art off from aseprite-mcp to godot-mcp — export formats, res:// path conventions, spritesheet JSON for AnimatedSprite2D, tileset and nine-patch import, and the import settings that keep pixel art crisp. Use when art needs to end up in a Godot scene.
---

# Aseprite → Godot Handoff

Two MCP servers, one pipeline. The handoff is a file on disk: Godot cannot read `.aseprite`, so every asset crosses the boundary as PNG plus, for animations, a JSON sidecar.

## When to activate

- Any task that ends with art inside a Godot scene
- Setting up `AnimatedSprite2D`, `Sprite2D`, `TileMap`, `NinePatchRect`, `TextureButton`
- Debugging blurry, misaligned, or missing textures in Godot

## Export directly into the Godot project

Do not export to a scratch folder and copy afterwards. Export to the real path so Godot's importer picks it up on the next filesystem scan:

```
export_spritesheet("player.aseprite",
                   "D:/path/to/GodotProject/assets/sprites/player_sheet.png",
                   data_filename="D:/path/to/GodotProject/assets/sprites/player_sheet.json",
                   sheet_type="horizontal", list_tags=True, data_format="json-array")
```

Then reference it from Godot as `res://assets/sprites/player_sheet.png`. The `res://` prefix maps to the project root — an absolute OS path will not resolve inside Godot.

Verify the file exists before the Godot call. `import_animated_sprite` failing on a missing texture reports a Godot-side error that reads nothing like "the export never happened".

## Per asset type

### Animated character → `AnimatedSprite2D`

```
# Aseprite
set_tag("player.aseprite", "idle", 1, 4)
set_tag("player.aseprite", "walk", 5, 12)
export_spritesheet("player.aseprite", ".../player_sheet.png",
                   data_filename=".../player_sheet.json", list_tags=True)

# Godot
create_scene("res://scenes/player.tscn", "CharacterBody2D")
create_node(parent_path, "AnimatedSprite2D", "Sprite")
import_animated_sprite(node_path, "res://assets/player_sheet.png",
                       "res://assets/player_sheet.json", animation_name, fps, autoplay)
create_node(parent_path, "CollisionShape2D", "Collision")
save_scene()
```

`list_tags=True` is what puts tag ranges in the JSON. Without it the sheet is one undifferentiated strip and each animation has to be sliced by hand.

### Static sprite → `Sprite2D`

```
export_frame("icon.aseprite", 1, ".../icon.png")
# Godot
create_node(parent_path, "Sprite2D", "Icon")
load_sprite(node_path, "res://assets/icon.png")
```

### Tileset → `TileMap`

```
# Aseprite: draw tiles on a grid
set_sprite_grid("tiles.aseprite", 0, 0, 16, 16)
export_sprite("tiles.aseprite", ".../tileset.png")

# Godot
create_node(parent_path, "TileMap", "Ground")
# then godot-mcp tileset tools to define the atlas, followed by
set_tile_cell / paint_tile_area
```

Keep the Aseprite grid and the Godot TileSet tile size identical. A 16×16 grid exported against a 32×32 TileSet silently offsets every tile.

### Scalable UI → `NinePatchRect`

```
create_nine_patch_slice("panel.aseprite", "panel",
                        {"x": 0, "y": 0, "width": 48, "height": 48},
                        {"x": 16, "y": 16, "width": 16, "height": 16})
export_sprite("panel.aseprite", ".../panel.png")

# Godot
create_node(parent_path, "NinePatchRect", "Panel")
load_sprite(node_path, "res://assets/ui/panel.png")
update_node_property(node_path, "patch_margin_left", 16)    # and top/right/bottom
```

The slice center rectangle and the four `patch_margin_*` values describe the same thing. Set them consistently or the corners will stretch.

### Layered art → separate nodes

```
export_layers("scene.aseprite", ".../layers/", include_hidden=False)
```

One PNG per layer, named after the layer. Use for parallax backgrounds where each layer scrolls at its own rate.

## Import settings that matter for pixel art

Godot's default texture import filters and mipmaps, which turns crisp pixel art into mush at any non-integer scale. Set these once per project via `godot-mcp`:

```
set_project_setting("rendering/textures/canvas_textures/default_texture_filter", 0)  # Nearest
```

Per texture, if the project default is not enough:

```
set_import_settings("res://assets/sprites/player_sheet.png", { "filter": false, "mipmaps": false })
reimport_file("res://assets/sprites/player_sheet.png")
```

Re-exporting a PNG over an existing one does not always trigger a reimport. When Godot shows stale art, call `scan_filesystem()` then `reimport_file(...)`.

## Path conventions

| Context | Form |
|---|---|
| Aseprite tool arguments | Absolute OS path, forward slashes |
| Godot tool arguments | `res://` relative to project root |
| Source `.aseprite` files | Outside the Godot project, or in a folder Godot ignores |
| Exported PNG/JSON | Inside the Godot project, under `assets/` |

Keeping `.aseprite` sources out of the project tree stops Godot from importing them as unknown resources and keeps the export the single source of truth for what the game ships.

## Look at what you built

The Godot side is not blind either. After wiring a scene, render it:

```
capture_scene_render(scene_path, width, height, transparent, output_path)
capture_editor_viewport(dimension, output_path)
```

`capture_scene_render` renders offscreen into a SubViewport — deterministic, no
play session needed, and it does not disturb the editor. Use it to check
layout, z-order, visibility and sprite placement rather than inferring them
from node properties. `capture_editor_viewport` grabs the editor's own view
including the user's camera and zoom.

Both return the image itself, so you can see the result.

## Wire the signals

Art and nodes alone do not make a game. Connect them:

```
list_signals(node_path, include_inherited)     # script-declared signals by default
connect_signal(from_node_path, signal_name, to_node_path, method_name, deferred, one_shot)
list_connections(node_path, signal_name)
```

Connections are persistent, so they save into the `.tscn` the way an
editor-made connection does. The target method must already exist — create it
with the script tools first, or the connect is rejected rather than failing
silently at runtime.

## Working with the editor closed

Everything above needs the Godot editor open with the plugin running. These do
not:

```
godot_headless_info()                                  # is the binary reachable?
validate_project_headless(project_path)                # import/parse errors
import_project_assets(project_path)                    # pick up newly exported PNGs
list_export_presets(project_path)
export_project(project_path, preset_name, output_path, debug)
run_headless_script(project_path, script)              # escape hatch
```

`import_project_assets` is the one to reach for right after exporting art from
Aseprite into the project: it makes Godot notice the new files without anyone
opening the editor. `export_project` is what turns the scene tree into
something runnable.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Godot: texture not found | Export path never resolved to the project, or `res://` prefix missing |
| Blurry sprite | Texture filter defaulting to linear — set Nearest |
| Animation is one long strip | `list_tags=True` omitted from `export_spritesheet` |
| Tiles offset by a few pixels | Aseprite grid size ≠ Godot TileSet tile size |
| Stale art after re-export | `scan_filesystem()` then `reimport_file(...)` |
| Godot: `not connected` | Editor must be open with the `godot_mcp` plugin enabled, WebSocket on port 9080. Headless tools work without it. |
| `Godot executable not found` | Set `GODOT_PATH`, or check `godot_headless_info` |
| Export succeeded but no file | Export templates not installed — Editor > Manage Export Templates |
| Aseprite tool: `Cannot run Aseprite at ...` | `ASEPRITE_PATH` unset or stale — check `get_aseprite_info` |
