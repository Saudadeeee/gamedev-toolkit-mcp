import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { MCPTool, CommandResult } from '../utils/types.js';

/**
 * Type definitions for project configuration tool parameters
 */
interface SetProjectSettingParams {
  setting_name: string;
  value: any;
}

interface GetProjectSettingParams {
  setting_name: string;
  default_value?: any;
}

interface ListProjectSettingsParams {
  prefix?: string;
}

interface AddInputActionParams {
  action_name: string;
  deadzone?: number;
}

interface AddInputEventParams {
  action_name: string;
  event_type: 'key' | 'mouse_button' | 'joypad_button' | 'joypad_motion';
  keycode?: string;
  button_index?: number;
  axis?: number;
  axis_value?: number;
}

interface RemoveInputActionParams {
  action_name: string;
}

interface AddAudioBusParams {
  bus_name: string;
  position?: number;
}

interface SetBusVolumeParams {
  bus_index: number;
  volume_db: number;
}

interface AddBusEffectParams {
  bus_index: number;
  effect_type: 'reverb' | 'delay' | 'chorus' | 'distortion' | 'eq' | 'compressor' | 'limiter';
  position?: number;
}

interface SetPhysicsLayerNameParams {
  layer_type: '2d_physics' | '3d_physics' | '2d_render' | '3d_render';
  layer_number: number;
  layer_name: string;
}

/**
 * Definition for project configuration tools - operations that modify project settings
 */
