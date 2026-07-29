@tool
class_name MCPMeshCommands
extends MCPBaseCommandProcessor

## Command processor for Custom Mesh and SurfaceTool operations

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"create_primitive_mesh":
			_create_primitive_mesh(client_id, params, command_id)
			return true
		"create_array_mesh":
			_create_array_mesh(client_id, params, command_id)
			return true
		"get_mesh_info":
			_get_mesh_info(client_id, params, command_id)
			return true
		"set_mesh_surface_material":
			_set_mesh_surface_material(client_id, params, command_id)
			return true
		"generate_mesh_normals":
			_generate_mesh_normals(client_id, params, command_id)
			return true
		"create_mesh_from_height_map":
			_create_mesh_from_height_map(client_id, params, command_id)
			return true
		"save_mesh_to_file":
			_save_mesh_to_file(client_id, params, command_id)
			return true
	return false

func _create_primitive_mesh(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "MeshInstance3D not found: %s" % node_path, command_id)

	var mesh_type = params.get("mesh_type", "BoxMesh")
	var mesh: Mesh

	match mesh_type:
		"BoxMesh":
			var m = BoxMesh.new()
			m.size = Vector3(params.get("size_x", 1.0), params.get("size_y", 1.0), params.get("size_z", 1.0))
			if params.has("subdivide_width"): m.subdivide_width = params["subdivide_width"]
			if params.has("subdivide_height"): m.subdivide_height = params["subdivide_height"]
			if params.has("subdivide_depth"): m.subdivide_depth = params["subdivide_depth"]
			mesh = m
		"SphereMesh":
			var m = SphereMesh.new()
			m.radius = params.get("size_x", 0.5)
			m.height = params.get("size_y", 1.0)
			if params.has("radial_segments"): m.radial_segments = params["radial_segments"]
			if params.has("rings"): m.rings = params["rings"]
			mesh = m
		"CylinderMesh":
			var m = CylinderMesh.new()
			m.top_radius = params.get("size_x", 0.5)
			m.bottom_radius = params.get("size_x", 0.5)
			m.height = params.get("size_y", 1.0)
			if params.has("radial_segments"): m.radial_segments = params["radial_segments"]
			if params.has("rings"): m.rings = params["rings"]
			mesh = m
		"CapsuleMesh":
			var m = CapsuleMesh.new()
			m.radius = params.get("size_x", 0.5)
			m.height = params.get("size_y", 2.0)
			if params.has("radial_segments"): m.radial_segments = params["radial_segments"]
			if params.has("rings"): m.rings = params["rings"]
			mesh = m
		"PlaneMesh":
			var m = PlaneMesh.new()
			m.size = Vector2(params.get("size_x", 2.0), params.get("size_y", 2.0))
			if params.has("subdivide_width"): m.subdivide_width = params["subdivide_width"]
			if params.has("subdivide_depth"): m.subdivide_depth = params["subdivide_depth"]
			mesh = m
		"QuadMesh":
			var m = QuadMesh.new()
			m.size = Vector2(params.get("size_x", 1.0), params.get("size_y", 1.0))
			mesh = m
		"TorusMesh":
			var m = TorusMesh.new()
			m.outer_radius = params.get("size_x", 1.0)
			m.inner_radius = params.get("size_y", 0.3)
			if params.has("rings"): m.rings = params["rings"]
			if params.has("radial_segments"): m.ring_segments = params["radial_segments"]
			mesh = m
		"PrismMesh":
			var m = PrismMesh.new()
			m.size = Vector3(params.get("size_x", 1.0), params.get("size_y", 1.0), params.get("size_z", 1.0))
			mesh = m
		"PointMesh":
			mesh = PointMesh.new()
		_:
			return _send_error(client_id, "Unknown mesh type: %s" % mesh_type, command_id)

	if "mesh" in node:
		node.mesh = mesh
	else:
		return _send_error(client_id, "Node does not support mesh assignment", command_id)

	_mark_scene_modified()
	_send_success(client_id, {"message": "Primitive mesh created", "mesh_type": mesh_type, "node_path": node_path}, command_id)

