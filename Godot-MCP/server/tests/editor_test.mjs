// End-to-end test against a live Godot editor.
//
// Builds a scene from a spritesheet Aseprite exported, wires a signal, groups
// a node and renders the result -- asserting on the returned data rather than
// trusting success strings.
//
// Requires the Godot editor open on the target project with the godot_mcp
// plugin enabled (WebSocket on port 9080), and the project to contain
// assets/sprites/hero_sheet.png + .json. Produce those with
// ../../aseprite-mcp/tests/pipeline_demo.py.
//
//     node tests/editor_test.mjs <path-to-the-godot-project>

import { getGodotConnection } from '../dist/utils/godot_connection.js';
import * as fs from 'fs';

const DEMO = process.argv[2];
if (!DEMO) {
  console.error('usage: node tests/editor_test.mjs <path-to-the-godot-project>');
  process.exit(2);
}
const results = [];

function check(label, ok, detail = '') {
  results.push({ label, ok });
  const text = String(detail).replace(/\n/g, ' | ').slice(0, 120);
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${label.padEnd(36)} ${text}`);
}

async function main() {
  const godot = getGodotConnection();
  await godot.connect();
  check('connected to the editor plugin', true, 'ws://localhost:9080');

  const send = (type, params = {}) => godot.sendCommand(type, params);

  // Re-runnable: clear what a previous run generated. Godot refuses to
  // overwrite an existing scene, which is correct but makes the demo
  // single-shot otherwise.
  for (const stale of ['scenes/main.tscn', 'scripts/main.gd']) {
    try { fs.unlinkSync(`${DEMO}/${stale}`); } catch { /* first run */ }
  }

  // --- scene construction ---------------------------------------------
  await send('create_scene', { path: 'res://scenes/main.tscn', root_node_type: 'Node2D' });

  // create_scene writes a new file but the editor keeps whatever it already
  // had open, so a second run would stack nodes on top of the first run's.
  // Clear the tree before building it.
  try {
    const existing = await send('list_nodes', { parent_path: '/root' });
    for (const child of existing.children ?? []) {
      await send('delete_node', { node_path: `/root/${child.name}` });
    }
  } catch { /* nothing open yet */ }
  check('create_scene', true, 'res://scenes/main.tscn (Node2D)');

  const hero = await send('create_node', {
    parent_path: '/root', node_type: 'AnimatedSprite2D', node_name: 'Hero',
  });
  check('create_node AnimatedSprite2D', !!hero.node_path, hero.node_path);

  await send('create_node', { parent_path: '/root', node_type: 'Button', node_name: 'PlayButton' });
  check('create_node Button', true, '/root/PlayButton');

  // --- the Aseprite handoff --------------------------------------------
  const imported = await send('import_animated_sprite', {
    node_path: '/root/Hero',
    texture_path: 'res://assets/sprites/hero_sheet.png',
    metadata_path: 'res://assets/sprites/hero_sheet.json',
    use_tags: true,
    autoplay: true,
  });
  const names = (imported.animations ?? []).map((a) => a.name);
  check('import_animated_sprite', imported.frame_count > 0,
    `${imported.frame_count} frames -> ${JSON.stringify(names)}`);
  check('one animation per Aseprite tag', JSON.stringify(names) === '["idle","blink"]',
    JSON.stringify(names));
  check('per-tag frame counts correct',
    (imported.animations ?? []).every((a) => a.frame_count === 4),
    JSON.stringify((imported.animations ?? []).map((a) => [a.name, a.frame_count])));
  // 120ms frames -> 1000/120 = 8.33 fps
  const speeds = (imported.animations ?? []).map((a) => Math.round(a.speed * 100) / 100);
  check('Aseprite frame durations preserved', speeds.every((s) => Math.abs(s - 8.33) < 0.1),
    `${JSON.stringify(speeds)} fps (from 120ms frames)`);

  // --- scripts + signals -------------------------------------------------
  await send('create_script', {
    script_path: 'res://scripts/main.gd',
    content: [
      'extends Node2D',
      '',
      'func _on_play_pressed() -> void:',
      '\t$Hero.play("blink")',
      '',
    ].join('\n'),
    node_path: '/root',
  });
  check('create_script + attach', true, 'res://scripts/main.gd');

  const sigs = await send('list_signals', { node_path: '/root/PlayButton', include_inherited: true });
  const hasPressed = (sigs.signals ?? []).some((s) => s.name === 'pressed');
  check('list_signals finds "pressed"', hasPressed, `${(sigs.signals ?? []).length} signals`);

  // The editor keeps the previous run's scene in memory, so drop any existing
  // connection first to stay re-runnable.
  const wiring = {
    from_node_path: '/root/PlayButton', signal_name: 'pressed',
    to_node_path: '/root', method_name: '_on_play_pressed',
  };
  try { await send('disconnect_signal', wiring); } catch { /* not connected yet */ }

  await send('connect_signal', wiring);
  check('connect_signal', true, 'PlayButton.pressed -> /root._on_play_pressed');

  const conns = await send('list_connections', {
    node_path: '/root/PlayButton', signal_name: 'pressed',
  });
  const conn = (conns.connections ?? [])[0];
  check('connection is listed', !!conn, JSON.stringify(conn ?? {}));
  check('connection is persistent (saves to .tscn)', conn?.persistent === true,
    `persistent=${conn?.persistent}`);

  // Connecting to a method that does not exist must be refused up front.
  let refused = false;
  try {
    await send('connect_signal', {
      from_node_path: '/root/PlayButton', signal_name: 'pressed',
      to_node_path: '/root', method_name: 'no_such_method',
    });
  } catch (e) {
    refused = /no method/i.test(e.message);
  }
  check('missing target method refused', refused, 'connect_signal validates the method exists');

  // --- groups -------------------------------------------------------------
  try { await send('remove_node_from_group', { node_path: '/root/Hero', group_name: 'actors' }); }
  catch { /* not grouped yet */ }
  const grouped = await send('add_node_to_group', {
    node_path: '/root/Hero', group_name: 'actors',
  });
  check('add_node_to_group', (grouped.groups ?? []).includes('actors'),
    JSON.stringify(grouped.groups));

  const inGroup = await send('list_nodes_in_group', { group_name: 'actors' });
  check('list_nodes_in_group', (inGroup.nodes ?? []).some((n) => n.name === 'Hero'),
    JSON.stringify((inGroup.nodes ?? []).map((n) => n.name)));

  await send('save_scene', {});
  check('save_scene', true, 'res://scenes/main.tscn written');

  // --- visual feedback ------------------------------------------------------
  const shot = await send('capture_scene_render', {
    width: 256, height: 256, transparent: false,
    output_path: 'res://capture_main.png', include_base64: true,
  });
  const shotPath = `${DEMO}/capture_main.png`;
  const shotExists = fs.existsSync(shotPath);
  check('capture_scene_render wrote a PNG', shotExists,
    `${shot.width}x${shot.height}, ${shotExists ? fs.statSync(shotPath).size : 0} bytes`);
  check('capture returned image bytes', (shot.base64_png ?? '').length > 100,
    `${shot.byte_size ?? 0} bytes base64`);

  // The render must not be a blank frame -- that is the failure mode where a
  // capture "succeeds" and shows nothing.
  if (shot.base64_png) {
    const png = Buffer.from(shot.base64_png, 'base64');
    check('render is a valid PNG', png.subarray(1, 4).toString() === 'PNG', png.subarray(0, 8).toString('hex'));
    // A blank 256x256 PNG compresses to a few hundred bytes; real content is bigger.
    check('render is not blank', png.length > 1000, `${png.length} bytes`);
  }

  check('capture auto-framed the content', shot.framed === true,
    `zoom=${shot.zoom?.toFixed?.(1)} rect=${JSON.stringify(shot.content_rect)}`);
  check('mixed Node2D+Control is flagged', typeof shot.warning === 'string',
    (shot.warning ?? '(no warning)').slice(0, 90));

  const unframed = await send('capture_scene_render', {
    width: 128, height: 128, fit_content: false,
    output_path: 'res://capture_unframed.png', include_base64: false,
  });
  check('fit_content=false skips framing', unframed.framed === undefined,
    `framed=${unframed.framed}`);

  const named = await send('capture_scene_render', {
    scene_path: 'res://scenes/main.tscn', width: 128, height: 128,
    output_path: 'res://capture_named.png', include_base64: false,
  });
  check('capture by scene path', named.width === 128 && named.height === 128,
    `${named.width}x${named.height} from ${named.source}`);

  // --- read the scene back ---------------------------------------------------
  const nodes = await send('list_nodes', { parent_path: '/root' });
  const childNames = (nodes.children ?? []).map((c) => c.name).sort();
  check('scene tree contains both nodes',
    JSON.stringify(childNames) === '["Hero","PlayButton"]', JSON.stringify(childNames));

  godot.disconnect();

  const failed = results.filter((r) => !r.ok).length;
  console.log(`\n${results.length - failed}/${results.length} passed`);
  process.exit(failed ? 1 : 0);
}

main().catch((err) => {
  console.error(`\nFATAL: ${err.message}`);
  process.exit(1);
});
