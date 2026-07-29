@tool
class_name MCPAnimationTreeCommands
extends MCPBaseCommandProcessor

## Command processor for AnimationTree operations

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"configure_animation_tree":
			_configure_animation_tree(client_id, params, command_id)
			return true
		"add_animation_tree_node":
			_add_animation_tree_node(client_id, params, command_id)
			return true
		"connect_animation_tree_nodes":
			_connect_animation_tree_nodes(client_id, params, command_id)
			return true
		"set_animation_tree_parameter":
			_set_animation_tree_parameter(client_id, params, command_id)
			return true
		"get_animation_tree_parameter":
			_get_animation_tree_parameter(client_id, params, command_id)
			return true
		"add_state_machine_transition":
			_add_state_machine_transition(client_id, params, command_id)
			return true
		"get_animation_tree_info":
			_get_animation_tree_info(client_id, params, command_id)
			return true
	return false

func _configure_animation_tree(client_id: int, params: Dictionary, command_id: String) -> void:
	var tree_path = params.get("tree_path", "")
	var node = _get_editor_node(tree_path)
	if not node:
		return _send_error(client_id, "AnimationTree not found: %s" % tree_path, command_id)
	if node.get_class() != "AnimationTree":
		return _send_error(client_id, "Node is not an AnimationTree: %s" % node.get_class(), command_id)

	if params.has("animation_player_path"):
		node.anim_player = params["animation_player_path"]
	if params.has("active"):
		node.active = params["active"]

	if params.has("root_node_type"):
		var root_type = params["root_node_type"]
		var root_node: AnimationNode
		match root_type:
			"blend_tree":
				root_node = AnimationNodeBlendTree.new()
			"state_machine":
				root_node = AnimationNodeStateMachine.new()
			"animation":
				root_node = AnimationNodeAnimation.new()
			"blend_space_1d":
				root_node = AnimationNodeBlendSpace1D.new()
			"blend_space_2d":
				root_node = AnimationNodeBlendSpace2D.new()
			_:
				return _send_error(client_id, "Unknown root node type: %s" % root_type, command_id)
		node.tree_root = root_node

	_mark_scene_modified()
	_send_success(client_id, {"message": "AnimationTree configured", "tree_path": tree_path}, command_id)

func _add_animation_tree_node(client_id: int, params: Dictionary, command_id: String) -> void:
	var tree_path = params.get("tree_path", "")
	var node = _get_editor_node(tree_path)
	if not node or node.get_class() != "AnimationTree":
		return _send_error(client_id, "AnimationTree not found: %s" % tree_path, command_id)

	if not node.tree_root:
		return _send_error(client_id, "AnimationTree has no root node. Use configure_animation_tree first.", command_id)

	var node_type = params.get("node_type", "animation")
	var node_name = params.get("node_name", "")
	var position = Vector2(params.get("position_x", 0.0), params.get("position_y", 0.0))

	var new_node: AnimationNode
	match node_type:
		"animation":
			new_node = AnimationNodeAnimation.new()
			if params.has("animation_name"):
				new_node.animation = params["animation_name"]
		"blend2":
			new_node = AnimationNodeBlend2.new()
		"blend3":
			new_node = AnimationNodeBlend3.new()
		"state_machine":
			new_node = AnimationNodeStateMachine.new()
		"blend_space_1d":
			new_node = AnimationNodeBlendSpace1D.new()
		"blend_space_2d":
			new_node = AnimationNodeBlendSpace2D.new()
		"time_scale":
			new_node = AnimationNodeTimeScale.new()
		"transition":
			new_node = AnimationNodeTransition.new()
		_:
			return _send_error(client_id, "Unknown node type: %s" % node_type, command_id)

	var root = node.tree_root
	if root is AnimationNodeBlendTree:
		root.add_node(node_name, new_node, position)
	elif root is AnimationNodeStateMachine:
		root.add_node(node_name, new_node, position)
	else:
		return _send_error(client_id, "Root node does not support adding child nodes", command_id)

	_mark_scene_modified()
	_send_success(client_id, {"message": "Animation tree node added", "node_name": node_name, "node_type": node_type}, command_id)

func _connect_animation_tree_nodes(client_id: int, params: Dictionary, command_id: String) -> void:
	var tree_path = params.get("tree_path", "")
	var node = _get_editor_node(tree_path)
	if not node or node.get_class() != "AnimationTree":
		return _send_error(client_id, "AnimationTree not found: %s" % tree_path, command_id)

	if not node.tree_root or not node.tree_root is AnimationNodeBlendTree:
		return _send_error(client_id, "AnimationTree root must be a BlendTree for connecting nodes", command_id)

	var root: AnimationNodeBlendTree = node.tree_root
	var from_node = params.get("from_node", "")
	var to_node = params.get("to_node", "")
	var to_input = params.get("to_input", 0)

	root.connect_node(to_node, to_input, from_node)
	_mark_scene_modified()
	_send_success(client_id, {"message": "Nodes connected", "from": from_node, "to": to_node, "input": to_input}, command_id)

