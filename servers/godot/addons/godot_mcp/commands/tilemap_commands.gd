@tool
class_name MCPTileMapCommands
extends MCPBaseCommandProcessor

## Command processor for TileMap and GridMap operations
## Handles 2D tile painting and 3D grid cell placement

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"set_tile_cell":
			_set_tile_cell(client_id, params, command_id)
			return true
		"erase_tile_cell":
			_erase_tile_cell(client_id, params, command_id)
			return true
		"paint_tile_area":
			_paint_tile_area(client_id, params, command_id)
			return true
		"get_tile_data":
			_get_tile_data(client_id, params, command_id)
			return true
		"get_used_tiles":
			_get_used_tiles(client_id, params, command_id)
			return true
		"clear_tilemap_layer":
			_clear_tilemap_layer(client_id, params, command_id)
			return true
		"set_gridmap_cell":
			_set_gridmap_cell(client_id, params, command_id)
			return true
		"erase_gridmap_cell":
			_erase_gridmap_cell(client_id, params, command_id)
			return true
		"get_gridmap_used_cells":
			_get_gridmap_used_cells(client_id, params, command_id)
			return true
	return false  # Command not handled

## TILEMAP (2D) COMMANDS

func _set_tile_cell(client_id: int, params: Dictionary, command_id: String) -> void:
	var tilemap_path = params.get("tilemap_path", "")
	var tilemap = _get_editor_node(tilemap_path)

	if not tilemap or not tilemap is TileMap:
		return _send_error(client_id, "TileMap not found or invalid: %s" % tilemap_path, command_id)

	var layer = params.get("layer", 0)
	var coords = Vector2i(params.get("coords_x", 0), params.get("coords_y", 0))
	var source_id = params.get("source_id", 0)
	var atlas_coords = Vector2i(params.get("atlas_coords_x", 0), params.get("atlas_coords_y", 0))
	var alternative = params.get("alternative_tile", 0)

	# Validate layer
	if layer < 0 or layer >= tilemap.get_layers_count():
		return _send_error(client_id, "Layer index %d out of range (max: %d)" % [layer, tilemap.get_layers_count() - 1], command_id)

	# Set the tile
	tilemap.set_cell(layer, coords, source_id, atlas_coords, alternative)
	_mark_scene_modified()

	_send_success(client_id, {
		"coords": [coords.x, coords.y],
		"layer": layer,
		"source_id": source_id
	}, command_id)

func _erase_tile_cell(client_id: int, params: Dictionary, command_id: String) -> void:
	var tilemap_path = params.get("tilemap_path", "")
	var tilemap = _get_editor_node(tilemap_path)

	if not tilemap or not tilemap is TileMap:
		return _send_error(client_id, "TileMap not found or invalid: %s" % tilemap_path, command_id)

	var layer = params.get("layer", 0)
	var coords = Vector2i(params.get("coords_x", 0), params.get("coords_y", 0))

	# Validate layer
	if layer < 0 or layer >= tilemap.get_layers_count():
		return _send_error(client_id, "Layer index %d out of range" % layer, command_id)

	# Erase the tile
	tilemap.erase_cell(layer, coords)
	_mark_scene_modified()

	_send_success(client_id, {
		"coords": [coords.x, coords.y],
		"layer": layer
	}, command_id)

func _paint_tile_area(client_id: int, params: Dictionary, command_id: String) -> void:
	var tilemap_path = params.get("tilemap_path", "")
	var tilemap = _get_editor_node(tilemap_path)

	if not tilemap or not tilemap is TileMap:
		return _send_error(client_id, "TileMap not found or invalid: %s" % tilemap_path, command_id)

	var layer = params.get("layer", 0)
	var start_x = params.get("start_x", 0)
	var start_y = params.get("start_y", 0)
	var end_x = params.get("end_x", 0)
	var end_y = params.get("end_y", 0)
	var source_id = params.get("source_id", 0)
	var atlas_coords = Vector2i(params.get("atlas_coords_x", 0), params.get("atlas_coords_y", 0))

	# Validate layer
	if layer < 0 or layer >= tilemap.get_layers_count():
		return _send_error(client_id, "Layer index %d out of range" % layer, command_id)

	# Paint the area
	var cells_painted = 0
	for x in range(start_x, end_x + 1):
		for y in range(start_y, end_y + 1):
			tilemap.set_cell(layer, Vector2i(x, y), source_id, atlas_coords, 0)
			cells_painted += 1

	_mark_scene_modified()

	_send_success(client_id, {
		"cells_painted": cells_painted,
		"area": [start_x, start_y, end_x, end_y],
		"layer": layer
	}, command_id)

