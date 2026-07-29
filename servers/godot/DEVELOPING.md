# Godot MCP — Claude Working Instructions

## Project Overview

This is a **Model Context Protocol (MCP) server** that lets AI models (Claude, etc.) control the Godot 4 editor in real time. It has two sides that must stay in sync:

```
AI Model (Claude)
     │
     │  MCP (stdio/HTTP)
     ▼
TypeScript Server  (Node.js / FastMCP)
     │
     │  WebSocket  ws://localhost:9080
     ▼
Godot Editor  (GDScript EditorPlugin)
```

---

## Directory Structure

```
Godot-MCP/
├── server/                          # TypeScript side
│   ├── src/
│   │   ├── index.ts                 # Entry point — registers all tools & resources
│   │   ├── tools/                   # One file per feature category
│   │   │   └── node_tools.ts        # Example: node manipulation tools
│   │   ├── resources/               # MCP resources (read-only data providers)
│   │   └── utils/
│   │       ├── godot_connection.ts  # WebSocket client (singleton GodotConnection)
│   │       └── types.ts             # MCPTool interface, GodotResponse, etc.
│   └── dist/                        # Compiled output (run `npm run build`)
│
└── addons/godot_mcp/               # GDScript side (Godot EditorPlugin)
    ├── plugin.cfg
    ├── mcp_server.gd                # Plugin entry point
    ├── websocket_server.gd          # WebSocket server on port 9080
    ├── command_handler.gd           # Routes commands to processors
    └── commands/
        ├── base_command_processor.gd  # Base class all processors extend
        └── *_commands.gd             # One file per feature category
```

---

## Architecture — How It Works

### TypeScript side (tool definition)

Each tool lives in `server/src/tools/<category>_tools.ts` and exports an array:

```typescript
// server/src/tools/node_tools.ts
import { z } from 'zod';
import { MCPTool } from '../utils/types.js';
import { getGodotConnection } from '../utils/godot_connection.js';

export const nodeTools: MCPTool[] = [
  {
    name: 'add_node',
    description: 'Add a node to the current scene',
    parameters: z.object({
      node_type: z.string().describe('Godot node class name, e.g. "MeshInstance3D"'),
      node_name: z.string().describe('Name for the new node'),
      parent_path: z.string().optional().default('.').describe('Path relative to scene root'),
    }),
    execute: async (args) => {
      const conn = getGodotConnection();
      const result = await conn.sendCommand('add_node', args);
      return JSON.stringify(result);
    },
  },
];
```

**Key rules:**
- `parameters` is a `z.ZodObject` — all field descriptions are shown to the AI
- `execute` calls `conn.sendCommand(type, params)` — this sends over WebSocket and waits for a response
- `conn.sendCommand` throws on error (Godot returned `status: "error"`) or timeout (20 s default)
- Return a `string` from `execute` — JSON.stringify the result

### GDScript side (command execution)

Each category has a processor in `addons/godot_mcp/commands/<category>_commands.gd`:

```gdscript
@tool
class_name MCPNodeCommands
extends MCPBaseCommandProcessor

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
    match command_type:
        "add_node":
            _add_node(client_id, params, command_id)
            return true   # IMPORTANT: return true to claim the command
    return false          # Not handled — let next processor try

func _add_node(client_id: int, params: Dictionary, command_id: String) -> void:
    var parent_path = params.get("parent_path", ".")
    var parent = _get_editor_node(parent_path)
    if not parent:
        return _send_error(client_id, "Parent not found: %s" % parent_path, command_id)

    # ... do work ...

    _mark_scene_modified()
    _send_success(client_id, { "message": "Node added", "node_name": node_name }, command_id)
```

**Key rules:**
- Must have `@tool` annotation at the top
- `class_name` must be unique and follow `MCP<Category>Commands` convention
- `extends MCPBaseCommandProcessor`
- `process_command` returns `true` if it handles the command, `false` otherwise
- Always call either `_send_success` or `_send_error` — never both, never neither
- Use `_get_editor_node(path)` to find nodes relative to `edited_scene_root`
- Call `_mark_scene_modified()` after any scene change

