import { z } from 'zod';
import * as fs from 'fs';
import * as path from 'path';
import { MCPTool } from '../utils/types.js';
import {
  readExportPresets,
  resolveGodotBinary,
  resolveProjectDir,
  runGodot,
  runHeadlessScript,
} from '../utils/godot_cli.js';

/**
 * Tools that drive Godot through its CLI instead of the editor plugin.
 *
 * Everything else in this server requires the editor to be open with the
 * WebSocket bridge running. These do not, which is what makes exporting a
 * build, validating a project in CI, or inspecting an unopened project
 * possible at all.
 */

/** Trim engine chatter down to something worth putting in a tool result. */
function summariseOutput(text: string, limit = 4000): string {
  const trimmed = text.trim();
  if (trimmed.length <= limit) return trimmed;
  return `${trimmed.slice(0, limit)}\n... (${trimmed.length - limit} more characters)`;
}

export const headlessTools: MCPTool[] = [
  {
    name: 'godot_headless_info',
    description:
      'Report the Godot binary the server will use for headless work, its version, and ' +
      'whether it is reachable. Run this first when a headless tool fails.',
    parameters: z.object({}),
    execute: async (): Promise<string> => {
      let binary: string;
      try {
        binary = resolveGodotBinary();
      } catch (error) {
        return `Godot not found: ${(error as Error).message}`;
      }

      const result = await runGodot(['--version'], { timeoutMs: 15_000 });
      const version = (result.stdout || result.stderr).trim().split('\n')[0] || 'unknown';

      return JSON.stringify(
        {
          binary,
          version,
          reachable: result.ok,
          note: result.ok
            ? 'Headless tools are available.'
            : 'The binary was found but did not run. Check permissions and architecture.',
        },
        null,
        2
      );
    },
  },

  {
    name: 'validate_project_headless',
    description:
      'Open a Godot project headlessly and report import/parse errors without touching the ' +
      'editor. Use to check a project is healthy before committing, or in CI.',
    parameters: z.object({
      project_path: z.string().describe('Path to the project folder or its project.godot'),
      timeout_seconds: z.number().default(120).describe('Give up after this many seconds'),
    }),
    execute: async ({
      project_path,
      timeout_seconds = 120,
    }: {
      project_path: string;
      timeout_seconds?: number;
    }): Promise<string> => {
      let projectDir: string;
      try {
        projectDir = resolveProjectDir(project_path);
      } catch (error) {
        return (error as Error).message;
      }

      // --quit exits after the first frame, which is enough for Godot to
      // import every resource and report anything that fails to parse. But it
      // needs a main scene to render that frame: without one, Godot prints
      // "Can't run project" and then -- when spawned with piped stdio -- never
      // exits, so the run used to burn the whole timeout and report "project
      // may be very large". --import does the same import pass and exits
      // cleanly, so projects with no main scene are validated with that.
      let projectFile = '';
      try {
        projectFile = fs.readFileSync(path.join(projectDir, 'project.godot'), 'utf8');
      } catch {
        // resolveProjectDir already proved it exists; a read failure here will
        // surface from the Godot run itself.
      }
      const hasMainScene = /^\s*run\/main_scene\s*=/m.test(projectFile);
      const modeFlag = hasMainScene ? '--quit' : '--import';

      const result = await runGodot(['--headless', '--path', projectDir, modeFlag], {
        timeoutMs: timeout_seconds * 1000,
      });

      const combined = `${result.stdout}\n${result.stderr}`;
      const problems = combined
        .split('\n')
        .filter((line) => /ERROR|SCRIPT ERROR|Failed to load|Parse Error|Cannot open/i.test(line))
        .map((line) => line.trim());

      if (result.timedOut) {
        return `Validation timed out after ${timeout_seconds}s (ran with ${modeFlag}). Project may be very large, or the run hung.`;
      }

      return JSON.stringify(
        {
          project: projectDir,
          mode: modeFlag,
          main_scene_defined: hasMainScene,
          exit_code: result.code,
          healthy: result.ok && problems.length === 0,
          problem_count: problems.length,
          problems: problems.slice(0, 50),
          output: problems.length === 0 ? summariseOutput(combined, 800) : undefined,
        },
        null,
        2
      );
    },
  },

  {
    name: 'list_export_presets',
    description:
      'List the export presets defined in a project (from export_presets.cfg). ' +
      'export_project needs one of these names.',
    parameters: z.object({
      project_path: z.string().describe('Path to the project folder or its project.godot'),
    }),
    execute: async ({ project_path }: { project_path: string }): Promise<string> => {
      let projectDir: string;
      try {
        projectDir = resolveProjectDir(project_path);
      } catch (error) {
        return (error as Error).message;
      }

      const presets = readExportPresets(projectDir);
      if (presets.length === 0) {
        return (
          `No export presets found in ${projectDir}. ` +
          'Create one in the editor via Project > Export before exporting.'
        );
      }
      return JSON.stringify({ project: projectDir, presets }, null, 2);
    },
  },

  {
    name: 'export_project',
    description:
      'Export a Godot project to a runnable build using a named preset, headlessly. ' +
      'This is what turns a scene tree into something you can actually run.',
    parameters: z.object({
      project_path: z.string().describe('Path to the project folder or its project.godot'),
      preset_name: z.string().describe('Preset name from list_export_presets'),
      output_path: z.string().describe('Output file path for the build'),
      debug: z
        .boolean()
        .default(false)
        .describe('Export a debug build (includes debug symbols and the remote debugger)'),
      timeout_seconds: z.number().default(600).describe('Give up after this many seconds'),
    }),
    execute: async ({
      project_path,
      preset_name,
      output_path,
      debug = false,
      timeout_seconds = 600,
    }: {
      project_path: string;
      preset_name: string;
      output_path: string;
      debug?: boolean;
      timeout_seconds?: number;
    }): Promise<string> => {
      let projectDir: string;
      try {
        projectDir = resolveProjectDir(project_path);
      } catch (error) {
        return (error as Error).message;
      }

      const presets = readExportPresets(projectDir);
      if (presets.length > 0 && !presets.includes(preset_name)) {
        return `Unknown preset '${preset_name}'. Available: ${presets.join(', ')}`;
      }

      const absoluteOutput = path.resolve(output_path);
      const outputDir = path.dirname(absoluteOutput);
      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
      }

      const flag = debug ? '--export-debug' : '--export-release';
      const result = await runGodot(
        ['--headless', '--path', projectDir, flag, preset_name, absoluteOutput],
        { timeoutMs: timeout_seconds * 1000 }
      );

      if (result.timedOut) {
        return `Export timed out after ${timeout_seconds}s.`;
      }

      const produced = fs.existsSync(absoluteOutput);
      if (!result.ok || !produced) {
        // Godot exits 0 on some export failures, so the file check is what
        // actually decides success here.
        return [
          `Export failed (exit ${result.code}, output ${produced ? 'exists' : 'missing'}).`,
          'Godot output:',
          summariseOutput(`${result.stdout}\n${result.stderr}`),
          '',
          'Common cause: the export template for this preset is not installed. ' +
            'Install it in the editor via Editor > Manage Export Templates.',
        ].join('\n');
      }

      const size = fs.statSync(absoluteOutput).size;
      return JSON.stringify(
        {
          project: projectDir,
          preset: preset_name,
          output: absoluteOutput,
          build: debug ? 'debug' : 'release',
          bytes: size,
        },
        null,
        2
      );
    },
  },

  {
    name: 'run_headless_script',
    description:
      'Run a GDScript snippet against a project headlessly and return its output. ' +
      'The snippet runs inside a SceneTree._init(), so ProjectSettings, ResourceLoader and ' +
      'the filesystem are all available. Use print() to return data. ' +
      'Escape hatch for anything no other tool covers, and works with the editor closed.',
    parameters: z.object({
      project_path: z.string().describe('Path to the project folder or its project.godot'),
      script: z
        .string()
        .describe('GDScript body. Indentation is added automatically; use print() for output.'),
      timeout_seconds: z.number().default(60).describe('Give up after this many seconds'),
    }),
    execute: async ({
      project_path,
      script,
      timeout_seconds = 60,
    }: {
      project_path: string;
      script: string;
      timeout_seconds?: number;
    }): Promise<string> => {
      let projectDir: string;
      try {
        projectDir = resolveProjectDir(project_path);
      } catch (error) {
        return (error as Error).message;
      }

      const result = await runHeadlessScript(projectDir, script, {
        timeoutMs: timeout_seconds * 1000,
      });

      if (result.timedOut) {
        return `Script timed out after ${timeout_seconds}s.`;
      }

      const errors = result.stderr
        .split('\n')
        .filter((line) => /SCRIPT ERROR|Parse Error|ERROR/i.test(line))
        .map((line) => line.trim());

      if (errors.length > 0) {
        return `Script reported errors:\n${errors.slice(0, 20).join('\n')}\n\nOutput:\n${summariseOutput(result.stdout)}`;
      }

      return summariseOutput(result.stdout) || '(script produced no output)';
    },
  },

  {
    name: 'import_project_assets',
    description:
      'Force Godot to (re)import a project\'s assets headlessly. Run after writing new PNG or ' +
      'JSON files into the project from Aseprite, so Godot picks them up without the editor.',
    parameters: z.object({
      project_path: z.string().describe('Path to the project folder or its project.godot'),
      timeout_seconds: z.number().default(300).describe('Give up after this many seconds'),
    }),
    execute: async ({
      project_path,
      timeout_seconds = 300,
    }: {
      project_path: string;
      timeout_seconds?: number;
    }): Promise<string> => {
      let projectDir: string;
      try {
        projectDir = resolveProjectDir(project_path);
      } catch (error) {
        return (error as Error).message;
      }

      const result = await runGodot(['--headless', '--path', projectDir, '--import'], {
        timeoutMs: timeout_seconds * 1000,
      });

      if (result.timedOut) {
        return `Import timed out after ${timeout_seconds}s.`;
      }

      const combined = `${result.stdout}\n${result.stderr}`;
      const imported = (combined.match(/Import(ing)?\s/gi) || []).length;
      // Scoped to resource problems. A bare /ERROR/ match also catches
      // editor-plugin chatter -- notably the MCP plugin failing to bind its
      // WebSocket port when an editor is already running -- and reports a
      // perfectly good import as failed.
      const failures = combined
        .split('\n')
        .filter((line) =>
          /Failed to load resource|Cannot open file|Failed to import|Error importing|Unrecognized (extension|file)/i.test(
            line
          )
        )
        .map((line) => line.trim());

      return JSON.stringify(
        {
          project: projectDir,
          exit_code: result.code,
          ok: result.ok && failures.length === 0,
          import_lines_seen: imported,
          failures: failures.slice(0, 30),
        },
        null,
        2
      );
    },
  },
];