func _get_tile_data(client_id: int, params: Dictionary, command_id: String) -> void:
	var tilemap_path = params.get("tilemap_path", "")
	var tilemap = _get_editor_node(tilemap_path)

	if not tilemap or not tilemap is TileMap:
		return _send_error(client_id, "TileMap not found or invalid: %s" % tilemap_path, command_id)

	var layer = params.get("layer", 0)
	var coords = Vector2i(params.get("coords_x", 0), params.get("coords_y", 0))

	# Validate layer
	if layer < 0 or layer >= tilemap.get_layers_count():
		return _send_error(client_id, "Layer index %d out of range" % layer, command_id)

	# Get tile data
	var source_id = tilemap.get_cell_source_id(layer, coords)
	var atlas_coords = tilemap.get_cell_atlas_coords(layer, coords)
	var alternative = tilemap.get_cell_alternative_tile(layer, coords)

	_send_success(client_id, {
		"coords": [coords.x, coords.y],
		"layer": layer,
		"source_id": source_id,
		"atlas_coords_x": atlas_coords.x,
		"atlas_coords_y": atlas_coords.y,
		"alternative_tile": alternative
	}, command_id)

func _get_used_tiles(client_id: int, params: Dictionary, command_id: String) -> void:
	var tilemap_path = params.get("tilemap_path", "")
	var tilemap = _get_editor_node(tilemap_path)

	if not tilemap or not tilemap is TileMap:
		return _send_error(client_id, "TileMap not found or invalid: %s" % tilemap_path, command_id)

	var layer = params.get("layer", 0)

	# Validate layer
	if layer < 0 or layer >= tilemap.get_layers_count():
		return _send_error(client_id, "Layer index %d out of range" % layer, command_id)

	# Get used cells
	var used_cells = tilemap.get_used_cells(layer)
	var cells_array = []

	for cell in used_cells:
		cells_array.append([cell.x, cell.y])

	_send_success(client_id, {
		"used_cells": cells_array,
		"count": cells_array.size(),
		"layer": layer
	}, command_id)

func _clear_tilemap_layer(client_id: int, params: Dictionary, command_id: String) -> void:
	var tilemap_path = params.get("tilemap_path", "")
	var tilemap = _get_editor_node(tilemap_path)

	if not tilemap or not tilemap is TileMap:
		return _send_error(client_id, "TileMap not found or invalid: %s" % tilemap_path, command_id)

	var layer = params.get("layer", 0)

	# Validate layer
	if layer < 0 or layer >= tilemap.get_layers_count():
		return _send_error(client_id, "Layer index %d out of range" % layer, command_id)

	# Clear the layer
	tilemap.clear_layer(layer)
	_mark_scene_modified()

	_send_success(client_id, {
		"layer": layer
	}, command_id)

## GRIDMAP (3D) COMMANDS

func _set_gridmap_cell(client_id: int, params: Dictionary, command_id: String) -> void:
	var gridmap_path = params.get("gridmap_path", "")
	var gridmap = _get_editor_node(gridmap_path)

	if not gridmap or not gridmap is GridMap:
		return _send_error(client_id, "GridMap not found or invalid: %s" % gridmap_path, command_id)

	var pos = Vector3i(params.get("pos_x", 0), params.get("pos_y", 0), params.get("pos_z", 0))
	var item_id = params.get("item_id", 0)
	var orientation = params.get("orientation", 0)

	# Validate item_id
	if item_id < 0:
		return _send_error(client_id, "Item ID cannot be negative", command_id)

	# Validate orientation (0-23)
	if orientation < 0 or orientation > 23:
		return _send_error(client_id, "Orientation must be between 0 and 23", command_id)

	# Set the cell
	gridmap.set_cell_item(pos, item_id, orientation)
	_mark_scene_modified()

	_send_success(client_id, {
		"position": [pos.x, pos.y, pos.z],
		"item_id": item_id,
		"orientation": orientation
	}, command_id)

func _erase_gridmap_cell(client_id: int, params: Dictionary, command_id: String) -> void:
	var gridmap_path = params.get("gridmap_path", "")
	var gridmap = _get_editor_node(gridmap_path)

	if not gridmap or not gridmap is GridMap:
		return _send_error(client_id, "GridMap not found or invalid: %s" % gridmap_path, command_id)

	var pos = Vector3i(params.get("pos_x", 0), params.get("pos_y", 0), params.get("pos_z", 0))

	# Erase the cell (set to -1)
	gridmap.set_cell_item(pos, -1)
	_mark_scene_modified()

	_send_success(client_id, {
		"position": [pos.x, pos.y, pos.z]
	}, command_id)

func _get_gridmap_used_cells(client_id: int, params: Dictionary, command_id: String) -> void:
	var gridmap_path = params.get("gridmap_path", "")
	var gridmap = _get_editor_node(gridmap_path)

	if not gridmap or not gridmap is GridMap:
		return _send_error(client_id, "GridMap not found or invalid: %s" % gridmap_path, command_id)

	# Get used cells
	var used_cells = gridmap.get_used_cells()
	var cells_array = []

	for cell in used_cells:
		cells_array.append([cell.x, cell.y, cell.z])

	_send_success(client_id, {
		"used_cells": cells_array,
		"count": cells_array.size()
	}, command_id)
