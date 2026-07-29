import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { MCPTool, CommandResult } from '../utils/types.js';

export const pathTools: MCPTool[] = [
  {
    name: 'add_path_point',
    description: 'Add a point to a Path2D or Path3D curve',
    parameters: z.object({
      node_path: z.string().describe('Path to Path2D or Path3D node'),
      x: z.number().describe('Point X position'),
      y: z.number().describe('Point Y position'),
      z: z.number().optional().describe('Point Z position (Path3D only)'),
      in_x: z.number().optional().default(0).describe('Bezier handle-in X (relative to point)'),
      in_y: z.number().optional().default(0).describe('Bezier handle-in Y'),
      in_z: z.number().optional().default(0).describe('Bezier handle-in Z (3D only)'),
      out_x: z.number().optional().default(0).describe('Bezier handle-out X (relative to point)'),
      out_y: z.number().optional().default(0).describe('Bezier handle-out Y'),
      out_z: z.number().optional().default(0).describe('Bezier handle-out Z (3D only)'),
      index: z.number().optional().describe('Insert at index (-1 = end)'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('add_path_point', params);
      return result.message || `Added path point at (${params.x}, ${params.y})`;
    },
  },

  {
    name: 'remove_path_point',
    description: 'Remove a point from a Path2D or Path3D curve by index',
    parameters: z.object({
      node_path: z.string().describe('Path to Path2D or Path3D node'),
      index: z.number().describe('Point index to remove'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('remove_path_point', params);
      return result.message || `Removed path point at index ${params.index}`;
    },
  },

  {
    name: 'set_path_point',
    description: 'Modify an existing point in a Path2D or Path3D curve',
    parameters: z.object({
      node_path: z.string().describe('Path to Path2D or Path3D node'),
      index: z.number().describe('Point index to modify'),
      x: z.number().optional().describe('New X position'),
      y: z.number().optional().describe('New Y position'),
      z: z.number().optional().describe('New Z position (3D only)'),
      in_x: z.number().optional().describe('New bezier handle-in X'),
      in_y: z.number().optional().describe('New bezier handle-in Y'),
      in_z: z.number().optional().describe('New bezier handle-in Z (3D only)'),
      out_x: z.number().optional().describe('New bezier handle-out X'),
      out_y: z.number().optional().describe('New bezier handle-out Y'),
      out_z: z.number().optional().describe('New bezier handle-out Z (3D only)'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_path_point', params);
      return result.message || `Updated path point at index ${params.index}`;
    },
  },

  {
    name: 'get_path_info',
    description: 'Get all points and configuration of a Path2D or Path3D curve',
    parameters: z.object({
      node_path: z.string().describe('Path to Path2D or Path3D node'),
    }),
    execute: async ({ node_path }): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('get_path_info', { node_path });
      return JSON.stringify(result, null, 2);
    },
  },

  {
    name: 'clear_path',
    description: 'Remove all points from a Path2D or Path3D curve',
    parameters: z.object({
      node_path: z.string().describe('Path to Path2D or Path3D node'),
    }),
    execute: async ({ node_path }): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('clear_path', { node_path });
      return result.message || 'Path cleared';
    },
  },

  {
    name: 'configure_path_follow',
    description: 'Configure a PathFollow2D or PathFollow3D node',
    parameters: z.object({
      node_path: z.string().describe('Path to PathFollow2D or PathFollow3D node'),
      progress: z.number().optional().describe('Progress along path in pixels/units'),
      progress_ratio: z.number().optional().describe('Progress as ratio (0.0 to 1.0)'),
      h_offset: z.number().optional().describe('Horizontal offset from path'),
      v_offset: z.number().optional().describe('Vertical offset from path'),
      rotation_mode: z.enum(['none', 'y', 'xy', 'xyz', 'oriented']).optional().describe('Rotation mode (PathFollow3D)'),
      loop: z.boolean().optional().describe('Whether to loop back to start'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('configure_path_follow', params);
      return result.message || 'PathFollow configured';
    },
  },

  {
    name: 'set_curve_baked_resolution',
    description: 'Set the bake interval (tessellation resolution) for a Path2D or Path3D',
    parameters: z.object({
      node_path: z.string().describe('Path to Path2D or Path3D node'),
      bake_interval: z.number().default(5.0).describe('Distance between baked points (lower = more accurate)'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_curve_baked_resolution', params);
      return result.message || `Bake interval set to ${params.bake_interval}`;
    },
  },
];
