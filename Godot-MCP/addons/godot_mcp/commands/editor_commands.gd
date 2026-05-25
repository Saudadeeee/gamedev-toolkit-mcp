@tool
class_name MCPEditorCommands
extends MCPBaseCommandProcessor

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"get_editor_state":
			_get_editor_state(client_id, params, command_id)
			return true
		"get_selected_node":
			_get_selected_node(client_id, params, command_id)
			return true
		"create_resource":
			_create_resource(client_id, params, command_id)
			return true
		"load_sprite":
			_load_sprite(client_id, params, command_id)
			return true
		"import_animated_sprite":
			_import_animated_sprite(client_id, params, command_id)
			return true
	return false  # Command not handled

func _get_editor_state(client_id: int, params: Dictionary, command_id: String) -> void:
	# Get editor plugin and interfaces
	var plugin = Engine.get_meta("GodotMCPPlugin")
	if not plugin:
		return _send_error(client_id, "GodotMCPPlugin not found in Engine metadata", command_id)
	
	var editor_interface = plugin.get_editor_interface()
	
	var state = {
		"current_scene": "",
		"current_script": "",
		"selected_nodes": [],
		"is_playing": editor_interface.is_playing_scene()
	}
	
	# Get current scene
	var edited_scene_root = editor_interface.get_edited_scene_root()
	if edited_scene_root:
		state["current_scene"] = edited_scene_root.scene_file_path
	
	# Get current script if any is being edited
	var script_editor = editor_interface.get_script_editor()
	var current_script = script_editor.get_current_script()
	if current_script:
		state["current_script"] = current_script.resource_path
	
	# Get selected nodes
	var selection = editor_interface.get_selection()
	var selected_nodes = selection.get_selected_nodes()
	
	for node in selected_nodes:
		state["selected_nodes"].append({
			"name": node.name,
			"path": str(node.get_path())
		})
	
	_send_success(client_id, state, command_id)

func _get_selected_node(client_id: int, params: Dictionary, command_id: String) -> void:
	# Get editor plugin and interfaces
	var plugin = Engine.get_meta("GodotMCPPlugin")
	if not plugin:
		return _send_error(client_id, "GodotMCPPlugin not found in Engine metadata", command_id)
	
	var editor_interface = plugin.get_editor_interface()
	var selection = editor_interface.get_selection()
	var selected_nodes = selection.get_selected_nodes()
	
	if selected_nodes.size() == 0:
		return _send_success(client_id, {
			"selected": false,
			"message": "No node is currently selected"
		}, command_id)
	
	var node = selected_nodes[0]  # Get the first selected node
	
	# Get node info
	var node_data = {
		"selected": true,
		"name": node.name,
		"type": node.get_class(),
		"path": str(node.get_path())
	}
	
	# Get script info if available
	var script = node.get_script()
	if script:
		node_data["script_path"] = script.resource_path
	
	# Get important properties
	var properties = {}
	var property_list = node.get_property_list()
	
	for prop in property_list:
		var name = prop["name"]
		if not name.begins_with("_"):  # Skip internal properties
			# Only include some common properties to avoid overwhelming data
			if name in ["position", "rotation", "scale", "visible", "modulate", "z_index"]:
				properties[name] = node.get(name)
	
	node_data["properties"] = properties
	
	_send_success(client_id, node_data, command_id)

func _create_resource(client_id: int, params: Dictionary, command_id: String) -> void:
	var resource_type = params.get("resource_type", "")
	var resource_path = params.get("resource_path", "")
	var properties = params.get("properties", {})
	
	# Validation
	if resource_type.is_empty():
		return _send_error(client_id, "Resource type cannot be empty", command_id)
	
	if resource_path.is_empty():
		return _send_error(client_id, "Resource path cannot be empty", command_id)
	
	# Make sure we have an absolute path
	if not resource_path.begins_with("res://"):
		resource_path = "res://" + resource_path
	
	# Get editor interface
	var plugin = Engine.get_meta("GodotMCPPlugin")
	if not plugin:
		return _send_error(client_id, "GodotMCPPlugin not found in Engine metadata", command_id)
	
	var editor_interface = plugin.get_editor_interface()
	
	# Create the resource
	var resource
	
	if ClassDB.class_exists(resource_type):
		if ClassDB.is_parent_class(resource_type, "Resource"):
			resource = ClassDB.instantiate(resource_type)
			if not resource:
				return _send_error(client_id, "Failed to instantiate resource: %s" % resource_type, command_id)
		else:
			return _send_error(client_id, "Type is not a Resource: %s" % resource_type, command_id)
	else:
		return _send_error(client_id, "Invalid resource type: %s" % resource_type, command_id)
	
	# Set properties
	for key in properties:
		resource.set(key, properties[key])
	
	# Create directory if needed
	var dir = resource_path.get_base_dir()
	if not DirAccess.dir_exists_absolute(dir):
		var err = DirAccess.make_dir_recursive_absolute(dir)
		if err != OK:
			return _send_error(client_id, "Failed to create directory: %s (Error code: %d)" % [dir, err], command_id)
	
	# Save the resource
	var result = ResourceSaver.save(resource, resource_path)
	if result != OK:
		return _send_error(client_id, "Failed to save resource: %d" % result, command_id)
	
	# Refresh the filesystem
	editor_interface.get_resource_filesystem().scan()
	
	_send_success(client_id, {
		"resource_path": resource_path,
		"resource_type": resource_type
	}, command_id)

