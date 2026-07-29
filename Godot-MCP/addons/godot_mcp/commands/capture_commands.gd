@tool
class_name MCPCaptureCommands
extends MCPBaseCommandProcessor

# Visual feedback. Without this an AI can build a scene and never see it --
# it has to infer the result from node properties, which is exactly how
# invisible, mispositioned or z-order-wrong nodes survive review.
#
# Rendering happens into an offscreen SubViewport rather than by running the
# game: it is deterministic, needs no play session, and works on the scene as
# currently edited.

const _MAX_DIMENSION := 4096
const _DEFAULT_DIMENSION := 512

func process_command(client_id: int, command_type: String, params: Dictionary, command_id: String) -> bool:
	match command_type:
		"capture_scene_render":
			_capture_scene_render(client_id, params, command_id)
			return true
		"capture_editor_viewport":
			_capture_editor_viewport(client_id, params, command_id)
			return true
	return false

# Resolve where to write, defaulting to a temp file inside the project so the
# path is always readable by the caller.
func _resolve_output(path: String) -> String:
	if path.is_empty():
		return "res://.godot/mcp_capture.png"
	if not path.begins_with("res://") and not path.is_absolute_path():
		return "res://" + path
	return path

func _finish(client_id: int, command_id: String, image: Image, output_path: String,
		include_base64: bool, extra: Dictionary) -> void:
	if image == null or image.is_empty():
		return _send_error(client_id, "Render produced an empty image", command_id)

	var absolute := ProjectSettings.globalize_path(output_path)
	var dir := absolute.get_base_dir()
	if not DirAccess.dir_exists_absolute(dir):
		DirAccess.make_dir_recursive_absolute(dir)

	var err := image.save_png(output_path)
	if err != OK:
		return _send_error(client_id, "Failed to save PNG to %s (error %d)" % [output_path, err], command_id)

	var result := {
		"output_path": output_path,
		"absolute_path": absolute,
		"width": image.get_width(),
		"height": image.get_height(),
	}
	for key in extra:
		result[key] = extra[key]

	if include_base64:
		var buffer := image.save_png_to_buffer()
		result["base64_png"] = Marshalls.raw_to_base64(buffer)
		result["byte_size"] = buffer.size()

	_send_success(client_id, result, command_id)

func _has_visible_control(root: Node) -> bool:
	var stack: Array[Node] = [root]
	while not stack.is_empty():
		var node: Node = stack.pop_back()
		if node is Control and node.visible:
			return true
		for child in node.get_children():
			stack.append(child)
	return false