export const projectConfigTools: MCPTool[] = [
  {
    name: 'set_project_setting',
    description: 'Set a project setting in project.godot and save',
    parameters: z.object({
      setting_name: z.string()
        .describe('Setting path (e.g., "application/config/name", "display/window/size/width")'),
      value: z.any()
        .describe('Value to set'),
    }),
    execute: async ({ setting_name, value }: SetProjectSettingParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('set_project_setting', {
          setting_name,
          value,
        });

        return `Set project setting "${setting_name}" to ${JSON.stringify(value)}`;
      } catch (error) {
        throw new Error(`Failed to set project setting: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'get_project_setting',
    description: 'Get a project setting value from project.godot',
    parameters: z.object({
      setting_name: z.string()
        .describe('Setting path'),
      default_value: z.any().optional()
        .describe('Default value if setting not found'),
    }),
    execute: async ({ setting_name, default_value }: GetProjectSettingParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('get_project_setting', {
          setting_name,
          default_value,
        });

        return `Setting "${setting_name}" = ${JSON.stringify(result.value)}`;
      } catch (error) {
        throw new Error(`Failed to get project setting: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'list_project_settings',
    description: 'List all project settings or settings matching a prefix',
    parameters: z.object({
      prefix: z.string().optional()
        .describe('Filter by prefix (e.g., "display/", "application/")'),
    }),
    execute: async ({ prefix }: ListProjectSettingsParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('list_project_settings', {
          prefix: prefix || '',
        });

        if (!result.settings || result.settings.length === 0) {
          return `No settings found${prefix ? ` with prefix "${prefix}"` : ''}`;
        }

        const formattedSettings = result.settings
          .map((setting: any) => `${setting.name}: ${JSON.stringify(setting.value)}`)
          .join('\n');

        return `Project Settings${prefix ? ` (prefix: "${prefix}")` : ''}:\n\n${formattedSettings}`;
      } catch (error) {
        throw new Error(`Failed to list project settings: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'add_input_action',
    description: 'Add a new input action to the input map',
    parameters: z.object({
      action_name: z.string()
        .describe('Action name (e.g., "jump", "move_left")'),
      deadzone: z.number().optional().default(0.5)
        .describe('Input deadzone (0.0-1.0)'),
    }),
    execute: async ({ action_name, deadzone }: AddInputActionParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('add_input_action', {
          action_name,
          deadzone: deadzone ?? 0.5,
        });

        return `Created input action "${action_name}" with deadzone ${deadzone}`;
      } catch (error) {
        throw new Error(`Failed to add input action: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'add_input_event',
    description: 'Add an input event (key, mouse, joypad) to an action',
    parameters: z.object({
      action_name: z.string()
        .describe('Action name to add event to'),
      event_type: z.enum(['key', 'mouse_button', 'joypad_button', 'joypad_motion'])
        .describe('Type of input event'),
      keycode: z.string().optional()
        .describe('For key events: KEY_SPACE, KEY_W, KEY_ESCAPE, etc.'),
      button_index: z.number().optional()
        .describe('For mouse/joypad button: button number (0-15)'),
      axis: z.number().optional()
        .describe('For joypad motion: axis number (0-9)'),
      axis_value: z.number().optional()
        .describe('For joypad motion: axis value (-1.0 or 1.0)'),
    }),
    execute: async (params: AddInputEventParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('add_input_event', params);

        return `Added ${params.event_type} event to action "${params.action_name}"`;
      } catch (error) {
        throw new Error(`Failed to add input event: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'remove_input_action',
    description: 'Remove an input action from the input map',
    parameters: z.object({
      action_name: z.string()
        .describe('Action name to remove'),
    }),
    execute: async ({ action_name }: RemoveInputActionParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('remove_input_action', {
          action_name,
        });

        return `Removed input action "${action_name}"`;
      } catch (error) {
        throw new Error(`Failed to remove input action: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'list_input_actions',
    description: 'List all input actions and their events',
    parameters: z.object({}), // No parameters
    execute: async (): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('list_input_actions', {});

        if (!result.actions || result.actions.length === 0) {
          return 'No input actions defined';
        }

        const formattedActions = result.actions
          .map((action: any) => {
            const events = action.events.map((e: any) => `  - ${e.type}: ${e.description}`).join('\n');
            return `${action.name} (deadzone: ${action.deadzone}):\n${events}`;
          })
          .join('\n\n');

        return `Input Actions:\n\n${formattedActions}`;
      } catch (error) {
        throw new Error(`Failed to list input actions: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'add_audio_bus',
    description: 'Add a new audio bus to the project',
    parameters: z.object({
      bus_name: z.string()
        .describe('Bus name (e.g., "Music", "SFX", "Ambience")'),
      position: z.number().optional()
        .describe('Position in bus list (default: add at end)'),
    }),
    execute: async ({ bus_name, position }: AddAudioBusParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('add_audio_bus', {
          bus_name,
          position: position ?? -1,
        });

        return `Created audio bus "${bus_name}" at index ${result.bus_index}`;
      } catch (error) {
        throw new Error(`Failed to add audio bus: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'set_bus_volume',
    description: 'Set the volume of an audio bus in dB',
    parameters: z.object({
      bus_index: z.number()
        .describe('Bus index (0 = Master bus)'),
      volume_db: z.number()
        .describe('Volume in decibels (-80 to 24 dB)'),
    }),
    execute: async ({ bus_index, volume_db }: SetBusVolumeParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('set_bus_volume', {
          bus_index,
          volume_db,
        });

        return `Set bus ${bus_index} volume to ${volume_db} dB`;
      } catch (error) {
        throw new Error(`Failed to set bus volume: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'add_bus_effect',
    description: 'Add an audio effect to a bus',
    parameters: z.object({
      bus_index: z.number()
        .describe('Bus index to add effect to'),
      effect_type: z.enum(['reverb', 'delay', 'chorus', 'distortion', 'eq', 'compressor', 'limiter'])
        .describe('Type of audio effect'),
      position: z.number().optional()
        .describe('Position in effect chain (default: add at end)'),
    }),
    execute: async ({ bus_index, effect_type, position }: AddBusEffectParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('add_bus_effect', {
          bus_index,
          effect_type,
          position: position ?? -1,
        });

        return `Added ${effect_type} effect to bus ${bus_index}`;
      } catch (error) {
        throw new Error(`Failed to add bus effect: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'list_audio_buses',
    description: 'List all audio buses with their configuration',
    parameters: z.object({}), // No parameters
    execute: async (): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('list_audio_buses', {});

        if (!result.buses || result.buses.length === 0) {
          return 'No audio buses configured';
        }

        const formattedBuses = result.buses
          .map((bus: any) => {
            const effects = bus.effects && bus.effects.length > 0
              ? '\n  Effects: ' + bus.effects.map((e: any) => e.type).join(', ')
              : '';
            return `${bus.index}: ${bus.name} (${bus.volume_db} dB)${effects}`;
          })
          .join('\n');

        return `Audio Buses:\n\n${formattedBuses}`;
      } catch (error) {
        throw new Error(`Failed to list audio buses: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'set_physics_layer_name',
    description: 'Set a name for a physics or render layer',
    parameters: z.object({
      layer_type: z.enum(['2d_physics', '3d_physics', '2d_render', '3d_render'])
        .describe('Type of layer'),
      layer_number: z.number().min(1).max(32)
        .describe('Layer number (1-32)'),
      layer_name: z.string()
        .describe('Name for the layer'),
    }),
    execute: async ({ layer_type, layer_number, layer_name }: SetPhysicsLayerNameParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('set_physics_layer_name', {
          layer_type,
          layer_number,
          layer_name,
        });

        return `Set ${layer_type} layer ${layer_number} name to "${layer_name}"`;
      } catch (error) {
        throw new Error(`Failed to set physics layer name: ${(error as Error).message}`);
      }
    },
  },
];
