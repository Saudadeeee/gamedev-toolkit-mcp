@tool
class_name MCPProjectConfigCommands
extends MCPBaseCommandProcessor

## Command processor for project configuration operations
## Handles ProjectSettings, InputMap, AudioServer, and physics layers

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"set_project_setting":
			_set_project_setting(client_id, params, command_id)
			return true
		"get_project_setting":
			_get_project_setting(client_id, params, command_id)
			return true
		"list_project_settings":
			_list_project_settings(client_id, params, command_id)
			return true
		"add_input_action":
			_add_input_action(client_id, params, command_id)
			return true
		"add_input_event":
			_add_input_event(client_id, params, command_id)
			return true
		"remove_input_action":
			_remove_input_action(client_id, params, command_id)
			return true
		"list_input_actions":
			_list_input_actions(client_id, params, command_id)
			return true
		"add_audio_bus":
			_add_audio_bus(client_id, params, command_id)
			return true
		"set_bus_volume":
			_set_bus_volume(client_id, params, command_id)
			return true
		"add_bus_effect":
			_add_bus_effect(client_id, params, command_id)
			return true
		"list_audio_buses":
			_list_audio_buses(client_id, params, command_id)
			return true
		"set_physics_layer_name":
			_set_physics_layer_name(client_id, params, command_id)
			return true
	return false  # Command not handled

## PROJECT SETTINGS COMMANDS

func _set_project_setting(client_id: int, params: Dictionary, command_id: String) -> void:
	var setting_name = params.get("setting_name", "")
	var value = params.get("value")

	if setting_name.is_empty():
		return _send_error(client_id, "Setting name cannot be empty", command_id)

	if value == null:
		return _send_error(client_id, "Value cannot be null", command_id)

	# Set the setting
	ProjectSettings.set_setting(setting_name, value)

	# Save project.godot
	var err = ProjectSettings.save()
	if err != OK:
		return _send_error(client_id, "Failed to save project settings: error code %d" % err, command_id)

	_send_success(client_id, {
		"setting": setting_name,
		"value": value
	}, command_id)

func _get_project_setting(client_id: int, params: Dictionary, command_id: String) -> void:
	var setting_name = params.get("setting_name", "")
	var default_value = params.get("default_value", null)

	if setting_name.is_empty():
		return _send_error(client_id, "Setting name cannot be empty", command_id)

	var value
	if ProjectSettings.has_setting(setting_name):
		value = ProjectSettings.get_setting(setting_name)
	else:
		value = default_value

	_send_success(client_id, {
		"setting": setting_name,
		"value": value,
		"exists": ProjectSettings.has_setting(setting_name)
	}, command_id)

func _list_project_settings(client_id: int, params: Dictionary, command_id: String) -> void:
	var prefix = params.get("prefix", "")

	var settings = []
	var property_list = ProjectSettings.get_property_list()

	for prop in property_list:
		var name = prop["name"]
		# Skip internal properties
		if name.begins_with("_"):
			continue

		# Filter by prefix if provided
		if not prefix.is_empty() and not name.begins_with(prefix):
			continue

		settings.append({
			"name": name,
			"value": ProjectSettings.get_setting(name)
		})

	_send_success(client_id, {
		"settings": settings,
		"count": settings.size(),
		"prefix": prefix
	}, command_id)

## INPUT MAP COMMANDS

func _add_input_action(client_id: int, params: Dictionary, command_id: String) -> void:
	var action_name = params.get("action_name", "")
	var deadzone = params.get("deadzone", 0.5)

	if action_name.is_empty():
		return _send_error(client_id, "Action name cannot be empty", command_id)

	if InputMap.has_action(action_name):
		return _send_error(client_id, "Input action already exists: %s" % action_name, command_id)

	# Add the action
	InputMap.add_action(action_name, deadzone)

	# Save to project settings
	ProjectSettings.save()

	_send_success(client_id, {
		"action": action_name,
		" deadzone": deadzone
	}, command_id)