func _capture_scene_render(client_id: int, params: Dictionary, command_id: String) -> void:
	var scene_path = params.get("scene_path", "")
	var width = int(params.get("width", _DEFAULT_DIMENSION))
	var height = int(params.get("height", _DEFAULT_DIMENSION))
	var transparent = bool(params.get("transparent", true))
	var output_path = _resolve_output(str(params.get("output_path", "")))
	var include_base64 = bool(params.get("include_base64", true))
	var fit_content = bool(params.get("fit_content", true))
	var padding = float(params.get("padding", 0.15))
	var max_zoom = float(params.get("max_zoom", 16.0))
	var nearest_filter = bool(params.get("nearest_filter", true))

	if width < 1 or height < 1 or width > _MAX_DIMENSION or height > _MAX_DIMENSION:
		return _send_error(client_id, "width and height must be between 1 and %d" % _MAX_DIMENSION, command_id)

	var plugin = Engine.get_meta("GodotMCPPlugin")
	if not plugin:
		return _send_error(client_id, "GodotMCPPlugin not found in Engine metadata", command_id)

	var instance: Node = null
	var source := ""

	if scene_path.is_empty():
		# Duplicate the edited scene so the capture cannot disturb what the
		# user has open.
		var edited = plugin.get_editor_interface().get_edited_scene_root()
		if not edited:
			return _send_error(client_id, "No scene is currently open and no scene_path was given", command_id)
		source = edited.scene_file_path
		instance = edited.duplicate()
	else:
		if not scene_path.begins_with("res://"):
			scene_path = "res://" + scene_path
		if not ResourceLoader.exists(scene_path):
			return _send_error(client_id, "Scene not found: %s" % scene_path, command_id)
		var packed = ResourceLoader.load(scene_path)
		if not packed is PackedScene:
			return _send_error(client_id, "Not a PackedScene: %s" % scene_path, command_id)
		source = scene_path
		instance = packed.instantiate()

	if not instance:
		return _send_error(client_id, "Failed to instantiate scene", command_id)

	var viewport := SubViewport.new()
	viewport.size = Vector2i(width, height)
	# The framing pass needs a transparent background to tell content from
	# empty space, so force it on and restore the caller's choice afterwards.
	viewport.transparent_bg = true if fit_content else transparent
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	# A SubViewport does not inherit the project's texture filter. Left at the
	# default, framing a 24px sprite up to 256px renders it blurred, which
	# defeats the point of looking at pixel art.
	if nearest_filter:
		viewport.canvas_item_default_texture_filter = \
			Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	viewport.add_child(instance)
	plugin.add_child(viewport)

	# Two frames: the first lets the scene enter the tree and lay itself out,
	# the second renders it. Reading after a single frame yields blank output.
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw

	var texture := viewport.get_texture()
	var image: Image = texture.get_image() if texture else null
	var framing := {}

	# Without a camera the viewport shows the world from (0,0) at 1:1, so a
	# small sprite lands as a speck in the corner and the capture is useless
	# even though it technically succeeded. Measure what was drawn, then frame
	# it and render again.
	if fit_content and image != null and not image.is_empty():
		var used := image.get_used_rect()
		if used.size.x > 0 and used.size.y > 0:
			var camera := Camera2D.new()
			camera.position = Vector2(used.position) + Vector2(used.size) * 0.5
			# Pass 1 has no camera, so viewport pixels map 1:1 to world units
			# and the used rect is already in world space.
			var margin := 1.0 + maxf(0.0, padding)
			var fit := minf(
				float(width) / (float(used.size.x) * margin),
				float(height) / (float(used.size.y) * margin))
			# Never magnify past the requested zoom cap, and never shrink below
			# 1:1 unless the content genuinely does not fit.
			fit = clampf(fit, 0.01, maxf(1.0, max_zoom))
			camera.zoom = Vector2(fit, fit)
			camera.enabled = true
			viewport.add_child(camera)
			camera.make_current()

			viewport.transparent_bg = transparent
			await RenderingServer.frame_post_draw
			await RenderingServer.frame_post_draw

			texture = viewport.get_texture()
			image = texture.get_image() if texture else image
			framing = {
				"framed": true,
				"content_rect": {
					"x": used.position.x, "y": used.position.y,
					"width": used.size.x, "height": used.size.y,
				},
				"zoom": fit,
			}

			# Camera2D moves the world, not the GUI layer. A scene mixing
			# Node2D art with Control nodes renders the Controls at their
			# original screen position and size while the art is zoomed, which
			# reads as a bug in the capture unless it is stated.
			if _has_visible_control(instance):
				framing["warning"] = (
					"Scene contains Control nodes. Camera2D does not affect the GUI layer, "
					+ "so Controls stay at screen scale while Node2D content is framed. "
					+ "Pass fit_content=false to see both at true scale.")
		else:
			framing = {"framed": false, "reason": "nothing was drawn"}

	viewport.queue_free()

	var extra := {"source": source, "mode": "scene_render"}
	for key in framing:
		extra[key] = framing[key]

	_finish(client_id, command_id, image, output_path, include_base64, extra)

func _capture_editor_viewport(client_id: int, params: Dictionary, command_id: String) -> void:
	var output_path = _resolve_output(str(params.get("output_path", "")))
	var include_base64 = bool(params.get("include_base64", true))
	var dimension = str(params.get("dimension", "2d"))

	if dimension != "2d" and dimension != "3d":
		return _send_error(client_id, "dimension must be '2d' or '3d'", command_id)

	var plugin = Engine.get_meta("GodotMCPPlugin")
	if not plugin:
		return _send_error(client_id, "GodotMCPPlugin not found in Engine metadata", command_id)

	var editor_interface = plugin.get_editor_interface()
	var viewport: Viewport = null

	if dimension == "2d":
		if editor_interface.has_method("get_editor_viewport_2d"):
			viewport = editor_interface.get_editor_viewport_2d()
	else:
		if editor_interface.has_method("get_editor_viewport_3d"):
			viewport = editor_interface.get_editor_viewport_3d(0)

	if not viewport:
		return _send_error(client_id,
			"Editor viewport unavailable; this Godot build does not expose it. " +
			"Use capture_scene_render instead.", command_id)

	await RenderingServer.frame_post_draw

	var texture := viewport.get_texture()
	var image: Image = texture.get_image() if texture else null

	_finish(client_id, command_id, image, output_path, include_base64, {
		"mode": "editor_viewport",
		"dimension": dimension,
	})
