import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { MCPTool, CommandResult } from '../utils/types.js';

export const skeletonTools: MCPTool[] = [
  {
    name: 'get_skeleton_info',
    description: 'Get bone count, names, and hierarchy for a Skeleton3D or Skeleton2D node',
    parameters: z.object({
      node_path: z.string().describe('Path to Skeleton3D or Skeleton2D node'),
    }),
    execute: async ({ node_path }): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('get_skeleton_info', { node_path });
      return JSON.stringify(result, null, 2);
    },
  },

  {
    name: 'set_bone_pose_rotation',
    description: 'Set the pose rotation for a specific bone in a Skeleton3D',
    parameters: z.object({
      node_path: z.string().describe('Path to Skeleton3D node'),
      bone_name: z.string().describe('Bone name'),
      x: z.number().describe('Rotation X (radians)'),
      y: z.number().describe('Rotation Y (radians)'),
      z: z.number().describe('Rotation Z (radians)'),
      w: z.number().default(1.0).describe('Rotation W quaternion component'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_bone_pose_rotation', params);
      return result.message || `Set bone rotation: ${params.bone_name}`;
    },
  },

  {
    name: 'set_bone_pose_position',
    description: 'Set the pose position for a specific bone in a Skeleton3D',
    parameters: z.object({
      node_path: z.string().describe('Path to Skeleton3D node'),
      bone_name: z.string().describe('Bone name'),
      x: z.number().describe('Position X'),
      y: z.number().describe('Position Y'),
      z: z.number().describe('Position Z'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_bone_pose_position', params);
      return result.message || `Set bone position: ${params.bone_name}`;
    },
  },

  {
    name: 'set_bone_pose_scale',
    description: 'Set the pose scale for a specific bone in a Skeleton3D',
    parameters: z.object({
      node_path: z.string().describe('Path to Skeleton3D node'),
      bone_name: z.string().describe('Bone name'),
      x: z.number().default(1.0).describe('Scale X'),
      y: z.number().default(1.0).describe('Scale Y'),
      z: z.number().default(1.0).describe('Scale Z'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_bone_pose_scale', params);
      return result.message || `Set bone scale: ${params.bone_name}`;
    },
  },

  {
    name: 'get_bone_pose',
    description: 'Get current pose (position, rotation, scale) for a specific bone',
    parameters: z.object({
      node_path: z.string().describe('Path to Skeleton3D node'),
      bone_name: z.string().describe('Bone name'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('get_bone_pose', params);
      return JSON.stringify(result, null, 2);
    },
  },

  {
    name: 'configure_skeleton_ik',
    description: 'Configure a SkeletonIK3D node (target node, tip bone, root bone, etc.)',
    parameters: z.object({
      ik_node_path: z.string().describe('Path to SkeletonIK3D node'),
      target_node_path: z.string().optional().describe('Path to target node'),
      tip_bone: z.string().optional().describe('Tip bone name'),
      root_bone: z.string().optional().describe('Root bone name'),
      min_distance: z.number().optional().describe('Minimum distance to stop solving'),
      max_iterations: z.number().optional().describe('Max IK iterations'),
      interpolation: z.number().optional().describe('IK interpolation factor (0-1)'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('configure_skeleton_ik', params);
      return result.message || 'SkeletonIK configured';
    },
  },

  {
    name: 'start_skeleton_ik',
    description: 'Start or stop SkeletonIK3D solving',
    parameters: z.object({
      ik_node_path: z.string().describe('Path to SkeletonIK3D node'),
      start: z.boolean().describe('True to start, false to stop'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('start_skeleton_ik', params);
      return result.message || `SkeletonIK ${params.start ? 'started' : 'stopped'}`;
    },
  },

  {
    name: 'reset_bone_poses',
    description: 'Reset all bone poses to rest position in a Skeleton3D',
    parameters: z.object({
      node_path: z.string().describe('Path to Skeleton3D node'),
    }),
    execute: async ({ node_path }): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('reset_bone_poses', { node_path });
      return result.message || 'Bone poses reset to rest';
    },
  },
];