func _add_input_event(client_id: int, params: Dictionary, command_id: String) -> void:
	var action_name = params.get("action_name", "")
	var event_type = params.get("event_type", "")

	if action_name.is_empty():
		return _send_error(client_id, "Action name cannot be empty", command_id)

	if not InputMap.has_action(action_name):
		return _send_error(client_id, "Action does not exist: %s" % action_name, command_id)

	var event: InputEvent

	match event_type:
		"key":
			var keycode_str = params.get("keycode", "")
			if keycode_str.is_empty():
				return _send_error(client_id, "Keycode is required for key events", command_id)

			event = InputEventKey.new()
			# Convert string like "KEY_SPACE" to actual keycode
			var keycode = OS.find_keycode_from_string(keycode_str)
			if keycode == KEY_NONE:
				return _send_error(client_id, "Invalid keycode: %s" % keycode_str, command_id)
			event.keycode = keycode

		"mouse_button":
			var button_index = params.get("button_index", -1)
			if button_index < 0:
				return _send_error(client_id, "Button index is required for mouse button events", command_id)

			event = InputEventMouseButton.new()
			event.button_index = button_index

		"joypad_button":
			var button_index = params.get("button_index", -1)
			if button_index < 0:
				return _send_error(client_id, "Button index is required for joypad button events", command_id)

			event = InputEventJoypadButton.new()
			event.button_index = button_index

		"joypad_motion":
			var axis = params.get("axis", -1)
			var axis_value = params.get("axis_value", 0.0)

			if axis < 0:
				return _send_error(client_id, "Axis is required for joypad motion events", command_id)

			event = InputEventJoypadMotion.new()
			event.axis = axis
			event.axis_value = axis_value

		_:
			return _send_error(client_id, "Unknown event type: %s" % event_type, command_id)

	# Add event to action
	InputMap.action_add_event(action_name, event)
	ProjectSettings.save()

	_send_success(client_id, {
		"action": action_name,
		"event_type": event_type
	}, command_id)

func _remove_input_action(client_id: int, params: Dictionary, command_id: String) -> void:
	var action_name = params.get("action_name", "")

	if action_name.is_empty():
		return _send_error(client_id, "Action name cannot be empty", command_id)

	if not InputMap.has_action(action_name):
		return _send_error(client_id, "Action does not exist: %s" % action_name, command_id)

	InputMap.erase_action(action_name)
	ProjectSettings.save()

	_send_success(client_id, {
		"action": action_name
	}, command_id)

func _list_input_actions(client_id: int, params: Dictionary, command_id: String) -> void:
	var actions = []
	var action_list = InputMap.get_actions()

	for action in action_list:
		var events = []
		var event_list = InputMap.action_get_events(action)

		for event in event_list:
			var event_info = {
				"type": "",
				"description": ""
			}

			if event is InputEventKey:
				event_info["type"] = "key"
				event_info["description"] = OS.get_keycode_string(event.keycode)
			elif event is InputEventMouseButton:
				event_info["type"] = "mouse_button"
				event_info["description"] = "Button %d" % event.button_index
			elif event is InputEventJoypadButton:
				event_info["type"] = "joypad_button"
				event_info["description"] = "Joy Button %d" % event.button_index
			elif event is InputEventJoypadMotion:
				event_info["type"] = "joypad_motion"
				event_info["description"] = "Joy Axis %d (value: %.2f)" % [event.axis, event.axis_value]
			else:
				event_info["type"] = "unknown"
				event_info["description"] = str(event)

			events.append(event_info)

		actions.append({
			"name": action,
			"deadzone": InputMap.action_get_deadzone(action),
			"events": events
		})

	_send_success(client_id, {
		"actions": actions,
		"count": actions.size()
	}, command_id)

## AUDIO SERVER COMMANDS

func _add_audio_bus(client_id: int, params: Dictionary, command_id: String) -> void:
	var bus_name = params.get("bus_name", "")
	var position = params.get("position", -1)

	if bus_name.is_empty():
		return _send_error(client_id, "Bus name cannot be empty", command_id)

	# Check if bus with this name already exists
	for i in range(AudioServer.bus_count):
		if AudioServer.get_bus_name(i) == bus_name:
			return _send_error(client_id, "Audio bus already exists: %s" % bus_name, command_id)

	# Add bus
	var bus_index
	if position >= 0:
		AudioServer.add_bus(position)
		bus_index = position
	else:
		AudioServer.add_bus()
		bus_index = AudioServer.bus_count - 1

	# Set bus name
	AudioServer.set_bus_name(bus_index, bus_name)

	_send_success(client_id, {
		"bus_name": bus_name,
		"bus_index": bus_index
	}, command_id)

