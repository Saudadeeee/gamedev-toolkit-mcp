import { z } from 'zod';
import { imageContent } from 'fastmcp';
import { getGodotConnection } from '../utils/godot_connection.js';
import { CommandResult, MCPTool } from '../utils/types.js';

/**
 * Visual feedback tools.
 *
 * Without these the assistant builds a scene and never sees it -- it has to
 * infer the result from node properties, which is how invisible, offscreen or
 * wrongly-layered nodes survive. These return an actual image, so the model
 * looks at what it made.
 */

interface CaptureResult extends CommandResult {
  output_path: string;
  absolute_path: string;
  width: number;
  height: number;
  base64_png?: string;
}

/**
 * Build the tool response. When the plugin returned base64 the image is
 * handed back as image content so the model can see it; otherwise the caller
 * gets the path to open.
 */
async function buildResponse(result: CaptureResult, label: string) {
  const summary = `${label} -> ${result.absolute_path} (${result.width}x${result.height})`;

  if (!result.base64_png) {
    return summary;
  }

  return {
    content: [
      { type: 'text' as const, text: summary },
      await imageContent({ buffer: Buffer.from(result.base64_png, 'base64') }),
    ],
  };
}

export const captureTools: MCPTool[] = [
  {
    name: 'capture_scene_render',
    description:
      'Render a scene offscreen and return the image, so you can see what you built. ' +
      'Renders the currently open scene by default, or any scene by path. Does not require ' +
      'the game to be running and does not disturb the editor. Use this to check layout, ' +
      'z-order, visibility and sprite placement instead of inferring them from properties.',
    parameters: z.object({
      scene_path: z
        .string()
        .default('')
        .describe('Scene to render (e.g. "res://scenes/level.tscn"). Empty renders the open scene.'),
      width: z.number().default(512).describe('Render width in pixels'),
      height: z.number().default(512).describe('Render height in pixels'),
      transparent: z.boolean().default(true).describe('Transparent background instead of opaque'),
      output_path: z
        .string()
        .default('')
        .describe('Where to save the PNG. Empty writes to res://.godot/mcp_capture.png'),
      include_image: z
        .boolean()
        .default(true)
        .describe('Return the rendered image itself, not just the path'),
      fit_content: z
        .boolean()
        .default(true)
        .describe(
          'Frame what was actually drawn. Without this a 2D scene renders from world (0,0) ' +
            'at 1:1, so a small sprite is a speck in the corner. Turn off to see raw world ' +
            'coordinates.'
        ),
      padding: z
        .number()
        .default(0.15)
        .describe('Empty margin around the framed content, as a fraction of its size'),
      max_zoom: z
        .number()
        .default(16)
        .describe('Cap on magnification when framing, so a tiny sprite is not blown up past this'),
      nearest_filter: z
        .boolean()
        .default(true)
        .describe(
          'Render with nearest-neighbour filtering. On by default: a SubViewport does not ' +
            'inherit the project texture filter, and magnified pixel art comes out blurred ' +
            'without it. Turn off for non-pixel-art scenes.'
        ),
    }),
    execute: async ({
      scene_path = '',
      width = 512,
      height = 512,
      transparent = true,
      output_path = '',
      include_image = true,
      fit_content = true,
      padding = 0.15,
      max_zoom = 16,
      nearest_filter = true,
    }) => {
      const godot = getGodotConnection();
      try {
        const result = await godot.sendCommand<CaptureResult>('capture_scene_render', {
          scene_path,
          width,
          height,
          transparent,
          output_path,
          include_base64: include_image,
          fit_content,
          padding,
          max_zoom,
          nearest_filter,
        });
        return await buildResponse(result, `Rendered ${scene_path || 'the open scene'}`);
      } catch (error) {
        throw new Error(`Failed to render scene: ${(error as Error).message}`);
      }
    },
  },

  {
    name: 'capture_editor_viewport',
    description:
      'Capture what the editor viewport is currently showing, including the camera position ' +
      'and zoom the user has set. Use capture_scene_render instead when you want a clean ' +
      'render of the scene itself rather than the editor view.',
    parameters: z.object({
      dimension: z.enum(['2d', '3d']).default('2d').describe('Which editor viewport to grab'),
      output_path: z
        .string()
        .default('')
        .describe('Where to save the PNG. Empty writes to res://.godot/mcp_capture.png'),
      include_image: z
        .boolean()
        .default(true)
        .describe('Return the captured image itself, not just the path'),
    }),
    execute: async ({ dimension = '2d', output_path = '', include_image = true }) => {
      const godot = getGodotConnection();
      try {
        const result = await godot.sendCommand<CaptureResult>('capture_editor_viewport', {
          dimension,
          output_path,
          include_base64: include_image,
        });
        return await buildResponse(result, `Captured the ${dimension} editor viewport`);
      } catch (error) {
        throw new Error(`Failed to capture editor viewport: ${(error as Error).message}`);
      }
    },
  },
];
