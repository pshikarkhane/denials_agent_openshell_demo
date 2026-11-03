#!/usr/bin/env node
// Renders gui/public/architecture.html with headless Chrome at 1920x1080, device scale
// factor 2, to gui/public/architecture.png (3840x2160). No dependencies: it talks to Chrome
// over the DevTools websocket (Node 22 has WebSocket built in). The slide is local and
// makes no network request.
// Usage: npm run slide:png     (CHROME=/path/to/chrome to override the default location)
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const pub = path.resolve(here, '../public');
const slide = path.join(pub, 'architecture.html');
const out = path.join(pub, 'architecture.png');

const CANDIDATES = [
  process.env.CHROME,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
].filter(Boolean);
const chromePath = CANDIDATES.find((p) => fs.existsSync(p));
if (!chromePath) {
  console.error('Chrome not found. Set CHROME=/path/to/chrome.');
  process.exit(1);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const port = 9300 + Math.floor(Math.random() * 500);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'slide-png-'));
const chrome = spawn(chromePath, ['--headless=new', `--remote-debugging-port=${port}`, '--no-first-run', `--user-data-dir=${profile}`, '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' });

try {
  let targets = [];
  for (let i = 0; i < 50 && !targets.length; i++) {
    try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); } catch { await sleep(200); }
  }
  const page = targets.find((t) => t.type === 'page');
  if (!page) throw new Error('could not reach Chrome');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((r) => (ws.onopen = r));
  let id = 0;
  const pending = new Map();
  ws.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) { pending.get(d.id)(d.result ?? d); pending.delete(d.id); }
  };
  const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });

  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 2, mobile: false });
  await send('Page.navigate', { url: pathToFileURL(slide).href });
  await sleep(2000);
  const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  fs.writeFileSync(out, Buffer.from(shot.data, 'base64'));
  ws.close();
  console.log(`wrote ${out}`);
} finally {
  chrome.kill();
  fs.rmSync(profile, { recursive: true, force: true });
}
