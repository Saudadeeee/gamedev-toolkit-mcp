import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { MCPTool, CommandResult } from '../utils/types.js';

/**
 * Type definitions for TileMap/GridMap tool parameters
 */
interface SetTileCellParams {
  tilemap_path: string;
  layer: number;
  coords_x: number;
  coords_y: number;
  source_id: number;
  atlas_coords_x: number;
  atlas_coords_y: number;
  alternative_tile?: number;
}

interface EraseTileCellParams {
  tilemap_path: string;
  layer: number;
  coords_x: number;
  coords_y: number;
}

interface PaintTileAreaParams {
  tilemap_path: string;
  layer: number;
  start_x: number;
  start_y: number;
  end_x: number;
  end_y: number;
  source_id: number;
  atlas_coords_x: number;
  atlas_coords_y: number;
}

interface GetTileDataParams {
  tilemap_path: string;
  layer: number;
  coords_x: number;
  coords_y: number;
}

interface GetUsedTilesParams {
  tilemap_path: string;
  layer: number;
}

interface ClearTileMapLayerParams {
  tilemap_path: string;
  layer: number;
}

interface SetGridMapCellParams {
  gridmap_path: string;
  pos_x: number;
  pos_y: number;
  pos_z: number;
  item_id: number;
  orientation?: number;
}

interface EraseGridMapCellParams {
  gridmap_path: string;
  pos_x: number;
  pos_y: number;
  pos_z: number;
}

interface GetGridMapUsedCellsParams {
  gridmap_path: string;
}

/**
 * Definition for TileMap/GridMap tools - operations for 2D/3D level design
 */