### Registering a new processor

After creating both files, register the processor in **`command_handler.gd`** inside `_initialize_command_processors()`:

```gdscript
# 1. Instantiate
var my_commands = MCPMyCommands.new()

# 2. Set server reference
my_commands._websocket_server = _websocket_server

# 3. Add to processor list
_command_processors.append(my_commands)

# 4. Add as child node
add_child(my_commands)
```

And register the tools in **`server/src/index.ts`**:

```typescript
import { myTools } from './tools/my_tools.js';

// In the tools registration array:
[...nodeTools, ...myTools, /* ... */].forEach(tool => server.addTool(tool));
```

---

## Base Class Helpers

`MCPBaseCommandProcessor` provides these helpers — use them in every command processor:

| Helper | Purpose |
|--------|---------|
| `_get_editor_node(path: String) -> Node` | Get node by path relative to scene root. Returns null if not found — always check. |
| `_send_success(client_id, result: Dictionary, command_id)` | Send success response. `result` keys become the tool's return value. |
| `_send_error(client_id, message: String, command_id)` | Send error response. The error message is thrown as an exception on the TS side. |
| `_mark_scene_modified()` | Mark the editor scene as unsaved (shows the asterisk). Call after any scene change. |
| `_get_undo_redo()` | Returns EditorUndoRedoManager for undoable operations. |
| `_parse_property_value(value)` | Converts string representations of Godot types (Vector3, Color, etc.) to actual types. |

---

## WebSocket Protocol

Commands flow like this:

```json
// TypeScript → Godot
{ "type": "add_node", "params": { "node_type": "MeshInstance3D", "parent_path": "." }, "commandId": "cmd_42" }

// Godot → TypeScript (success)
{ "status": "success", "result": { "message": "Node added", "node_name": "MeshInstance3D" }, "commandId": "cmd_42" }

// Godot → TypeScript (error)
{ "status": "error", "message": "Parent not found: NonExistent", "commandId": "cmd_42" }
```

The WebSocket server runs on **port 9080** (`addons/godot_mcp/websocket_server.gd`).

---

## Adding a New Feature Category — Full Workflow

1. **Create GDScript processor** at `addons/godot_mcp/commands/<category>_commands.gd`
2. **Create TypeScript tools** at `server/src/tools/<category>_tools.ts`
3. **Register in `command_handler.gd`** — add instantiation, server ref, append, add_child
4. **Register in `server/src/index.ts`** — import and spread into the tools array
5. **Build the server**: `cd server && npm run build`
6. **Reload the Godot plugin** (disable + re-enable in Project → Plugins, or restart editor)
7. **Test**: `cd server && node tests/editor_test.mjs <project>`

---

## Common Pitfalls

### GDScript

- **Missing `@tool`**: Without `@tool`, the script doesn't run in the editor — commands will silently fail.
- **Forgetting `return true`**: If `process_command` returns `false` for a handled command, the router reports "Unknown command".
- **Missing `_send_success`/`_send_error`**: If neither is called, the TS side will wait until the 20 s timeout.
- **`ResourceSaver.save()` blocking**: This call can block `_process()` on the editor main thread. Always validate the path starts with `res://` before calling it. Do NOT set `resource_path` on a resource before saving — pass the path directly to `save()`.
- **`_get_editor_node` returns null**: No scene is open, or the path is wrong. Always guard with `if not node: return _send_error(...)`.
- **Crashing the plugin**: A GDScript runtime error inside a command processor stops `_process()` from running, breaking the WebSocket server. After a crash, the Godot editor must be restarted. Use `if x != null` guards liberally.

### TypeScript

- **Forgetting `.js` extension on imports**: All local imports must end with `.js` (even if the source is `.ts`): `import { x } from './tools/x_tools.js'`.
- **Not rebuilding after changes**: `npm run build` must be run after every TypeScript change. The MCP server runs from `dist/index.js`.
- **Tool not registered in index.ts**: New tools added to a tools file won't be exposed to the AI unless spread into the tools array in `index.ts`.

---

## Parameter Conventions

Follow these naming conventions in Zod schemas and GDScript `params.get()` to keep both sides consistent:

