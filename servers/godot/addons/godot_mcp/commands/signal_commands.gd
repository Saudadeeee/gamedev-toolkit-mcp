@tool
class_name MCPSignalCommands
extends MCPBaseCommandProcessor

# Signals are how Godot nodes talk to each other. Without tools to wire them,
# an AI can build a scene tree and scripts but cannot connect the two, so the
# result never actually runs as a game.
#
# Connections are made with CONNECT_PERSIST, which is the flag the editor uses
# and the reason a connection survives into the saved .tscn. Omitting it makes
# a connection that works until the scene is reloaded and then silently is not
# there any more.

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"list_signals":
			_list_signals(client_id, params, command_id)
			return true
		"list_connections":
			_list_connections(client_id, params, command_id)
			return true
		"connect_signal":
			_connect_signal(client_id, params, command_id)
			return true
		"disconnect_signal":
			_disconnect_signal(client_id, params, command_id)
			return true
	return false

func _list_signals(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var include_inherited = bool(params.get("include_inherited", false))

	if node_path.is_empty():
		return _send_error(client_id, "Node path cannot be empty", command_id)

	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	# A bare Node already declares a dozen built-in signals; listing them by
	# default buries the handful the user actually authored on the script.
	var script_signals := {}
	if node.get_script():
		for entry in node.get_script().get_script_signal_list():
			script_signals[entry["name"]] = true

	var signals := []
	for entry in node.get_signal_list():
		var name: String = entry["name"]
		var from_script: bool = script_signals.has(name)
		if not include_inherited and not from_script:
			continue
		var args := []
		for arg in entry.get("args", []):
			args.append({"name": arg.get("name", ""), "type": arg.get("type", 0)})
		signals.append({
			"name": name,
			"args": args,
			"from_script": from_script,
			"connection_count": node.get_signal_connection_list(name).size(),
		})

	_send_success(client_id, {
		"node_path": node_path,
		"node_type": node.get_class(),
		"signals": signals,
		"include_inherited": include_inherited,
	}, command_id)

func _list_connections(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var signal_name = params.get("signal_name", "")

	if node_path.is_empty():
		return _send_error(client_id, "Node path cannot be empty", command_id)

	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	var names := []
	if signal_name.is_empty():
		for entry in node.get_signal_list():
			names.append(entry["name"])
	else:
		if not node.has_signal(signal_name):
			return _send_error(client_id, "Node has no signal '%s'" % signal_name, command_id)
		names.append(signal_name)

	var connections := []
	for name in names:
		for conn in node.get_signal_connection_list(name):
			var callable: Callable = conn["callable"]
			var target = callable.get_object()
			connections.append({
				"signal": name,
				"target_path": str(target.get_path()) if target is Node else "",
				"target_type": target.get_class() if target else "",
				"method": callable.get_method(),
				"flags": conn.get("flags", 0),
				"persistent": (int(conn.get("flags", 0)) & Object.CONNECT_PERSIST) != 0,
			})

	_send_success(client_id, {
		"node_path": node_path,
		"connections": connections,
	}, command_id)

func _connect_signal(client_id: int, params: Dictionary, command_id: String) -> void:
	var from_path = params.get("from_node_path", "")
	var signal_name = params.get("signal_name", "")
	var to_path = params.get("to_node_path", "")
	var method_name = params.get("method_name", "")
	var deferred = bool(params.get("deferred", false))
	var one_shot = bool(params.get("one_shot", false))

	for pair in [[from_path, "from_node_path"], [signal_name, "signal_name"],
			[to_path, "to_node_path"], [method_name, "method_name"]]:
		if str(pair[0]).is_empty():
			return _send_error(client_id, "%s cannot be empty" % pair[1], command_id)

	var from_node = _get_editor_node(from_path)
	if not from_node:
		return _send_error(client_id, "Source node not found: %s" % from_path, command_id)

	var to_node = _get_editor_node(to_path)
	if not to_node:
		return _send_error(client_id, "Target node not found: %s" % to_path, command_id)

	if not from_node.has_signal(signal_name):
		return _send_error(client_id,
			"Node %s has no signal '%s'" % [from_path, signal_name], command_id)

	# Checked rather than assumed: connecting to a method that does not exist
	# produces a connection that fails only when the signal first fires, which
	# is usually far from where the mistake was made.
	if not to_node.has_method(method_name):
		return _send_error(client_id,
			"Node %s has no method '%s'. Add it to the script first." % [to_path, method_name],
			command_id)

	var callable := Callable(to_node, method_name)
	if from_node.is_connected(signal_name, callable):
		return _send_error(client_id,
			"%s.%s is already connected to %s.%s" % [from_path, signal_name, to_path, method_name],
			command_id)

	var flags := Object.CONNECT_PERSIST
	if deferred:
		flags |= Object.CONNECT_DEFERRED
	if one_shot:
		flags |= Object.CONNECT_ONE_SHOT

	var err := from_node.connect(signal_name, callable, flags)
	if err != OK:
		return _send_error(client_id, "connect() failed with error %d" % err, command_id)

	_mark_scene_modified()
	_send_success(client_id, {
		"from_node_path": from_path,
		"signal_name": signal_name,
		"to_node_path": to_path,
		"method_name": method_name,
		"deferred": deferred,
		"one_shot": one_shot,
		"persistent": true,
	}, command_id)

func _disconnect_signal(client_id: int, params: Dictionary, command_id: String) -> void:
	var from_path = params.get("from_node_path", "")
	var signal_name = params.get("signal_name", "")
	var to_path = params.get("to_node_path", "")
	var method_name = params.get("method_name", "")

	for pair in [[from_path, "from_node_path"], [signal_name, "signal_name"],
			[to_path, "to_node_path"], [method_name, "method_name"]]:
		if str(pair[0]).is_empty():
			return _send_error(client_id, "%s cannot be empty" % pair[1], command_id)

	var from_node = _get_editor_node(from_path)
	if not from_node:
		return _send_error(client_id, "Source node not found: %s" % from_path, command_id)

	var to_node = _get_editor_node(to_path)
	if not to_node:
		return _send_error(client_id, "Target node not found: %s" % to_path, command_id)

	if not from_node.has_signal(signal_name):
		return _send_error(client_id,
			"Node %s has no signal '%s'" % [from_path, signal_name], command_id)

	var callable := Callable(to_node, method_name)
	if not from_node.is_connected(signal_name, callable):
		return _send_error(client_id,
			"%s.%s is not connected to %s.%s" % [from_path, signal_name, to_path, method_name],
			command_id)

	from_node.disconnect(signal_name, callable)

	_mark_scene_modified()
	_send_success(client_id, {
		"from_node_path": from_path,
		"signal_name": signal_name,
		"to_node_path": to_path,
		"method_name": method_name,
		"disconnected": true,
	}, command_id)
