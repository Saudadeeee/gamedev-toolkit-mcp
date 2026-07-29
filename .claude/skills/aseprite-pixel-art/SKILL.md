---
name: aseprite-pixel-art
description: Drawing pixel art with the aseprite MCP server — layer discipline, the *_at tools, palette-first colour, and verifying output by reading pixels back instead of assuming. Use when creating or editing any sprite, tile, icon, or texture.
---

# Drawing Pixel Art with aseprite-mcp

The server exposes 162 tools. Most mistakes come from picking the wrong five, not from missing capability.

## When to activate

- Creating a sprite, tile, icon, UI element, or texture
- Editing existing pixel art
- Colour work: palettes, ramps, recolouring, quantization
- Any task where the result is an image file rather than a scene

## The two rules that prevent most failures

### 1. Always use the `*_at` variants

`draw_pixels`, `draw_line`, `draw_rectangle`, `draw_circle` and `fill_area` operate on whatever cel Aseprite happens to consider active. Across separate tool calls that is not predictable — each call is its own Aseprite process.

The `*_at` variants take `layer_name` and `frame_index` explicitly and normalize the cel first, so coordinates are sprite-global and the target is unambiguous:

```
draw_pixels_at(filename, layer_name, frame_index, pixels, create_if_missing=True)
draw_line_at(filename, layer_name, frame_index, x1, y1, x2, y2, color, thickness)
draw_rectangle_at(filename, layer_name, frame_index, x, y, width, height, color, fill)
draw_circle_at(filename, layer_name, frame_index, center_x, center_y, radius, color, fill)
draw_ellipse_at(filename, layer_name, frame_index, center_x, center_y, radius_x, radius_y, color, fill)
fill_area_at(filename, layer_name, frame_index, x, y, color)
```

`draw_polygon`, `draw_path` and `apply_gradient_rect` already require layer + frame. Use those over the bare variants without exception.

### 2. Verify by reading pixels, not by trusting the return string

A tool returning "Rectangle drawn" means the script ran. It does not mean the result looks right — wrong layer order, wrong colour, off-by-one bounds all return success.

```
get_composite_rect(filename, x, y, width, height, frame_index)   # flattened result, JSON
get_pixels_rect(filename, x, y, width, height, layer_name, frame_index)  # one layer
get_pixel_color(filename, x, y, layer_name, frame_index)
export_frame(filename, frame_index, output_filename, scale=8)     # magnified PNG to look at
```

Export at `scale=8` or `10` and read the PNG when shape and readability matter. Use `get_composite_rect` when a specific pixel value matters. Check after each meaningful stage, not once at the end — a mistake at layer 1 is cheap to fix and expensive to find under layer 5.

## Layer discipline

Set up the layer stack before drawing anything. Repainting is destructive; hiding a layer is not.

```
create_canvas(width, height, filename)
add_layer(filename, "outline")
add_layer(filename, "base")
add_layer(filename, "shading")
add_layer(filename, "highlight")
```

Layers are drawn bottom-to-top in creation order. Group related layers with `add_group(filename, group_name, parent_group)` and address nested layers as `"group/child"` — `find_layer` resolves that path.

One concern per layer. When the user asks to "make the shading darker", a separate shading layer is a one-call change; a merged sprite is a repaint.

`create_canvas` makes a sprite with a default `Layer 1`. Either draw on it by name or ignore it — do not assume it is gone.

## Colour

Set the palette first, then draw from it. Picking colours ad hoc produces sprites with 40 near-identical shades that read as muddy at 16×16.

```
list_palette_presets()                          # gameboy, pico8, c64, dawnbringer16, ...
apply_palette_preset(filename, "pico8")
generate_color_ramp(base_color, steps=5, hue_shift_degrees=20, lightness_range=0.5)
set_palette(filename, colors)
```

`generate_color_ramp` returns a shading ramp with hue shift built in — real pixel art shifts hue toward blue in shadow and toward yellow in light rather than just darkening. Take the ramp, then use its entries as your `color` arguments.

Colour arguments accept `#RGB`, `#RGBA`, `#RRGGBB` and `#RRGGBBAA`. Alpha is respected; use it for soft shadow layers.

To fix colour after the fact:

```
get_color_stats(filename, frame_index, top=16)     # what is actually in the image
quantize_to_palette(filename, layer_name, start_frame, end_frame)
remap_colors_in_cel_range(filename, layer_name, start_frame, end_frame, mappings)
replace_color(...)                                  # single colour swap
```

## Shading

Flat colour is a silhouette, not a sprite. `shade_directional` replaces every
opaque pixel with an entry from a ramp you supply, so the result cannot drift
off-palette the way a brightness filter would.

```
suggest_shading_ramp(filename, frame_index, steps)   # ramp from colours already present
shade_directional(filename, layer_name, ramp_colors, frame_index,
                  light_direction, style, intensity)
```

`light_direction` is one of eight compass points. `style`:

