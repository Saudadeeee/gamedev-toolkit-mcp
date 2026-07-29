import { Resource } from 'fastmcp';
import { getGodotConnection } from '../utils/godot_connection.js';

/**
 * MCP Resource for input map configuration
 */
export const inputMapResource: Resource = {
  uri: 'godot/project/input_map',
  name: 'Input Map',
  description: 'All input actions and their mapped events',
  mimeType: 'application/json',
  async load() {
    const godot = getGodotConnection();

    try {
      const result = await godot.sendCommand('list_input_actions', {});

      return {
        text: JSON.stringify(result, null, 2)
      };
    } catch (error) {
      console.error('Error fetching input map:', error);
      throw error;
    }
  },
};

/**
 * MCP Resource for audio bus layout
 */
export const audioBusLayoutResource: Resource = {
  uri: 'godot/project/audio_buses',
  name: 'Audio Bus Layout',
  description: 'All audio buses and their configuration',
  mimeType: 'application/json',
  async load() {
    const godot = getGodotConnection();

    try {
      const result = await godot.sendCommand('list_audio_buses', {});

      return {
        text: JSON.stringify(result, null, 2)
      };
    } catch (error) {
      console.error('Error fetching audio bus layout:', error);
      throw error;
    }
  },
};

/**
 * MCP Resource for project settings
 */
export const allProjectSettingsResource: Resource = {
  uri: 'godot/project/all_settings',
  name: 'All Project Settings',
  description: 'Complete list of all project settings',
  mimeType: 'application/json',
  async load() {
    const godot = getGodotConnection();

    try {
      const result = await godot.sendCommand('list_project_settings', { prefix: '' });

      return {
        text: JSON.stringify(result, null, 2)
      };
    } catch (error) {
      console.error('Error fetching project settings:', error);
      throw error;
    }
  },
};
