import { Resource } from 'fastmcp';
import { getGodotConnection } from '../utils/godot_connection.js';

/**
 * MCP Resource for animation list
 */
export const animationListResource: Resource = {
  uri: 'godot/animations/list',
  name: 'Animation List',
  description: 'All animations in AnimationPlayer nodes (use specific path with query params: ?path=...)',
  mimeType: 'application/json',
  async load() {
    const godot = getGodotConnection();

    try {
      // This would need animation_player_path from URI query params
      return {
        text: JSON.stringify({
          message: 'To get animations, use list_animations tool with specific animation_player_path',
          example: 'list_animations with animation_player_path="AnimationPlayer"'
        }, null, 2)
      };
    } catch (error) {
      console.error('Error fetching animation list:', error);
      throw error;
    }
  },
};

/**
 * MCP Resource for animation data
 */
export const animationDataResource: Resource = {
  uri: 'godot/animation/data',
  name: 'Animation Data',
  description: 'Complete animation data including tracks and keyframes (use query params: ?path=...&name=...)',
  mimeType: 'application/json',
  async load() {
    const godot = getGodotConnection();

    try {
      return {
        text: JSON.stringify({
          message: 'To get animation data, use get_animation_data tool with animation_player_path and animation_name',
          example: 'get_animation_data with animation_player_path="AnimationPlayer" and animation_name="walk"'
        }, null, 2)
      };
    } catch (error) {
      console.error('Error fetching animation data:', error);
      throw error;
    }
  },
};
