import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { MCPTool, CommandResult } from '../utils/types.js';

export const navigationTools: MCPTool[] = [
  {
    name: 'bake_navigation_mesh',
    description: 'Bake the navigation mesh for a NavigationRegion2D or NavigationRegion3D node',
    parameters: z.object({
      node_path: z.string().describe('Path to NavigationRegion2D or NavigationRegion3D node'),
    }),
    execute: async ({ node_path }): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('bake_navigation_mesh', { node_path });
      return result.message || `Navigation mesh baked for ${node_path}`;
    },
  },

  {
    name: 'get_navigation_path',
    description: 'Calculate a navigation path between two points using NavigationServer',
    parameters: z.object({
      from_x: z.number().describe('Start X position'),
      from_y: z.number().describe('Start Y position'),
      from_z: z.number().optional().describe('Start Z position (3D only)'),
      to_x: z.number().describe('End X position'),
      to_y: z.number().describe('End Y position'),
      to_z: z.number().optional().describe('End Z position (3D only)'),
      is_3d: z.boolean().default(false).describe('Use 3D navigation (true) or 2D (false)'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('get_navigation_path', params);
      return JSON.stringify(result, null, 2);
    },
  },

  {
    name: 'set_navigation_target',
    description: 'Set the movement target for a NavigationAgent2D or NavigationAgent3D',
    parameters: z.object({
      agent_path: z.string().describe('Path to NavigationAgent2D or NavigationAgent3D node'),
      target_x: z.number().describe('Target X position'),
      target_y: z.number().describe('Target Y position'),
      target_z: z.number().optional().describe('Target Z position (3D only)'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_navigation_target', params);
      return result.message || 'Navigation target set';
    },
  },

  {
    name: 'get_navigation_agent_info',
    description: 'Get information about a NavigationAgent (position, target, path)',
    parameters: z.object({
      agent_path: z.string().describe('Path to NavigationAgent2D or NavigationAgent3D node'),
    }),
    execute: async ({ agent_path }): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('get_navigation_agent_info', { agent_path });
      return JSON.stringify(result, null, 2);
    },
  },

  {
    name: 'configure_navigation_region',
    description: 'Configure a NavigationRegion2D or NavigationRegion3D (enabled, layers, etc.)',
    parameters: z.object({
      node_path: z.string().describe('Path to NavigationRegion node'),
      enabled: z.boolean().optional().describe('Enable/disable the region'),
      navigation_layers: z.number().optional().describe('Navigation layer bitmask'),
      enter_cost: z.number().optional().describe('Cost to enter this region'),
      travel_cost: z.number().optional().describe('Travel cost multiplier'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('configure_navigation_region', params);
      return result.message || 'Navigation region configured';
    },
  },

  {
    name: 'set_navigation_mesh_property',
    description: 'Set a property on a NavigationMesh resource',
    parameters: z.object({
      node_path: z.string().describe('Path to NavigationRegion3D node'),
      property: z.string().describe('Property name (e.g., "cell_size", "agent_height", "agent_radius")'),
      value: z.union([z.number(), z.string(), z.boolean()]).describe('Property value'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_navigation_mesh_property', params);
      return result.message || `Set navigation mesh property: ${params.property}`;
    },
  },
];
