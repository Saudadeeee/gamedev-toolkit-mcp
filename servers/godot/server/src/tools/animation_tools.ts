import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { MCPTool, CommandResult } from '../utils/types.js';

/**
 * Type definitions for Animation tool parameters
 */
interface CreateAnimationParams {
  animation_player_path: string;
  animation_name: string;
  length?: number;
}

interface DeleteAnimationParams {
  animation_player_path: string;
  animation_name: string;
}

interface ListAnimationsParams {
  animation_player_path: string;
}

interface AddAnimationTrackParams {
  animation_player_path: string;
  animation_name: string;
  track_type: 'value' | 'transform3d' | 'method' | 'bezier' | 'audio' | 'animation';
  target_path: string;
  position?: number;
}

interface RemoveAnimationTrackParams {
  animation_player_path: string;
  animation_name: string;
  track_index: number;
}

interface InsertAnimationKeyParams {
  animation_player_path: string;
  animation_name: string;
  track_index: number;
  time: number;
  value: any;
}

interface RemoveAnimationKeyParams {
  animation_player_path: string;
  animation_name: string;
  track_index: number;
  key_index: number;
}

interface GetAnimationDataParams {
  animation_player_path: string;
  animation_name: string;
}

interface PlayAnimationParams {
  animation_player_path: string;
  animation_name: string;
  custom_speed?: number;
  from_end?: boolean;
}

interface StopAnimationParams {
  animation_player_path: string;
  keep_state?: boolean;
}

/**
 * Definition for Animation System tools - operations for creating and manipulating animations
 */
export const animationTools: MCPTool[] = [
  {
    name: 'create_animation',
    description: 'Create a new animation in an AnimationPlayer',
    parameters: z.object({
      animation_player_path: z.string()
        .describe('Path to AnimationPlayer node'),
      animation_name: z.string()
        .describe('Animation name (e.g., "idle", "walk", "jump")'),
      length: z.number().default(1.0)
        .describe('Animation length in seconds'),
    }),
    execute: async (params: CreateAnimationParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('create_animation', params);
        return `Created animation "${params.animation_name}" with length ${params.length}s`;
      } catch (error) {
        throw new Error(`Failed to create animation: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'delete_animation',
    description: 'Delete an animation from an AnimationPlayer',
    parameters: z.object({
      animation_player_path: z.string()
        .describe('Path to AnimationPlayer node'),
      animation_name: z.string()
        .describe('Animation name to delete'),
    }),
    execute: async (params: DeleteAnimationParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('delete_animation', params);
        return `Deleted animation "${params.animation_name}"`;
      } catch (error) {
        throw new Error(`Failed to delete animation: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'list_animations',
    description: 'List all animations in an AnimationPlayer',
    parameters: z.object({
      animation_player_path: z.string()
        .describe('Path to AnimationPlayer node'),
    }),
    execute: async (params: ListAnimationsParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('list_animations', params);

        if (!result.animations || result.animations.length === 0) {
          return 'No animations found';
        }

        const animList = result.animations.map((anim: any) =>
          `- ${anim.name} (${anim.length}s, ${anim.track_count} tracks)`
        ).join('\n');

        return `Animations:\n${animList}`;
      } catch (error) {
        throw new Error(`Failed to list animations: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'add_animation_track',
    description: 'Add a track to an animation',
    parameters: z.object({
      animation_player_path: z.string()
        .describe('Path to AnimationPlayer node'),
      animation_name: z.string()
        .describe('Animation name'),
      track_type: z.enum(['value', 'transform3d', 'method', 'bezier', 'audio', 'animation'])
        .describe('Track type'),
      target_path: z.string()
        .describe('NodePath to target (e.g., ".:position", "Sprite2D:modulate")'),
      position: z.number().optional()
        .describe('Track position in list (default: add at end)'),
    }),
    execute: async (params: AddAnimationTrackParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('add_animation_track', params);
        return `Added ${params.track_type} track at index ${result.track_index} to "${params.animation_name}"`;
      } catch (error) {
        throw new Error(`Failed to add animation track: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'remove_animation_track',
    description: 'Remove a track from an animation',
    parameters: z.object({
      animation_player_path: z.string()
        .describe('Path to AnimationPlayer node'),
      animation_name: z.string()
        .describe('Animation name'),
      track_index: z.number()
        .describe('Track index to remove'),
    }),
    execute: async (params: RemoveAnimationTrackParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('remove_animation_track', params);
        return `Removed track ${params.track_index} from "${params.animation_name}"`;
      } catch (error) {
        throw new Error(`Failed to remove animation track: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'insert_animation_key',
    description: 'Insert a keyframe in an animation track',
    parameters: z.object({
      animation_player_path: z.string()
        .describe('Path to AnimationPlayer node'),
      animation_name: z.string()
        .describe('Animation name'),
      track_index: z.number()
        .describe('Track index'),
      time: z.number()
        .describe('Time in seconds for keyframe'),
      value: z.any()
        .describe('Keyframe value (depends on track type: Vector2, float, Color, etc.)'),
    }),
    execute: async (params: InsertAnimationKeyParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('insert_animation_key', params);
        return `Inserted keyframe at ${params.time}s in track ${params.track_index} (key index: ${result.key_index})`;
      } catch (error) {
        throw new Error(`Failed to insert animation key: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'remove_animation_key',
    description: 'Remove a keyframe from an animation track',
    parameters: z.object({
      animation_player_path: z.string()
        .describe('Path to AnimationPlayer node'),
      animation_name: z.string()
        .describe('Animation name'),
      track_index: z.number()
        .describe('Track index'),
      key_index: z.number()
        .describe('Key index to remove'),
    }),
    execute: async (params: RemoveAnimationKeyParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('remove_animation_key', params);
        return `Removed key ${params.key_index} from track ${params.track_index}`;
      } catch (error) {
        throw new Error(`Failed to remove animation key: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'get_animation_data',
    description: 'Get complete animation data including all tracks and keyframes',
    parameters: z.object({
      animation_player_path: z.string()
        .describe('Path to AnimationPlayer node'),
      animation_name: z.string()
        .describe('Animation name'),
    }),
    execute: async (params: GetAnimationDataParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('get_animation_data', params);

        return JSON.stringify(result, null, 2);
      } catch (error) {
        throw new Error(`Failed to get animation data: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'play_animation',
    description: 'Play an animation (for testing in editor)',
    parameters: z.object({
      animation_player_path: z.string()
        .describe('Path to AnimationPlayer node'),
      animation_name: z.string()
        .describe('Animation name to play'),
      custom_speed: z.number().default(1.0)
        .describe('Playback speed multiplier'),
      from_end: z.boolean().default(false)
        .describe('Play backwards from end'),
    }),
    execute: async (params: PlayAnimationParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('play_animation', params);
        return `Playing animation "${params.animation_name}" at ${params.custom_speed}x speed`;
      } catch (error) {
        throw new Error(`Failed to play animation: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'stop_animation',
    description: 'Stop the currently playing animation',
    parameters: z.object({
      animation_player_path: z.string()
        .describe('Path to AnimationPlayer node'),
      keep_state: z.boolean().default(false)
        .describe('Keep current animation state'),
    }),
    execute: async (params: StopAnimationParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('stop_animation', params);
        return 'Stopped animation playback';
      } catch (error) {
        throw new Error(`Failed to stop animation: ${(error as Error).message}`);
      }
    },
  },
];
