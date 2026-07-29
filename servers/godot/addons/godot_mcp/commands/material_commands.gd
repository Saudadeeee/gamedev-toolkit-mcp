@tool
class_name MCPMaterialCommands
extends MCPBaseCommandProcessor

## Command processor for Material and Shader operations

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"create_material":
			_create_material(client_id, params, command_id)
			return true
		"set_material_property":
			_set_material_property(client_id, params, command_id)
			return true
		"get_material_properties":
			_get_material_properties(client_id, params, command_id)
			return true
		"set_shader_code":
			_set_shader_code(client_id, params, command_id)
			return true
		"set_shader_parameter":
			_set_shader_parameter(client_id, params, command_id)
			return true
	return false

func _create_material(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var material_type = params.get("material_type", "StandardMaterial3D")
	var surface_index = params.get("surface_index", 0)

	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	# Create the material
	var material: Material
	if ClassDB.class_exists(material_type) and ClassDB.can_instantiate(material_type):
		material = ClassDB.instantiate(material_type)
	else:
		return _send_error(client_id, "Unknown material type: %s" % material_type, command_id)

	# Assign material to node
	if node.has_method("set_surface_override_material"):
		node.set_surface_override_material(surface_index, material)
	elif "material" in node:
		node.material = material
	elif "material_override" in node:
		node.material_override = material
	else:
		return _send_error(client_id, "Node does not support material assignment", command_id)

	_mark_scene_modified()

	_send_success(client_id, {
		"node_path": node_path,
		"material_type": material_type,
		"surface_index": surface_index
	}, command_id)

func _set_material_property(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var surface_index = params.get("surface_index", 0)
	var property = params.get("property", "")
	var value = params.get("value")

	if property.is_empty():
		return _send_error(client_id, "Property name cannot be empty", command_id)

	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	# Get the material
	var material = _get_material_from_node(node, surface_index)
	if not material:
		return _send_error(client_id, "No material found on node at surface %d" % surface_index, command_id)

	# Check property exists
	if not property in material:
		return _send_error(client_id, "Property '%s' not found on material %s" % [property, material.get_class()], command_id)

	# Parse and set value
	var parsed_value = _parse_property_value(value)
	material.set(property, parsed_value)
	_mark_scene_modified()

	_send_success(client_id, {
		"node_path": node_path,
		"property": property,
		"value": str(parsed_value)
	}, command_id)

func _get_material_properties(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var surface_index = params.get("surface_index", 0)

	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	var material = _get_material_from_node(node, surface_index)
	if not material:
		return _send_error(client_id, "No material found on node at surface %d" % surface_index, command_id)

	# Get all properties
	var properties = {}
	for prop in material.get_property_list():
		var prop_name = prop["name"]
		if not prop_name.begins_with("_") and prop["usage"] & PROPERTY_USAGE_EDITOR:
			properties[prop_name] = str(material.get(prop_name))

	_send_success(client_id, {
		"node_path": node_path,
		"material_type": material.get_class(),
		"surface_index": surface_index,
		"properties": properties
	}, command_id)

func _set_shader_code(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var surface_index = params.get("surface_index", 0)
	var shader_code = params.get("shader_code", "")

	if shader_code.is_empty():
		return _send_error(client_id, "Shader code cannot be empty", command_id)

	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	var material = _get_material_from_node(node, surface_index)
	if not material or not material is ShaderMaterial:
		return _send_error(client_id, "ShaderMaterial not found on node at surface %d" % surface_index, command_id)

	# Create or get shader
	var shader = material.shader
	if not shader:
		shader = Shader.new()
		material.shader = shader

	shader.code = shader_code
	_mark_scene_modified()

	_send_success(client_id, {
		"node_path": node_path,
		"surface_index": surface_index
	}, command_id)

func _set_shader_parameter(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var surface_index = params.get("surface_index", 0)
	var parameter_name = params.get("parameter_name", "")
	var value = params.get("value")

	if parameter_name.is_empty():
		return _send_error(client_id, "Parameter name cannot be empty", command_id)

	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	var material = _get_material_from_node(node, surface_index)
	if not material or not material is ShaderMaterial:
		return _send_error(client_id, "ShaderMaterial not found on node at surface %d" % surface_index, command_id)

	var parsed_value = _parse_property_value(value)
	material.set_shader_parameter(parameter_name, parsed_value)
	_mark_scene_modified()

	_send_success(client_id, {
		"node_path": node_path,
		"parameter_name": parameter_name,
		"value": str(parsed_value)
	}, command_id)

## Helper: get material from node using various methods
func _get_material_from_node(node: Node, surface_index: int) -> Material:
	if node.has_method("get_surface_override_material"):
		var mat = node.get_surface_override_material(surface_index)
		if mat:
			return mat
		# Fall back to active material
		if node.has_method("get_active_material"):
			return node.get_active_material(surface_index)
	if "material" in node and node.material:
		return node.material
	if "material_override" in node and node.material_override:
		return node.material_override
	return null
