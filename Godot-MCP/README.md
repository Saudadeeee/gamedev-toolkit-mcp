# Godot MCP

A Godot Engine plugin and TypeScript MCP (Model Context Protocol) server that allows AI assistants to interact directly with your Godot projects — reading scenes, modifying nodes, running scripts, and more.

[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io/)
[![Godot 4.x](https://img.shields.io/badge/Godot-4.x-blue)](https://godotengine.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green)](https://nodejs.org/)

---

## Credits

This project is based on **[Godot-MCP](https://github.com/ee0pdt/Godot-MCP)** by [@ee0pdt](https://github.com/ee0pdt), which established the WebSocket bridge architecture between the Godot editor and MCP clients.

The original project covered node, scene, script, project, and editor commands. This fork substantially expands the command set with rendering, animation, physics, UI, and asset pipeline capabilities.

---

## What's New in This Fork

The following command modules were added on top of the original:

| Module | Description |
|---|---|
| `animation_commands.gd` + `animation_tools.ts` | AnimationPlayer control, track editing, playback |
| `animation_tree_commands.gd` + `animation_tree_tools.ts` | AnimationTree and state machine management |
| `environment_commands.gd` + `environment_tools.ts` | WorldEnvironment, sky, lighting setup |
| `import_commands.gd` + `import_tools.ts` | Asset import configuration |
| `material_commands.gd` + `material_tools.ts` | Material creation and property editing |
| `mesh_commands.gd` + `mesh_tools.ts` | MeshInstance, MeshLibrary, mesh export |
| `navigation_commands.gd` + `navigation_tools.ts` | NavigationRegion, navmesh baking |
| `particle_commands.gd` + `particle_tools.ts` | GPUParticles3D/2D configuration |
| `path_commands.gd` + `path_tools.ts` | Path3D, PathFollow, curve editing |
| `playback_commands.gd` + `playback_tools.ts` | Audio and video playback control |
| `project_config_commands.gd` + `project_config_tools.ts` | ProjectSettings read/write |
| `skeleton_commands.gd` + `skeleton_tools.ts` | Skeleton3D, bones, IK |
| `theme_commands.gd` + `theme_tools.ts` | UI Theme creation and editing |
| `tilemap_commands.gd` + `tilemap_tools.ts` | TileMap, TileSet, tile placement |
| `tween_commands.gd` + `tween_tools.ts` | Tween animations |
| `editor_script_commands.gd` + (editor tools) | Run arbitrary EditorScript in-editor |

---

## Architecture

```
Claude / AI Client
       │  MCP (stdio)
       ▼
  Node.js MCP Server (server/src/)
       │  WebSocket (port 9080)
       ▼
  Godot Plugin (addons/godot_mcp/)
       │  GDScript
       ▼
  Godot Editor / Running Project
```

The Godot plugin runs a WebSocket server inside the editor. The Node.js server connects to it and exposes all commands as MCP tools to AI clients.

---

## Setup

### 1. Build the MCP Server

```bash
cd server
npm install
npm run build
cd ..
```

### 2. Enable the Godot Plugin

1. Open your Godot project
2. Go to **Project → Project Settings → Plugins**
3. Enable **"Godot MCP"**

To use in your own project: copy the `addons/godot_mcp/` folder into your project's `addons/` directory and enable the plugin.

### 3. Configure Claude Desktop / Claude Code

```json
{
  "mcpServers": {
    "godot-mcp": {
      "command": "node",
      "args": [
        "/absolute/path/to/Godot-MCP/server/dist/index.js"
      ],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

### 4. Open Godot and Start Working

Open your Godot project in the editor. The plugin connects automatically. You can now interact with your project through Claude.

---

## Available Tools

### Original Commands
| Tool | Description |
|---|---|
| `get_project_info` | Project metadata and settings |
| `list_projects` | List available Godot projects |
| `create_node` | Create a new node in a scene |
| `update_node_property` | Modify node properties |
| `delete_node` | Delete a node |
| `create_scene` | Create a new scene file |
| `save_scene` | Save the current scene |
| `load_sprite` | Load a sprite resource |
| `import_animated_sprite` | Build SpriteFrames on an AnimatedSprite2D from spritesheet JSON |
| `run_project` | Run the Godot project |
| `stop_project` | Stop the running project |
| `get_debug_output` | Get console/debug output |
| `launch_editor` | Launch the Godot editor |
| `get_godot_version` | Get current Godot version |
| `export_mesh_library` | Export a MeshLibrary resource |
| `get_uid` / `update_project_uids` | UID management |

### Extended Commands (this fork)
| Category | Tools |
|---|---|
| **Animation** | Create/edit animations, control AnimationPlayer |
| **Animation Tree** | State machine setup, blend trees |
| **Environment** | Sky, ambient light, fog, tone mapping |
| **Import** | Configure asset import settings |
| **Material** | Create StandardMaterial3D, ShaderMaterial |
| **Mesh** | Mesh instances, MeshLibrary export |
| **Navigation** | NavMesh baking, NavigationAgent setup |
| **Particles** | Configure particle systems |
| **Path** | Curve/path creation and editing |
| **Playback** | AudioStreamPlayer, VideoStreamPlayer |
| **Project Config** | Read/write project.godot settings |
| **Skeleton** | Bone transforms, IK chains |
| **Theme** | UI theme properties |
| **TileMap** | Tile placement, TileSet configuration |
| **Tween** | Property/method tweens |
| **Editor Script** | Run custom EditorScript in the editor |

---

## Resource Endpoints

```
godot://project/info     - Project metadata
godot://scene/current    - Currently open scene tree
godot://script/current   - Currently open script
```

---

## Usage Examples

```
Create a CharacterBody3D player with a CollisionShape and MeshInstance.

Add a NavigationRegion3D and bake the navmesh.

Create an AnimationPlayer on the player node with a walk animation.

Set up a WorldEnvironment with a procedural sky and ambient light.
```

---

## Troubleshooting

**WebSocket connection refused** — Make sure the Godot project is open in the editor with the plugin enabled. The plugin starts the WebSocket server on port 9080.

**Plugin not showing** — Reload the Godot project after copying the `addons/godot_mcp/` folder. Verify it appears in **Project Settings → Plugins**.

**Commands not available** — Rebuild the server (`npm run build` in `server/`) after any source changes.

**Editor freezes during commands** — Some operations (navmesh baking, heavy imports) block the editor briefly. This is expected behavior.

---

## Documentation

Extended documentation is in the `docs/` folder:

- [Getting Started](docs/getting-started.md)
- [Installation Guide](docs/installation-guide.md)
- [Command Reference](docs/command-reference.md)
- [Architecture](docs/architecture.md)

---

## License

MIT License — see [LICENSE](LICENSE).

Original project by [@ee0pdt](https://github.com/ee0pdt) — MIT License.