func _set_bus_volume(client_id: int, params: Dictionary, command_id: String) -> void:
	var bus_index = params.get("bus_index", -1)
	var volume_db = params.get("volume_db", 0.0)

	if bus_index < 0:
		return _send_error(client_id, "Bus index cannot be negative", command_id)

	if bus_index >= AudioServer.bus_count:
		return _send_error(client_id, "Bus index %d out of range (max: %d)" % [bus_index, AudioServer.bus_count - 1], command_id)

	# Set volume
	AudioServer.set_bus_volume_db(bus_index, volume_db)

	_send_success(client_id, {
		"bus_index": bus_index,
		"volume_db": volume_db
	}, command_id)

func _add_bus_effect(client_id: int, params: Dictionary, command_id: String) -> void:
	var bus_index = params.get("bus_index", -1)
	var effect_type = params.get("effect_type", "")
	var position = params.get("position", -1)

	if bus_index < 0 or bus_index >= AudioServer.bus_count:
		return _send_error(client_id, "Invalid bus index: %d" % bus_index, command_id)

	# Create the effect
	var effect: AudioEffect
	match effect_type:
		"reverb":
			effect = AudioEffectReverb.new()
		"delay":
			effect = AudioEffectDelay.new()
		"chorus":
			effect = AudioEffectChorus.new()
		"distortion":
			effect = AudioEffectDistortion.new()
		"eq":
			effect = AudioEffectEQ.new()
		"compressor":
			effect = AudioEffectCompressor.new()
		"limiter":
			effect = AudioEffectLimiter.new()
		_:
			return _send_error(client_id, "Unknown effect type: %s" % effect_type, command_id)

	# Add effect to bus
	if position >= 0:
		AudioServer.add_bus_effect(bus_index, effect, position)
	else:
		AudioServer.add_bus_effect(bus_index, effect)

	_send_success(client_id, {
		"bus_index": bus_index,
		"effect_type": effect_type
	}, command_id)

func _list_audio_buses(client_id: int, params: Dictionary, command_id: String) -> void:
	var buses = []

	for i in range(AudioServer.bus_count):
		var bus_info = {
			"index": i,
			"name": AudioServer.get_bus_name(i),
			"volume_db": AudioServer.get_bus_volume_db(i),
			"mute": AudioServer.is_bus_mute(i),
			"solo": AudioServer.is_bus_solo(i),
			"effects": []
		}

		# Get effects on this bus
		var effect_count = AudioServer.get_bus_effect_count(i)
		for j in range(effect_count):
			var effect = AudioServer.get_bus_effect(i, j)
			bus_info["effects"].append({
				"index": j,
				"type": effect.get_class(),
				"enabled": AudioServer.is_bus_effect_enabled(i, j)
			})

		buses.append(bus_info)

	_send_success(client_id, {
		"buses": buses,
		"count": buses.size()
	}, command_id)

## PHYSICS LAYER COMMANDS

func _set_physics_layer_name(client_id: int, params: Dictionary, command_id: String) -> void:
	var layer_type = params.get("layer_type", "")
	var layer_number = params.get("layer_number", 0)
	var layer_name = params.get("layer_name", "")

	if layer_type.is_empty():
		return _send_error(client_id, "Layer type cannot be empty", command_id)

	if layer_number < 1 or layer_number > 32:
		return _send_error(client_id, "Layer number must be between 1 and 32", command_id)

	if layer_name.is_empty():
		return _send_error(client_id, "Layer name cannot be empty", command_id)

	# Build the setting name
	var setting_name = "layer_names/%s/layer_%d" % [layer_type, layer_number]

	# Set the layer name
	ProjectSettings.set_setting(setting_name, layer_name)

	# Save project.godot
	var err = ProjectSettings.save()
	if err != OK:
		return _send_error(client_id, "Failed to save project settings: error code %d" % err, command_id)

	_send_success(client_id, {
		"layer_type": layer_type,
		"layer_number": layer_number,
		"layer_name": layer_name
	}, command_id)
