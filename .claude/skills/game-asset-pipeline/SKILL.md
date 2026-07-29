---
name: game-asset-pipeline
description: Orchestrating the four-server toolkit — Aseprite (2D art), Blockbench (3D models), Audacity (audio) and Godot (engine). Who owns what, the handoff format between each pair, folder layout, and the readiness checks that prevent half the failures. Use when a task spans more than one tool.
---

# Orchestrating the Asset Toolkit

Four servers, one project. Each owns a domain and hands off to the next as a
file on disk — no server can read another's working format.

| Server | Working format | Hands off as |
|---|---|---|
| `aseprite` | `.aseprite` | PNG, spritesheet PNG + JSON |
| `blockbench` | `.bbmodel` | glTF/GLB, OBJ, model JSON + texture PNG |
| `audacity` | `.aup3` | WAV, OGG, MP3 |
| `godot-mcp` | `.tscn`, `.gd` | the game itself |

## When to activate

- A task touches more than one of art, models, audio, engine
- Setting up a new project's asset folders
- Something is not responding and you need to know which layer is at fault

## Start with readiness, not with work

The four servers have genuinely different prerequisites, and the failure
messages do not say so.

```
get_toolkit_status        # on the aseprite server — installed AND reachable
```

| Server | App must be running? | Why |
|---|---|---|
| `aseprite` | no | spawns `aseprite --batch` per call |
| `godot-mcp` headless | no | drives the binary directly |
| `godot-mcp` scene tools | **yes** | WebSocket bridge inside the editor, port 9080 |
| `blockbench` | **yes** | the MCP server *is* a Blockbench plugin, port 3000 |
| `audacity` | **yes** | talks over `mod-script-pipe`, which a running Audacity creates |

Two of the four need an app open before they answer anything. Checking first
turns "the tool is broken" into "Blockbench is closed".

## Folder layout

Keep sources out of the engine project and exports inside it. Godot imports
everything under `res://`, so a stray `.aseprite` or `.aup3` becomes an
unknown resource it tries to parse on every scan.

```
project/
├── sources/              # never inside the Godot project
│   ├── art/     *.aseprite
│   ├── models/  *.bbmodel
│   └── audio/   *.aup3
└── game/                 # the Godot project
    ├── project.godot
    └── assets/
        ├── sprites/  *.png  *.json
        ├── models/   *.glb  *.png
        └── audio/    *.ogg  *.wav
```

The export is the contract. Re-exporting over the same path and re-importing
is the whole update loop.

## Handoffs

### Aseprite → Godot (2D)

```
export_spritesheet(..., data_filename=..., list_tags=True)
import_animated_sprite(node_path, texture, metadata, use_tags=True)
```

`list_tags=True` is what makes one Godot animation per Aseprite tag, with the
per-frame durations preserved. Without it you get one undifferentiated strip.
See the `aseprite-godot-pipeline` skill for the detail.

### Aseprite → Blockbench (texture for a model)

Pixel-art textures for low-poly models are authored in Aseprite, not painted
in Blockbench. Export a PNG sized to the model's UV space, then apply it as
the model texture. Keep the texture power-of-two and use nearest filtering at
both ends, or the pixels blur.

### Blockbench → Godot (3D)

Export glTF/GLB — Godot imports it natively with materials and bones intact.
OBJ loses animation. The texture PNG travels alongside; set its import filter
to Nearest for pixel-art textures, exactly as for sprites.

### Audacity → Godot (audio)

- **OGG Vorbis** for music and long ambience: small, and Godot loops it natively
- **WAV** for short SFX: no decode latency, size is irrelevant at that length
- Mono for positional 3D/2D sounds, stereo only for music and UI

Set loop points in Godot's import settings, not by padding the file.

## Order of work

Art and audio are independent; the engine depends on both. Do the leaf work
first so the engine step never waits on a missing file.

```
1. get_toolkit_status
2. Aseprite   -> sprites, tags, spritesheet export
   Blockbench -> models, UVs, glTF export        (independent of art)
   Audacity   -> SFX and music, OGG/WAV export   (independent of art)
3. Godot -> import assets, build scenes, wire signals
4. Godot -> capture_scene_render to see the result
5. Godot -> validate_project_headless, export_project
```

## Verify at each boundary

Every server can report on its own output. Use it — a success string only
means the command ran.

| Stage | Check |
|---|---|
| Aseprite | `get_composite_rect`, `export_frame(scale=8)`, `audit_animation` |
| Blockbench | inspect the model's element/UV listing after edits |
| Audacity | read the track/selection state back after an effect |
| Godot | `capture_scene_render` (see it), `validate_project_headless` (parse it) |

The most common silent failure across all four is the same shape: an export
that never landed where the next stage looks for it. Confirm the file exists
before the next server references it.

## Troubleshooting by layer

| Symptom | Layer | Fix |
|---|---|---|
| Any tool: connection refused | bridge | `get_toolkit_status`; open the app |
| Blockbench tools absent | plugin | Load the MCP plugin in Blockbench, check port 3000 |
| Audacity tools time out | module | Enable `mod-script-pipe`, restart Audacity (3.x only) |
| Godot scene tools fail, headless works | editor | Open the project with the `godot_mcp` plugin enabled |
| Aseprite reports "Cannot run Aseprite" | path | `get_aseprite_info`, set `ASEPRITE_PATH` |
| Art looks blurry in game | import | Texture filter to Nearest, both for sprites and model textures |
| Asset changed but game shows the old one | import | `import_project_assets`, or `scan_filesystem` + `reimport_file` |
