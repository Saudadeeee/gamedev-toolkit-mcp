// Every headless tool, against a real Godot binary and a real project.
//
// These need no editor: the point of the headless path is that it works with
// Godot closed. They do need the binary, so set GODOT_PATH if auto-detection
// misses it (check with godot_headless_info).
//
//     node tests/headless_test.mjs <path-to-a-godot-project>
import { headlessTools } from '../dist/tools/headless_tools.js';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

const DEMO = process.argv[2];
if (!DEMO) {
  console.error('usage: node tests/headless_test.mjs <path-to-a-godot-project>');
  process.exit(2);
}
const results = [];

function check(label, ok, detail = '') {
  results.push({ label, ok });
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${label.padEnd(38)} ${String(detail).replace(/\n/g, ' | ').slice(0, 110)}`);
}

const tool = (name) => headlessTools.find((t) => t.name === name);

async function main() {
  // --- godot_headless_info ------------------------------------------
  const info = await tool('godot_headless_info').execute({});
  let parsed = null;
  try {
    parsed = JSON.parse(info);
  } catch { /* left null, reported below */ }
  check('godot_headless_info returns JSON', parsed !== null, info);
  check('binary reachable', parsed?.reachable === true, parsed?.version);
  check('version is Godot 4', /^4\./.test(parsed?.version ?? ''), parsed?.version);

  // --- validate_project_headless -------------------------------------
  const valid = await tool('validate_project_headless').execute({
    project_path: DEMO,
    timeout_seconds: 120,
  });
  let v = null;
  try {
    v = JSON.parse(valid);
  } catch { /* reported below */ }
  check('validate_project_headless runs', v !== null, valid);
  check('demo project reports healthy', v?.healthy === true,
    `problems=${v?.problem_count} ${JSON.stringify(v?.problems ?? []).slice(0, 80)}`);

  // A project that does not exist must be rejected, not crash.
  const missing = await tool('validate_project_headless').execute({ project_path: 'C:/nope' });
  check('missing project rejected', missing.includes('No project.godot'), missing);

  // --- list_export_presets --------------------------------------------
  // Works against any project, so both outcomes are valid: the tool must
  // either name the presets or say plainly that there are none.
  const presets = await tool('list_export_presets').execute({ project_path: DEMO });
  let presetNames = [];
  if (presets.includes('No export presets')) {
    check('list_export_presets (none defined)', true, presets.slice(0, 70));
  } else {
    try {
      presetNames = JSON.parse(presets).presets ?? [];
    } catch { /* reported by the check below */ }
    check('list_export_presets (parsed)', presetNames.length > 0, JSON.stringify(presetNames));
  }

  // --- export_project ---------------------------------------------------
  // Exporting writes a real build, so it goes to a temp dir -- never into the
  // project under test, which may be someone's actual game.
  const buildDir = fs.mkdtempSync(path.join(os.tmpdir(), 'godot-mcp-export-'));
  const buildPath = path.join(buildDir, 'verify-export.exe');
  const presetToTry = presetNames[0] ?? 'Windows Desktop';

  const exportResult = await tool('export_project').execute({
    project_path: DEMO,
    preset_name: presetToTry,
    output_path: buildPath,
    timeout_seconds: 300,
  });

  if (presetNames.length === 0) {
    check('export rejects an unknown preset',
      /Unknown preset|Export failed/i.test(exportResult), exportResult.slice(0, 90));
  } else {
    // Either outcome is correct: a build when templates are installed, a clear
    // failure when they are not. What must not happen is a silent success.
    const built = fs.existsSync(buildPath);
    const failedClearly = /Export failed|export template/i.test(exportResult);
    check('export either builds or fails clearly', built || failedClearly,
      built ? `built ${fs.statSync(buildPath).size} bytes` : exportResult.slice(0, 90));
    check('export result matches reality',
      built ? !failedClearly : failedClearly,
      `file ${built ? 'exists' : 'missing'}, reported ${failedClearly ? 'failure' : 'success'}`);
  }
  fs.rmSync(buildDir, { recursive: true, force: true });

  // --- run_headless_script ----------------------------------------------
  const script = await tool('run_headless_script').execute({
    project_path: DEMO,
    script: [
      'print("engine=" + Engine.get_version_info().string)',
      'print("project=" + str(ProjectSettings.get_setting("application/config/name")))',
      'var d = DirAccess.open("res://")',
      'print("dirs=" + str(d.get_directories()))',
    ].join('\n'),
    timeout_seconds: 60,
  });
  check('run_headless_script executes', script.includes('engine=4.'), script);
  // Read the expected name from the project rather than hardcoding one, so
  // this passes against whatever project the caller pointed at.
  const projectFile = fs.readFileSync(path.join(DEMO, 'project.godot'), 'utf8');
  const nameMatch = projectFile.match(/config\/name\s*=\s*"([^"]*)"/);
  const expectedName = nameMatch ? nameMatch[1] : '';
  check('script sees ProjectSettings',
    expectedName ? script.includes(`project=${expectedName}`) : script.includes('project='),
    `expected "${expectedName}"`);
  check('script sees the filesystem', script.includes('addons'), script);

  // A script with a deliberate error must be reported, not swallowed.
  const broken = await tool('run_headless_script').execute({
    project_path: DEMO,
    script: 'this_function_does_not_exist()',
    timeout_seconds: 60,
  });
  check('script errors surface', /error/i.test(broken), broken);

  // --- import_project_assets ---------------------------------------------
  const imported = await tool('import_project_assets').execute({
    project_path: DEMO,
    timeout_seconds: 180,
  });
  let imp = null;
  try {
    imp = JSON.parse(imported);
  } catch { /* reported below */ }
  check('import_project_assets runs', imp !== null, imported);
  check('import reports no failures', (imp?.failures ?? ['?']).length === 0,
    JSON.stringify(imp?.failures ?? []).slice(0, 80));

  const failed = results.filter((r) => !r.ok).length;
  console.log(`\n${results.length - failed}/${results.length} passed`);
  process.exit(failed ? 1 : 0);
}

main();