| style | Reads as |
|---|---|
| `smooth` | Gradual falloff across the form — the default for organic shapes |
| `hard` | Two tones with a sharp terminator — metal, cel-shaded, high contrast |
| `pillow` | Shading radiates from the centre outward. Usually a mistake: it ignores form and makes everything look like a cushion. Included because it is occasionally what you want for gems and orbs. |

Ramp order does not matter; entries are sorted dark-to-light by perceptual
luminance before use. Lower `intensity` compresses toward the lit end, leaving
the form flatter.

Shade on a duplicate layer when possible — shading is destructive, and a flat
base is much easier to re-light than a shaded one is to un-light.

## Palette snapping

`snap_to_palette` forces a cel onto a fixed palette, matching in CIELAB rather
than RGB. This matters: RGB distance treats an equal shift in red and in green
as equally different, so it regularly snaps to a visibly wrong entry. Use it on
imported art, or after any operation that introduced off-palette colours.

`sort_sprite_palette(filename, key)` reorders the palette by `luminance`,
`hue`, `saturation` or `lightness`. Luminance order makes the palette directly
usable as a shading ramp.

## Dithering

A smooth gradient introduces hundreds of colours and stops being pixel art.
Dithering blends two colours with a pattern instead.

```
list_dither_patterns()                                  # the catalogue
apply_dither_texture(..., pattern, density, only_opaque)
apply_dither_gradient_pattern(..., pattern, horizontal)
apply_floyd_steinberg(...)
```

| Group | Patterns | Use for |
|---|---|---|
| Ordered | `bayer2x2`, `bayer4x4`, `bayer8x8` | Gradients. Bigger matrix = smoother ramp, more visible grid at small sizes. |
| Screens | `checker`, `lines-horizontal`, `lines-vertical`, `diagonal`, `cross` | Flat ~50% blends, cloth, metal |
| Textures | `grass`, `water`, `stone`, `cloud`, `brick`, `dots`, `noise` | Material surfaces over a flat fill |
| Error diffusion | `apply_floyd_steinberg` | Photographic sources. Irregular, so it reads as noise at sprite size. |

Set `only_opaque=True` to texture a drawn shape without spilling into the
transparent background. Patterns tile against absolute canvas coordinates, so
adjacent fills line up.

## Antialiasing

```
detect_antialias_candidates(filename, layer_name, frame_index)   # read-only
apply_antialias(filename, layer_name, frame_index, max_pixels)
```

Detection is separate and read-only on purpose. Antialiasing costs palette
entries and reads as blur at small sizes, so it belongs on long diagonals and
curves, not on every corner. Inspect the count first.

## Effects worth knowing

Prefer the native engine filters — they are Aseprite's own implementations, not reimplementations:

```
outline_native(filename, layer_name, frame_index, color, place="outside", matrix="circle")
adjust_hsl_native(...)      adjust_brightness_contrast(...)      invert_colors(...)
apply_convolution(...)      list_convolution_matrices()
```

`apply_dither_gradient(filename, layer_name, frame_index, x, y, w, h, color_start, color_end, horizontal)` gives an ordered-dither blend — the correct way to gradient in pixel art, since a smooth gradient introduces hundreds of colours.

`posterize`, `pixelate` and `drop_shadow` have no native equivalent and are implemented per-pixel here.

## Slices and tiles

Slices mark named regions a game engine can cut out. Nine-patch slices additionally mark which pixels stretch:

```
create_slice(filename, name, x, y, width, height)
create_nine_patch_slice(filename, name, bounds, center)   # center is relative to bounds
set_slice_center(filename, name, x, y, width, height)
export_slices(filename, output_folder)                    # packed PNG + JSON map
```

For tilemaps:

```
create_tilemap_layer(filename, layer_name, tile_width, tile_height)
set_tiles(filename, layer_name, frame_index, tiles)
get_tilemap_info(filename)
```

## Escape hatch

`run_lua_script(script, filename)` runs arbitrary Lua against the sprite. Use it when no tool fits — but signal failure with `print("ERROR:...")`, since a bare `return` in Aseprite batch mode is discarded and the call reports success.

## Anti-patterns

| Don't | Do |
|---|---|
| `draw_rectangle` without layer/frame | `draw_rectangle_at` |
| Draw everything on one layer | One layer per concern |
| Pick colours per-call | Set a palette, draw from it |
| Trust "drawn successfully" | `get_composite_rect` or `export_frame(scale=8)` |
| Smooth gradient in pixel art | `apply_dither_gradient_pattern` with `bayer8x8` |
| Brightness filter to shade | `shade_directional` with a palette ramp |
| Nearest colour in RGB | `snap_to_palette` (matches in CIELAB) |
| Antialias everything | `detect_antialias_candidates` first, then apply selectively |
| Hand-rolled outline loop | `outline_native` |
| Write a `draw_text` helper | Aseprite Lua has no text API — import a pre-rendered PNG with `import_image_as_layer` |
