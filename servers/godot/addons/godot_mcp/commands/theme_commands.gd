@tool
class_name MCPThemeCommands
extends MCPBaseCommandProcessor

## Command processor for UI Theme operations

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"create_theme":
			_create_theme(client_id, params, command_id)
			return true
		"set_theme_color":
			_set_theme_color(client_id, params, command_id)
			return true
		"set_theme_font":
			_set_theme_font(client_id, params, command_id)
			return true
		"set_theme_font_size":
			_set_theme_font_size(client_id, params, command_id)
			return true
		"set_theme_constant":
			_set_theme_constant(client_id, params, command_id)
			return true
		"set_theme_stylebox":
			_set_theme_stylebox(client_id, params, command_id)
			return true
		"assign_theme_to_node":
			_assign_theme_to_node(client_id, params, command_id)
			return true
		"get_theme_items":
			_get_theme_items(client_id, params, command_id)
			return true
	return false

func _create_theme(client_id: int, params: Dictionary, command_id: String) -> void:
	var theme = Theme.new()
	var save_path = params.get("save_path", "")

	if not save_path.is_empty():
		var err = ResourceSaver.save(theme, save_path)
		if err != OK:
			return _send_error(client_id, "Failed to save theme: error %d" % err, command_id)
		_send_success(client_id, {"message": "Theme created and saved", "save_path": save_path}, command_id)
	else:
		_send_success(client_id, {"message": "Theme created (not saved - provide save_path to save)"}, command_id)

func _load_theme(path: String) -> Theme:
	if ResourceLoader.exists(path):
		var res = ResourceLoader.load(path)
		if res is Theme:
			return res
	return null

func _set_theme_color(client_id: int, params: Dictionary, command_id: String) -> void:
	var theme_path = params.get("theme_path", "")
	var theme = _load_theme(theme_path)
	if not theme:
		return _send_error(client_id, "Theme not found: %s" % theme_path, command_id)

	var control_type = params.get("control_type", "")
	var color_name = params.get("color_name", "")
	var color = Color(params.get("r", 1.0), params.get("g", 1.0), params.get("b", 1.0), params.get("a", 1.0))

	theme.set_color(color_name, control_type, color)
	ResourceSaver.save(theme, theme_path)
	_send_success(client_id, {"message": "Theme color set", "control_type": control_type, "color_name": color_name}, command_id)

func _set_theme_font(client_id: int, params: Dictionary, command_id: String) -> void:
	var theme_path = params.get("theme_path", "")
	var theme = _load_theme(theme_path)
	if not theme:
		return _send_error(client_id, "Theme not found: %s" % theme_path, command_id)

	var control_type = params.get("control_type", "")
	var font_name = params.get("font_name", "")
	var font_path = params.get("font_path", "")

	if not ResourceLoader.exists(font_path):
		return _send_error(client_id, "Font file not found: %s" % font_path, command_id)

	var font = ResourceLoader.load(font_path)
	if not font is Font:
		return _send_error(client_id, "Resource is not a Font: %s" % font_path, command_id)

	theme.set_font(font_name, control_type, font)
	ResourceSaver.save(theme, theme_path)
	_send_success(client_id, {"message": "Theme font set", "control_type": control_type, "font_name": font_name}, command_id)

func _set_theme_font_size(client_id: int, params: Dictionary, command_id: String) -> void:
	var theme_path = params.get("theme_path", "")
	var theme = _load_theme(theme_path)
	if not theme:
		return _send_error(client_id, "Theme not found: %s" % theme_path, command_id)

	var control_type = params.get("control_type", "")
	var font_size_name = params.get("font_size_name", "font_size")
	var size = params.get("size", 16)

	theme.set_font_size(font_size_name, control_type, size)
	ResourceSaver.save(theme, theme_path)
	_send_success(client_id, {"message": "Theme font size set", "size": size}, command_id)

func _set_theme_constant(client_id: int, params: Dictionary, command_id: String) -> void:
	var theme_path = params.get("theme_path", "")
	var theme = _load_theme(theme_path)
	if not theme:
		return _send_error(client_id, "Theme not found: %s" % theme_path, command_id)

	var control_type = params.get("control_type", "")
	var constant_name = params.get("constant_name", "")
	var value = params.get("value", 0)

	theme.set_constant(constant_name, control_type, value)
	ResourceSaver.save(theme, theme_path)
	_send_success(client_id, {"message": "Theme constant set", "constant_name": constant_name, "value": value}, command_id)

