"""Tool modules. Importing a module registers its @mcp.tool() functions.

Grouped by origin so the boundary stays visible when re-syncing with
https://github.com/diivi/aseprite-mcp upstream:

* upstream modules are taken as-is
* ``*_extra`` / ``*_sprite`` modules hold tools this fork adds on top
* ``system_info`` is the Godot/Aseprite path bridge, specific to this fork
"""

# Canvas, drawing and export primitives
from . import canvas
from . import drawing
from . import drawing_advanced
from . import export
from . import export_extra

# Animation, cels and frames
from . import animation
from . import cel_operations

# Layers
from . import layers
from . import layer_advanced
from . import scene

# Color
from . import palette
from . import palette_extra
from . import fx
from . import native_fx
from . import effects
from . import dither_tools
from . import shading

# Reading back what was drawn
from . import pixel_read
from . import analysis
from . import quality

# Regions, slices, tilemaps, transforms
from . import selection
from . import slices
from . import slices_extra
from . import tilemap
from . import transform
from . import transform_sprite

# Files, environment and escape hatches
from . import file_utils
from . import system_info
from . import preview
from . import script
from . import guide
from . import ai_features
