import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { MCPTool, CommandResult } from '../utils/types.js';

/**
 * Type definitions for node tool parameters
 */
interface CreateNodeParams {
  parent_path: string;
  node_type: string;
  node_name: string;
}

interface DeleteNodeParams {
  node_path: string;
}

interface UpdateNodePropertyParams {
  node_path: string;
  property: string;
  value: any;
}

interface GetNodePropertiesParams {
  node_path: string;
}

interface ListNodesParams {
  parent_path: string;
}

interface LoadSpriteParams {
  node_path: string;
  texture_path: string;
}

interface ImportAnimatedSpriteParams {
  node_path: string;
  texture_path: string;
  metadata_path: string;
  animation_name?: string;
  fps?: number;
  autoplay?: boolean;
  use_tags?: boolean;
}

interface ImportedAnimation {
  name: string;
  frame_count: number;
  direction: string;
  speed: number;
}

/**
 * Definition for node tools - operations that manipulate nodes in the scene tree
 */
export const nodeTools: MCPTool[] = [
  {
    name: 'create_node',
    description: 'Create a new node in the Godot scene tree',
    parameters: z.object({
      parent_path: z.string()
        .describe('Path to the parent node where the new node will be created (e.g. "/root", "/root/MainScene")'),
      node_type: z.string()
        .describe('Type of node to create (e.g. "Node2D", "Sprite2D", "Label")'),
      node_name: z.string()
        .describe('Name for the new node'),
    }),
    execute: async ({ parent_path, node_type, node_name }: CreateNodeParams): Promise<string> => {
      const godot = getGodotConnection();
      
      try {
        const result = await godot.sendCommand<CommandResult>('create_node', {
          parent_path,
          node_type,
          node_name,
        });
        
        return `Created ${node_type} node named "${node_name}" at ${result.node_path}`;
      } catch (error) {
        throw new Error(`Failed to create node: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'delete_node',
    description: 'Delete a node from the Godot scene tree',
    parameters: z.object({
      node_path: z.string()
        .describe('Path to the node to delete (e.g. "/root/MainScene/Player")'),
    }),
    execute: async ({ node_path }: DeleteNodeParams): Promise<string> => {
      const godot = getGodotConnection();
      
      try {
        await godot.sendCommand('delete_node', { node_path });
        return `Deleted node at ${node_path}`;
      } catch (error) {
        throw new Error(`Failed to delete node: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'update_node_property',
    description: 'Update a property of a node in the Godot scene tree',
    parameters: z.object({
      node_path: z.string()
        .describe('Path to the node to update (e.g. "/root/MainScene/Player")'),
      property: z.string()
        .describe('Name of the property to update (e.g. "position", "text", "modulate")'),
      value: z.any()
        .describe('New value for the property'),
    }),
    execute: async ({ node_path, property, value }: UpdateNodePropertyParams): Promise<string> => {
      const godot = getGodotConnection();
      
      try {
        const result = await godot.sendCommand<CommandResult>('update_node_property', {
          node_path,
          property,
          value,
        });
        
        return `Updated property "${property}" of node at ${node_path} to ${JSON.stringify(value)}`;
      } catch (error) {
        throw new Error(`Failed to update node property: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'get_node_properties',
    description: 'Get all properties of a node in the Godot scene tree',
    parameters: z.object({
      node_path: z.string()
        .describe('Path to the node to inspect (e.g. "/root/MainScene/Player")'),
    }),
    execute: async ({ node_path }: GetNodePropertiesParams): Promise<string> => {
      const godot = getGodotConnection();
      
      try {
        const result = await godot.sendCommand<CommandResult>('get_node_properties', { node_path });
        
        // Format properties for display
        const formattedProperties = Object.entries(result.properties)
          .map(([key, value]) => `${key}: ${JSON.stringify(value)}`)
          .join('\n');
        
        return `Properties of node at ${node_path}:\n\n${formattedProperties}`;
      } catch (error) {
        throw new Error(`Failed to get node properties: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'list_nodes',
    description: 'List all child nodes under a parent node in the Godot scene tree',
    parameters: z.object({
      parent_path: z.string()
        .describe('Path to the parent node (e.g. "/root", "/root/MainScene")'),
    }),
    execute: async ({ parent_path }: ListNodesParams): Promise<string> => {
      const godot = getGodotConnection();
      
      try {
        const result = await godot.sendCommand<CommandResult>('list_nodes', { parent_path });
        
        if (result.children.length === 0) {
          return `No child nodes found under ${parent_path}`;
        }
        
        // Format children for display
        const formattedChildren = result.children
          .map((child: any) => `${child.name} (${child.type}) - ${child.path}`)
          .join('\n');
        
        return `Children of node at ${parent_path}:\n\n${formattedChildren}`;
      } catch (error) {
        throw new Error(`Failed to list nodes: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'load_sprite',
    description: 'Load a texture into a Sprite2D or TextureRect node',
    parameters: z.object({
      node_path: z.string()
        .describe('Path to the target Sprite2D or TextureRect node'),
      texture_path: z.string()
        .describe('Godot resource path to the texture (e.g. "res://assets/player.png")'),
    }),
    execute: async ({ node_path, texture_path }: LoadSpriteParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        await godot.sendCommand('load_sprite', {
          node_path,
          texture_path,
        });
        return `Loaded texture ${texture_path} into ${node_path}`;
      } catch (error) {
        throw new Error(`Failed to load sprite: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'import_animated_sprite',
    description:
      'Create SpriteFrames on an AnimatedSprite2D from an Aseprite spritesheet and JSON metadata. ' +
      'When the metadata carries Aseprite tags (exported with list_tags), one Godot animation is ' +
      'created per tag, honouring each tag\'s playback direction. Per-frame durations from Aseprite ' +
      'are preserved; fps is only used as a fallback when the metadata has no durations.',
    parameters: z.object({
      node_path: z.string()
        .describe('Path to the AnimatedSprite2D node'),
      texture_path: z.string()
        .describe('Godot resource path to the spritesheet texture (e.g. "res://assets/player_sheet.png")'),
      metadata_path: z.string()
        .describe('Godot resource path to the Aseprite JSON metadata (e.g. "res://assets/player_sheet.json")'),
      animation_name: z.string().default('default')
        .describe('Animation name to use when the metadata has no tags. Ignored when tags are present.'),
      fps: z.number().default(12)
        .describe('Fallback playback speed, used only when the metadata carries no per-frame durations'),
      autoplay: z.boolean().default(true)
        .describe('Whether the first imported animation should autoplay'),
      use_tags: z.boolean().default(true)
        .describe('Create one animation per Aseprite tag. Set false to import every frame as a single animation.'),
    }),
    execute: async ({
      node_path,
      texture_path,
      metadata_path,
      animation_name = 'default',
      fps = 12,
      autoplay = true,
      use_tags = true,
    }: ImportAnimatedSpriteParams): Promise<string> => {
      const godot = getGodotConnection();

      try {
        const result = await godot.sendCommand<CommandResult>('import_animated_sprite', {
          node_path,
          texture_path,
          metadata_path,
          animation_name,
          fps,
          autoplay,
          use_tags,
        });

        const animations = (result.animations ?? []) as ImportedAnimation[];
        if (animations.length > 1) {
          const summary = animations
            .map((a) => `${a.name} (${a.frame_count} frames, ${a.speed.toFixed(1)} fps, ${a.direction})`)
            .join(', ');
          return `Imported ${result.frame_count} frames into ${node_path} as ${animations.length} animations: ${summary}`;
        }

        const only = animations[0];
        const name = only?.name ?? animation_name;
        const speed = only ? `, ${only.speed.toFixed(1)} fps` : '';
        return `Imported ${result.frame_count} frames into ${node_path} as animation "${name}"${speed}`;
      } catch (error) {
        throw new Error(`Failed to import animated sprite: ${(error as Error).message}`);
      }
    },
  },
];
