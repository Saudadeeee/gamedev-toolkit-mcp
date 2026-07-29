import { z } from 'zod';

/**
 * A tool result. Plain text for most tools; a content array when a tool
 * returns something the model needs to see rather than read, such as a
 * rendered screenshot.
 */
export type MCPToolResult =
  | string
  | {
      content: Array<
        | { type: 'text'; text: string }
        | { type: 'image'; data: string; mimeType: string }
      >;
    };

/**
 * Interface for FastMCP tool definition
 */
export interface MCPTool<T = any> {
  name: string;
  description: string;
  parameters: z.ZodType<T>;
  execute: (args: T) => Promise<MCPToolResult>;
}

/**
 * Generic response from a Godot command
 */
export interface CommandResult {
  [key: string]: any;
}