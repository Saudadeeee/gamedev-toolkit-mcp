# Credits

**Maintainer:** Saudade — [gamedev-toolkit-mcp](https://github.com/Saudadeeee/gamedev-toolkit-mcp)

This project is a merge and extension of several open-source MCP servers. This
file records what came from where, so the attribution is specific rather than a
blanket "inspired by".

Two upstreams were **merged** into this repo; two more are **integrated** as
separate MCP servers without copying their code. The licence of each is noted
below, and the distinction matters — see the Licence section.

---

## Direct ancestors — code taken and merged

### [diivi/aseprite-mcp](https://github.com/diivi/aseprite-mcp)
*Author: [@diivi](https://github.com/diivi) · MIT*

The foundation of `servers/aseprite/`. This project began as a separate fork and
was later merged with upstream wholesale, so a large share of the Aseprite
server is diivi's code, taken essentially unmodified:

| Module | What it provides |
|---|---|
| `core/commands.py` | The `ERROR:` protocol, `lua_escape`, `reject_traversal`, `execute_lua_script_checked` |
| `core/lua.py` | `FIND_LAYER`, `NORMALIZE_CEL`, `PSET`, HSL conversions |
| `core/colors.py`, `core/native.py` | Hex parsing, native `app.command.*` wrapper |
| `tools/animation.py` | Eased tweening, oscillation, tags, onion skin, cel propagation |
| `tools/quality.py` | `validate_scene`, `audit_animation`, `animation_sanitize` |
| `tools/pixel_read.py`, `tools/analysis.py` | Pixel readback, colour stats, frame diffing |
| `tools/canvas.py`, `drawing.py`, `export.py`, `layers.py`, `palette.py`, `fx.py`, `native_fx.py`, `selection.py`, `slices.py`, `tilemap.py`, `transform.py`, `scene.py`, `script.py`, `preview.py`, `guide.py` | Taken as-is |

The three architectural properties this fork is built on — errors that cannot
fail silently, escaped Lua interpolation, and cel normalization so coordinates
are sprite-global — are all diivi's design. They replaced this fork's earlier
approach, which had none of them.

### [ee0pdt/Godot-MCP](https://github.com/ee0pdt/Godot-MCP)
*MIT*

The base of `servers/godot/`: the WebSocket bridge between a Node.js MCP server and
a GDScript editor plugin, the command-processor dispatch pattern, and the
original node, script, scene, editor and project command sets.

### [bradypp/godot-mcp](https://github.com/bradypp/godot-mcp)
*MIT*

The earlier subprocess-based Godot MCP that ee0pdt's plugin approach replaced.
Referenced in this project's README as the architectural comparison point.

---

## Vendored

These run alongside this repo's own two servers. Each is declared in
[`toolkit.json`](toolkit.json) as `"origin": "vendored"` and lives under
`servers/`, copied **verbatim** from upstream with its own `LICENSE` intact.
None of them is modified here; see [`docs/vendoring.md`](docs/vendoring.md) for
the rules and the update procedure, and [`COPYRIGHT`](COPYRIGHT) for the licence
inventory.

Vendoring GPL-3.0 code is why this project is GPL-3.0 rather than permissive —
[`docs/licensing.md`](docs/licensing.md) explains the reasoning. Before the
relicense these were cloned into a gitignored `external/` instead.

What this repo adds on top is discovery, readiness probing, routing and
documentation: see `aseprite_mcp/core/tool_registry.py`, `AGENTS.md`, and the
skills.

### [MarkusPfundstein/mcp-obsidian](https://github.com/MarkusPfundstein/mcp-obsidian)
*Notes and planning via Obsidian · MIT · 15 tools*

Python over stdio, talking to Obsidian through its **Local REST API** community
plugin. Used for the planning layer: design docs, task lists and the record of
what was built — the only part of this pipeline that survives between sessions.

Needs `OBSIDIAN_API_KEY` from the Local REST API plugin's settings.

What this repo adds: Obsidian executable detection, registry entry, routing
rules, and the Step 0 "read the plan first" convention in `AGENTS.md`.

### [jasonjgardner/blockbench-mcp-plugin](https://github.com/jasonjgardner/blockbench-mcp-plugin)
*3D modelling via Blockbench · **GPL-3.0***

Runs as a plugin **inside Blockbench**, serving MCP over HTTP on
`localhost:3000/bb-mcp` by default — the plugin picks the port, so the
candidates in `toolkit.json` get probed. Reached here through `mcp-remote`.

This is the component that set the project's licence. It is **GPL-3.0**, and
GPL-3.0 code cannot be redistributed under a more permissive licence — so
vendoring it meant relicensing the whole distribution from MIT to GPL-3.0. See
[`docs/licensing.md`](docs/licensing.md).

The source is vendored for licence compliance and reference only. The server
exists inside the Blockbench process, so this repo does not build or launch it;
the app loads the plugin itself.

What this repo adds: Blockbench executable detection across platforms and
package managers, a readiness probe that reports whether the plugin is actually
serving on its port, routing rules in `AGENTS.md`, and the `blockbench-modeling`
skill.

### [xDarkzx/Audacity-MCP](https://github.com/xDarkzx/Audacity-MCP)
*Audio editing via Audacity · **Apache-2.0***

Python + FastMCP over stdio, talking to Audacity through its `mod-script-pipe`
named pipe. 131 tools plus 9 pipelines.

Not vendored because it is a thin, well-maintained bridge to Audacity's own
scripting module — a fork would add nothing but maintenance. Requires Audacity
3.x with `mod-script-pipe` enabled; 4.x is not supported upstream.

What this repo adds: Audacity executable detection, a readiness probe that
checks whether the scripting pipes actually exist (the usual reason a call
fails, and invisible from the error message), routing rules, and the
`audacity-audio` skill.

---

## Features adapted — reimplemented, not copied

The following capabilities were identified by surveying comparable servers.
The designs are theirs; the implementations here are original, written against
this project's own conventions.

### [willibrandon/pixel-mcp](https://github.com/willibrandon/pixel-mcp)
*Go implementation of an Aseprite MCP server*

Its feature set showed what a serious pixel-art MCP should cover. Adapted:

| Capability | Where it lives here | How this implementation differs |
|---|---|---|
| Directional shading | `tools/shading.py` → `shade_directional` | Derives lighting by marching the silhouette toward the light rather than from a normal map; ramp order is normalised by perceptual luminance so caller order does not matter |
| Dither pattern library | `core/dither.py`, `tools/dither_tools.py` | 15 threshold matrices plus Floyd-Steinberg; matrices tile against absolute canvas coordinates so adjacent fills line up |
| Palette snapping | `tools/shading.py` → `snap_to_palette` | Matches in CIELAB via `core/color_space.py`; reads the cel's distinct colours first and applies one remap, rather than testing every pixel |
| Antialias detection | `tools/shading.py` → `detect_antialias_candidates`, `apply_antialias` | Detection and application are separate tools, and detection is read-only, because over-antialiasing is the usual failure |
| Palette sorting | `tools/dither_tools.py` → `sort_sprite_palette` | Refuses indexed sprites, where reordering the palette would silently remap every pixel |

The Bayer matrices are the standard recursive construction and are not
anyone's original work; the texture stencils here were authored for this
project.

### [tugcantopaloglu/godot-mcp](https://github.com/tugcantopaloglu/godot-mcp)
*157-tool Godot MCP server*

Its coverage exposed the gaps on the Godot side. Adapted:

| Capability | Where it lives here | How this implementation differs |
|---|---|---|
| Screenshots for visual feedback | `commands/capture_commands.gd`, `tools/capture_tools.ts` | Renders offscreen into a `SubViewport` instead of screenshotting a running game, so it is deterministic and needs no play session; returns the image as MCP image content so the model actually sees it |
| Signal wiring | `commands/signal_commands.gd`, `tools/signal_tools.ts` | Connects with `CONNECT_PERSIST` so the connection is saved into the scene, and verifies the target method exists before connecting |
| Node groups | `commands/group_commands.gd` | Walks the edited scene rather than the SceneTree group index, which does not describe an unrun scene |
| Headless operation | `utils/godot_cli.ts`, `tools/headless_tools.ts` | Separate CLI path alongside the plugin bridge, so export, validation and asset import work with the editor closed |
| Project export | `tools/headless_tools.ts` → `export_project` | Verifies the output file exists, because Godot exits 0 on some export failures |

### [youichi-uda/aseprite-mcp-pro](https://github.com/youichi-uda/aseprite-mcp-pro)

Referenced for its Aseprite-to-Godot integration approach. No code taken.

---

## Not adopted, and why

Recorded so the omissions read as decisions rather than oversights.

- **A persistent Aseprite Lua extension** (as `aseprite-mcp-pro` uses) instead
  of spawning `aseprite --batch` per call. Faster, and it would make clipboard
  and selection state survive across tool calls. Not adopted because it
  requires installing an extension into Aseprite and keeping the app open,
  which the current design does not.
- **A second input-map implementation.** `project_config_tools.ts` already has
  `add_input_action` / `add_input_event`; a duplicate would silently shadow it,
  since FastMCP keeps whichever tool registers last.
- **C#/.NET project support.** Real gap. GDScript only for now.
- **Networking and multiplayer tools.** Out of scope for a 2D asset pipeline.

---

## Licence

This project is **GPL-3.0-or-later**. It was MIT through commit `c5f32f4`, and
became GPL-3.0 when the Blockbench plugin was vendored — see
[`docs/licensing.md`](docs/licensing.md) for the reasoning and what it means for
you.

**Forked upstreams** (`diivi/aseprite-mcp`, `ee0pdt/Godot-MCP`) are MIT. Their
copyright notices are retained in `servers/aseprite/LICENSE` and
`servers/godot/LICENSE`. MIT permits sublicensing, so this fork ships under
GPL-3.0 as part of the whole; the original MIT grant on their work is not
revoked and remains available from upstream.

**Vendored servers** keep their own licences in their own directories —
`servers/blockbench/` is GPL-3.0, `servers/audacity/` is Apache-2.0,
`servers/obsidian/` is MIT. All three are one-way compatible into GPL-3.0, which
is what makes the combination distributable. None of them is modified here.

[`COPYRIGHT`](COPYRIGHT) is the full per-component inventory.

If you are one of the authors above and want the attribution worded
differently, please open an issue.
