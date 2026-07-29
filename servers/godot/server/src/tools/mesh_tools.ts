import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { MCPTool, CommandResult } from '../utils/types.js';

export const meshTools: MCPTool[] = [
  {
    name: 'create_primitive_mesh',
    description: 'Create and assign a primitive mesh resource (BoxMesh, SphereMesh, CylinderMesh, PlaneMesh, etc.) to a MeshInstance3D',
    parameters: z.object({
      node_path: z.string().describe('Path to MeshInstance3D node'),
      mesh_type: z.enum(['BoxMesh', 'SphereMesh', 'CylinderMesh', 'CapsuleMesh', 'PlaneMesh', 'QuadMesh', 'TorusMesh', 'PrismMesh', 'PointMesh', 'TubeTrailMesh', 'RibbonTrailMesh']).describe('Primitive mesh type'),
      size_x: z.number().optional().default(1.0).describe('Size/radius X'),
      size_y: z.number().optional().default(1.0).describe('Size/height Y'),
      size_z: z.number().optional().default(1.0).describe('Size Z (BoxMesh)'),
      subdivide_width: z.number().optional().describe('Subdivisions along width'),
      subdivide_height: z.number().optional().describe('Subdivisions along height'),
      subdivide_depth: z.number().optional().describe('Subdivisions along depth (BoxMesh)'),
      rings: z.number().optional().describe('Number of rings (SphereMesh, CylinderMesh, TorusMesh)'),
      radial_segments: z.number().optional().describe('Radial segments count'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('create_primitive_mesh', params);
      return result.message || `Created ${params.mesh_type} on ${params.node_path}`;
    },
  },

  {
    name: 'create_array_mesh',
    description: 'Create a custom ArrayMesh from vertex, normal, UV, and index arrays and assign to MeshInstance3D',
    parameters: z.object({
      node_path: z.string().describe('Path to MeshInstance3D node'),
      vertices: z.array(z.number()).describe('Flat array of vertex positions [x0,y0,z0, x1,y1,z1, ...]'),
      normals: z.array(z.number()).optional().describe('Flat array of normals [x0,y0,z0, ...] (same count as vertices)'),
      uvs: z.array(z.number()).optional().describe('Flat array of UV coords [u0,v0, u1,v1, ...] (same count as vertices)'),
      indices: z.array(z.number()).optional().describe('Triangle indices [i0,i1,i2, ...]'),
      primitive_type: z.enum(['triangles', 'triangle_strip', 'lines', 'line_strip', 'points']).default('triangles').describe('Primitive type'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('create_array_mesh', params);
      return result.message || `Custom mesh created on ${params.node_path}`;
    },
  },

  {
    name: 'get_mesh_info',
    description: 'Get information about the mesh on a MeshInstance2D or MeshInstance3D (surface count, vertex count, materials)',
    parameters: z.object({
      node_path: z.string().describe('Path to MeshInstance2D or MeshInstance3D node'),
    }),
    execute: async ({ node_path }): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('get_mesh_info', { node_path });
      return JSON.stringify(result, null, 2);
    },
  },

  {
    name: 'set_mesh_surface_material',
    description: 'Set or replace the material on a specific surface of a mesh',
    parameters: z.object({
      node_path: z.string().describe('Path to MeshInstance3D node'),
      surface_index: z.number().default(0).describe('Surface index'),
      material_type: z.enum(['StandardMaterial3D', 'ShaderMaterial', 'ORMMaterial3D']).default('StandardMaterial3D').describe('Material type to create'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_mesh_surface_material', params);
      return result.message || `Material set on surface ${params.surface_index}`;
    },
  },

  {
    name: 'generate_mesh_normals',
    description: 'Recalculate smooth/flat normals for a mesh using SurfaceTool',
    parameters: z.object({
      node_path: z.string().describe('Path to MeshInstance3D node'),
      smooth: z.boolean().default(true).describe('True for smooth normals, false for flat'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('generate_mesh_normals', params);
      return result.message || `Normals regenerated (${params.smooth ? 'smooth' : 'flat'})`;
    },
  },

  {
    name: 'create_mesh_from_height_map',
    description: 'Generate a terrain mesh from a 2D grid of height values',
    parameters: z.object({
      node_path: z.string().describe('Path to MeshInstance3D node'),
      width: z.number().describe('Grid width (columns)'),
      depth: z.number().describe('Grid depth (rows)'),
      heights: z.array(z.number()).describe('Flat array of height values [width * depth]'),
      cell_size: z.number().default(1.0).describe('Size of each grid cell'),
      height_scale: z.number().default(1.0).describe('Scale multiplier for heights'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('create_mesh_from_height_map', params);
      return result.message || `Height map mesh created (${params.width}x${params.depth})`;
    },
  },

  {
    name: 'save_mesh_to_file',
    description: 'Save the mesh resource from a MeshInstance3D to a .tres or .res file',
    parameters: z.object({
      node_path: z.string().describe('Path to MeshInstance3D node'),
      save_path: z.string().describe('File path to save (e.g., "res://meshes/my_mesh.tres")'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('save_mesh_to_file', params);
      return result.message || `Mesh saved to ${params.save_path}`;
    },
  },
];
