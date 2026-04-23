import { spawn } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const platformDir = resolve(scriptDir, '..');
const clientDir = resolve(platformDir, '..', 'client');
const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm';

const children = [];
let shuttingDown = false;

function prefixOutput(stream, prefix, target) {
  stream.on('data', (chunk) => {
    const lines = chunk.toString().split(/\r?\n/);
    lines.forEach((line, index) => {
      if (!line && index === lines.length - 1) return;
      target.write(`[${prefix}] ${line}\n`);
    });
  });
}

function run(name, command, args, cwd) {
  const child = spawn(command, args, {
    cwd,
    env: process.env,
    stdio: ['inherit', 'pipe', 'pipe'],
  });

  children.push(child);
  prefixOutput(child.stdout, name, process.stdout);
  prefixOutput(child.stderr, name, process.stderr);

  child.on('exit', (code, signal) => {
    if (shuttingDown) return;
    shuttingDown = true;
    children.forEach((item) => {
      if (item !== child && !item.killed) item.kill();
    });
    if (signal) {
      process.kill(process.pid, signal);
    } else {
      process.exit(code ?? 0);
    }
  });

  return child;
}

function shutdown() {
  if (shuttingDown) return;
  shuttingDown = true;
  children.forEach((child) => {
    if (!child.killed) child.kill();
  });
}

process.on('SIGINT', () => {
  shutdown();
  process.exit(130);
});

process.on('SIGTERM', () => {
  shutdown();
  process.exit(143);
});

run('workspace', npmCommand, ['run', 'start', '--', '--host', '0.0.0.0', '--port', '4001', '--strictPort'], clientDir);
run('platform', npmCommand, ['exec', 'vite', '--', '--host', '0.0.0.0', '--port', '3001'], platformDir);
