@tool
class_name MCPPlaybackCommands
extends MCPBaseCommandProcessor

## Command processor for playback control operations
## Handles playing/stopping scenes in the Godot editor

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"play_main_scene":
			_play_main_scene(client_id, params, command_id)
			return true
		"play_current_scene":
			_play_current_scene(client_id, params, command_id)
			return true
		"play_custom_scene":
			_play_custom_scene(client_id, params, command_id)
			return true
		"stop_playing_scene":
			_stop_playing_scene(client_id, params, command_id)
			return true
		"get_play_status":
			_get_play_status(client_id, params, command_id)
			return true
	return false  # Command not handled

func _play_main_scene(client_id: int, params: Dictionary, command_id: String) -> void:
	var plugin = Engine.get_meta("GodotMCPPlugin")
	if not plugin:
		return _send_error(client_id, "GodotMCPPlugin not found in Engine metadata", command_id)

	var editor_interface = plugin.get_editor_interface()

	# Play the main scene (F5)
	editor_interface.play_main_scene()

	_send_success(client_id, {
		"message": "Started playing main scene"
	}, command_id)

func _play_current_scene(client_id: int, params: Dictionary, command_id: String) -> void:
	var plugin = Engine.get_meta("GodotMCPPlugin")
	if not plugin:
		return _send_error(client_id, "GodotMCPPlugin not found in Engine metadata", command_id)

	var editor_interface = plugin.get_editor_interface()
	var edited_scene_root = editor_interface.get_edited_scene_root()

	if not edited_scene_root:
		return _send_error(client_id, "No scene is currently being edited", command_id)

	# Play the current scene (F6)
	editor_interface.play_current_scene()

	_send_success(client_id, {
		"message": "Started playing current scene"
	}, command_id)

func _play_custom_scene(client_id: int, params: Dictionary, command_id: String) -> void:
	var scene_path = params.get("scene_path", "")

	# Validation
	if scene_path.is_empty():
		return _send_error(client_id, "Scene path cannot be empty", command_id)

	# Check if scene file exists
	if not FileAccess.file_exists(scene_path):
		return _send_error(client_id, "Scene file not found: %s" % scene_path, command_id)

	var plugin = Engine.get_meta("GodotMCPPlugin")
	if not plugin:
		return _send_error(client_id, "GodotMCPPlugin not found in Engine metadata", command_id)

	var editor_interface = plugin.get_editor_interface()

	# Play the custom scene
	editor_interface.play_custom_scene(scene_path)

	_send_success(client_id, {
		"message": "Started playing scene: %s" % scene_path,
		"scene_path": scene_path
	}, command_id)

func _stop_playing_scene(client_id: int, params: Dictionary, command_id: String) -> void:
	var plugin = Engine.get_meta("GodotMCPPlugin")
	if not plugin:
		return _send_error(client_id, "GodotMCPPlugin not found in Engine metadata", command_id)

	var editor_interface = plugin.get_editor_interface()

	# Check if a scene is actually playing
	if not editor_interface.is_playing_scene():
		return _send_error(client_id, "No scene is currently playing", command_id)

	# Stop the playing scene (F8)
	editor_interface.stop_playing_scene()

	_send_success(client_id, {
		"message": "Stopped playing scene"
	}, command_id)

func _get_play_status(client_id: int, params: Dictionary, command_id: String) -> void:
	var plugin = Engine.get_meta("GodotMCPPlugin")
	if not plugin:
		return _send_error(client_id, "GodotMCPPlugin not found in Engine metadata", command_id)

	var editor_interface = plugin.get_editor_interface()

	var is_playing = editor_interface.is_playing_scene()
	var playing_scene = null

	if is_playing:
		playing_scene = editor_interface.get_playing_scene()

	_send_success(client_id, {
		"is_playing": is_playing,
		"playing_scene": playing_scene
	}, command_id)
