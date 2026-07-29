import { Resource } from 'fastmcp';
import { getGodotConnection } from '../utils/godot_connection.js';

/**
 * MCP Resource for playback state
 */
export const playbackStateResource: Resource = {
  uri: 'godot/playback/state',
  name: 'Playback State',
  description: 'Current playback state - whether a scene is playing and which scene',
  mimeType: 'application/json',
  async load() {
    const godot = getGodotConnection();

    try {
      const result = await godot.sendCommand('get_play_status', {});

      const state = {
        is_playing: result.is_playing || false,
        playing_scene: result.playing_scene || null,
        timestamp: new Date().toISOString(),
      };

      return {
        text: JSON.stringify(state, null, 2)
      };
    } catch (error) {
      console.error('Error fetching playback state:', error);
      throw error;
    }
  },
};
