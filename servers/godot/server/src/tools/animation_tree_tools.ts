import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { MCPTool, CommandResult } from '../utils/types.js';

export const animationTreeTools: MCPTool[] = [
  {
    name: 'configure_animation_tree',
    description: 'Configure an AnimationTree node (set root node type, animation player path, active state)',
    parameters: z.object({
      tree_path: z.string().describe('Path to AnimationTree node'),
      animation_player_path: z.string().optional().describe('Path to AnimationPlayer node'),
      active: z.boolean().optional().describe('Activate or deactivate the AnimationTree'),
      root_node_type: z.enum(['blend_tree', 'state_machine', 'animation', 'blend_space_1d', 'blend_space_2d']).optional().describe('Type of root AnimationNode to create'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('configure_animation_tree', params);
      return result.message || 'AnimationTree configured';
    },
  },

  {
    name: 'add_animation_tree_node',
    description: 'Add a node to an AnimationTree BlendTree or StateMachine',
    parameters: z.object({
      tree_path: z.string().describe('Path to AnimationTree node'),
      node_type: z.enum(['animation', 'blend2', 'blend3', 'state_machine', 'blend_space_1d', 'blend_space_2d', 'time_scale', 'transition']).describe('Type of AnimationNode to add'),
      node_name: z.string().describe('Name for this node in the tree'),
      animation_name: z.string().optional().describe('Animation name (for animation nodes)'),
      position_x: z.number().optional().describe('Visual X position in editor graph'),
      position_y: z.number().optional().describe('Visual Y position in editor graph'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('add_animation_tree_node', params);
      return result.message || `Added animation tree node: ${params.node_name}`;
    },
  },

  {
    name: 'connect_animation_tree_nodes',
    description: 'Connect two nodes in an AnimationTree BlendTree',
    parameters: z.object({
      tree_path: z.string().describe('Path to AnimationTree node'),
      from_node: z.string().describe('Source node name'),
      to_node: z.string().describe('Destination node name'),
      to_input: z.number().default(0).describe('Input port index on destination node'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('connect_animation_tree_nodes', params);
      return result.message || `Connected ${params.from_node} to ${params.to_node}`;
    },
  },

  {
    name: 'set_animation_tree_parameter',
    description: 'Set a blend/parameter value on an AnimationTree (blend amounts, transitions, etc.)',
    parameters: z.object({
      tree_path: z.string().describe('Path to AnimationTree node'),
      parameter: z.string().describe('Parameter path (e.g., "parameters/blend_amount", "parameters/StateMachine/current")'),
      value: z.union([z.number(), z.string(), z.boolean()]).describe('Parameter value'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_animation_tree_parameter', params);
      return result.message || `Set parameter: ${params.parameter} = ${params.value}`;
    },
  },

  {
    name: 'get_animation_tree_parameter',
    description: 'Get a parameter value from an AnimationTree',
    parameters: z.object({
      tree_path: z.string().describe('Path to AnimationTree node'),
      parameter: z.string().describe('Parameter path'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('get_animation_tree_parameter', params);
      return JSON.stringify(result, null, 2);
    },
  },

  {
    name: 'add_state_machine_transition',
    description: 'Add a transition between states in an AnimationNodeStateMachine',
    parameters: z.object({
      tree_path: z.string().describe('Path to AnimationTree node'),
      state_machine_path: z.string().optional().default('').describe('Path within tree to state machine node (empty = root)'),
      from_state: z.string().describe('Source state name'),
      to_state: z.string().describe('Destination state name'),
      switch_mode: z.enum(['immediate', 'sync', 'at_end']).default('immediate').describe('When transition switches'),
      auto_advance: z.boolean().default(false).describe('Auto-advance to next state'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('add_state_machine_transition', params);
      return result.message || `Added transition: ${params.from_state} -> ${params.to_state}`;
    },
  },

  {
    name: 'get_animation_tree_info',
    description: 'Get full information about an AnimationTree (nodes, connections, parameters)',
    parameters: z.object({
      tree_path: z.string().describe('Path to AnimationTree node'),
    }),
    execute: async ({ tree_path }): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('get_animation_tree_info', { tree_path });
      return JSON.stringify(result, null, 2);
    },
  },
];
