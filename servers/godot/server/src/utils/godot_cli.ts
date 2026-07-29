/**
 * Headless Godot invocation.
 *
 * Every other tool in this server needs the Godot editor open with the plugin
 * running, because it talks over the WebSocket bridge. That is the right
 * design for live scene manipulation, but it makes a whole class of work
 * impossible: exporting a build, validating a project in CI, or inspecting a
 * project nobody has opened yet.
 *
 * These helpers shell out to the Godot binary with `--headless` instead, so
 * they work with no editor at all.
 */

import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { getGodotInfo } from './pathResolver.js';

export interface GodotRunResult {
  ok: boolean;
  code: number | null;
  stdout: string;
  stderr: string;
  timedOut: boolean;
  command: string;
}

/** Default ceiling for a headless run. Exports of a large project are slow. */
const DEFAULT_TIMEOUT_MS = 180_000;

/**
 * Resolve the Godot executable, preferring an explicit GODOT_PATH.
 * Throws with actionable text rather than returning a bare null, so the
 * failure reaches the caller as a message they can act on.
 */
export function resolveGodotBinary(): string {
  const fromEnv = process.env.GODOT_PATH;
  if (fromEnv && fs.existsSync(fromEnv)) return fromEnv;

  const detected = getGodotInfo();
  if (detected.found) return detected.path;

  throw new Error(
    'Godot executable not found. Set GODOT_PATH to the Godot 4 binary, or install it ' +
      'somewhere the path resolver looks (Program Files, C:/Godot, /Applications, $PATH).'
  );
}

/**
 * Locate the project.godot for a given path.
 * Accepts either the directory or the file itself.
 */
export function resolveProjectDir(projectPath: string): string {
  const candidate = path.resolve(projectPath);
  const asFile = candidate.endsWith('project.godot') ? candidate : path.join(candidate, 'project.godot');

  if (!fs.existsSync(asFile)) {
    throw new Error(`No project.godot found at ${asFile}`);
  }
  return path.dirname(asFile);
}

/** Run the Godot binary with the given arguments and capture its output. */
export function runGodot(
  args: string[],
  options: { cwd?: string; timeoutMs?: number } = {}
): Promise<GodotRunResult> {
  const binary = resolveGodotBinary();
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const command = `${binary} ${args.join(' ')}`;

  return new Promise((resolve) => {
    const child = spawn(binary, args, {
      cwd: options.cwd,
      // Godot writes diagnostics to stderr and script output to stdout; both
      // matter, so neither is discarded.
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    let timedOut = false;

    const timer = setTimeout(() => {
      timedOut = true;
      child.kill();
    }, timeoutMs);

    child.stdout.on('data', (d) => (stdout += d.toString()));
    child.stderr.on('data', (d) => (stderr += d.toString()));

    child.on('error', (err) => {
      clearTimeout(timer);
      resolve({
        ok: false,
        code: null,
        stdout,
        stderr: `${stderr}\n${err.message}`.trim(),
        timedOut,
        command,
      });
    });

    child.on('close', (code) => {
      clearTimeout(timer);
      resolve({ ok: code === 0 && !timedOut, code, stdout, stderr, timedOut, command });
    });
  });
}

/**
 * Run a GDScript snippet headlessly against a project.
 *
 * The script is written into the project as a temporary `.gd` file because
 * Godot's `--script` only accepts a path inside the project's resource
 * filesystem. It is removed afterwards even when the run fails.
 */
export async function runHeadlessScript(
  projectDir: string,
  scriptBody: string,
  options: { timeoutMs?: number } = {}
): Promise<GodotRunResult> {
  const tmpName = `.mcp_headless_${process.pid}_${Date.now()}.gd`;
  const tmpPath = path.join(projectDir, tmpName);

  const wrapped = scriptBody.includes('func _init')
    ? scriptBody
    : `@tool\nextends SceneTree\n\nfunc _init():\n${scriptBody
        .split('\n')
        .map((line) => `\t${line}`)
        .join('\n')}\n\tquit()\n`;

  fs.writeFileSync(tmpPath, wrapped, 'utf8');

  try {
    return await runGodot(['--headless', '--path', projectDir, '--script', tmpName], {
      cwd: projectDir,
      timeoutMs: options.timeoutMs,
    });
  } finally {
    try {
      fs.unlinkSync(tmpPath);
    } catch {
      /* best effort: a leftover temp script is noise, not a failure */
    }
  }
}

/** Read the export presets defined for a project, if any. */
export function readExportPresets(projectDir: string): string[] {
  const presetFile = path.join(projectDir, 'export_presets.cfg');
  if (!fs.existsSync(presetFile)) return [];

  const contents = fs.readFileSync(presetFile, 'utf8');
  const names: string[] = [];
  const pattern = /^name\s*=\s*"([^"]*)"/gm;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(contents)) !== null) {
    names.push(match[1]);
  }
  return names;
}
