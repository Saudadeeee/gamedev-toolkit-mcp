import { Resource } from 'fastmcp';
import { getGodotConnection } from '../utils/godot_connection.js';

export const importSettingsResource: Resource = {
  uri: 'godot/import/settings',
  name: 'Import Settings',
  description: 'Import settings for asset files (use get_import_settings tool with specific file_path)',
  mimeType: 'application/json',
  async load() {
    return {
      text: JSON.stringify({
        message: 'To get import settings, use get_import_settings tool with specific file_path',
        example: 'get_import_settings with file_path="res://textures/player.png"'
      }, null, 2)
    };
  },
};
