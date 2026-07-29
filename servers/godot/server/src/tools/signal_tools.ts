import { z } from 'zod';
import { getGodotConnection } from '../utils/godot_connection.js';
import { CommandResult, MCPTool } from '../utils/types.js';

/**
 * Signal wiring and node groups.
 *
 * Signals are how Godot nodes communicate; without these tools a scene tree
 * and its scripts can be built but never connected, so nothing actually
 * happens when the game runs.
 *
 * Input-map tools deliberately live in project_config_tools.ts instead --
 * add_input_action + add_input_event already cover it there, and a second
 * implementation would just shadow the first (FastMCP keeps whichever
 * registers last, silently).
 */

export const signalTools: MCPTool[] = [
  {
    name: 'list_signals',
    description:
      'List the signals a node can emit. Returns the ones declared on its script by default; ' +
      'pass include_inherited to also get the dozens Godot defines on every Node.',
    parameters: z.object({
      node_path: z.string().describe('Path to the node (e.g. "/root/Main/Player")'),
      include_inherited: z
        .boolean()
        .default(false)
        .describe('Include built-in engine signals as well as script-declared ones'),
    }),
    execute: async ({
      node_path,
      include_inherited = false,
    }: {
      node_path: string;
      include_inherited?: boolean;
    }): Promise<string> => {
      const godot = getGodotConnection();
      try {
        const result = await godot.sendCommand<CommandResult>('list_signals', {
          node_path,
          include_inherited,
        });
        return JSON.stringify(result, null, 2);
      } catch (error) {
        throw new Error(`Failed to list signals: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'list_connections',
    description:
      'List the existing signal connections on a node, including which are persistent ' +
      '(saved into the scene) and which are runtime-only.',
    parameters: z.object({
      node_path: z.string().describe('Path to the node'),
      signal_name: z
        .string()
        .default('')
        .describe('Restrict to one signal. Empty lists connections for all of them.'),
    }),
    execute: async ({
      node_path,
      signal_name = '',
    }: {
      node_path: string;
      signal_name?: string;
    }): Promise<string> => {
      const godot = getGodotConnection();
      try {
        const result = await godot.sendCommand<CommandResult>('list_connections', {
          node_path,
          signal_name,
        });
        return JSON.stringify(result, null, 2);
      } catch (error) {
        throw new Error(`Failed to list connections: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'connect_signal',
    description:
      'Connect a signal on one node to a method on another. The connection is persistent, ' +
      'so it is saved into the scene file the way an editor-made connection is. ' +
      'The target method must already exist -- create it with the script tools first.',
    parameters: z.object({
      from_node_path: z.string().describe('Node that emits the signal'),
      signal_name: z.string().describe('Signal to connect (e.g. "pressed", "body_entered")'),
      to_node_path: z.string().describe('Node holding the receiving method'),
      method_name: z.string().describe('Method to call when the signal fires'),
      deferred: z
        .boolean()
        .default(false)
        .describe('Call at idle time instead of immediately. Needed when the handler changes the scene tree.'),
      one_shot: z.boolean().default(false).describe('Disconnect automatically after the first emission'),
    }),
    execute: async ({
      from_node_path,
      signal_name,
      to_node_path,
      method_name,
      deferred = false,
      one_shot = false,
    }: {
      from_node_path: string;
      signal_name: string;
      to_node_path: string;
      method_name: string;
      deferred?: boolean;
      one_shot?: boolean;
    }): Promise<string> => {
      const godot = getGodotConnection();
      try {
        await godot.sendCommand<CommandResult>('connect_signal', {
          from_node_path,
          signal_name,
          to_node_path,
          method_name,
          deferred,
          one_shot,
        });
        const modifiers = [deferred && 'deferred', one_shot && 'one-shot'].filter(Boolean);
        const suffix = modifiers.length ? ` (${modifiers.join(', ')})` : '';
        return `Connected ${from_node_path}.${signal_name} -> ${to_node_path}.${method_name}${suffix}`;
      } catch (error) {
        throw new Error(`Failed to connect signal: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'disconnect_signal',
    description: 'Remove an existing signal connection between two nodes.',
    parameters: z.object({
      from_node_path: z.string().describe('Node that emits the signal'),
      signal_name: z.string().describe('Signal to disconnect'),
      to_node_path: z.string().describe('Node holding the receiving method'),
      method_name: z.string().describe('Method currently connected'),
    }),
    execute: async ({
      from_node_path,
      signal_name,
      to_node_path,
      method_name,
    }: {
      from_node_path: string;
      signal_name: string;
      to_node_path: string;
      method_name: string;
    }): Promise<string> => {
      const godot = getGodotConnection();
      try {
        await godot.sendCommand<CommandResult>('disconnect_signal', {
          from_node_path,
          signal_name,
          to_node_path,
          method_name,
        });
        return `Disconnected ${from_node_path}.${signal_name} from ${to_node_path}.${method_name}`;
      } catch (error) {
        throw new Error(`Failed to disconnect signal: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'add_node_to_group',
    description:
      'Add a node to a group so it can be found at runtime with get_nodes_in_group. ' +
      'Membership is persistent, so it is written into the scene file.',
    parameters: z.object({
      node_path: z.string().describe('Path to the node'),
      group_name: z.string().describe('Group name (e.g. "enemies", "pickups")'),
    }),
    execute: async ({
      node_path,
      group_name,
    }: {
      node_path: string;
      group_name: string;
    }): Promise<string> => {
      const godot = getGodotConnection();
      try {
        const result = await godot.sendCommand<CommandResult>('add_node_to_group', {
          node_path,
          group_name,
        });
        return `Added ${node_path} to group "${group_name}" (now in: ${(result.groups ?? []).join(', ')})`;
      } catch (error) {
        throw new Error(`Failed to add node to group: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'remove_node_from_group',
    description: 'Remove a node from a group.',
    parameters: z.object({
      node_path: z.string().describe('Path to the node'),
      group_name: z.string().describe('Group name'),
    }),
    execute: async ({
      node_path,
      group_name,
    }: {
      node_path: string;
      group_name: string;
    }): Promise<string> => {
      const godot = getGodotConnection();
      try {
        await godot.sendCommand<CommandResult>('remove_node_from_group', {
          node_path,
          group_name,
        });
        return `Removed ${node_path} from group "${group_name}"`;
      } catch (error) {
        throw new Error(`Failed to remove node from group: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'list_nodes_in_group',
    description:
      'List nodes in a group within the open scene, or every group in the scene when no ' +
      'group name is given.',
    parameters: z.object({
      group_name: z
        .string()
        .default('')
        .describe('Group to filter by. Empty returns every grouped node plus a group census.'),
    }),
    execute: async ({ group_name = '' }: { group_name?: string }): Promise<string> => {
      const godot = getGodotConnection();
      try {
        const result = await godot.sendCommand<CommandResult>('list_nodes_in_group', {
          group_name,
        });
        return JSON.stringify(result, null, 2);
      } catch (error) {
        throw new Error(`Failed to list nodes in group: ${(error as Error).message}`);
      }
    },
  },
];