func _load_sprite(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var texture_path = params.get("texture_path", "")

	if node_path.is_empty():
		return _send_error(client_id, "Node path cannot be empty", command_id)
	if texture_path.is_empty():
		return _send_error(client_id, "Texture path cannot be empty", command_id)

	if not texture_path.begins_with("res://"):
		texture_path = "res://" + texture_path

	if not ResourceLoader.exists(texture_path):
		return _send_error(client_id, "Texture file not found: %s" % texture_path, command_id)

	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	var texture = ResourceLoader.load(texture_path)
	if not texture:
		return _send_error(client_id, "Failed to load texture: %s" % texture_path, command_id)

	if node is Sprite2D:
		node.texture = texture
	elif node is TextureRect:
		node.texture = texture
	else:
		return _send_error(client_id, "Node does not support direct texture assignment: %s" % node.get_class(), command_id)

	_mark_scene_modified()
	_send_success(client_id, {
		"node_path": node_path,
		"texture_path": texture_path
	}, command_id)

func _import_animated_sprite(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var texture_path = params.get("texture_path", "")
	var metadata_path = params.get("metadata_path", "")
	var animation_name = params.get("animation_name", "default")
	var fps = params.get("fps", 12.0)
	var autoplay = params.get("autoplay", true)

	if node_path.is_empty():
		return _send_error(client_id, "Node path cannot be empty", command_id)
	if texture_path.is_empty():
		return _send_error(client_id, "Texture path cannot be empty", command_id)
	if metadata_path.is_empty():
		return _send_error(client_id, "Metadata path cannot be empty", command_id)

	if not texture_path.begins_with("res://"):
		texture_path = "res://" + texture_path
	if not metadata_path.begins_with("res://"):
		metadata_path = "res://" + metadata_path

	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)
	if not node is AnimatedSprite2D:
		return _send_error(client_id, "Node is not an AnimatedSprite2D: %s" % node_path, command_id)

	if not ResourceLoader.exists(texture_path):
		return _send_error(client_id, "Texture file not found: %s" % texture_path, command_id)
	if not FileAccess.file_exists(metadata_path):
		return _send_error(client_id, "Metadata file not found: %s" % metadata_path, command_id)

	var texture = ResourceLoader.load(texture_path)
	if not texture:
		return _send_error(client_id, "Failed to load texture: %s" % texture_path, command_id)

	var file = FileAccess.open(metadata_path, FileAccess.READ)
	if not file:
		return _send_error(client_id, "Failed to open metadata file: %s" % metadata_path, command_id)

	var json_text = file.get_as_text()
	file.close()

	var json = JSON.new()
	var parse_result = json.parse(json_text)
	if parse_result != OK:
		return _send_error(client_id, "Failed to parse metadata JSON: %s" % json.get_error_message(), command_id)

	var data = json.get_data()
	if typeof(data) != TYPE_DICTIONARY:
		return _send_error(client_id, "Metadata JSON root must be an object", command_id)

	if not data.has("frames"):
		return _send_error(client_id, "Metadata JSON missing 'frames'", command_id)

	var frames_data = data["frames"]
	var frame_entries: Array = []

	if typeof(frames_data) == TYPE_ARRAY:
		frame_entries = frames_data
	elif typeof(frames_data) == TYPE_DICTIONARY:
		for frame_name in frames_data.keys():
			var entry = frames_data[frame_name]
			if typeof(entry) == TYPE_DICTIONARY:
				var copy = entry.duplicate(true)
				copy["_frame_name"] = frame_name
				frame_entries.append(copy)
	else:
		return _send_error(client_id, "Metadata 'frames' must be an array or object", command_id)

	if frame_entries.is_empty():
		return _send_error(client_id, "Metadata contains no frame entries", command_id)

	frame_entries.sort_custom(func(a, b):
		var a_name = str(a.get("filename", a.get("_frame_name", "")))
		var b_name = str(b.get("filename", b.get("_frame_name", "")))
		return a_name.naturalnocasecmp_to(b_name) < 0
	)

	var sprite_frames = SpriteFrames.new()
	if not sprite_frames.has_animation(animation_name):
		sprite_frames.add_animation(animation_name)
	sprite_frames.set_animation_loop(animation_name, true)
	sprite_frames.set_animation_speed(animation_name, float(fps))

	for frame_entry in frame_entries:
		if typeof(frame_entry) != TYPE_DICTIONARY:
			continue
		var rect_data = frame_entry.get("frame", null)
		if typeof(rect_data) != TYPE_DICTIONARY:
			continue

		var x = int(rect_data.get("x", 0))
		var y = int(rect_data.get("y", 0))
		var w = int(rect_data.get("w", 0))
		var h = int(rect_data.get("h", 0))

		if w <= 0 or h <= 0:
			continue

		var atlas = AtlasTexture.new()
		atlas.atlas = texture
		atlas.region = Rect2(x, y, w, h)
		sprite_frames.add_frame(animation_name, atlas)

	var frame_count = sprite_frames.get_frame_count(animation_name)
	if frame_count == 0:
		return _send_error(client_id, "No valid animation frames were created from metadata", command_id)

	node.sprite_frames = sprite_frames
	node.animation = animation_name
	node.autoplay = animation_name if autoplay else StringName()

	_mark_scene_modified()
	_send_success(client_id, {
		"node_path": node_path,
		"texture_path": texture_path,
		"metadata_path": metadata_path,
		"animation_name": animation_name,
		"frame_count": frame_count,
		"fps": fps
	}, command_id)
