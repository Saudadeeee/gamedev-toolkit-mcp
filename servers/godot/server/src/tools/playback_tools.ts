import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { MCPTool, CommandResult } from '../utils/types.js';

/**
 * Type definitions for playback tool parameters
 */
interface PlayCustomSceneParams {
  scene_path: string;
}

interface StopPlayingSceneParams {
  // No parameters needed
}

/**
 * Definition for playback tools - operations that control scene playback in the editor
 */
export const playbackTools: MCPTool[] = [
  {
    name: 'play_main_scene',
    description: 'Play the project main scene (equivalent to pressing F5 in Godot)',
    parameters: z.object({}), // No parameters needed
    execute: async (): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('play_main_scene', {});
        return result.message || 'Started playing main scene';
      } catch (error) {
        throw new Error(`Failed to play main scene: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'play_current_scene',
    description: 'Play the currently edited scene (equivalent to pressing F6 in Godot)',
    parameters: z.object({}), // No parameters needed
    execute: async (): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('play_current_scene', {});
        return result.message || 'Started playing current scene';
      } catch (error) {
        throw new Error(`Failed to play current scene: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'play_custom_scene',
    description: 'Play a specific scene by path',
    parameters: z.object({
      scene_path: z.string()
        .describe('Path to the scene file to play (e.g., "res://levels/level1.tscn")'),
    }),
    execute: async ({ scene_path }: PlayCustomSceneParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('play_custom_scene', {
          scene_path,
        });

        return result.message || `Started playing scene: ${scene_path}`;
      } catch (error) {
        throw new Error(`Failed to play custom scene: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'stop_playing_scene',
    description: 'Stop the currently playing scene (equivalent to pressing F8 in Godot)',
    parameters: z.object({}), // No parameters needed
    execute: async (): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('stop_playing_scene', {});
        return result.message || 'Stopped playing scene';
      } catch (error) {
        throw new Error(`Failed to stop playing scene: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'get_play_status',
    description: 'Check if a scene is currently playing and get the playing scene path',
    parameters: z.object({}), // No parameters needed
    execute: async (): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('get_play_status', {});

        if (result.is_playing) {
          return `Scene is playing: ${result.playing_scene || 'unknown scene'}`;
        } else {
          return 'No scene is currently playing';
        }
      } catch (error) {
        throw new Error(`Failed to get play status: ${(error as Error).message}`);
      }
    },
  },
];