export const tilemapTools: MCPTool[] = [
  {
    name: 'set_tile_cell',
    description: 'Set a tile at specific coordinates in a TileMap (2D)',
    parameters: z.object({
      tilemap_path: z.string()
        .describe('Path to TileMap node'),
      layer: z.number().default(0)
        .describe('TileMap layer index'),
      coords_x: z.number()
        .describe('X coordinate'),
      coords_y: z.number()
        .describe('Y coordinate'),
      source_id: z.number()
        .describe('TileSet source ID'),
      atlas_coords_x: z.number()
        .describe('Atlas X coordinate'),
      atlas_coords_y: z.number()
        .describe('Atlas Y coordinate'),
      alternative_tile: z.number().default(0)
        .describe('Alternative tile variant'),
    }),
    execute: async (params: SetTileCellParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('set_tile_cell', params);
        return `Set tile at (${params.coords_x}, ${params.coords_y}) on layer ${params.layer}`;
      } catch (error) {
        throw new Error(`Failed to set tile: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'erase_tile_cell',
    description: 'Erase a tile at specific coordinates in a TileMap',
    parameters: z.object({
      tilemap_path: z.string()
        .describe('Path to TileMap node'),
      layer: z.number().default(0)
        .describe('TileMap layer index'),
      coords_x: z.number()
        .describe('X coordinate'),
      coords_y: z.number()
        .describe('Y coordinate'),
    }),
    execute: async (params: EraseTileCellParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('erase_tile_cell', params);
        return `Erased tile at (${params.coords_x}, ${params.coords_y}) on layer ${params.layer}`;
      } catch (error) {
        throw new Error(`Failed to erase tile: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'paint_tile_area',
    description: 'Paint multiple tiles in a rectangular area',
    parameters: z.object({
      tilemap_path: z.string()
        .describe('Path to TileMap node'),
      layer: z.number().default(0)
        .describe('TileMap layer index'),
      start_x: z.number()
        .describe('Start X coordinate'),
      start_y: z.number()
        .describe('Start Y coordinate'),
      end_x: z.number()
        .describe('End X coordinate'),
      end_y: z.number()
        .describe('End Y coordinate'),
      source_id: z.number()
        .describe('TileSet source ID'),
      atlas_coords_x: z.number()
        .describe('Atlas X coordinate'),
      atlas_coords_y: z.number()
        .describe('Atlas Y coordinate'),
    }),
    execute: async (params: PaintTileAreaParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('paint_tile_area', params);
        return `Painted ${result.cells_painted || 0} tiles in area (${params.start_x},${params.start_y}) to (${params.end_x},${params.end_y})`;
      } catch (error) {
        throw new Error(`Failed to paint tile area: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'get_tile_data',
    description: 'Get tile information at specific coordinates',
    parameters: z.object({
      tilemap_path: z.string()
        .describe('Path to TileMap node'),
      layer: z.number().default(0)
        .describe('TileMap layer'),
      coords_x: z.number()
        .describe('X coordinate'),
      coords_y: z.number()
        .describe('Y coordinate'),
    }),
    execute: async (params: GetTileDataParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('get_tile_data', params);

        if (result.source_id === -1) {
          return `No tile at (${params.coords_x}, ${params.coords_y})`;
        }

        return `Tile at (${params.coords_x}, ${params.coords_y}): source=${result.source_id}, atlas=(${result.atlas_coords_x}, ${result.atlas_coords_y}), alt=${result.alternative_tile}`;
      } catch (error) {
        throw new Error(`Failed to get tile data: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'get_used_tiles',
    description: 'Get all tiles currently placed in a TileMap layer',
    parameters: z.object({
      tilemap_path: z.string()
        .describe('Path to TileMap node'),
      layer: z.number().default(0)
        .describe('TileMap layer'),
    }),
    execute: async (params: GetUsedTilesParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('get_used_tiles', params);

        if (!result.used_cells || result.used_cells.length === 0) {
          return `No tiles placed on layer ${params.layer}`;
        }

        return `Found ${result.used_cells.length} tiles on layer ${params.layer}`;
      } catch (error) {
        throw new Error(`Failed to get used tiles: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'clear_tilemap_layer',
    description: 'Clear all tiles in a TileMap layer',
    parameters: z.object({
      tilemap_path: z.string()
        .describe('Path to TileMap node'),
      layer: z.number().default(0)
        .describe('TileMap layer'),
    }),
    execute: async (params: ClearTileMapLayerParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('clear_tilemap_layer', params);
        return `Cleared all tiles on layer ${params.layer}`;
      } catch (error) {
        throw new Error(`Failed to clear tilemap layer: ${(error as Error).message}`);
      }
    },
  },

  // GridMap (3D) tools
  {
    name: 'set_gridmap_cell',
    description: 'Set a 3D tile in a GridMap',
    parameters: z.object({
      gridmap_path: z.string()
        .describe('Path to GridMap node'),
      pos_x: z.number()
        .describe('X position'),
      pos_y: z.number()
        .describe('Y position'),
      pos_z: z.number()
        .describe('Z position'),
      item_id: z.number()
        .describe('Mesh library item ID'),
      orientation: z.number().default(0)
        .describe('Rotation (0-23)'),
    }),
    execute: async (params: SetGridMapCellParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('set_gridmap_cell', params);
        return `Set GridMap cell at (${params.pos_x}, ${params.pos_y}, ${params.pos_z}) with item ${params.item_id}`;
      } catch (error) {
        throw new Error(`Failed to set gridmap cell: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'erase_gridmap_cell',
    description: 'Erase a cell in a GridMap',
    parameters: z.object({
      gridmap_path: z.string()
        .describe('Path to GridMap node'),
      pos_x: z.number()
        .describe('X position'),
      pos_y: z.number()
        .describe('Y position'),
      pos_z: z.number()
        .describe('Z position'),
    }),
    execute: async (params: EraseGridMapCellParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('erase_gridmap_cell', params);
        return `Erased GridMap cell at (${params.pos_x}, ${params.pos_y}, ${params.pos_z})`;
      } catch (error) {
        throw new Error(`Failed to erase gridmap cell: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'get_gridmap_used_cells',
    description: 'Get all occupied cells in a GridMap',
    parameters: z.object({
      gridmap_path: z.string()
        .describe('Path to GridMap node'),
    }),
    execute: async (params: GetGridMapUsedCellsParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('get_gridmap_used_cells', params);

        if (!result.used_cells || result.used_cells.length === 0) {
          return 'No cells placed in GridMap';
        }

        return `Found ${result.used_cells.length} cells in GridMap`;
      } catch (error) {
        throw new Error(`Failed to get gridmap used cells: ${(error as Error).message}`);
      }
    },
  },
];
