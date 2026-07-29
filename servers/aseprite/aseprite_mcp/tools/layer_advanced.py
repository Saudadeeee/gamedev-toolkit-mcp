"""Layer-group reparenting and multi-layer merge.

Rename, delete, duplicate, reorder, blend mode, merge-down and flatten live in
:mod:`layers`; visibility and opacity live in :mod:`animation`; creating a
group lives in :mod:`canvas`. What none of them cover is moving an *existing*
layer into (or out of) a group, and collapsing an arbitrary set of layers into
one — both added here.
"""

import os
from typing import List

from ..core.commands import AsepriteCommand, lua_escape
from ..core.lua import FIND_LAYER
from .. import mcp


@mcp.tool()
async def move_layer_to_group(filename: str, layer_name: str, group_name: str = "") -> str:
    """Move an existing layer into a group, or back out to the sprite root.

    Args:
        filename: Aseprite file to modify
        layer_name: Layer to reparent
        group_name: Destination group name; empty string moves the layer to
            the sprite root
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if not layer_name.strip():
        return "layer_name cannot be empty"

    safe_layer = lua_escape(layer_name)
    safe_group = lua_escape(group_name)

    script = f"""
    {FIND_LAYER}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local target = find_layer(spr, "{safe_layer}")
    if not target then print("ERROR:Layer not found") return end

    local parent = spr
    if "{safe_group}" ~= "" then
        local group = find_layer(spr, "{safe_group}")
        if not group then print("ERROR:Group not found") return end
        if not group.isGroup then print("ERROR:Destination is not a group") return end
        local walk = group
        while walk do
            if walk == target then print("ERROR:Cannot move a group into itself") return end
            walk = walk.parent
            if walk == spr then break end
        end
        parent = group
    end

    app.transaction(function()
        target.parent = parent
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        destination = f"group '{group_name}'" if group_name else "the sprite root"
        return f"Moved layer '{layer_name}' to {destination} in {filename}"
    return f"Failed to move layer: {output}"


@mcp.tool()
async def merge_layers(filename: str, layer_names: List[str], result_name: str = "") -> str:
    """Flatten several layers into one, bottom-up, across every frame.

    Layers are composited in their current stacking order — the lowest named
    layer receives the result and the others are deleted. Use ``merge_layer_down``
    when only two adjacent layers are involved.

    Args:
        filename: Aseprite file to modify
        layer_names: At least two layer names to merge
        result_name: Name for the merged layer; empty keeps the bottom layer's name
    """
    if not os.path.exists(filename):
        return f"File {filename} not found"
    if not layer_names or len(layer_names) < 2:
        return "layer_names needs at least 2 entries"
    if len(set(layer_names)) != len(layer_names):
        return "layer_names contains duplicates"

    names_lua = ", ".join(f'"{lua_escape(n)}"' for n in layer_names)
    safe_result = lua_escape(result_name)

    script = f"""
    {FIND_LAYER}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local wanted = {{{names_lua}}}
    -- Match by name, not by object identity: Aseprite hands out a fresh
    -- userdata wrapper on each access, so a layer used as a table key never
    -- matches the same layer reached through a second traversal.
    local want = {{}}
    for _, name in ipairs(wanted) do
        local l = find_layer(spr, name)
        if not l then print("ERROR:Layer not found: " .. name) return end
        if l.isGroup then print("ERROR:Cannot merge a group: " .. name) return end
        want[l.name] = true
    end

    -- Walk the sprite in stacking order so compositing respects z-order.
    local ordered = {{}}
    local function walk(layers)
        for _, l in ipairs(layers) do
            if l.isGroup then
                walk(l.layers)
            elseif want[l.name] then
                ordered[#ordered + 1] = l
                want[l.name] = nil
            end
        end
    end
    walk(spr.layers)
    if #ordered < 2 then print("ERROR:Fewer than 2 mergeable layers resolved") return end

    local base = ordered[1]

    app.transaction(function()
        for f = 1, #spr.frames do
            local acc = Image(spr.width, spr.height, spr.colorMode)
            for _, l in ipairs(ordered) do
                local cel = l:cel(f)
                if cel and l.isVisible then
                    acc:drawImage(cel.image, cel.position, l.opacity, l.blendMode)
                end
            end
            local base_cel = base:cel(f)
            if base_cel then
                base_cel.image = acc
                base_cel.position = Point(0, 0)
            else
                spr:newCel(base, f, acc, Point(0, 0))
            end
        end

        base.opacity = 255
        base.blendMode = BlendMode.NORMAL
        if "{safe_result}" ~= "" then base.name = "{safe_result}" end

        for i = #ordered, 2, -1 do spr:deleteLayer(ordered[i]) end
    end)

    spr:saveAs(spr.filename)
    print("merged=" .. #ordered)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if not success:
        return f"Failed to merge layers: {output}"

    # Aseprite may prepend warnings to stdout, so pick out our own line
    # rather than assuming the count is the last thing printed.
    count = next(
        (line.split("=", 1)[1] for line in output.splitlines() if line.startswith("merged=")),
        str(len(layer_names)),
    )
    label = result_name or layer_names[0]
    return f"Merged {count} layers into '{label}' in {filename}"
