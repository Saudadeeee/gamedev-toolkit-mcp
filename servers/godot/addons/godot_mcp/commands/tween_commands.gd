@tool
class_name MCPTweenCommands
extends MCPBaseCommandProcessor

## Command processor for Tween animation operations

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"animate_node_property":
			_animate_node_property(client_id, params, command_id)
			return true
		"create_tween_script":
			_create_tween_script(client_id, params, command_id)
			return true
		"create_animation_from_tween":
			_create_animation_from_tween(client_id, params, command_id)
			return true
	return false

func _animate_node_property(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var property = params.get("property", "")
	var to_value = params.get("to_value")
	var duration = params.get("duration", 1.0)
	var ease_type_str = params.get("ease_type", "ease_in_out")

	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	# Find or create AnimationPlayer sibling or on same node
	var player: AnimationPlayer = null
	var parent = node.get_parent()
	if parent:
		for child in parent.get_children():
			if child is AnimationPlayer:
				player = child
				break

	if not player:
		# Create one
		player = AnimationPlayer.new()
		player.name = "AnimationPlayer"
		if parent:
			parent.add_child(player)
			player.owner = node.owner if node.owner else node
		else:
			return _send_error(client_id, "Cannot create AnimationPlayer - node has no parent", command_id)

	# Create or get animation
	var anim_name = "tween_%s" % property.replace(":", "_").replace("/", "_")
	if not player.has_animation(anim_name):
		var anim = Animation.new()
		anim.length = duration
		player.add_animation(anim_name, anim)

	var animation = player.get_animation(anim_name)
	animation.length = duration

	# Determine relative node path from AnimationPlayer
	var rel_path = player.get_parent().get_path_to(node)
	var full_track_path = "%s:%s" % [rel_path, property]

	# Add or find track
	var track_idx = animation.find_track(full_track_path, Animation.TYPE_VALUE)
	if track_idx == -1:
		track_idx = animation.add_track(Animation.TYPE_VALUE)
		animation.track_set_path(track_idx, full_track_path)

	# Set ease type
	var ease_map = {
		"linear": [Animation.INTERPOLATION_LINEAR, 1],
		"ease_in": [Animation.INTERPOLATION_CUBIC, 1],
		"ease_out": [Animation.INTERPOLATION_CUBIC, 2],
		"ease_in_out": [Animation.INTERPOLATION_CUBIC, 3],
		"spring": [Animation.INTERPOLATION_CUBIC, 3],
		"bounce": [Animation.INTERPOLATION_LINEAR, 2],
		"elastic": [Animation.INTERPOLATION_CUBIC, 3],
		"back": [Animation.INTERPOLATION_CUBIC, 3]
	}
	if ease_type_str in ease_map:
		animation.track_set_interpolation_type(track_idx, ease_map[ease_type_str][0])

	# Get current value if from_value not specified
	var from_value = params.get("from_value")
	if from_value == null and property in node:
		from_value = node.get(property)

	# Insert keyframes
	if from_value != null:
		animation.track_insert_key(track_idx, 0.0, _parse_property_value(from_value))
	animation.track_insert_key(track_idx, duration, _parse_property_value(to_value))

	_mark_scene_modified()
	_send_success(client_id, {
		"message": "Property animation created",
		"animation_name": anim_name,
		"property": property,
		"duration": duration
	}, command_id)

func _create_tween_script(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var property = params.get("property", "position")
	var to_value = params.get("to_value")
	var duration = params.get("duration", 1.0)
	var ease_type = params.get("ease_type", "ease_in_out")
	var loop = params.get("loop", false)
	var ping_pong = params.get("ping_pong", false)

	var ease_map = {
		"linear": "Tween.EASE_IN_OUT",
		"ease_in": "Tween.EASE_IN",
		"ease_out": "Tween.EASE_OUT",
		"ease_in_out": "Tween.EASE_IN_OUT"
	}
	var ease_str = ease_map.get(ease_type, "Tween.EASE_IN_OUT")

	var to_value_str = str(to_value)
	if to_value is Array and to_value.size() == 2:
		to_value_str = "Vector2(%s, %s)" % [to_value[0], to_value[1]]
	elif to_value is Array and to_value.size() == 3:
		to_value_str = "Vector3(%s, %s, %s)" % [to_value[0], to_value[1], to_value[2]]
	elif to_value is Array and to_value.size() == 4:
		to_value_str = "Color(%s, %s, %s, %s)" % [to_value[0], to_value[1], to_value[2], to_value[3]]

	var loop_line = ""
	if loop and ping_pong:
		loop_line = "\ttween.set_loops()\n\ttween.set_parallel(false)\n"
	elif loop:
		loop_line = "\ttween.set_loops()\n"

	var code = """extends Node

func _ready():
\t_start_tween()

func _start_tween():
\tvar tween = create_tween()
%s\ttween.set_ease(%s)
\ttween.set_trans(Tween.TRANS_SINE)
\ttween.tween_property(%s, "%s", %s, %s)
""" % [loop_line, ease_str, node_path, property, to_value_str, duration]

	_send_success(client_id, {"code": code, "message": "Tween script generated"}, command_id)

func _create_animation_from_tween(client_id: int, params: Dictionary, command_id: String) -> void:
	# This creates a simple script via execute that runs a tween
	var target_node_path = params.get("target_node_path", "")
	var property_node_path = params.get("property_node_path", target_node_path)
	var property = params.get("property", "position")
	var final_value = params.get("final_value")
	var duration = params.get("duration", 1.0)
	var trans_type = params.get("trans_type", "SINE")
	var ease_type_str = params.get("ease_type", "EASE_IN_OUT")

	var target_node = _get_editor_node(target_node_path)
	if not target_node:
		return _send_error(client_id, "Target node not found: %s" % target_node_path, command_id)

	var final_value_parsed = _parse_property_value(final_value)

	# Use a helper script to start tween at runtime
	var script_text = """@tool
extends Node

func _ready():
\tawait get_tree().process_frame
\tvar target = get_node_or_null(\"%s\")
\tif target:
\t\tvar tween = create_tween()
\t\ttween.set_ease(Tween.%s)
\t\ttween.set_trans(Tween.TRANS_%s)
\t\ttween.tween_property(target, \"%s\", %s, %s)
""" % [property_node_path, ease_type_str, trans_type, property, str(final_value_parsed), duration]

	_send_success(client_id, {
		"message": "Use execute_editor_script with this code to run the tween",
		"script_code": script_text
	}, command_id)
