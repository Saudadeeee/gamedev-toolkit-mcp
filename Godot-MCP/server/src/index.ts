import { FastMCP } from 'fastmcp';
import { nodeTools } from './tools/node_tools.js';
import { scriptTools } from './tools/script_tools.js';
import { sceneTools } from './tools/scene_tools.js';
import { editorTools } from './tools/editor_tools.js';
import { playbackTools } from './tools/playback_tools.js';
import { projectConfigTools } from './tools/project_config_tools.js';
import { tilemapTools } from './tools/tilemap_tools.js';
import { animationTools } from './tools/animation_tools.js';
import { materialTools } from './tools/material_tools.js';
import { importTools } from './tools/import_tools.js';
import { navigationTools } from './tools/navigation_tools.js';
import { particleTools } from './tools/particle_tools.js';
import { environmentTools } from './tools/environment_tools.js';
import { animationTreeTools } from './tools/animation_tree_tools.js';
import { skeletonTools } from './tools/skeleton_tools.js';
import { themeTools } from './tools/theme_tools.js';
import { tweenTools } from './tools/tween_tools.js';
import { pathTools } from './tools/path_tools.js';
import { meshTools } from './tools/mesh_tools.js';
import { systemInfoTools } from './tools/system_info_tools.js';
import { getGodotConnection } from './utils/godot_connection.js';

// Import resources
import {
  sceneListResource,
  sceneStructureResource
} from './resources/scene_resources.js';
import {
  scriptResource,
  scriptListResource,
  scriptMetadataResource
} from './resources/script_resources.js';
import {
  projectStructureResource,
  projectSettingsResource,
  projectResourcesResource
} from './resources/project_resources.js';
import {
  editorStateResource,
  selectedNodeResource,
  currentScriptResource
} from './resources/editor_resources.js';
import {
  playbackStateResource
} from './resources/playback_resources.js';
import {
  inputMapResource,
  audioBusLayoutResource,
  allProjectSettingsResource
} from './resources/project_config_resources.js';
import {
  tilemapDataResource,
  gridmapDataResource
} from './resources/tilemap_resources.js';
import {
  animationListResource,
  animationDataResource
} from './resources/animation_resources.js';
import {
  importSettingsResource
} from './resources/import_resources.js';
import {
  materialResource
} from './resources/material_resources.js';

/**
 * Main entry point for the Godot MCP server
 */
async function main() {
  console.error('Starting Godot MCP server...');

  // Create FastMCP instance
  const server = new FastMCP({
    name: 'GodotMCP',
    version: '1.0.0',
  });

  // Register all tools
  [
    ...nodeTools,
    ...scriptTools,
    ...sceneTools,
    ...editorTools,
    ...playbackTools,
    ...projectConfigTools,
    ...tilemapTools,
    ...animationTools,
    ...materialTools,
    ...importTools,
    ...navigationTools,
    ...particleTools,
    ...environmentTools,
    ...animationTreeTools,
    ...skeletonTools,
    ...themeTools,
    ...tweenTools,
    ...pathTools,
    ...meshTools,
    ...systemInfoTools,
  ].forEach(tool => {
    server.addTool(tool);
  });

  // Register all resources
  server.addResource(sceneListResource);
  server.addResource(scriptListResource);
  server.addResource(projectStructureResource);
  server.addResource(projectSettingsResource);
  server.addResource(projectResourcesResource);
  server.addResource(editorStateResource);
  server.addResource(selectedNodeResource);
  server.addResource(currentScriptResource);
  server.addResource(sceneStructureResource);
  server.addResource(scriptResource);
  server.addResource(scriptMetadataResource);
  server.addResource(playbackStateResource);
  server.addResource(inputMapResource);
  server.addResource(audioBusLayoutResource);
  server.addResource(allProjectSettingsResource);
  server.addResource(tilemapDataResource);
  server.addResource(gridmapDataResource);
  server.addResource(animationListResource);
  server.addResource(animationDataResource);
  server.addResource(importSettingsResource);
  server.addResource(materialResource);

  // Try to connect to Godot
  try {
    const godot = getGodotConnection();
    await godot.connect();
    console.error('Successfully connected to Godot WebSocket server');
  } catch (error) {
    const err = error as Error;
    console.warn(`Could not connect to Godot: ${err.message}`);
    console.warn('Will retry connection when commands are executed');
  }

  // Start the server
  server.start({
    transportType: 'stdio',
  });

  console.error('Godot MCP server started');

  // Handle cleanup
  const cleanup = () => {
    console.error('Shutting down Godot MCP server...');
    const godot = getGodotConnection();
    godot.disconnect();
    process.exit(0);
  };

  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);
}

// Start the server
main().catch(error => {
  console.error('Failed to start Godot MCP server:', error);
  process.exit(1);
});
