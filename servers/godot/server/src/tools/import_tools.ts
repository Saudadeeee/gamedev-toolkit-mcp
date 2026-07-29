import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { MCPTool, CommandResult } from '../utils/types.js';

export const importTools: MCPTool[] = [
  {
    name: 'scan_filesystem',
    description: 'Rescan the Godot filesystem for new or changed files',
    parameters: z.object({}),
    execute: async (): Promise<string> => {
      const godot = getGodotConnection();
      try {
        await godot.sendCommand('scan_filesystem', {});
        return 'Filesystem scan initiated';
      } catch (error) {
        throw new Error(`Failed to scan filesystem: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'reimport_file',
    description: 'Force reimport of a specific asset file',
    parameters: z.object({
      file_path: z.string().describe('Path to asset file (e.g., "res://textures/player.png")'),
    }),
    execute: async ({ file_path }): Promise<string> => {
      const godot = getGodotConnection();
      try {
        await godot.sendCommand('reimport_file', { file_path });
        return `Reimported: ${file_path}`;
      } catch (error) {
        throw new Error(`Failed to reimport file: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'get_import_settings',
    description: 'Get import settings for an asset file',
    parameters: z.object({
      file_path: z.string().describe('Path to asset file (e.g., "res://textures/player.png")'),
    }),
    execute: async ({ file_path }): Promise<string> => {
      const godot = getGodotConnection();
      try {
        const result = await godot.sendCommand<CommandResult>('get_import_settings', { file_path });
        return JSON.stringify(result, null, 2);
      } catch (error) {
        throw new Error(`Failed to get import settings: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'set_import_setting',
    description: 'Modify an import setting for an asset and reimport it',
    parameters: z.object({
      file_path: z.string().describe('Path to asset file'),
      setting_key: z.string().describe('Setting key (e.g., "params/compress/mode", "params/mipmaps/generate")'),
      value: z.any().describe('Setting value'),
    }),
    execute: async ({ file_path, setting_key, value }): Promise<string> => {
      const godot = getGodotConnection();
      try {
        await godot.sendCommand('set_import_setting', { file_path, setting_key, value });
        return `Updated import setting "${setting_key}" for ${file_path}`;
      } catch (error) {
        throw new Error(`Failed to set import setting: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'list_filesystem_files',
    description: 'List all files in a directory of the Godot project filesystem',
    parameters: z.object({
      path: z.string().default('res://').describe('Directory path to list (e.g., "res://", "res://scenes/")'),
      recursive: z.boolean().default(false).describe('Include subdirectories'),
      filter_extension: z.string().optional().describe('Filter by extension (e.g., ".tscn", ".png")'),
    }),
    execute: async ({ path, recursive, filter_extension }): Promise<string> => {
      const godot = getGodotConnection();
      try {
        const result = await godot.sendCommand<CommandResult>('list_filesystem_files', { path, recursive, filter_extension });
        if (!result.files || result.files.length === 0) {
          return `No files found in ${path}`;
        }
        return `Files in ${path}:\n${result.files.join('\n')}`;
      } catch (error) {
        throw new Error(`Failed to list filesystem files: ${(error as Error).message}`);
      }
    },
  },
];
