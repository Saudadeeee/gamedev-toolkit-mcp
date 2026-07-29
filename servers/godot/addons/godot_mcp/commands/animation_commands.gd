@tool
class_name MCPAnimationCommands
extends MCPBaseCommandProcessor

## Command processor for Animation system operations
## Handles AnimationPlayer, Animation tracks, and keyframes

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"create_animation":
			_create_animation(client_id, params, command_id)
			return true
		"delete_animation":
			_delete_animation(client_id, params, command_id)
			return true
		"list_animations":
			_list_animations(client_id, params, command_id)
			return true
		"add_animation_track":
			_add_animation_track(client_id, params, command_id)
			return true
		"remove_animation_track":
			_remove_animation_track(client_id, params, command_id)
			return true
		"insert_animation_key":
			_insert_animation_key(client_id, params, command_id)
			return true
		"remove_animation_key":
			_remove_animation_key(client_id, params, command_id)
			return true
		"get_animation_data":
			_get_animation_data(client_id, params, command_id)
			return true
		"play_animation":
			_play_animation(client_id, params, command_id)
			return true
		"stop_animation":
			_stop_animation(client_id, params, command_id)
			return true
	return false  # Command not handled

## ANIMATION MANAGEMENT COMMANDS

func _create_animation(client_id: int, params: Dictionary, command_id: String) -> void:
	var player_path = params.get("animation_player_path", "")
	var player = _get_editor_node(player_path)

	if not player or not player is AnimationPlayer:
		return _send_error(client_id, "AnimationPlayer not found or invalid: %s" % player_path, command_id)

	var anim_name = params.get("animation_name", "new_animation")
	var length = params.get("length", 1.0)

	if player.has_animation(anim_name):
		return _send_error(client_id, "Animation already exists: %s" % anim_name, command_id)

	# Create new animation
	var animation = Animation.new()
	animation.length = length

	# Add animation to player
	player.add_animation(anim_name, animation)
	_mark_scene_modified()

	_send_success(client_id, {
		"animation_name": anim_name,
		"length": length
	}, command_id)

func _delete_animation(client_id: int, params: Dictionary, command_id: String) -> void:
	var player_path = params.get("animation_player_path", "")
	var player = _get_editor_node(player_path)

	if not player or not player is AnimationPlayer:
		return _send_error(client_id, "AnimationPlayer not found or invalid: %s" % player_path, command_id)

	var anim_name = params.get("animation_name", "")

	if not player.has_animation(anim_name):
		return _send_error(client_id, "Animation not found: %s" % anim_name, command_id)

	# Remove animation
	player.remove_animation(anim_name)
	_mark_scene_modified()

	_send_success(client_id, {
		"animation_name": anim_name
	}, command_id)

func _list_animations(client_id: int, params: Dictionary, command_id: String) -> void:
	var player_path = params.get("animation_player_path", "")
	var player = _get_editor_node(player_path)

	if not player or not player is AnimationPlayer:
		return _send_error(client_id, "AnimationPlayer not found or invalid: %s" % player_path, command_id)

	var animations = []
	var anim_list = player.get_animation_list()

	for anim_name in anim_list:
		var anim = player.get_animation(anim_name)
		animations.append({
			"name": anim_name,
			"length": anim.length,
			"track_count": anim.get_track_count()
		})

	_send_success(client_id, {
		"animations": animations,
		"count": animations.size()
	}, command_id)

## TRACK MANAGEMENT COMMANDS

