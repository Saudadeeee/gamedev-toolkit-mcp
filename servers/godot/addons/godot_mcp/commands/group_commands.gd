@tool
class_name MCPGroupCommands
extends MCPBaseCommandProcessor

# Node groups.
#
# Group membership is how a running game finds "all enemies" or "all pickups"
# without holding references. It has to be set persistently or it exists only
# until the scene is reloaded.
#
# Input-map commands are deliberately absent: project_config_commands.gd
# already implements add_input_action / add_input_event / remove_input_action,
# and a second handler for the same command name would shadow it.

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"add_node_to_group":
			_add_node_to_group(client_id, params, command_id)
			return true
		"remove_node_from_group":
			_remove_node_from_group(client_id, params, command_id)
			return true
		"list_nodes_in_group":
			_list_nodes_in_group(client_id, params, command_id)
			return true
	return false

func _add_node_to_group(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var group_name = str(params.get("group_name", "")).strip_edges()

	if node_path.is_empty():
		return _send_error(client_id, "Node path cannot be empty", command_id)
	if group_name.is_empty():
		return _send_error(client_id, "group_name cannot be empty", command_id)

	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	if node.is_in_group(group_name):
		return _send_error(client_id,
			"Node %s is already in group '%s'" % [node_path, group_name], command_id)

	# persistent=true is what writes the group into the .tscn; without it the
	# membership is runtime-only and disappears on reload.
	node.add_to_group(group_name, true)

	_mark_scene_modified()
	_send_success(client_id, {
		"node_path": node_path,
		"group_name": group_name,
		"groups": node.get_groups(),
	}, command_id)

func _remove_node_from_group(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var group_name = str(params.get("group_name", "")).strip_edges()

	if node_path.is_empty():
		return _send_error(client_id, "Node path cannot be empty", command_id)
	if group_name.is_empty():
		return _send_error(client_id, "group_name cannot be empty", command_id)

	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Node not found: %s" % node_path, command_id)

	if not node.is_in_group(group_name):
		return _send_error(client_id,
			"Node %s is not in group '%s'" % [node_path, group_name], command_id)

	node.remove_from_group(group_name)

	_mark_scene_modified()
	_send_success(client_id, {
		"node_path": node_path,
		"group_name": group_name,
		"groups": node.get_groups(),
	}, command_id)

func _list_nodes_in_group(client_id: int, params: Dictionary, command_id: String) -> void:
	var group_name = str(params.get("group_name", "")).strip_edges()

	var plugin = Engine.get_meta("GodotMCPPlugin")
	if not plugin:
		return _send_error(client_id, "GodotMCPPlugin not found in Engine metadata", command_id)

	var root = plugin.get_editor_interface().get_edited_scene_root()
	if not root:
		return _send_error(client_id, "No scene is currently open", command_id)

	# Walking the edited scene rather than get_tree().get_nodes_in_group():
	# at edit time the scene is not running, so the SceneTree group index does
	# not describe the scene the user is looking at.
	var matches := []
	var all_groups := {}
	var stack := [root]
	while not stack.is_empty():
		var node: Node = stack.pop_back()
		for group in node.get_groups():
			var name := str(group)
			# Godot uses "_"-prefixed internal groups for its own bookkeeping.
			if name.begins_with("_"):
				continue
			all_groups[name] = int(all_groups.get(name, 0)) + 1
			if group_name.is_empty() or name == group_name:
				matches.append({
					"node_path": str(root.get_path_to(node)),
					"name": node.name,
					"type": node.get_class(),
					"group": name,
				})
		for child in node.get_children():
			stack.append(child)

	_send_success(client_id, {
		"group_name": group_name,
		"nodes": matches,
		"all_groups": all_groups,
	}, command_id)
