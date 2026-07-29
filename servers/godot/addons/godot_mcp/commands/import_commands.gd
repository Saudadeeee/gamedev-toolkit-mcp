@tool
class_name MCPImportCommands
extends MCPBaseCommandProcessor

## Command processor for Import and Asset Management operations

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"scan_filesystem":
			_scan_filesystem(client_id, params, command_id)
			return true
		"reimport_file":
			_reimport_file(client_id, params, command_id)
			return true
		"get_import_settings":
			_get_import_settings(client_id, params, command_id)
			return true
		"set_import_setting":
			_set_import_setting(client_id, params, command_id)
			return true
		"list_filesystem_files":
			_list_filesystem_files(client_id, params, command_id)
			return true
	return false

func _scan_filesystem(client_id: int, params: Dictionary, command_id: String) -> void:
	var plugin = Engine.get_meta("GodotMCPPlugin")
	if not plugin:
		return _send_error(client_id, "GodotMCPPlugin not found", command_id)

	var editor_interface = plugin.get_editor_interface()
	var filesystem = editor_interface.get_resource_filesystem()
	filesystem.scan()

	_send_success(client_id, {"message": "Filesystem scan initiated"}, command_id)

func _reimport_file(client_id: int, params: Dictionary, command_id: String) -> void:
	var file_path = params.get("file_path", "")
	if file_path.is_empty():
		return _send_error(client_id, "File path cannot be empty", command_id)

	if not ResourceLoader.exists(file_path):
		return _send_error(client_id, "File not found: %s" % file_path, command_id)

	var plugin = Engine.get_meta("GodotMCPPlugin")
	if not plugin:
		return _send_error(client_id, "GodotMCPPlugin not found", command_id)

	var editor_interface = plugin.get_editor_interface()
	var filesystem = editor_interface.get_resource_filesystem()
	filesystem.update_file(file_path)

	_send_success(client_id, {"file_path": file_path}, command_id)

func _get_import_settings(client_id: int, params: Dictionary, command_id: String) -> void:
	var file_path = params.get("file_path", "")
	if file_path.is_empty():
		return _send_error(client_id, "File path cannot be empty", command_id)

	# Import settings are stored in .import files
	var import_path = file_path + ".import"
	if not FileAccess.file_exists(import_path):
		return _send_error(client_id, "No import file found for: %s" % file_path, command_id)

	var config = ConfigFile.new()
	var err = config.load(import_path)
	if err != OK:
		return _send_error(client_id, "Failed to load import file: error %d" % err, command_id)

	# Collect all settings
	var settings = {}
	for section in config.get_sections():
		settings[section] = {}
		for key in config.get_section_keys(section):
			settings[section][key] = config.get_value(section, key)

	_send_success(client_id, {
		"file_path": file_path,
		"import_path": import_path,
		"settings": settings
	}, command_id)

func _set_import_setting(client_id: int, params: Dictionary, command_id: String) -> void:
	var file_path = params.get("file_path", "")
	var setting_key = params.get("setting_key", "")
	var value = params.get("value")

	if file_path.is_empty():
		return _send_error(client_id, "File path cannot be empty", command_id)
	if setting_key.is_empty():
		return _send_error(client_id, "Setting key cannot be empty", command_id)

	var import_path = file_path + ".import"
	if not FileAccess.file_exists(import_path):
		return _send_error(client_id, "No import file found for: %s" % file_path, command_id)

	var config = ConfigFile.new()
	var err = config.load(import_path)
	if err != OK:
		return _send_error(client_id, "Failed to load import file: error %d" % err, command_id)

	# Parse setting_key as "section/key"
	var parts = setting_key.split("/", false, 1)
	if parts.size() < 2:
		return _send_error(client_id, "setting_key must be in format 'section/key' (e.g., 'params/compress/mode')", command_id)

	var section = parts[0]
	var key = parts[1]

	config.set_value(section, key, value)

	err = config.save(import_path)
	if err != OK:
		return _send_error(client_id, "Failed to save import file: error %d" % err, command_id)

	# Trigger reimport
	var plugin = Engine.get_meta("GodotMCPPlugin")
	if plugin:
		var filesystem = plugin.get_editor_interface().get_resource_filesystem()
		filesystem.update_file(file_path)

	_send_success(client_id, {
		"file_path": file_path,
		"setting_key": setting_key,
		"value": value
	}, command_id)

func _list_filesystem_files(client_id: int, params: Dictionary, command_id: String) -> void:
	var path = params.get("path", "res://")
	var recursive = params.get("recursive", false)
	var filter_extension = params.get("filter_extension", "")

	var files = []
	_collect_files(path, recursive, filter_extension, files)

	_send_success(client_id, {
		"path": path,
		"files": files,
		"count": files.size()
	}, command_id)

func _collect_files(dir_path: String, recursive: bool, extension_filter: String, result: Array) -> void:
	var dir = DirAccess.open(dir_path)
	if not dir:
		return

	dir.list_dir_begin()
	var file_name = dir.get_next()

	while file_name != "":
		if file_name.begins_with("."):
			file_name = dir.get_next()
			continue

		var full_path = dir_path.path_join(file_name)

		if dir.current_is_dir():
			if recursive:
				_collect_files(full_path + "/", recursive, extension_filter, result)
		else:
			# Skip .import files
			if file_name.ends_with(".import"):
				file_name = dir.get_next()
				continue
			if extension_filter.is_empty() or file_name.ends_with(extension_filter):
				result.append(full_path)

		file_name = dir.get_next()

	dir.list_dir_end()
