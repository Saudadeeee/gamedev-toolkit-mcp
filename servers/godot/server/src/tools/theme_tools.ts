import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { MCPTool, CommandResult } from '../utils/types.js';

export const themeTools: MCPTool[] = [
  {
    name: 'create_theme',
    description: 'Create a new Theme resource and optionally save it to disk',
    parameters: z.object({
      save_path: z.string().optional().describe('Path to save theme file (e.g., "res://theme/my_theme.tres")'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('create_theme', params);
      return result.message || 'Theme created';
    },
  },

  {
    name: 'set_theme_color',
    description: 'Set a color item in a Theme resource (for a specific Control type)',
    parameters: z.object({
      theme_path: z.string().describe('Path to theme file (e.g., "res://theme/my_theme.tres")'),
      control_type: z.string().describe('Control type name (e.g., "Button", "Label", "LineEdit")'),
      color_name: z.string().describe('Color name (e.g., "font_color", "font_disabled_color", "icon_normal_color")'),
      r: z.number().min(0).max(1).describe('Red component (0-1)'),
      g: z.number().min(0).max(1).describe('Green component (0-1)'),
      b: z.number().min(0).max(1).describe('Blue component (0-1)'),
      a: z.number().min(0).max(1).default(1.0).describe('Alpha component (0-1)'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_theme_color', params);
      return result.message || `Set theme color: ${params.control_type}/${params.color_name}`;
    },
  },

  {
    name: 'set_theme_font',
    description: 'Set a font item in a Theme resource',
    parameters: z.object({
      theme_path: z.string().describe('Path to theme file'),
      control_type: z.string().describe('Control type name (e.g., "Button", "Label")'),
      font_name: z.string().describe('Font name (e.g., "font")'),
      font_path: z.string().describe('Path to font resource (e.g., "res://fonts/my_font.ttf")'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_theme_font', params);
      return result.message || `Set theme font: ${params.control_type}/${params.font_name}`;
    },
  },

  {
    name: 'set_theme_font_size',
    description: 'Set a font size item in a Theme resource',
    parameters: z.object({
      theme_path: z.string().describe('Path to theme file'),
      control_type: z.string().describe('Control type name'),
      font_size_name: z.string().describe('Font size name (e.g., "font_size")'),
      size: z.number().describe('Font size in pixels'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_theme_font_size', params);
      return result.message || `Set theme font size: ${params.size}px`;
    },
  },

  {
    name: 'set_theme_constant',
    description: 'Set a constant (integer) item in a Theme resource',
    parameters: z.object({
      theme_path: z.string().describe('Path to theme file'),
      control_type: z.string().describe('Control type name'),
      constant_name: z.string().describe('Constant name (e.g., "separation", "icon_max_width")'),
      value: z.number().describe('Constant value'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_theme_constant', params);
      return result.message || `Set theme constant: ${params.control_type}/${params.constant_name} = ${params.value}`;
    },
  },

  {
    name: 'set_theme_stylebox',
    description: 'Set a StyleBox for a Control in a Theme (set background/border styling)',
    parameters: z.object({
      theme_path: z.string().describe('Path to theme file'),
      control_type: z.string().describe('Control type name (e.g., "Button", "PanelContainer")'),
      stylebox_name: z.string().describe('StyleBox name (e.g., "normal", "hover", "pressed", "disabled", "panel")'),
      stylebox_type: z.enum(['flat', 'empty', 'line']).default('flat').describe('StyleBox type'),
      bg_r: z.number().optional().describe('Background color R (StyleBoxFlat)'),
      bg_g: z.number().optional().describe('Background color G (StyleBoxFlat)'),
      bg_b: z.number().optional().describe('Background color B (StyleBoxFlat)'),
      bg_a: z.number().optional().describe('Background color A (StyleBoxFlat)'),
      corner_radius: z.number().optional().describe('Corner radius for all corners (StyleBoxFlat)'),
      border_width: z.number().optional().describe('Border width for all sides (StyleBoxFlat)'),
      border_r: z.number().optional().describe('Border color R (StyleBoxFlat)'),
      border_g: z.number().optional().describe('Border color G (StyleBoxFlat)'),
      border_b: z.number().optional().describe('Border color B (StyleBoxFlat)'),
      border_a: z.number().optional().describe('Border color A (StyleBoxFlat)'),
      content_margin: z.number().optional().describe('Content margin for all sides'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('set_theme_stylebox', params);
      return result.message || `Set stylebox: ${params.control_type}/${params.stylebox_name}`;
    },
  },

  {
    name: 'assign_theme_to_node',
    description: 'Assign a Theme resource to a Control node',
    parameters: z.object({
      node_path: z.string().describe('Path to Control node'),
      theme_path: z.string().describe('Path to theme file (e.g., "res://theme/my_theme.tres")'),
    }),
    execute: async (params): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('assign_theme_to_node', params);
      return result.message || `Theme assigned to ${params.node_path}`;
    },
  },

  {
    name: 'get_theme_items',
    description: 'Get all items (colors, fonts, constants, styleboxes) from a Theme resource',
    parameters: z.object({
      theme_path: z.string().describe('Path to theme file'),
    }),
    execute: async ({ theme_path }): Promise<string> => {
      const godot = getGodotConnection();
      const result = await godot.sendCommand<CommandResult>('get_theme_items', { theme_path });
      return JSON.stringify(result, null, 2);
    },
  },
];
