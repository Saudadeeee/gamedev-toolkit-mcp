import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { MCPTool, CommandResult } from '../utils/types.js';

export const tweenTools: MCPTool[] = [
  {
    name: 'animate_node_property',
    description: 'Create a Tween animation that animates a node property over time (adds an AnimationPlayer track)',
    parameters: z.object({
      node_path: z.string().describe('Path to target node'),
      property: z.string().describe('Property to animate (e.g., "position", "modulate", "scale")'),
      from_value: z.union([z.number(), z.array(z.number()), z.string()]).optional().describe('Starting value (uses current if omitted)'),
      to_value: z.union([z.number(), z.array(z.number()), z.string()]).describe('End value to animate to'),
      duration: z.number().default(1.0).describe('Animation duration in seconds'),
      ease_type: z.enum(['linear', 'ease_in', 'ease_out', 'ease_in_out', 'spring', 'bounce', 'elastic', 'back']).default('ease_in_out').describe('Easing type'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('animate_node_property', params);
      return result.message || `Property animation created for ${params.node_path}.${params.property}`;
    },
  },

  {
    name: 'create_tween_script',
    description: 'Generate a GDScript code snippet that uses Tween to animate properties',
    parameters: z.object({
      node_path: z.string().describe('Path to target node (relative or absolute)'),
      property: z.string().describe('Property to tween (e.g., "position", "modulate:a")'),
      to_value: z.union([z.number(), z.array(z.number()), z.string()]).describe('Target value'),
      duration: z.number().default(1.0).describe('Tween duration in seconds'),
      ease_type: z.enum(['linear', 'ease_in', 'ease_out', 'ease_in_out']).default('ease_in_out').describe('Easing type'),
      loop: z.boolean().default(false).describe('Loop the tween'),
      ping_pong: z.boolean().default(false).describe('Ping-pong (back and forth) loop'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('create_tween_script', params);
      return result.code || result.message || 'Tween script generated';
    },
  },

  {
    name: 'create_animation_from_tween',
    description: 'Create a Tween at runtime in the currently running scene and animate a property',
    parameters: z.object({
      target_node_path: z.string().describe('Path to node that owns the tween'),
      property_node_path: z.string().optional().describe('Path to node with property to animate (defaults to target)'),
      property: z.string().describe('Property path to animate'),
      final_value: z.union([z.number(), z.array(z.number())]).describe('Final value'),
      duration: z.number().default(1.0).describe('Duration in seconds'),
      trans_type: z.enum(['LINEAR', 'SINE', 'QUINT', 'QUART', 'QUAD', 'EXPO', 'ELASTIC', 'CUBIC', 'CIRC', 'BOUNCE', 'BACK', 'SPRING']).default('SINE').describe('Transition curve type'),
      ease_type: z.enum(['EASE_IN', 'EASE_OUT', 'EASE_IN_OUT', 'EASE_OUT_IN']).default('EASE_IN_OUT').describe('Ease direction'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('create_animation_from_tween', params);
      return result.message || 'Tween animation started';
    },
  },
];
