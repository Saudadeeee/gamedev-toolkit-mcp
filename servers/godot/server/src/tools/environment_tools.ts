import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { MCPTool, CommandResult } from '../utils/types.js';

export const environmentTools: MCPTool[] = [
  {
    name: 'set_light_property',
    description: 'Set a property on a Light2D, DirectionalLight3D, OmniLight3D, or SpotLight3D node',
    parameters: z.object({
      node_path: z.string().describe('Path to light node'),
      property: z.string().describe('Property name (e.g., "light_color", "light_energy", "shadow_enabled", "omni_range", "spot_angle")'),
      value: z.union([z.number(), z.boolean(), z.string(), z.array(z.number())]).describe('Property value'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_light_property', params);
      return result.message || `Set light property: ${params.property}`;
    },
  },

  {
    name: 'configure_environment',
    description: 'Configure an Environment resource (background, ambient light, fog, glow, etc.)',
    parameters: z.object({
      node_path: z.string().describe('Path to WorldEnvironment node'),
      property: z.string().describe('Environment property (e.g., "background_mode", "ambient_light_color", "fog_enabled", "glow_enabled", "tonemap_mode")'),
      value: z.union([z.number(), z.boolean(), z.string(), z.array(z.number())]).describe('Property value'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('configure_environment', params);
      return result.message || `Environment property set: ${params.property}`;
    },
  },

  {
    name: 'set_sky',
    description: 'Set the sky for a WorldEnvironment node (ProceduralSkyMaterial, PanoramaSkyMaterial, etc.)',
    parameters: z.object({
      node_path: z.string().describe('Path to WorldEnvironment node'),
      sky_type: z.enum(['procedural', 'panorama', 'physical_sun_sky']).describe('Sky material type'),
      sky_top_color: z.array(z.number()).optional().describe('Top color [r,g,b] for procedural sky'),
      sky_horizon_color: z.array(z.number()).optional().describe('Horizon color [r,g,b] for procedural sky'),
      ground_bottom_color: z.array(z.number()).optional().describe('Ground color [r,g,b] for procedural sky'),
      sun_angle_max: z.number().optional().describe('Sun angle max for procedural sky'),
      texture_path: z.string().optional().describe('Panorama texture path for panorama sky'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_sky', params);
      return result.message || `Sky set to ${params.sky_type}`;
    },
  },

  {
    name: 'set_fog',
    description: 'Configure fog settings on a WorldEnvironment node',
    parameters: z.object({
      node_path: z.string().describe('Path to WorldEnvironment node'),
      enabled: z.boolean().describe('Enable or disable fog'),
      color_r: z.number().optional().describe('Fog color R (0-1)'),
      color_g: z.number().optional().describe('Fog color G (0-1)'),
      color_b: z.number().optional().describe('Fog color B (0-1)'),
      density: z.number().optional().describe('Fog density'),
      aerial_perspective: z.number().optional().describe('Aerial perspective factor (0-1)'),
      sky_affect: z.number().optional().describe('How much fog affects sky (0-1)'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_fog', params);
      return result.message || `Fog ${params.enabled ? 'enabled' : 'disabled'}`;
    },
  },

  {
    name: 'configure_camera',
    description: 'Configure a Camera2D or Camera3D node properties',
    parameters: z.object({
      node_path: z.string().describe('Path to Camera2D or Camera3D node'),
      fov: z.number().optional().describe('Field of view in degrees (Camera3D)'),
      near: z.number().optional().describe('Near clip plane distance'),
      far: z.number().optional().describe('Far clip plane distance'),
      zoom_x: z.number().optional().describe('Zoom X (Camera2D)'),
      zoom_y: z.number().optional().describe('Zoom Y (Camera2D)'),
      projection: z.enum(['perspective', 'orthogonal', 'frustum']).optional().describe('Projection mode (Camera3D)'),
      size: z.number().optional().describe('Orthogonal size (Camera3D orthogonal mode)'),
      current: z.boolean().optional().describe('Set as current active camera'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('configure_camera', params);
      return result.message || 'Camera configured';
    },
  },

  {
    name: 'get_environment_info',
    description: 'Get current environment and lighting configuration',
    parameters: z.object({
      node_path: z.string().describe('Path to WorldEnvironment node'),
    }),
    execute: async ({ node_path }): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('get_environment_info', { node_path });
      return JSON.stringify(result, null, 2);
    },
  },
];