func _add_animation_track(client_id: int, params: Dictionary, command_id: String) -> void:
	var player_path = params.get("animation_player_path", "")
	var player = _get_editor_node(player_path)

	if not player or not player is AnimationPlayer:
		return _send_error(client_id, "AnimationPlayer not found or invalid: %s" % player_path, command_id)

	var anim_name = params.get("animation_name", "")
	if not player.has_animation(anim_name):
		return _send_error(client_id, "Animation not found: %s" % anim_name, command_id)

	var animation = player.get_animation(anim_name)
	var track_type_str = params.get("track_type", "value")
	var target_path = params.get("target_path", "")
	var position = params.get("position", -1)

	if target_path.is_empty():
		return _send_error(client_id, "Target path cannot be empty", command_id)

	# Map track type string to enum
	var track_type
	match track_type_str:
		"value":
			track_type = Animation.TYPE_VALUE
		"transform3d":
			track_type = Animation.TYPE_POSITION_3D  # Godot 4.x
		"method":
			track_type = Animation.TYPE_METHOD
		"bezier":
			track_type = Animation.TYPE_BEZIER
		"audio":
			track_type = Animation.TYPE_AUDIO
		"animation":
			track_type = Animation.TYPE_ANIMATION
		_:
			return _send_error(client_id, "Unknown track type: %s" % track_type_str, command_id)

	# Add track
	var track_idx
	if position >= 0:
		track_idx = animation.add_track(track_type, position)
	else:
		track_idx = animation.add_track(track_type)

	# Set track path
	animation.track_set_path(track_idx, NodePath(target_path))
	_mark_scene_modified()

	_send_success(client_id, {
		"track_index": track_idx,
		"track_type": track_type_str,
		"target_path": target_path
	}, command_id)

func _remove_animation_track(client_id: int, params: Dictionary, command_id: String) -> void:
	var player_path = params.get("animation_player_path", "")
	var player = _get_editor_node(player_path)

	if not player or not player is AnimationPlayer:
		return _send_error(client_id, "AnimationPlayer not found or invalid: %s" % player_path, command_id)

	var anim_name = params.get("animation_name", "")
	if not player.has_animation(anim_name):
		return _send_error(client_id, "Animation not found: %s" % anim_name, command_id)

	var animation = player.get_animation(anim_name)
	var track_idx = params.get("track_index", -1)

	if track_idx < 0 or track_idx >= animation.get_track_count():
		return _send_error(client_id, "Track index %d out of range (max: %d)" % [track_idx, animation.get_track_count() - 1], command_id)

	# Remove track
	animation.remove_track(track_idx)
	_mark_scene_modified()

	_send_success(client_id, {
		"track_index": track_idx
	}, command_id)

## KEYFRAME MANAGEMENT COMMANDS

func _insert_animation_key(client_id: int, params: Dictionary, command_id: String) -> void:
	var player_path = params.get("animation_player_path", "")
	var player = _get_editor_node(player_path)

	if not player or not player is AnimationPlayer:
		return _send_error(client_id, "AnimationPlayer not found or invalid: %s" % player_path, command_id)

	var anim_name = params.get("animation_name", "")
	if not player.has_animation(anim_name):
		return _send_error(client_id, "Animation not found: %s" % anim_name, command_id)

	var animation = player.get_animation(anim_name)
	var track_idx = params.get("track_index", -1)
	var time = params.get("time", 0.0)
	var value = params.get("value")

	if track_idx < 0 or track_idx >= animation.get_track_count():
		return _send_error(client_id, "Track index %d out of range" % track_idx, command_id)

	# Parse value if it's a Godot type string
	var parsed_value = _parse_property_value(value)

	# Insert keyframe
	var key_idx = animation.track_insert_key(track_idx, time, parsed_value)
	_mark_scene_modified()

	_send_success(client_id, {
		"track_index": track_idx,
		"key_index": key_idx,
		"time": time
	}, command_id)

func _remove_animation_key(client_id: int, params: Dictionary, command_id: String) -> void:
	var player_path = params.get("animation_player_path", "")
	var player = _get_editor_node(player_path)

	if not player or not player is AnimationPlayer:
		return _send_error(client_id, "AnimationPlayer not found or invalid: %s" % player_path, command_id)

	var anim_name = params.get("animation_name", "")
	if not player.has_animation(anim_name):
		return _send_error(client_id, "Animation not found: %s" % anim_name, command_id)

	var animation = player.get_animation(anim_name)
	var track_idx = params.get("track_index", -1)
	var key_idx = params.get("key_index", -1)

	if track_idx < 0 or track_idx >= animation.get_track_count():
		return _send_error(client_id, "Track index %d out of range" % track_idx, command_id)

	var key_count = animation.track_get_key_count(track_idx)
	if key_idx < 0 or key_idx >= key_count:
		return _send_error(client_id, "Key index %d out of range (max: %d)" % [key_idx, key_count - 1], command_id)

	# Remove keyframe
	animation.track_remove_key(track_idx, key_idx)
	_mark_scene_modified()

	_send_success(client_id, {
		"track_index": track_idx,
		"key_index": key_idx
	}, command_id)

