@tool
class_name MCPNavigationCommands
extends MCPBaseCommandProcessor

## Command processor for Navigation operations

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"bake_navigation_mesh":
			_bake_navigation_mesh(client_id, params, command_id)
			return true
		"get_navigation_path":
			_get_navigation_path(client_id, params, command_id)
			return true
		"set_navigation_target":
			_set_navigation_target(client_id, params, command_id)
			return true
		"get_navigation_agent_info":
			_get_navigation_agent_info(client_id, params, command_id)
			return true
		"configure_navigation_region":
			_configure_navigation_region(client_id, params, command_id)
			return true
		"set_navigation_mesh_property":
			_set_navigation_mesh_property(client_id, params, command_id)
			return true
	return false

func _bake_navigation_mesh(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	if node.has_method("bake_navigation_mesh"):
		node.bake_navigation_mesh()
		_send_success(client_id, {"message": "Navigation mesh baking started for %s" % node_path, "node_path": node_path}, command_id)
	else:
		return _send_error(client_id, "Node does not support bake_navigation_mesh: %s" % node.get_class(), command_id)

func _get_navigation_path(client_id: int, params: Dictionary, command_id: String) -> void:
	var is_3d = params.get("is_3d", false)
	var from_x = params.get("from_x", 0.0)
	var from_y = params.get("from_y", 0.0)
	var to_x = params.get("to_x", 0.0)
	var to_y = params.get("to_y", 0.0)

	var path_points = []

	if is_3d:
		var from_z = params.get("from_z", 0.0)
		var to_z = params.get("to_z", 0.0)
		var map = NavigationServer3D.get_maps()
		if map.is_empty():
			return _send_error(client_id, "No 3D navigation map found", command_id)
		var path = NavigationServer3D.map_get_path(map[0], Vector3(from_x, from_y, from_z), Vector3(to_x, to_y, to_z), true)
		for pt in path:
			path_points.append([pt.x, pt.y, pt.z])
	else:
		var map = NavigationServer2D.get_maps()
		if map.is_empty():
			return _send_error(client_id, "No 2D navigation map found", command_id)
		var path = NavigationServer2D.map_get_path(map[0], Vector2(from_x, from_y), Vector2(to_x, to_y), true)
		for pt in path:
			path_points.append([pt.x, pt.y])

	_send_success(client_id, {
		"path": path_points,
		"point_count": path_points.size(),
		"is_3d": is_3d
	}, command_id)

func _set_navigation_target(client_id: int, params: Dictionary, command_id: String) -> void:
	var agent_path = params.get("agent_path", "")
	var node = _get_editor_node(agent_path)
	if not node:
		return _send_error(client_id, "NavigationAgent not found: %s" % agent_path, command_id)

	var target_x = params.get("target_x", 0.0)
	var target_y = params.get("target_y", 0.0)

	if node.get_class() == "NavigationAgent3D":
		var target_z = params.get("target_z", 0.0)
		node.set_target_position(Vector3(target_x, target_y, target_z))
	elif node.get_class() == "NavigationAgent2D":
		node.set_target_position(Vector2(target_x, target_y))
	else:
		return _send_error(client_id, "Node is not a NavigationAgent: %s" % node.get_class(), command_id)

	_mark_scene_modified()
	_send_success(client_id, {"message": "Navigation target set", "agent_path": agent_path}, command_id)

func _get_navigation_agent_info(client_id: int, params: Dictionary, command_id: String) -> void:
	var agent_path = params.get("agent_path", "")
	var node = _get_editor_node(agent_path)
	if not node:
		return _send_error(client_id, "NavigationAgent not found: %s" % agent_path, command_id)

	var info = {"node_class": node.get_class(), "agent_path": agent_path}

	if node.has_method("get_target_position"):
		var target = node.get_target_position()
		if target is Vector3:
			info["target_position"] = [target.x, target.y, target.z]
		elif target is Vector2:
			info["target_position"] = [target.x, target.y]

	if "path_desired_distance" in node:
		info["path_desired_distance"] = node.path_desired_distance
	if "target_desired_distance" in node:
		info["target_desired_distance"] = node.target_desired_distance
	if "max_speed" in node:
		info["max_speed"] = node.max_speed
	if "navigation_layers" in node:
		info["navigation_layers"] = node.navigation_layers

	_send_success(client_id, info, command_id)

func _configure_navigation_region(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "NavigationRegion not found: %s" % node_path, command_id)

	if params.has("enabled") and "enabled" in node:
		node.enabled = params["enabled"]
	if params.has("navigation_layers") and "navigation_layers" in node:
		node.navigation_layers = params["navigation_layers"]
	if params.has("enter_cost") and "enter_cost" in node:
		node.enter_cost = params["enter_cost"]
	if params.has("travel_cost") and "travel_cost" in node:
		node.travel_cost = params["travel_cost"]

	_mark_scene_modified()
	_send_success(client_id, {"message": "Navigation region configured", "node_path": node_path}, command_id)

func _set_navigation_mesh_property(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "NavigationRegion3D not found: %s" % node_path, command_id)

	if not node.has_method("get_navigation_mesh") and not "navigation_mesh" in node:
		return _send_error(client_id, "Node does not have a navigation mesh", command_id)

	var nav_mesh = node.navigation_mesh
	if not nav_mesh:
		nav_mesh = NavigationMesh.new()
		node.navigation_mesh = nav_mesh

	var property = params.get("property", "")
	var value = params.get("value")

	if not property in nav_mesh:
		return _send_error(client_id, "Property not found on NavigationMesh: %s" % property, command_id)

	nav_mesh.set(property, value)
	_mark_scene_modified()
	_send_success(client_id, {"message": "Navigation mesh property set", "property": property, "value": value}, command_id)
