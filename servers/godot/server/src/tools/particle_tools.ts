import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { MCPTool, CommandResult } from '../utils/types.js';

export const particleTools: MCPTool[] = [
  {
    name: 'configure_particles',
    description: 'Configure GPUParticles2D, GPUParticles3D, CPUParticles2D, or CPUParticles3D properties',
    parameters: z.object({
      node_path: z.string().describe('Path to particles node'),
      amount: z.number().optional().describe('Number of particles'),
      lifetime: z.number().optional().describe('Particle lifetime in seconds'),
      one_shot: z.boolean().optional().describe('Emit once then stop'),
      preprocess: z.number().optional().describe('Preprocess time in seconds'),
      speed_scale: z.number().optional().describe('Playback speed multiplier'),
      explosiveness: z.number().optional().describe('How instantaneous emission is (0-1)'),
      randomness: z.number().optional().describe('Emission randomness (0-1)'),
      emitting: z.boolean().optional().describe('Whether particles are currently emitting'),
      fixed_fps: z.number().optional().describe('Fixed FPS for particles (0 = disabled)'),
      local_coords: z.boolean().optional().describe('Use local coordinate space'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('configure_particles', params);
      return result.message || `Particles configured at ${params.node_path}`;
    },
  },

  {
    name: 'set_particle_material',
    description: 'Set or configure the ParticleProcessMaterial for a GPU particles node',
    parameters: z.object({
      node_path: z.string().describe('Path to GPUParticles2D or GPUParticles3D node'),
      property: z.string().describe('Material property (e.g., "color", "initial_velocity_min", "gravity", "scale_min")'),
      value: z.union([z.number(), z.string(), z.array(z.number())]).describe('Property value'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_particle_material', params);
      return result.message || `Particle material property set: ${params.property}`;
    },
  },

  {
    name: 'set_particle_emission_shape',
    description: 'Set the emission shape for a particle system',
    parameters: z.object({
      node_path: z.string().describe('Path to GPU/CPU particles node'),
      shape: z.enum(['point', 'sphere', 'sphere_surface', 'box', 'points', 'directed_points', 'ring']).describe('Emission shape type'),
      shape_x: z.number().optional().describe('Shape extents X'),
      shape_y: z.number().optional().describe('Shape extents Y'),
      shape_z: z.number().optional().describe('Shape extents Z (3D only)'),
      radius: z.number().optional().describe('Sphere/ring radius'),
      ring_axis_x: z.number().optional().describe('Ring axis X'),
      ring_axis_y: z.number().optional().describe('Ring axis Y'),
      ring_axis_z: z.number().optional().describe('Ring axis Z'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_particle_emission_shape', params);
      return result.message || `Particle emission shape set to: ${params.shape}`;
    },
  },

  {
    name: 'restart_particles',
    description: 'Restart/reset a particle system (clears existing particles and starts fresh)',
    parameters: z.object({
      node_path: z.string().describe('Path to particles node'),
    }),
    execute: async ({ node_path }): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('restart_particles', { node_path });
      return result.message || 'Particles restarted';
    },
  },

  {
    name: 'get_particle_info',
    description: 'Get current configuration of a particle system',
    parameters: z.object({
      node_path: z.string().describe('Path to particles node'),
    }),
    execute: async ({ node_path }): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('get_particle_info', { node_path });
      return JSON.stringify(result, null, 2);
    },
  },
];
