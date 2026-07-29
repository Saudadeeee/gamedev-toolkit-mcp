@tool
class_name MCPParticleCommands
extends MCPBaseCommandProcessor

## Command processor for Particle system operations

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"configure_particles":
			_configure_particles(client_id, params, command_id)
			return true
		"set_particle_material":
			_set_particle_material(client_id, params, command_id)
			return true
		"set_particle_emission_shape":
			_set_particle_emission_shape(client_id, params, command_id)
			return true
		"restart_particles":
			_restart_particles(client_id, params, command_id)
			return true
		"get_particle_info":
			_get_particle_info(client_id, params, command_id)
			return true
	return false

func _configure_particles(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	var particle_classes = ["GPUParticles2D", "GPUParticles3D", "CPUParticles2D", "CPUParticles3D"]
	if not node.get_class() in particle_classes:
		return _send_error(client_id, "Node is not a particle system: %s" % node.get_class(), command_id)

	var props_map = {
		"amount": "amount",
		"lifetime": "lifetime",
		"one_shot": "one_shot",
		"preprocess": "preprocess",
		"speed_scale": "speed_scale",
		"explosiveness": "explosiveness",
		"randomness": "randomness",
		"emitting": "emitting",
		"fixed_fps": "fixed_fps",
		"local_coords": "local_coords"
	}

	for key in props_map:
		if params.has(key) and props_map[key] in node:
			node.set(props_map[key], params[key])

	_mark_scene_modified()
	_send_success(client_id, {"message": "Particles configured", "node_path": node_path}, command_id)

func _set_particle_material(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	var property = params.get("property", "")
	var value = params.get("value")

	# Get or create process material
	var material: ParticleProcessMaterial
	if "process_material" in node:
		if not node.process_material:
			node.process_material = ParticleProcessMaterial.new()
		material = node.process_material
	else:
		return _send_error(client_id, "Node does not have a process_material (use GPUParticles2D/3D)", command_id)

	if not property in material:
		return _send_error(client_id, "Property not found on ParticleProcessMaterial: %s" % property, command_id)

	var parsed_value = _parse_property_value(value)
	material.set(property, parsed_value)
	_mark_scene_modified()

	_send_success(client_id, {"message": "Particle material property set", "property": property}, command_id)

func _set_particle_emission_shape(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	var shape_name = params.get("shape", "point")

	# For CPUParticles, set emission_shape property directly
	if node.get_class() in ["CPUParticles2D", "CPUParticles3D"]:
		var shape_enum_map = {
			"point": 0,
			"sphere": 1,
			"sphere_surface": 2,
			"box": 3,
			"points": 4,
			"directed_points": 5,
			"ring": 6
		}
		if not shape_name in shape_enum_map:
			return _send_error(client_id, "Unknown emission shape: %s" % shape_name, command_id)
		node.emission_shape = shape_enum_map[shape_name]
		if params.has("radius") and "emission_sphere_radius" in node:
			node.emission_sphere_radius = params["radius"]
		if params.has("shape_x") and "emission_box_extents" in node:
			node.emission_box_extents = Vector3(
				params.get("shape_x", 1.0),
				params.get("shape_y", 1.0),
				params.get("shape_z", 1.0)
			)
	elif node.get_class() in ["GPUParticles2D", "GPUParticles3D"]:
		# GPU particles use ParticleProcessMaterial emission shape
		var material: ParticleProcessMaterial
		if not node.process_material:
			node.process_material = ParticleProcessMaterial.new()
		material = node.process_material

		var shape_enum_map = {
			"point": 0,
			"sphere": 1,
			"sphere_surface": 2,
			"box": 3,
			"points": 4,
			"directed_points": 5,
			"ring": 6
		}
		if not shape_name in shape_enum_map:
			return _send_error(client_id, "Unknown emission shape: %s" % shape_name, command_id)
		material.emission_shape = shape_enum_map[shape_name]
		if params.has("radius"):
			material.emission_sphere_radius = params["radius"]
		if params.has("shape_x"):
			material.emission_box_extents = Vector3(
				params.get("shape_x", 1.0),
				params.get("shape_y", 1.0),
				params.get("shape_z", 1.0)
			)
	else:
		return _send_error(client_id, "Node is not a particle system: %s" % node.get_class(), command_id)

	_mark_scene_modified()
	_send_success(client_id, {"message": "Particle emission shape set to %s" % shape_name, "shape": shape_name}, command_id)

func _restart_particles(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	if node.has_method("restart"):
		node.restart()
	else:
		return _send_error(client_id, "Node does not support restart", command_id)

	_send_success(client_id, {"message": "Particles restarted"}, command_id)

func _get_particle_info(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	var info = {
		"node_class": node.get_class(),
		"node_path": node_path
	}

	var common_props = ["amount", "lifetime", "one_shot", "preprocess", "speed_scale",
		"explosiveness", "randomness", "emitting", "fixed_fps", "local_coords"]
	for prop in common_props:
		if prop in node:
			info[prop] = node.get(prop)

	_send_success(client_id, info, command_id)
