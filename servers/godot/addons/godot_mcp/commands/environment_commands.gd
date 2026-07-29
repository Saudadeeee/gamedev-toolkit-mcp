@tool
class_name MCPEnvironmentCommands
extends MCPBaseCommandProcessor

## Command processor for Lighting and Environment operations

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"set_light_property":
			_set_light_property(client_id, params, command_id)
			return true
		"configure_environment":
			_configure_environment(client_id, params, command_id)
			return true
		"set_sky":
			_set_sky(client_id, params, command_id)
			return true
		"set_fog":
			_set_fog(client_id, params, command_id)
			return true
		"configure_camera":
			_configure_camera(client_id, params, command_id)
			return true
		"get_environment_info":
			_get_environment_info(client_id, params, command_id)
			return true
	return false

func _set_light_property(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Light node not found: %s" % node_path, command_id)

	var property = params.get("property", "")
	var value = params.get("value")

	if not property in node:
		return _send_error(client_id, "Property not found on %s: %s" % [node.get_class(), property], command_id)

	var parsed_value = _parse_property_value(value)
	node.set(property, parsed_value)
	_mark_scene_modified()
	_send_success(client_id, {"message": "Light property set", "property": property, "node_path": node_path}, command_id)

func _configure_environment(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "WorldEnvironment not found: %s" % node_path, command_id)

	if node.get_class() != "WorldEnvironment":
		return _send_error(client_id, "Node is not a WorldEnvironment: %s" % node.get_class(), command_id)

	# Get or create Environment resource
	var env: Environment
	if not node.environment:
		node.environment = Environment.new()
	env = node.environment

	var property = params.get("property", "")
	var value = params.get("value")

	if not property in env:
		return _send_error(client_id, "Property not found on Environment: %s" % property, command_id)

	var parsed_value = _parse_property_value(value)
	env.set(property, parsed_value)
	_mark_scene_modified()
	_send_success(client_id, {"message": "Environment property set", "property": property}, command_id)

func _set_sky(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "WorldEnvironment not found: %s" % node_path, command_id)

	if not node.environment:
		node.environment = Environment.new()
	var env: Environment = node.environment

	var sky_type = params.get("sky_type", "procedural")
	var sky = Sky.new()
	var sky_material: Material

	match sky_type:
		"procedural":
			var proc_sky = ProceduralSkyMaterial.new()
			if params.has("sky_top_color"):
				var c = params["sky_top_color"]
				proc_sky.sky_top_color = Color(c[0], c[1], c[2])
			if params.has("sky_horizon_color"):
				var c = params["sky_horizon_color"]
				proc_sky.sky_horizon_color = Color(c[0], c[1], c[2])
			if params.has("ground_bottom_color"):
				var c = params["ground_bottom_color"]
				proc_sky.ground_bottom_color = Color(c[0], c[1], c[2])
			if params.has("sun_angle_max"):
				proc_sky.sun_angle_max = params["sun_angle_max"]
			sky_material = proc_sky
		"panorama":
			var pan_sky = PanoramaSkyMaterial.new()
			if params.has("texture_path"):
				var tex = load(params["texture_path"])
				if tex:
					pan_sky.panorama = tex
			sky_material = pan_sky
		"physical_sun_sky":
			sky_material = PhysicalSkyMaterial.new()
		_:
			return _send_error(client_id, "Unknown sky type: %s" % sky_type, command_id)

	sky.sky_material = sky_material
	env.sky = sky
	env.background_mode = Environment.BG_SKY
	_mark_scene_modified()
	_send_success(client_id, {"message": "Sky set to %s" % sky_type, "sky_type": sky_type}, command_id)

func _set_fog(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "WorldEnvironment not found: %s" % node_path, command_id)

	if not node.environment:
		node.environment = Environment.new()
	var env: Environment = node.environment

	var enabled = params.get("enabled", true)
	env.fog_enabled = enabled

	if params.has("color_r") or params.has("color_g") or params.has("color_b"):
		var r = params.get("color_r", 1.0)
		var g = params.get("color_g", 1.0)
		var b = params.get("color_b", 1.0)
		env.fog_light_color = Color(r, g, b)

	if params.has("density"):
		env.fog_density = params["density"]
	if params.has("aerial_perspective"):
		env.fog_aerial_perspective = params["aerial_perspective"]
	if params.has("sky_affect"):
		env.fog_sky_affect = params["sky_affect"]

	_mark_scene_modified()
	_send_success(client_id, {"message": "Fog %s" % ("enabled" if enabled else "disabled"), "enabled": enabled}, command_id)

func _configure_camera(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Camera not found: %s" % node_path, command_id)

	var camera_class = node.get_class()

	if camera_class == "Camera3D":
		if params.has("fov"):
			node.fov = params["fov"]
		if params.has("near"):
			node.near = params["near"]
		if params.has("far"):
			node.far = params["far"]
		if params.has("size"):
			node.size = params["size"]
		if params.has("projection"):
			var proj_map = {"perspective": 0, "orthogonal": 1, "frustum": 2}
			if params["projection"] in proj_map:
				node.projection = proj_map[params["projection"]]
		if params.has("current"):
			node.current = params["current"]
	elif camera_class == "Camera2D":
		if params.has("zoom_x") or params.has("zoom_y"):
			node.zoom = Vector2(params.get("zoom_x", node.zoom.x), params.get("zoom_y", node.zoom.y))
		if params.has("near"):
			node.limit_left = -params["near"]
		if params.has("current"):
			node.enabled = params["current"]
	else:
		return _send_error(client_id, "Node is not a Camera: %s" % camera_class, command_id)

	_mark_scene_modified()
	_send_success(client_id, {"message": "Camera configured", "node_path": node_path}, command_id)

func _get_environment_info(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "WorldEnvironment not found: %s" % node_path, command_id)

	var info = {"node_path": node_path, "has_environment": false}

	if node.environment:
		var env = node.environment
		info["has_environment"] = true
		info["background_mode"] = env.background_mode
		info["fog_enabled"] = env.fog_enabled
		info["glow_enabled"] = env.glow_enabled
		info["ssao_enabled"] = env.ssao_enabled
		info["has_sky"] = env.sky != null

	_send_success(client_id, info, command_id)
