@tool
class_name MCPCommandHandler
extends Node

var _websocket_server
var _command_processors = []

func _ready():
	print("Command handler initializing...")
	await get_tree().process_frame
	_websocket_server = get_parent()
	print("WebSocket server reference set: ", _websocket_server)
	
	# Initialize command processors
	_initialize_command_processors()
	
	print("Command handler initialized and ready to process commands")

func _initialize_command_processors():
	# One list, not four. Registering a processor used to mean adding it to a
	# constructor list, a server-reference list, an append list and an
	# add_child list -- miss any one and the processor is silently inert.
	var processors := [
		MCPNodeCommands.new(),
		MCPScriptCommands.new(),
		MCPSceneCommands.new(),
		MCPProjectCommands.new(),
		MCPEditorCommands.new(),
		MCPEditorScriptCommands.new(),
		MCPPlaybackCommands.new(),
		MCPProjectConfigCommands.new(),
		MCPTileMapCommands.new(),
		MCPNavigationCommands.new(),
		MCPParticleCommands.new(),
		MCPEnvironmentCommands.new(),
		MCPAnimationTreeCommands.new(),
		MCPSkeletonCommands.new(),
		MCPThemeCommands.new(),
		MCPTweenCommands.new(),
		MCPPathCommands.new(),
		MCPMeshCommands.new(),
		MCPAnimationCommands.new(),
		MCPMaterialCommands.new(),
		MCPImportCommands.new(),
		MCPSignalCommands.new(),
		MCPCaptureCommands.new(),
		MCPGroupCommands.new(),
	]

	for processor in processors:
		processor._websocket_server = _websocket_server
		_command_processors.append(processor)
		add_child(processor)

	print("Registered %d command processors" % processors.size())

func _handle_command(client_id: int, command: Dictionary) -> void:
	var command_type = command.get("type", "")
	var params = command.get("params", {})
	var command_id = command.get("commandId", "")
	
	print("Processing command: %s" % command_type)
	
	# Try each processor until one handles the command
	for processor in _command_processors:
		if processor.process_command(client_id, command_type, params, command_id):
			return
	
	# If no processor handled the command, send an error
	_send_error(client_id, "Unknown command: %s" % command_type, command_id)

func _send_error(client_id: int, message: String, command_id: String) -> void:
	var response = {
		"status": "error",
		"message": message
	}
	
	if not command_id.is_empty():
		response["commandId"] = command_id
	
	_websocket_server.send_response(client_id, response)
	print("Error: %s" % message)
