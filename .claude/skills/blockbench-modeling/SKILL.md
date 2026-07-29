---
name: blockbench-modeling
description: Low-poly 3D modelling with the blockbench MCP server — format choice, box modelling discipline, UV layout, texturing from Aseprite pixel art, bone rigs, and the export formats Godot actually wants. Use for any 3D model, voxel-style asset, or model texture work.
---

# Modelling with blockbench-mcp

Blockbench is a box modeller: geometry is cubes and meshes with flat, usually
pixel-art textures. That constraint is the point — it is why models made here
sit next to Aseprite sprites without looking out of place.

The MCP server runs **inside Blockbench** as a plugin, serving HTTP on
`localhost:3000/bb-mcp` — usually. The plugin picks its own port, so 3456 and
3001 also turn up; `scripts/write_mcp_config.py` probes the candidates listed in
`toolkit.json` and pins whichever answers. Blockbench must be open before any
tool answers. Check with `get_blockbench_info` on the `aseprite` server.

## When to activate

- Creating or editing a 3D model, prop, character or tile
- UV layout and model texturing
- Rigging bones or animating a model
- Exporting a model for Godot

## Pick the format first — it is hard to change later

Blockbench projects have a format, and it constrains everything after it.

| Format | Use for | Constraint |
|---|---|---|
| **Generic Model** | Anything going to Godot or a general engine | Free — cubes and meshes, any size |
| **Modded Entity** | Minecraft mod entities | Java-model rules |
| **Bedrock Model** | Minecraft Bedrock | Bedrock geometry schema |
| **Java Block/Item** | Minecraft resource packs | 3x3 cube limit, 16px grid |
| **Free Mesh** | Organic shapes | No cube primitives; harder to keep low-poly |

For a Godot game, use **Generic Model** unless you are specifically targeting
Minecraft. Starting in a Minecraft format and exporting to glTF later means
fighting rules that exist for a different engine.

## Build order

Same discipline as layers in Aseprite: structure before detail, because
restructuring later is destructive.

1. **Blockout** — the silhouette in a handful of cubes at the real scale
2. **Group** — one group per moving part (`head`, `torso`, `arm_left`)
3. **Refine** — subdivide only where the shape needs it
4. **UV** — lay out the map before texturing, not after
5. **Texture** — apply the PNG, then adjust UVs to suit
6. **Rig** — bones parented to the groups from step 2
7. **Animate** — keyframes on the bones

Groups made in step 2 become bones in step 6 and node names in Godot. Name
them as you want them to appear in the engine.

## Scale and grid

Decide the unit scale once. Blockbench works in "pixels" where 16 units is
conventionally 1 metre (a Minecraft block). Godot works in metres.

- Model at 16 units = 1 m, and the glTF export lands at the right size in Godot
- Keep vertices on whole units where possible — off-grid geometry shows as
  seams and z-fighting in a low-poly style
- A 1×1×1 metre prop is a 16×16×16 cube here

## UV layout

The UV map is what makes a pixel-art texture read correctly. Two rules do most
of the work:

- **Match texel density across faces.** A face that gets twice the UV area for
  the same world size renders at twice the resolution and looks wrong next to
  its neighbours.
- **Snap UVs to the texture's pixel grid.** Half-pixel UV offsets sample
  between texels and produce the blurry, shimmering edges that ruin pixel art
  in 3D.

Box UV (auto-unwrap per cube) is right for blocky models. Reach for manual UV
only when reusing texture space matters.

## Texturing from Aseprite

Author the texture in Aseprite, not in Blockbench's paint mode — you get
layers, palettes, dithering and shading there, and none of that here.

```
# Aseprite: size the canvas to the UV space, power-of-two
create_canvas(64, 64, "sources/models/hero_tex.aseprite")
... draw, shade_directional, snap_to_palette ...
export_sprite(..., "game/assets/models/hero_tex.png")

# Blockbench: apply it as the model texture, then fit UVs to it
```

Keep the texture power-of-two (16/32/64/128). Use **nearest** filtering in
Godot's import settings — the default linear filter blurs a 64px texture the
moment the model is anything but head-on.

## Export for Godot

| Format | Carries | Use when |
|---|---|---|
| **glTF / GLB** | meshes, materials, bones, animation | default choice for Godot |
| **OBJ** | meshes and materials only | static props, no animation |
| **Blockbench `.bbmodel`** | everything, but Godot cannot read it | keep as the source file |

GLB is a single file with the texture embedded — simpler to move. glTF +
separate PNG keeps the texture editable in place, which matters when Aseprite
is still iterating on it.

Export into the Godot project (`game/assets/models/`), then call
`import_project_assets` on the `godot-mcp` server so Godot picks it up without
anyone opening the editor.

## Anti-patterns

| Don't | Do |
|---|---|
| Start in a Minecraft format for a Godot game | Generic Model |
| Paint textures in Blockbench | Author in Aseprite, apply here |
| Model at an arbitrary scale | 16 units = 1 m, on-grid vertices |
| Texture before laying out UVs | UV first, then texture to fit |
| Export OBJ for an animated model | glTF/GLB |
| Leave the texture filter at default in Godot | Nearest, or the pixels blur |
| Detail every face | Detail what the camera sees; it is a low-poly style |