func _create_array_mesh(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "MeshInstance3D not found: %s" % node_path, command_id)

	var vertices_flat: Array = params.get("vertices", [])
	if vertices_flat.is_empty() or vertices_flat.size() % 3 != 0:
		return _send_error(client_id, "Vertices must be a non-empty flat array with count divisible by 3", command_id)

	var arrays = []
	arrays.resize(Mesh.ARRAY_MAX)

	# Build vertex array
	var verts = PackedVector3Array()
	for i in range(0, vertices_flat.size(), 3):
		verts.append(Vector3(vertices_flat[i], vertices_flat[i+1], vertices_flat[i+2]))
	arrays[Mesh.ARRAY_VERTEX] = verts

	# Normals
	var normals_flat: Array = params.get("normals", [])
	if not normals_flat.is_empty() and normals_flat.size() == vertices_flat.size():
		var norms = PackedVector3Array()
		for i in range(0, normals_flat.size(), 3):
			norms.append(Vector3(normals_flat[i], normals_flat[i+1], normals_flat[i+2]))
		arrays[Mesh.ARRAY_NORMAL] = norms

	# UVs
	var uvs_flat: Array = params.get("uvs", [])
	if not uvs_flat.is_empty():
		var uvs = PackedVector2Array()
		for i in range(0, uvs_flat.size(), 2):
			uvs.append(Vector2(uvs_flat[i], uvs_flat[i+1]))
		arrays[Mesh.ARRAY_TEX_UV] = uvs

	# Indices
	var indices: Array = params.get("indices", [])
	if not indices.is_empty():
		var idx = PackedInt32Array()
		for i in indices:
			idx.append(i)
		arrays[Mesh.ARRAY_INDEX] = idx

	# Primitive type
	var prim_map = {
		"triangles": Mesh.PRIMITIVE_TRIANGLES,
		"triangle_strip": Mesh.PRIMITIVE_TRIANGLE_STRIP,
		"lines": Mesh.PRIMITIVE_LINES,
		"line_strip": Mesh.PRIMITIVE_LINE_STRIP,
		"points": Mesh.PRIMITIVE_POINTS
	}
	var prim_type = prim_map.get(params.get("primitive_type", "triangles"), Mesh.PRIMITIVE_TRIANGLES)

	var array_mesh = ArrayMesh.new()
	array_mesh.add_surface_from_arrays(prim_type, arrays)

	if "mesh" in node:
		node.mesh = array_mesh
	else:
		return _send_error(client_id, "Node does not support mesh assignment", command_id)

	_mark_scene_modified()
	_send_success(client_id, {
		"message": "ArrayMesh created",
		"vertex_count": verts.size(),
		"surface_count": array_mesh.get_surface_count()
	}, command_id)

