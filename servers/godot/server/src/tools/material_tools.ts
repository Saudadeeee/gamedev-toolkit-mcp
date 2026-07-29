import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { MCPTool, CommandResult } from '../utils/types.js';

export const materialTools: MCPTool[] = [
  {
    name: 'create_material',
    description: 'Create and assign a new material to a node',
    parameters: z.object({
      node_path: z.string().describe('Path to node'),
      material_type: z.enum(['StandardMaterial3D', 'ShaderMaterial', 'CanvasItemMaterial', 'ORMMaterial3D'])
        .describe('Material type'),
      surface_index: z.number().default(0).describe('Material surface slot index'),
    }),
    execute: async ({ node_path, material_type, surface_index }): Promise<string> => {
      const godot = getGodotConnection();
      try {
        const result = await godot.sendCommand<CommandResult>('create_material', { node_path, material_type, surface_index });
        return `Created ${material_type} on "${node_path}" surface ${surface_index}`;
      } catch (error) {
        throw new Error(`Failed to create material: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'set_material_property',
    description: 'Set a property on a node\'s material (e.g., albedo_color, metallic, roughness)',
    parameters: z.object({
      node_path: z.string().describe('Path to node with material'),
      surface_index: z.number().default(0).describe('Material surface slot index'),
      property: z.string().describe('Property name (e.g., "albedo_color", "metallic", "roughness", "emission_enabled")'),
      value: z.any().describe('Property value'),
    }),
    execute: async ({ node_path, surface_index, property, value }): Promise<string> => {
      const godot = getGodotConnection();
      try {
        await godot.sendCommand('set_material_property', { node_path, surface_index, property, value });
        return `Set material property "${property}" on "${node_path}"`;
      } catch (error) {
        throw new Error(`Failed to set material property: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'get_material_properties',
    description: 'Get all properties of a node\'s material',
    parameters: z.object({
      node_path: z.string().describe('Path to node with material'),
      surface_index: z.number().default(0).describe('Material surface slot index'),
    }),
    execute: async ({ node_path, surface_index }): Promise<string> => {
      const godot = getGodotConnection();
      try {
        const result = await godot.sendCommand<CommandResult>('get_material_properties', { node_path, surface_index });
        return JSON.stringify(result, null, 2);
      } catch (error) {
        throw new Error(`Failed to get material properties: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'set_shader_code',
    description: 'Set GLSL shader code on a ShaderMaterial',
    parameters: z.object({
      node_path: z.string().describe('Path to node with ShaderMaterial'),
      surface_index: z.number().default(0).describe('Material surface slot index'),
      shader_code: z.string().describe('GLSL shader source code'),
    }),
    execute: async ({ node_path, surface_index, shader_code }): Promise<string> => {
      const godot = getGodotConnection();
      try {
        await godot.sendCommand('set_shader_code', { node_path, surface_index, shader_code });
        return `Updated shader code on "${node_path}"`;
      } catch (error) {
        throw new Error(`Failed to set shader code: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'set_shader_parameter',
    description: 'Set a shader uniform/parameter on a ShaderMaterial',
    parameters: z.object({
      node_path: z.string().describe('Path to node with ShaderMaterial'),
      surface_index: z.number().default(0).describe('Material surface slot index'),
      parameter_name: z.string().describe('Shader uniform name'),
      value: z.any().describe('Parameter value'),
    }),
    execute: async ({ node_path, surface_index, parameter_name, value }): Promise<string> => {
      const godot = getGodotConnection();
      try {
        await godot.sendCommand('set_shader_parameter', { node_path, surface_index, parameter_name, value });
        return `Set shader parameter "${parameter_name}" on "${node_path}"`;
      } catch (error) {
        throw new Error(`Failed to set shader parameter: ${(error as Error).message}`);
      }
    },
  },
];
