@tool
class_name MCPSkeletonCommands
extends MCPBaseCommandProcessor

## Command processor for Skeleton and IK operations

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"get_skeleton_info":
			_get_skeleton_info(client_id, params, command_id)
			return true
		"set_bone_pose_rotation":
			_set_bone_pose_rotation(client_id, params, command_id)
			return true
		"set_bone_pose_position":
			_set_bone_pose_position(client_id, params, command_id)
			return true
		"set_bone_pose_scale":
			_set_bone_pose_scale(client_id, params, command_id)
			return true
		"get_bone_pose":
			_get_bone_pose(client_id, params, command_id)
			return true
		"configure_skeleton_ik":
			_configure_skeleton_ik(client_id, params, command_id)
			return true
		"start_skeleton_ik":
			_start_skeleton_ik(client_id, params, command_id)
			return true
		"reset_bone_poses":
			_reset_bone_poses(client_id, params, command_id)
			return true
	return false

func _get_skeleton_info(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node:
		return _send_error(client_id, "Skeleton not found: %s" % node_path, command_id)

	var info = {"node_path": node_path, "node_class": node.get_class()}

	if node.get_class() == "Skeleton3D":
		info["bone_count"] = node.get_bone_count()
		var bones = []
		for i in range(node.get_bone_count()):
			bones.append({
				"index": i,
				"name": node.get_bone_name(i),
				"parent": node.get_bone_parent(i)
			})
		info["bones"] = bones
	elif node.get_class() == "Skeleton2D":
		info["bone_count"] = node.get_bone_count()
		var bones = []
		for i in range(node.get_bone_count()):
			var bone = node.get_bone(i)
			if bone:
				bones.append({"index": i, "name": bone.name})
		info["bones"] = bones
	else:
		return _send_error(client_id, "Node is not a Skeleton: %s" % node.get_class(), command_id)

	_send_success(client_id, info, command_id)

func _set_bone_pose_rotation(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node or node.get_class() != "Skeleton3D":
		return _send_error(client_id, "Skeleton3D not found: %s" % node_path, command_id)

	var bone_name = params.get("bone_name", "")
	var bone_idx = node.find_bone(bone_name)
	if bone_idx == -1:
		return _send_error(client_id, "Bone not found: %s" % bone_name, command_id)

	var quat = Quaternion(params.get("x", 0.0), params.get("y", 0.0), params.get("z", 0.0), params.get("w", 1.0))
	node.set_bone_pose_rotation(bone_idx, quat)
	_mark_scene_modified()
	_send_success(client_id, {"message": "Bone rotation set", "bone_name": bone_name}, command_id)

func _set_bone_pose_position(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node or node.get_class() != "Skeleton3D":
		return _send_error(client_id, "Skeleton3D not found: %s" % node_path, command_id)

	var bone_name = params.get("bone_name", "")
	var bone_idx = node.find_bone(bone_name)
	if bone_idx == -1:
		return _send_error(client_id, "Bone not found: %s" % bone_name, command_id)

	var pos = Vector3(params.get("x", 0.0), params.get("y", 0.0), params.get("z", 0.0))
	node.set_bone_pose_position(bone_idx, pos)
	_mark_scene_modified()
	_send_success(client_id, {"message": "Bone position set", "bone_name": bone_name}, command_id)

func _set_bone_pose_scale(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node or node.get_class() != "Skeleton3D":
		return _send_error(client_id, "Skeleton3D not found: %s" % node_path, command_id)

	var bone_name = params.get("bone_name", "")
	var bone_idx = node.find_bone(bone_name)
	if bone_idx == -1:
		return _send_error(client_id, "Bone not found: %s" % bone_name, command_id)

	var scale = Vector3(params.get("x", 1.0), params.get("y", 1.0), params.get("z", 1.0))
	node.set_bone_pose_scale(bone_idx, scale)
	_mark_scene_modified()
	_send_success(client_id, {"message": "Bone scale set", "bone_name": bone_name}, command_id)

func _get_bone_pose(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node or node.get_class() != "Skeleton3D":
		return _send_error(client_id, "Skeleton3D not found: %s" % node_path, command_id)

	var bone_name = params.get("bone_name", "")
	var bone_idx = node.find_bone(bone_name)
	if bone_idx == -1:
		return _send_error(client_id, "Bone not found: %s" % bone_name, command_id)

	var pos = node.get_bone_pose_position(bone_idx)
	var rot = node.get_bone_pose_rotation(bone_idx)
	var scale = node.get_bone_pose_scale(bone_idx)

	_send_success(client_id, {
		"bone_name": bone_name,
		"bone_index": bone_idx,
		"position": [pos.x, pos.y, pos.z],
		"rotation": [rot.x, rot.y, rot.z, rot.w],
		"scale": [scale.x, scale.y, scale.z]
	}, command_id)

func _configure_skeleton_ik(client_id: int, params: Dictionary, command_id: String) -> void:
	var ik_path = params.get("ik_node_path", "")
	var node = _get_editor_node(ik_path)
	if not node:
		return _send_error(client_id, "SkeletonIK3D not found: %s" % ik_path, command_id)
	if node.get_class() != "SkeletonIK3D":
		return _send_error(client_id, "Node is not SkeletonIK3D: %s" % node.get_class(), command_id)

	if params.has("target_node_path"):
		node.target_node = params["target_node_path"]
	if params.has("tip_bone"):
		node.tip_bone = params["tip_bone"]
	if params.has("root_bone"):
		node.root_bone = params["root_bone"]
	if params.has("min_distance"):
		node.min_distance = params["min_distance"]
	if params.has("max_iterations"):
		node.max_iterations = params["max_iterations"]
	if params.has("interpolation"):
		node.interpolation = params["interpolation"]

	_mark_scene_modified()
	_send_success(client_id, {"message": "SkeletonIK configured", "ik_path": ik_path}, command_id)

func _start_skeleton_ik(client_id: int, params: Dictionary, command_id: String) -> void:
	var ik_path = params.get("ik_node_path", "")
	var node = _get_editor_node(ik_path)
	if not node or node.get_class() != "SkeletonIK3D":
		return _send_error(client_id, "SkeletonIK3D not found: %s" % ik_path, command_id)

	var start = params.get("start", true)
	if start:
		node.start()
	else:
		node.stop()

	_send_success(client_id, {"message": "SkeletonIK %s" % ("started" if start else "stopped")}, command_id)

func _reset_bone_poses(client_id: int, params: Dictionary, command_id: String) -> void:
	var node_path = params.get("node_path", "")
	var node = _get_editor_node(node_path)
	if not node or node.get_class() != "Skeleton3D":
		return _send_error(client_id, "Skeleton3D not found: %s" % node_path, command_id)

	for i in range(node.get_bone_count()):
		node.reset_bone_pose(i)

	_mark_scene_modified()
	_send_success(client_id, {"message": "All bone poses reset to rest", "bone_count": node.get_bone_count()}, command_id)
