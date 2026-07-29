---
name: aseprite-mcp-dev
description: Adding or modifying tools in the aseprite MCP server itself — the ERROR protocol, Lua escaping, cel normalization, known Aseprite Lua traps, and the smoke test gate. Use when editing files under servers/aseprite/aseprite_mcp/.
---

# Working on the aseprite MCP Server

Read [`servers/aseprite/DEVELOPING.md`](../../../servers/aseprite/DEVELOPING.md) for the full architecture. This skill is the checklist for touching the code.

## When to activate

- Adding a new `@mcp.tool()` function
- Fixing or extending an existing tool
- Merging a newer upstream from `diivi/aseprite-mcp`
- Debugging a tool that reports success but does nothing

## The failure mode this codebase is built around

Aseprite's batch runner **discards a top-level Lua `return`** and **always exits 0**. A script that hits an error looks byte-identical, from Python's side, to one that worked. Every convention below exists to close that hole.

## Checklist for a new tool

**1. Validate in Python before generating Lua.** File existence, numeric ranges, enum values, colour parsing. Return a plain string on rejection — cheaper than a process spawn and the message is clearer.

```python
if not os.path.exists(filename):
    return f"File {filename} not found"
if width <= 0 or height <= 0:
    return "width and height must be positive"

rgba = parse_hex_color(color)
if rgba is None:
    return f"Invalid color value: {color}"
r, g, b, a = rgba
```

**2. Escape every interpolated string.** Numbers are safe after `int()`/`float()` coercion; strings are not.

```python
from ..core.commands import lua_escape, reject_traversal

safe_layer = lua_escape(layer_name)
error = reject_traversal(output_path)   # for any path the user supplies
if error:
    return error
```

**3. Signal Lua failure with `ERROR:`.**

```lua
local spr = app.activeSprite
if not spr then print("ERROR:No active sprite") return end
if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end
```

**4. Resolve the target explicitly.** Never rely on `app.activeLayer` / `app.activeCel` — each tool call is a separate process with unpredictable active state.

```python
from ..core.lua import FIND_LAYER, NORMALIZE_CEL, PSET
```

```lua
local target = find_layer(spr, "{safe_layer}")
if not target then print("ERROR:Layer not found") return end
if target.isGroup then print("ERROR:Layer is a group") return end

local cel = normalize_cel(spr, target, idx, true)   -- canvas-sized, anchored (0,0)
local img = cel.image
```

`normalize_cel` is what makes coordinates sprite-global. Skip it and drawing lands at an offset whenever the cel has been moved.

**5. Wrap mutations in a transaction and save.**

```lua
app.transaction(function()
    -- mutations
end)
spr:saveAs(spr.filename)
print("OK")
```

**6. Use the checked runner and return a useful message.**

```python
success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
if success:
    return f"Did the thing on '{layer_name}' frame {frame_index} in {filename}"
return f"Failed to do the thing: {output}"
```

Print a count rather than `"OK"` when the caller could plausibly want it (`print("pixels=" .. n)`), then surface it in the return string. A tool that reports `stray=0` tells the caller it ran and found nothing; `OK` does not distinguish that from a no-op bug.

**7. Register the module** in `tools/__init__.py`.

**8. Check for a name collision.** FastMCP keeps whichever tool registered last and says nothing.

```bash
uv run python -c "import asyncio,collections;from aseprite_mcp import mcp;import aseprite_mcp.tools;t=[x.name for x in asyncio.run(mcp.list_tools())];print(len(t),[n for n,c in collections.Counter(t).items() if c>1])"
```

**9. Add coverage to `tests/smoke_test.py`** — an `expect_ok` for the happy path, and `expect_failure(label, coro, expected_message)` for each rejection. Matching the message, not just "something failed", is what catches a tool failing for the wrong reason.

**10. Run the gate.**

```bash
uv run tests/smoke_test.py --clean
```

## Aseprite Lua traps

Each of these cost real debugging time. They are not in Aseprite's docs.

**Closing a source sprite frees images derived from it.** Opening a second sprite to read its pixels? `close()` it *after* the read loop. Close it first and Aseprite segfaults with an empty stderr — the tool reports failure with no message at all.

**Layer objects cannot be table keys.** Aseprite returns a fresh userdata wrapper per property access, so `set[layer] = true` never matches the same layer found by a later traversal. Key on `layer.name`.

**An empty palette corrupts the file.** `spr:setPalette(p)` with `#p == 0` writes a sprite that fails to reopen — `Unsupported chunk type 0`, all layers gone. Guard with `if #palette == 0 then print("ERROR:...") return end`.

**`Color{fromString="#RRGGBBAA"}` silently yields transparent black.** Aseprite parses 6 hex digits only. Always pass channels numerically: `Color(r, g, b, a)`.

**`saveCopyAs` always writes the whole sprite.** For per-frame output, build a throwaway one-frame sprite with `Image:drawSprite(spr, i)` and save that.

**Native `app.command.*` filters act on the active target, not on arguments.** Use `core/native.py::build_native_command_script`, which activates the layer/frame first and fails loudly if it cannot.

**There is no text rendering API.** Do not add a `draw_text` tool. Import a pre-rendered PNG instead.

**Clipboard and selection do not persist across calls.** Separate processes; the `.aseprite` format stores no selection mask. Region tools must take explicit coordinates.

## Where code belongs

| Kind | Location |
|---|---|
| Upstream module, unmodified | `tools/{canvas,drawing,export,animation,layers,palette,fx,native_fx,pixel_read,analysis,quality,selection,slices,tilemap,transform,scene,script,preview,guide}.py` |
| This fork's additions | `tools/*_extra.py`, `transform_sprite.py`, `drawing_advanced.py`, `effects.py`, `cel_operations.py`, `layer_advanced.py`, `file_utils.py`, `ai_features.py`, `system_info.py` |
| Reusable Lua | `core/lua.py` |
| Shared Python helpers | `core/colors.py`, `core/commands.py`, `utils/` |

Keep additions out of upstream modules. The split is what makes re-syncing a newer `diivi/aseprite-mcp` a file copy rather than a merge conflict.

## Reviewing a diff

- Does every Lua error path `print("ERROR:...")` instead of `return`?
- Does it call `execute_lua_script_checked`, not `execute_lua_script`?
- Is every interpolated string wrapped in `lua_escape`?
- Does any user-supplied path skip `reject_traversal`?
- Does it resolve layer + frame explicitly rather than using active state?
- Are sprite-global coordinates preceded by `normalize_cel`?
- Is a second opened sprite closed *after* its pixels are read?
- Does `smoke_test.py` cover both the success and the rejection?