| Data type | TS param names | GDScript `params.get()` |
|-----------|----------------|-------------------------|
| Node path | `node_path` | `params.get("node_path", "")` |
| Position/size 3D | `x`, `y`, `z` | `params.get("x", 0.0)` |
| Color RGBA | `r`, `g`, `b`, `a` | `params.get("r", 1.0)` |
| Color as array | `value: [r,g,b,a]` | `var c = params["value"]` then `Color(c[0],c[1],c[2],c[3])` |
| Boolean flag | `enabled` / `active` | `params.get("enabled", true)` |
| Enum/type string | `mesh_type`, `shape` | `params.get("mesh_type", "BoxMesh")` |
| Resource path | `save_path`, `theme_path` | `params.get("save_path", "")` |

---

## Build & Run Commands

```bash
# Build TypeScript server
cd server && npm run build

# Start server (for use with MCP client)
cd server && npm run start

# Dev mode (watch + rebuild on changes)
cd server && npm run dev

# Run integration tests
cd server && node tests/editor_test.mjs <path-to-a-godot-project>
```

The Godot editor must be running with the plugin enabled before tests can pass.

---

## Integration Test

`server/tests/editor_test.mjs` connects to the Godot WebSocket on port 9080 and drives a full pipeline: build a scene from an Aseprite spritesheet, wire a signal, group a node, render the result. `server/tests/headless_test.mjs` covers the CLI path and needs no editor. Both require:

1. Godot editor running with the `godot_mcp` plugin enabled
2. The test scene `res://test_mcp_full.tscn` present in the project
3. Port 9080 accessible

Run them with: `node server/tests/editor_test.mjs <project>` and `node server/tests/headless_test.mjs <project>`

If commands time out and the WebSocket stops responding after a test run, the Godot editor needs to be restarted — this usually means a GDScript runtime error crashed the plugin's `_process()` loop.

---

## Registered Command Categories

| GDScript Class | File | Commands prefix |
|----------------|------|-----------------|
| MCPNodeCommands | node_commands.gd | add_node, remove_node, list_nodes, edit_node… |
| MCPSceneCommands | scene_commands.gd | open_scene, save_scene, create_scene… |
| MCPScriptCommands | script_commands.gd | create_script, edit_script… |
| MCPProjectCommands | project_commands.gd | get_project_info… |
| MCPEditorCommands | editor_commands.gd | get_editor_state, launch_editor… |
| MCPEditorScriptCommands | editor_script_commands.gd | run_editor_script… |
| MCPPlaybackCommands | playback_commands.gd | run_project, stop_project, get_play_status |
| MCPProjectConfigCommands | project_config_commands.gd | set_project_setting, add_input_action, add_audio_bus… |
| MCPTileMapCommands | tilemap_commands.gd | set_tile_cell, get_tilemap_info… |
| MCPNavigationCommands | navigation_commands.gd | bake_navigation_mesh, get_navigation_path… |
| MCPParticleCommands | particle_commands.gd | configure_particles, set_particle_material… |
| MCPEnvironmentCommands | environment_commands.gd | set_light_property, configure_environment, set_sky, set_fog… |
| MCPAnimationTreeCommands | animation_tree_commands.gd | configure_animation_tree, add_animation_tree_node… |
| MCPSkeletonCommands | skeleton_commands.gd | get_skeleton_info, set_bone_pose_rotation… |
| MCPThemeCommands | theme_commands.gd | create_theme, set_theme_color, set_theme_stylebox… |
| MCPTweenCommands | tween_commands.gd | animate_node_property, create_tween_script… |
| MCPPathCommands | path_commands.gd | add_path_point, clear_path, configure_path_follow… |
| MCPMeshCommands | mesh_commands.gd | create_primitive_mesh, create_array_mesh, save_mesh_to_file… |
| MCPImportCommands | import_commands.gd | list_filesystem_files, scan_filesystem… |
| MCPMaterialCommands | material_commands.gd | create_material, set_material_property… |
| MCPAnimationCommands | animation_commands.gd | create_animation, add_animation_track… |