func _set_theme_stylebox(client_id: int, params: Dictionary, command_id: String) -> void:
	var theme_path = params.get("theme_path", "")
	var theme = _load_theme(theme_path)
	if not theme:
		return _send_error(client_id, "Theme not found: %s" % theme_path, command_id)

	var control_type = params.get("control_type", "")
	var stylebox_name = params.get("stylebox_name", "normal")
	var stylebox_type = params.get("stylebox_type", "flat")

	var stylebox: StyleBox
	match stylebox_type:
		"flat":
			var sb = StyleBoxFlat.new()
			if params.has("bg_r") or params.has("bg_g") or params.has("bg_b"):
				sb.bg_color = Color(params.get("bg_r", 0.2), params.get("bg_g", 0.2), params.get("bg_b", 0.2), params.get("bg_a", 1.0))
			if params.has("corner_radius"):
				var r = int(params["corner_radius"])
				sb.corner_radius_top_left = r
				sb.corner_radius_top_right = r
				sb.corner_radius_bottom_left = r
				sb.corner_radius_bottom_right = r
			if params.has("border_width"):
				var bw = int(params["border_width"])
				sb.border_width_top = bw
				sb.border_width_bottom = bw
				sb.border_width_left = bw
				sb.border_width_right = bw
			if params.has("border_r") or params.has("border_g") or params.has("border_b"):
				sb.border_color = Color(params.get("border_r", 0.0), params.get("border_g", 0.0), params.get("border_b", 0.0), params.get("border_a", 1.0))
			if params.has("content_margin"):
				var cm = params["content_margin"]
				sb.content_margin_top = cm
				sb.content_margin_bottom = cm
				sb.content_margin_left = cm
				sb.content_margin_right = cm
			stylebox = sb
		"empty":
			stylebox = StyleBoxEmpty.new()
		"line":
			stylebox = StyleBoxLine.new()
		_:
			return _send_error(client_id, "Unknown stylebox type: %s" % stylebox_type, command_id)

	theme.set_stylebox(stylebox_name, control_type, stylebox)
	ResourceSaver.save(theme, theme_path)
	_send_success(client_id, {"message": "Theme stylebox set", "control_type": control_type, "stylebox_name": stylebox_name}, command_id)

func _assign_theme_to_node(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var theme_path = params.get("theme_path", "")

	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	if not "theme" in node:
		return _send_error(client_id, "Node does not support theme assignment (not a Control?)", command_id)

	var theme = _load_theme(theme_path)
	if not theme:
		return _send_error(client_id, "Theme not found: %s" % theme_path, command_id)

	node.theme = theme
	_mark_scene_modified()
	_send_success(client_id, {"message": "Theme assigned to node", "node_path": node_path, "theme_path": theme_path}, command_id)

func _get_theme_items(client_id: int, params: Dictionary, command_id: String) -> void:
	var theme_path = params.get("theme_path", "")
	var theme = _load_theme(theme_path)
	if not theme:
		return _send_error(client_id, "Theme not found: %s" % theme_path, command_id)

	var items = {"colors": {}, "fonts": {}, "font_sizes": {}, "constants": {}, "styleboxes": {}}

	for type_name in theme.get_type_list():
		for color_name in theme.get_color_list(type_name):
			var key = "%s/%s" % [type_name, color_name]
			var c = theme.get_color(color_name, type_name)
			items["colors"][key] = [c.r, c.g, c.b, c.a]
		for font_name in theme.get_font_list(type_name):
			var key = "%s/%s" % [type_name, font_name]
			items["fonts"][key] = "font"
		for size_name in theme.get_font_size_list(type_name):
			var key = "%s/%s" % [type_name, size_name]
			items["font_sizes"][key] = theme.get_font_size(size_name, type_name)
		for const_name in theme.get_constant_list(type_name):
			var key = "%s/%s" % [type_name, const_name]
			items["constants"][key] = theme.get_constant(const_name, type_name)
		for sb_name in theme.get_stylebox_list(type_name):
			var key = "%s/%s" % [type_name, sb_name]
			var sb = theme.get_stylebox(sb_name, type_name)
			items["styleboxes"][key] = sb.get_class() if sb else "null"

	_send_success(client_id, items, command_id)
