@tool
class_name MCPPathCommands
extends MCPBaseCommandProcessor

## Command processor for Path2D/Path3D operations

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"add_path_point":
			_add_path_point(client_id, params, command_id)
			return true
		"remove_path_point":
			_remove_path_point(client_id, params, command_id)
			return true
		"set_path_point":
			_set_path_point(client_id, params, command_id)
			return true
		"get_path_info":
			_get_path_info(client_id, params, command_id)
			return true
		"clear_path":
			_clear_path(client_id, params, command_id)
			return true
		"configure_path_follow":
			_configure_path_follow(client_id, params, command_id)
			return true
		"set_curve_baked_resolution":
			_set_curve_baked_resolution(client_id, params, command_id)
			return true
	return false

func _get_curve(node: Node) -> Object:
	if node.get_class() == "Path2D" or node.get_class() == "Path3D":
		if node.curve:
			return node.curve
		# Create curve if missing
		if node.get_class() == "Path2D":
			node.curve = Curve2D.new()
		else:
			node.curve = Curve3D.new()
		return node.curve
	return null

func _add_path_point(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Path node not found: %s" % node_path, command_id)

	var curve = _get_curve(node)
	if not curve:
		return _send_error(client_id, "Node is not a Path2D or Path3D: %s" % node.get_class(), command_id)

	var index = params.get("index", -1)

	if node.get_class() == "Path2D":
		var pos = Vector2(params.get("x", 0.0), params.get("y", 0.0))
		var handle_in = Vector2(params.get("in_x", 0.0), params.get("in_y", 0.0))
		var handle_out = Vector2(params.get("out_x", 0.0), params.get("out_y", 0.0))
		if index == -1:
			curve.add_point(pos, handle_in, handle_out)
		else:
			curve.add_point(pos, handle_in, handle_out, index)
		_mark_scene_modified()
		_send_success(client_id, {
			"message": "Path2D point added",
			"point_count": curve.get_point_count(),
			"position": [pos.x, pos.y]
		}, command_id)
	elif node.get_class() == "Path3D":
		var pos = Vector3(params.get("x", 0.0), params.get("y", 0.0), params.get("z", 0.0))
		var handle_in = Vector3(params.get("in_x", 0.0), params.get("in_y", 0.0), params.get("in_z", 0.0))
		var handle_out = Vector3(params.get("out_x", 0.0), params.get("out_y", 0.0), params.get("out_z", 0.0))
		if index == -1:
			curve.add_point(pos, handle_in, handle_out)
		else:
			curve.add_point(pos, handle_in, handle_out, index)
		_mark_scene_modified()
		_send_success(client_id, {
			"message": "Path3D point added",
			"point_count": curve.get_point_count(),
			"position": [pos.x, pos.y, pos.z]
		}, command_id)

func _remove_path_point(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Path node not found: %s" % node_path, command_id)

	var curve = _get_curve(node)
	if not curve:
		return _send_error(client_id, "Node has no curve", command_id)

	var index = params.get("index", 0)
	if index < 0 or index >= curve.get_point_count():
		return _send_error(client_id, "Point index out of range: %d" % index, command_id)

	curve.remove_point(index)
	_mark_scene_modified()
	_send_success(client_id, {"message": "Path point removed", "index": index, "remaining_points": curve.get_point_count()}, command_id)

func _set_path_point(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Path node not found: %s" % node_path, command_id)

	var curve = _get_curve(node)
	if not curve:
		return _send_error(client_id, "Node has no curve", command_id)

	var index = params.get("index", 0)
	if index < 0 or index >= curve.get_point_count():
		return _send_error(client_id, "Point index out of range: %d" % index, command_id)

	if node.get_class() == "Path2D":
		if params.has("x") or params.has("y"):
			var current = curve.get_point_position(index)
			curve.set_point_position(index, Vector2(params.get("x", current.x), params.get("y", current.y)))
		if params.has("in_x") or params.has("in_y"):
			var current_in = curve.get_point_in(index)
			curve.set_point_in(index, Vector2(params.get("in_x", current_in.x), params.get("in_y", current_in.y)))
		if params.has("out_x") or params.has("out_y"):
			var current_out = curve.get_point_out(index)
			curve.set_point_out(index, Vector2(params.get("out_x", current_out.x), params.get("out_y", current_out.y)))
	elif node.get_class() == "Path3D":
		if params.has("x") or params.has("y") or params.has("z"):
			var current = curve.get_point_position(index)
			curve.set_point_position(index, Vector3(params.get("x", current.x), params.get("y", current.y), params.get("z", current.z)))
		if params.has("in_x") or params.has("in_y") or params.has("in_z"):
			var current_in = curve.get_point_in(index)
			curve.set_point_in(index, Vector3(params.get("in_x", current_in.x), params.get("in_y", current_in.y), params.get("in_z", current_in.z)))
		if params.has("out_x") or params.has("out_y") or params.has("out_z"):
			var current_out = curve.get_point_out(index)
			curve.set_point_out(index, Vector3(params.get("out_x", current_out.x), params.get("out_y", current_out.y), params.get("out_z", current_out.z)))

	_mark_scene_modified()
	_send_success(client_id, {"message": "Path point updated", "index": index}, command_id)

func _get_path_info(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Path node not found: %s" % node_path, command_id)

	var curve = _get_curve(node)
	if not curve:
		return _send_error(client_id, "Node is not a Path2D or Path3D: %s" % node.get_class(), command_id)

	var info = {
		"node_class": node.get_class(),
		"point_count": curve.get_point_count(),
		"bake_interval": curve.bake_interval,
		"baked_length": curve.get_baked_length(),
		"points": []
	}

	for i in range(curve.get_point_count()):
		var pt = {"index": i}
		var pos = curve.get_point_position(i)
		var pt_in = curve.get_point_in(i)
		var pt_out = curve.get_point_out(i)
		if node.get_class() == "Path2D":
			pt["position"] = [pos.x, pos.y]
			pt["handle_in"] = [pt_in.x, pt_in.y]
			pt["handle_out"] = [pt_out.x, pt_out.y]
		else:
			pt["position"] = [pos.x, pos.y, pos.z]
			pt["handle_in"] = [pt_in.x, pt_in.y, pt_in.z]
			pt["handle_out"] = [pt_out.x, pt_out.y, pt_out.z]
		info["points"].append(pt)

	_send_success(client_id, info, command_id)

func _clear_path(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Path node not found: %s" % node_path, command_id)

	var curve = _get_curve(node)
	if not curve:
		return _send_error(client_id, "Node has no curve", command_id)

	curve.clear_points()
	_mark_scene_modified()
	_send_success(client_id, {"message": "Path cleared"}, command_id)

func _configure_path_follow(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "PathFollow not found: %s" % node_path, command_id)

	var follow_class = node.get_class()
	if follow_class not in ["PathFollow2D", "PathFollow3D"]:
		return _send_error(client_id, "Node is not a PathFollow: %s" % follow_class, command_id)

	if params.has("progress"):
		node.progress = params["progress"]
	if params.has("progress_ratio"):
		node.progress_ratio = params["progress_ratio"]
	if params.has("h_offset"):
		node.h_offset = params["h_offset"]
	if params.has("v_offset"):
		node.v_offset = params["v_offset"]
	if params.has("loop"):
		node.loop = params["loop"]

	if follow_class == "PathFollow3D" and params.has("rotation_mode"):
		var mode_map = {"none": 0, "y": 1, "xy": 2, "xyz": 3, "oriented": 4}
		if params["rotation_mode"] in mode_map:
			node.rotation_mode = mode_map[params["rotation_mode"]]

	_mark_scene_modified()
	_send_success(client_id, {"message": "PathFollow configured", "node_path": node_path}, command_id)

func _set_curve_baked_resolution(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Path node not found: %s" % node_path, command_id)

	var curve = _get_curve(node)
	if not curve:
		return _send_error(client_id, "Node has no curve", command_id)

	curve.bake_interval = params.get("bake_interval", 5.0)
	_mark_scene_modified()
	_send_success(client_id, {"message": "Bake interval set", "bake_interval": curve.bake_interval}, command_id)