func _set_animation_tree_parameter(client_id: int, params: Dictionary, command_id: String) -> void:
	var tree_path = params.get("tree_path", "")
	var node = _get_editor_node(tree_path)
	if not node or node.get_class() != "AnimationTree":
		return _send_error(client_id, "AnimationTree not found: %s" % tree_path, command_id)

	var parameter = params.get("parameter", "")
	var value = params.get("value")

	node.set(parameter, value)
	_mark_scene_modified()
	_send_success(client_id, {"message": "Parameter set", "parameter": parameter, "value": value}, command_id)

func _get_animation_tree_parameter(client_id: int, params: Dictionary, command_id: String) -> void:
	var tree_path = params.get("tree_path", "")
	var node = _get_editor_node(tree_path)
	if not node or node.get_class() != "AnimationTree":
		return _send_error(client_id, "AnimationTree not found: %s" % tree_path, command_id)

	var parameter = params.get("parameter", "")
	var value = node.get(parameter)
	_send_success(client_id, {"parameter": parameter, "value": str(value)}, command_id)

func _add_state_machine_transition(client_id: int, params: Dictionary, command_id: String) -> void:
	var tree_path = params.get("tree_path", "")
	var node = _get_editor_node(tree_path)
	if not node or node.get_class() != "AnimationTree":
		return _send_error(client_id, "AnimationTree not found: %s" % tree_path, command_id)

	var from_state = params.get("from_state", "")
	var to_state = params.get("to_state", "")
	var switch_mode_str = params.get("switch_mode", "immediate")
	var auto_advance = params.get("auto_advance", false)

	# Get the state machine (root or nested)
	var sm: AnimationNodeStateMachine
	var sm_path = params.get("state_machine_path", "")

	if sm_path.is_empty():
		if node.tree_root is AnimationNodeStateMachine:
			sm = node.tree_root
		else:
			return _send_error(client_id, "Root is not a StateMachine. Provide state_machine_path.", command_id)
	else:
		if node.tree_root is AnimationNodeBlendTree:
			var bt: AnimationNodeBlendTree = node.tree_root
			var sm_node = bt.get_node(sm_path)
			if sm_node is AnimationNodeStateMachine:
				sm = sm_node
			else:
				return _send_error(client_id, "Node at path is not a StateMachine", command_id)
		else:
			return _send_error(client_id, "Cannot find state machine at path", command_id)

	var transition = AnimationNodeStateMachineTransition.new()
	var switch_mode_map = {
		"immediate": AnimationNodeStateMachineTransition.SWITCH_MODE_IMMEDIATE,
		"sync": AnimationNodeStateMachineTransition.SWITCH_MODE_SYNC,
		"at_end": AnimationNodeStateMachineTransition.SWITCH_MODE_AT_END
	}
	if switch_mode_str in switch_mode_map:
		transition.switch_mode = switch_mode_map[switch_mode_str]
	transition.advance_mode = AnimationNodeStateMachineTransition.ADVANCE_MODE_AUTO if auto_advance else AnimationNodeStateMachineTransition.ADVANCE_MODE_ENABLED

	sm.add_transition(from_state, to_state, transition)
	_mark_scene_modified()
	_send_success(client_id, {"message": "Transition added", "from": from_state, "to": to_state}, command_id)

func _get_animation_tree_info(client_id: int, params: Dictionary, command_id: String) -> void:
	var tree_path = params.get("tree_path", "")
	var node = _get_editor_node(tree_path)
	if not node or node.get_class() != "AnimationTree":
		return _send_error(client_id, "AnimationTree not found: %s" % tree_path, command_id)

	var info = {
		"tree_path": tree_path,
		"active": node.active,
		"anim_player": str(node.anim_player),
		"has_root": node.tree_root != null
	}

	if node.tree_root:
		info["root_type"] = node.tree_root.get_class()
		if node.tree_root is AnimationNodeStateMachine:
			var sm: AnimationNodeStateMachine = node.tree_root
			info["states"] = Array(sm.get_node_list())
		elif node.tree_root is AnimationNodeBlendTree:
			var bt: AnimationNodeBlendTree = node.tree_root
			info["nodes"] = Array(bt.get_node_list())

	_send_success(client_id, info, command_id)
