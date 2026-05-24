import { z } from 'zod';
import { MCPTool } from '../utils/types.js';
import {
  getAllApplicationInfo,
  getGodotInfo,
  getAsepriteInfo,
  resolveApplicationPath,
} from '../utils/pathResolver.js';
import * as os from 'os';
import * as process from 'process';

/**
 * Get information about all detected game development applications.
 */
export const systemInfoTools: MCPTool[] = [
  {
    name: 'get_application_info',
    description: 'Get information about detected game development applications (Godot, Aseprite)',
    parameters: z.object({}),
    execute: async (): Promise<string> => {
      const info = getAllApplicationInfo();

      const lines: string[] = [];
      lines.push('=== Game Development Tools Detected ===');
      lines.push('');

      for (const [appName, details] of Object.entries(info)) {
        const status = details.found ? '✓' : '✗';
        lines.push(`${status} ${appName.charAt(0).toUpperCase() + appName.slice(1)}:`);
        lines.push(`  Path: ${details.path}`);
        lines.push(`  Version: ${details.version}`);
        lines.push('');
      }

      return lines.join('\n');
    },
  },

  {
    name: 'get_godot_info',
    description: 'Get Godot executable path and version',
    parameters: z.object({}),
    execute: async (): Promise<string> => {
      const info = getGodotInfo();
      const envPath = process.env.GODOT_PATH;

      const lines: string[] = [];
      lines.push('=== Godot Information ===');

      if (envPath) {
        lines.push(`GODOT_PATH (env): ${envPath}`);
      }

      if (info.found) {
        lines.push(`Detected path: ${info.path}`);
        lines.push(`Version: ${info.version}`);
        lines.push('  ✓ Ready to use');
      } else {
        lines.push('Godot 4.x not found in common locations.');
        lines.push('  Download from: https://godotengine.org/download');
        lines.push('  Or set GODOT_PATH environment variable.');
      }

      return lines.join('\n');
    },
  },

  {
    name: 'get_aseprite_info',
    description: 'Get Aseprite executable path and version',
    parameters: z.object({}),
    execute: async (): Promise<string> => {
      const info = getAsepriteInfo();
      const envPath = process.env.ASEPRITE_PATH;

      const lines: string[] = [];
      lines.push('=== Aseprite Information ===');

      if (envPath) {
        lines.push(`ASEPRITE_PATH (env): ${envPath}`);
      }

      if (info.found) {
        lines.push(`Detected path: ${info.path}`);
        lines.push(`Version: ${info.version}`);
        lines.push('  ✓ Ready to use');
      } else {
        lines.push('Aseprite not found in common locations.');
        lines.push('  Install from: https://aseprite.org');
        lines.push('  Or set ASEPRITE_PATH environment variable.');
      }

      return lines.join('\n');
    },
  },

  {
    name: 'get_system_info',
    description: 'Get system information for troubleshooting MCP connections',
    parameters: z.object({}),
    execute: async (): Promise<string> => {
      const lines: string[] = [];
      lines.push('=== System Information ===');
      lines.push(`Platform: ${os.platform()} ${os.release()}`);
      lines.push(`Node.js: ${process.version}`);
      lines.push(`Architecture: ${os.arch()}`);
      lines.push('');
      lines.push('=== Environment Variables ===');

      const envVars = {
        'ASEPRITE_PATH': process.env.ASEPRITE_PATH || 'Not set',
        'GODOT_PATH': process.env.GODOT_PATH || 'Not set',
        'PATH': process.env.PATH?.substring(0, 100) + '...' || 'Not set',
      };

      for (const [varName, value] of Object.entries(envVars)) {
        lines.push(`${varName}: ${value}`);
      }

      return lines.join('\n');
    },
  },

  {
    name: 'resolve_application_path',
    description: 'Resolve the full path to a game development application (aseprite or godot)',
    parameters: z.object({
      application: z.string()
        .describe('The application name (aseprite or godot)'),
    }),
    execute: async ({ application }: { application: string }): Promise<string> => {
      const info = resolveApplicationPath(application);

      if (info.found) {
        return `${application.charAt(0).toUpperCase() + application.slice(1)} found at: ${info.path}`;
      }

      return `${application.charAt(0).toUpperCase() + application.slice(1)} not found. Common locations checked.`;
    },
  },
];