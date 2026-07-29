import { Resource } from 'fastmcp';
import { getGodotConnection } from '../utils/godot_connection.js';

/**
 * MCP Resource for TileMap data
 * Note: This is a template resource - actual URI should include tilemap path
 */
export const tilemapDataResource: Resource = {
  uri: 'godot/tilemap/data',
  name: 'TileMap Data',
  description: 'All tiles in a TileMap (use specific path with query params: ?path=...&layer=...)',
  mimeType: 'application/json',
  async load() {
    const godot = getGodotConnection();

    try {
      // This would need path and layer from URI query params in real implementation
      // For now, return a helpful message
      return {
        text: JSON.stringify({
          message: 'To get TileMap data, use get_used_tiles tool with specific tilemap_path and layer',
          example: 'get_used_tiles with tilemap_path="TileMap" and layer=0'
        }, null, 2)
      };
    } catch (error) {
      console.error('Error fetching tilemap data:', error);
      throw error;
    }
  },
};

/**
 * MCP Resource for GridMap data
 */
export const gridmapDataResource: Resource = {
  uri: 'godot/gridmap/data',
  name: 'GridMap Data',
  description: 'All cells in a GridMap (use specific path with query params: ?path=...)',
  mimeType: 'application/json',
  async load() {
    const godot = getGodotConnection();

    try {
      // This would need path from URI query params in real implementation
      return {
        text: JSON.stringify({
          message: 'To get GridMap data, use get_gridmap_used_cells tool with specific gridmap_path',
          example: 'get_gridmap_used_cells with gridmap_path="GridMap"'
        }, null, 2)
      };
    } catch (error) {
      console.error('Error fetching gridmap data:', error);
      throw error;
    }
  },
};
