# Aseprite MCP — Internal Guide

Architecture and maintenance notes. For installation and the tool catalogue, see [README.md](README.md). For using the tools to make art, see the skills under [`.claude/skills/`](../../.claude/skills/).

---

## Architecture

The server does not talk to Aseprite through an API. Each tool builds a Lua script, writes it to a temp file, and runs:

```
aseprite --batch <sprite> --script <tmp.lua>
```

The sprite passed to `--batch` becomes `app.activeSprite` inside the script. Tools finish by calling `spr:saveAs(spr.filename)`.

```
aseprite_mcp/
├── __init__.py          # FastMCP instance
├── __main__.py          # stdio entrypoint
├── core/
│   ├── commands.py      # process runner, Lua escaping, traversal guard
│   ├── path_resolver.py # Aseprite + Godot executable discovery
│   ├── lua.py           # shared Lua snippets
│   ├── colors.py        # hex colour parsing
│   ├── color_space.py   # CIELAB, perceptual matching, palette ordering
│   ├── dither.py        # dither matrices and texture stencils
│   └── native.py        # wrapper for app.command.* engine filters
├── tools/               # 33 modules; each @mcp.tool() is one MCP tool
└── utils/               # Lua templates, constants, validators
```

Adding a tool means adding an `@mcp.tool()` function to a module in `tools/`, then importing that module in `tools/__init__.py`.

---

## Three rules for writing a tool

Break any one of these and you get a silent bug, not a reported error.

### 1. Signal failure with `ERROR:`, never with `return`

Aseprite's batch runner **discards** a top-level `return "message"` and **always exits 0**. A broken script is indistinguishable from a working one.

```lua
-- WRONG: the caller sees success
if not spr then return "No active sprite" end

-- RIGHT
if not spr then print("ERROR:No active sprite") return end
```

On the Python side call `execute_lua_script_checked` — it scans stdout for the `ERROR:` line — not `execute_lua_script`.

```python
success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
if success:
    return f"Done: {filename}"
return f"Failed to do the thing: {output}"
```

### 2. Escape every interpolated string

Filenames and layer names are user input. Unescaped, they break out of the Lua string literal and run arbitrary code.

```python
from ..core.commands import lua_escape, reject_traversal

safe_layer = lua_escape(layer_name)          # for use inside an f-string of Lua
error = reject_traversal(output_path)        # blocks ../ per path component
if error:
    return error
```

Numbers interpolate directly (the signature already coerces to `int`/`float`). Colours go through `parse_hex_color`, which accepts `#RGB`, `#RGBA`, `#RRGGBB`, `#RRGGBBAA` and returns `(r, g, b, a)`.

Never use `Color{fromString="#RRGGBBAA"}`. Aseprite only parses 6 hex digits; given 8 it returns **transparent black with no error**. Always pass channels numerically: `Color(r, g, b, a)`.

### 3. Normalize the cel before using sprite coordinates

`cel.image:putPixel(x, y)` works in **cel-local** space. Once a cel has been moved, drawing at (10, 10) lands somewhere else.

```lua
local cel = normalize_cel(spr, layer, frame, true)  -- canvas-sized image anchored at (0,0)
local img = cel.image
```

After that, every coordinate is sprite-global.

---

## Shared Lua snippets (`core/lua.py`)

| Name | Purpose |
|---|---|
| `FIND_LAYER` | `find_layer(spr, name)` — breadth-first search into groups, understands `group/child` paths, backtracks correctly when a layer name itself contains `/` |
| `NORMALIZE_CEL` | `normalize_cel(spr, layer, frame, create)` — see rule 3 |
| `PSET` | `pset(img, x, y, color)` — bounds-guarded putPixel |
| `HSL` | `rgb_to_hsl` / `hsl_to_rgb` |

`core/native.py::build_native_command_script` wraps `app.command.*`. The key detail: native commands act on the **active** sprite/layer/frame, not on arguments — so the wrapper activates the target **first** and fails immediately if it cannot be resolved. Without that step, a filter silently hits the wrong layer.

---

## Aseprite Lua traps

Recorded so nobody rediscovers them the hard way.

**Closing a source sprite kills images derived from it.** When opening a second sprite to read pixels, `close()` it **after** the read loop, not before. Close it first and Aseprite crashes with an empty stderr.

