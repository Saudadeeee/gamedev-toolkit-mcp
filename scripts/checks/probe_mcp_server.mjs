// Measure how long the Godot MCP server takes to answer tools/list with no
// Godot editor running -- the case that used to stall behind connection retries.
import { spawn } from 'node:child_process';

const SERVER = process.argv[2];
const started = Date.now();

const child = spawn('node', [SERVER], { stdio: ['pipe', 'pipe', 'pipe'] });

let buffer = '';
let done = false;

function finish(code, message) {
  if (done) return;
  done = true;
  console.log(message);
  child.kill();
  process.exit(code);
}

child.stdout.on('data', (chunk) => {
  buffer += chunk.toString();
  const lines = buffer.split('\n');
  buffer = lines.pop() ?? '';
  for (const line of lines) {
    if (!line.trim()) continue;
    let msg;
    try {
      msg = JSON.parse(line);
    } catch {
      continue;
    }
    if (msg.id === 1 && msg.result) {
      console.log(`initialize   ${Date.now() - started}ms  ${JSON.stringify(msg.result.serverInfo)}`);
    }
    if (msg.id === 2) {
      if (!msg.result) return finish(1, `tools/list FAILED: ${JSON.stringify(msg.error)}`);
      const tools = msg.result.tools;
      const names = tools.map((t) => t.name);
      const dup = names.filter((n, i) => names.indexOf(n) !== i);
      const ias = tools.find((t) => t.name === 'import_animated_sprite');
      console.log(`tools/list   ${Date.now() - started}ms  ${tools.length} tools`);
      console.log(`duplicates   ${dup.length ? dup.join(', ') : 'none'}`);
      console.log(`import_animated_sprite params: ${Object.keys(ias.inputSchema.properties).join(', ')}`);
      return finish(0, `\nserver was usable ${Date.now() - started}ms after spawn`);
    }
  }
});

child.stderr.on('data', (d) => {
  for (const line of d.toString().trim().split('\n')) {
    if (line.trim()) console.log(`  [stderr ${Date.now() - started}ms] ${line.trim()}`);
  }
});

const send = (obj) => child.stdin.write(JSON.stringify(obj) + '\n');

send({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'probe', version: '0' } } });
send({ jsonrpc: '2.0', method: 'notifications/initialized' });
send({ jsonrpc: '2.0', id: 2, method: 'tools/list' });

setTimeout(() => finish(1, 'TIMEOUT: no tools/list response within 60s'), 60000);