func _get_animation_data(client_id: int, params: Dictionary, command_id: String) -> void:
	var player_path = params.get("animation_player_path", "")
	var player = _get_editor_node(player_path)

	if not player or not player is AnimationPlayer:
		return _send_error(client_id, "AnimationPlayer not found or invalid: %s" % player_path, command_id)

	var anim_name = params.get("animation_name", "")
	if not player.has_animation(anim_name):
		return _send_error(client_id, "Animation not found: %s" % anim_name, command_id)

	var animation = player.get_animation(anim_name)

	# Build animation data structure
	var tracks = []
	for track_idx in range(animation.get_track_count()):
		var track_info = {
			"index": track_idx,
			"type": _get_track_type_name(animation.track_get_type(track_idx)),
			"path": str(animation.track_get_path(track_idx)),
			"keys": []
		}

		# Get all keys for this track
		var key_count = animation.track_get_key_count(track_idx)
		for key_idx in range(key_count):
			var key_time = animation.track_get_key_time(track_idx, key_idx)
			var key_value = animation.track_get_key_value(track_idx, key_idx)

			track_info["keys"].append({
				"index": key_idx,
				"time": key_time,
				"value": str(key_value)  # Convert to string for JSON
			})

		tracks.append(track_info)

	_send_success(client_id, {
		"name": anim_name,
		"length": animation.length,
		"loop_mode": animation.loop_mode,
		"step": animation.step,
		"track_count": animation.get_track_count(),
		"tracks": tracks
	}, command_id)

func _get_track_type_name(track_type: int) -> String:
	match track_type:
		Animation.TYPE_VALUE:
			return "value"
		Animation.TYPE_POSITION_3D:
			return "position_3d"
		Animation.TYPE_ROTATION_3D:
			return "rotation_3d"
		Animation.TYPE_SCALE_3D:
			return "scale_3d"
		Animation.TYPE_BLEND_SHAPE:
			return "blend_shape"
		Animation.TYPE_METHOD:
			return "method"
		Animation.TYPE_BEZIER:
			return "bezier"
		Animation.TYPE_AUDIO:
			return "audio"
		Animation.TYPE_ANIMATION:
			return "animation"
		_:
			return "unknown"

## PLAYBACK COMMANDS

func _play_animation(client_id: int, params: Dictionary, command_id: String) -> void:
	var player_path = params.get("animation_player_path", "")
	var player = _get_editor_node(player_path)

	if not player or not player is AnimationPlayer:
		return _send_error(client_id, "AnimationPlayer not found or invalid: %s" % player_path, command_id)

	var anim_name = params.get("animation_name", "")
	if not player.has_animation(anim_name):
		return _send_error(client_id, "Animation not found: %s" % anim_name, command_id)

	var custom_speed = params.get("custom_speed", 1.0)
	var from_end = params.get("from_end", false)

	# Play animation
	player.play(anim_name, -1, custom_speed, from_end)

	_send_success(client_id, {
		"animation_name": anim_name,
		"custom_speed": custom_speed
	}, command_id)

func _stop_animation(client_id: int, params: Dictionary, command_id: String) -> void:
	var player_path = params.get("animation_player_path", "")
	var player = _get_editor_node(player_path)

	if not player or not player is AnimationPlayer:
		return _send_error(client_id, "AnimationPlayer not found or invalid: %s" % player_path, command_id)

	var keep_state = params.get("keep_state", false)

	# Stop animation
	player.stop(keep_state)

	_send_success(client_id, {
		"keep_state": keep_state
	}, command_id)