```lua
local pat = Image(src.width, src.height, src.colorMode)
pat:drawImage(src_cel.image, src_cel.position)
-- ... read pat here ...
src:close()   -- last
```

**Layer objects are unusable as table keys.** Aseprite hands out a fresh userdata wrapper on each property access, so `set[layer]` never matches the same layer reached through a second traversal. Key on `layer.name` instead.

**An empty palette corrupts the file.** `spr:setPalette(palette)` with `#palette == 0` produces a file that fails to reopen — `Unsupported chunk type 0`, all layers gone. Always check `#palette == 0` first.

**`saveCopyAs` always writes the whole sprite**; it cannot write a single frame. To export per frame, build a throwaway one-frame sprite with `Image:drawSprite(spr, i)` and save that.

**There is no text rendering API.** Aseprite Lua cannot draw text. Do not write a `draw_text` tool.

**Clipboard and selection do not survive across calls.** Each tool call is a separate Aseprite process, so the clipboard dies with it, and the `.aseprite` format does not persist a selection mask. Region operations must take explicit coordinates — see `selection.py`.

---

## Executable discovery

Resolution order in `AsepriteCommand.get_aseprite_executable()`:

1. `ASEPRITE_PATH` environment variable — **and the file must exist**; a stale path is skipped rather than raised
2. `core/path_resolver.py` scans Program Files, Steam, `%LOCALAPPDATA%`, `/Applications`, `$PATH`
3. Bare `aseprite` as a last resort

`.env` is loaded from an absolute path next to `pyproject.toml`, not from the cwd — an MCP server is normally spawned from the client's working directory, so a cwd-relative load finds nothing.

When Aseprite cannot be reached, tools return `Cannot run Aseprite at '<path>'`. The server does **not** die.

Inspect with `get_aseprite_info`, `get_godot_info`, `get_app_info`, `get_system_info`.

---

## Running

```bash
uv sync
uv run -m aseprite_mcp                                  # stdio server
uv run pytest tests/ --ignore=tests/smoke_test.py       # 84 unit tests, no Aseprite needed
uv run tests/smoke_test.py --clean                      # 53 checks against a real Aseprite
```

Two suites, split by what they need:

**`tests/test_core.py` and `tests/test_error_protocol.py`** cover the pure logic —
colour parsing, Lua escaping, traversal rejection, CIELAB matching, dither
matrices, wildcard path expansion, and the `ERROR:` protocol itself with the
subprocess stubbed out. No Aseprite install, so these run in CI. 100% coverage
on `colors.py`, `color_space.py` and `dither.py`.

**`tests/smoke_test.py`** drives a real Aseprite. It exercises every tool this
fork added or rewrote, then checks invalid inputs are **rejected with the
expected message** — not merely "something failed", which would pass while
proving nothing.

Run both before committing anything under `tools/` or `core/`. CI
(`.github/workflows/ci.yml`) runs the unit suite, checks for duplicate tool
names, and verifies the server completes an MCP handshake.

---

## Staying in sync with upstream

This fork merges [diivi/aseprite-mcp](https://github.com/diivi/aseprite-mcp). The boundary is kept visible so re-syncing stays possible:

- **Taken from upstream unmodified:** `canvas`, `drawing`, `export`, `animation`, `layers`, `palette`, `fx`, `native_fx`, `pixel_read`, `analysis`, `quality`, `selection`, `slices`, `tilemap`, `transform`, `scene`, `script`, `preview`, `guide`
- **This fork's own:** `*_extra`, `transform_sprite`, `drawing_advanced`, `effects`, `cel_operations`, `layer_advanced`, `file_utils`, `ai_features`, `system_info`, `shading`, `dither_tools`, plus `core/color_space.py` and `core/dither.py`
- **`core/commands.py` is a blend:** the fork's `path_resolver` integration plus upstream's `lua_escape` / `reject_traversal` / `execute_lua_script_checked`

To pull a newer upstream: overwrite the first group, leave the second untouched, then re-run the smoke test and check for duplicate tool names:

```bash
uv run python -c "import asyncio,collections;from aseprite_mcp import mcp;import aseprite_mcp.tools;t=[x.name for x in asyncio.run(mcp.list_tools())];print(len(t),[n for n,c in collections.Counter(t).items() if c>1])"
```

FastMCP keeps whichever tool registered last and says nothing about the collision. That command is what catches it.