func _get_mesh_info(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	if not "mesh" in node or not node.mesh:
		return _send_error(client_id, "Node has no mesh", command_id)

	var mesh: Mesh = node.mesh
	var info = {
		"node_path": node_path,
		"mesh_class": mesh.get_class(),
		"surface_count": mesh.get_surface_count(),
		"surfaces": []
	}

	for i in range(mesh.get_surface_count()):
		var surface_info = {
			"index": i,
			"primitive_type": mesh.surface_get_primitive_type(i),
			"name": mesh.surface_get_name(i) if mesh.has_method("surface_get_name") else ""
		}
		if mesh.has_method("surface_get_arrays"):
			var arrays = mesh.surface_get_arrays(i)
			if arrays[Mesh.ARRAY_VERTEX]:
				surface_info["vertex_count"] = arrays[Mesh.ARRAY_VERTEX].size()
			if arrays[Mesh.ARRAY_INDEX]:
				surface_info["index_count"] = arrays[Mesh.ARRAY_INDEX].size()
		info["surfaces"].append(surface_info)

	_send_success(client_id, info, command_id)

func _set_mesh_surface_material(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	var surface_index = params.get("surface_index", 0)
	var material_type = params.get("material_type", "StandardMaterial3D")

	var material: Material
	match material_type:
		"StandardMaterial3D":
			material = StandardMaterial3D.new()
		"ShaderMaterial":
			material = ShaderMaterial.new()
		"ORMMaterial3D":
			material = ORMMaterial3D.new()
		_:
			return _send_error(client_id, "Unknown material type: %s" % material_type, command_id)

	if node.has_method("set_surface_override_material"):
		node.set_surface_override_material(surface_index, material)
	else:
		return _send_error(client_id, "Node does not support surface materials", command_id)

	_mark_scene_modified()
	_send_success(client_id, {"message": "Surface material set", "surface": surface_index, "material_type": material_type}, command_id)

func _generate_mesh_normals(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	if not "mesh" in node or not node.mesh:
		return _send_error(client_id, "Node has no mesh", command_id)

	var mesh: Mesh = node.mesh
	var smooth = params.get("smooth", true)

	# Use SurfaceTool to regenerate normals
	var new_array_mesh = ArrayMesh.new()
	for i in range(mesh.get_surface_count()):
		var st = SurfaceTool.new()
		st.begin(mesh.surface_get_primitive_type(i))
		st.create_from(mesh, i)
		if smooth:
			st.generate_normals()
		else:
			st.generate_normals(true)
		st.commit(new_array_mesh)

	node.mesh = new_array_mesh
	_mark_scene_modified()
	_send_success(client_id, {"message": "Normals regenerated (%s)" % ("smooth" if smooth else "flat")}, command_id)

func _create_mesh_from_height_map(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "MeshInstance3D not found: %s" % node_path, command_id)

	var width = params.get("width", 2)
	var depth = params.get("depth", 2)
	var heights: Array = params.get("heights", [])
	var cell_size = params.get("cell_size", 1.0)
	var height_scale = params.get("height_scale", 1.0)

	if heights.size() != width * depth:
		return _send_error(client_id, "Heights array size (%d) must equal width*depth (%d)" % [heights.size(), width * depth], command_id)

	var st = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)

	# Generate vertices and triangles
	for z in range(depth):
		for x in range(width):
			var h = heights[z * width + x] * height_scale
			st.set_uv(Vector2(float(x) / (width - 1), float(z) / (depth - 1)))
			st.add_vertex(Vector3(x * cell_size, h, z * cell_size))

	# Generate indices
	for z in range(depth - 1):
		for x in range(width - 1):
			var i0 = z * width + x
			var i1 = i0 + 1
			var i2 = i0 + width
			var i3 = i2 + 1
			st.add_index(i0); st.add_index(i2); st.add_index(i1)
			st.add_index(i1); st.add_index(i2); st.add_index(i3)

	st.generate_normals()
	var mesh = st.commit()

	if "mesh" in node:
		node.mesh = mesh
	else:
		return _send_error(client_id, "Node does not support mesh assignment", command_id)

	_mark_scene_modified()
	_send_success(client_id, {
		"message": "Height map mesh created",
		"width": width,
		"depth": depth,
		"vertex_count": width * depth
	}, command_id)

func _save_mesh_to_file(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	if not "mesh" in node or not node.mesh:
		return _send_error(client_id, "Node has no mesh", command_id)

	var save_path = params.get("save_path", "")
	if save_path.is_empty():
		return _send_error(client_id, "Save path cannot be empty", command_id)

	if not save_path.ends_with(".tres") and not save_path.ends_with(".res"):
		return _send_error(client_id, "Save path must end with .tres or .res", command_id)

	if not save_path.begins_with("res://"):
		return _send_error(client_id, "Save path must start with res://", command_id)

	# Convert to ArrayMesh so it can be saved as a standalone resource
	var mesh: Mesh = node.mesh
	var array_mesh: ArrayMesh
	if mesh is ArrayMesh:
		array_mesh = mesh
	else:
		array_mesh = ArrayMesh.new()
		for i in range(mesh.get_surface_count()):
			var st = SurfaceTool.new()
			st.begin(mesh.surface_get_primitive_type(i))
			st.create_from(mesh, i)
			st.commit(array_mesh)

	var err = ResourceSaver.save(array_mesh, save_path)
	if err != OK:
		return _send_error(client_id, "Failed to save mesh (error %d)" % err, command_id)

	_send_success(client_id, {"message": "Mesh saved", "save_path": save_path}, command_id)
