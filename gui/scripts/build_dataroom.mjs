#!/usr/bin/env node
// Builds gui/public/data/dataroom/<runId>__<caseId>.json (plus index.json): the
// case documents, the payer policies and the letter's links to both, per run.
// Usage: node scripts/build_dataroom.mjs [--runs <folder-or-glob>[,<more>]] [--data <dir>] [--out <dir>]
//
// HARD RULES: reads ONLY, by explicit allowlisted paths,
//   data/cases/<case>/task.md, data/cases/<case>/docs/** and data/policy_library/*.txt.
// It never lists the case folder root and never opens truth.json, rubric.json,
// gold/ or attacks/. A text that names one of them is replaced by a one-line
// note and reported; the guard is not loosened.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { assertAllowedPath, assertTreeClean, findForbiddenTokens, readGuarded } from '../src/data/guard.ts';
import { buildDataRoomView, unavailableDataRoom } from '../src/data/dataroom.ts';
import { DEFAULT_RUNS, SOURCES, expand } from './build_cache.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const guiRoot = path.resolve(here, '..');
const repoRoot = path.resolve(guiRoot, '..');

const NOTE = (name) => `[Text withheld: ${name} names a scoring file, so it is not shipped in the GUI.]`;

function listFiles(dir) {
  const out = [];
  const walk = (d, rel) => {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      assertAllowedPath(e.name);
      if (e.isDirectory()) walk(path.join(d, e.name), `${rel}${e.name}/`);
      else out.push(`${rel}${e.name}`);
    }
  };
  walk(dir, '');
  return out.sort();
}

/** Reads the allowlisted case files; null when the case folder or its docs are missing. */
export function readCaseFiles(dataDir, caseId) {
  assertAllowedPath(caseId);
  const caseDir = path.join(dataDir, 'cases', caseId);
  const docsDir = path.join(caseDir, 'docs');
  const task = path.join(caseDir, 'task.md');
  if (!fs.existsSync(docsDir) || !fs.existsSync(task)) return null;
  assertTreeClean(docsDir);
  return [
    ...listFiles(docsDir).map((rel) => ({ path: rel, text: readGuarded(path.join(docsDir, rel)) })),
    { path: 'task.md', text: readGuarded(task) },
  ];
}

export function readPolicyFiles(dataDir) {
  const dir = path.join(dataDir, 'policy_library');
  if (!fs.existsSync(dir)) return null;
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith('.txt'))
    .sort()
    .map((f) => ({ file: f, text: readGuarded(path.join(dir, f)) }));
}

/** Replaces any text that trips the guard with a note; returns the names withheld. */
function sanitize(files, withheld, label) {
  return files.map((f) => {
    const hits = findForbiddenTokens(f.text);
    if (!hits.length) return f;
    const name = label(f);
    withheld.push(name);
    console.warn(`withheld ${name}: names ${hits.join(', ')}`);
    return { ...f, text: NOTE(name) };
  });
}

export function buildDataRooms({ runs = DEFAULT_RUNS, out = path.join(guiRoot, 'public/data/dataroom'), dataDir = path.join(repoRoot, 'data'), cwd = repoRoot } = {}) {
  const dirs = runs.flatMap((p) => expand(p, cwd));
  if (dirs.length === 0) throw new Error(`no run folders matched: ${runs.join(', ')}`);
  for (const d of dirs) assertTreeClean(d);

  const policyRaw = readPolicyFiles(dataDir);
  const files = new Map();
  const entries = [];
  const caseCache = new Map();
  for (const dir of dirs) {
    const source = SOURCES.find((s) => s.canRead(dir));
    if (!source) continue;
    const run = source.read(dir);
    if (!caseCache.has(run.caseId)) caseCache.set(run.caseId, readCaseFiles(dataDir, run.caseId));
    const caseRaw = caseCache.get(run.caseId);
    let view;
    if (!caseRaw || !policyRaw) {
      view = unavailableDataRoom(run);
    } else {
      const withheld = [];
      const caseFiles = sanitize(caseRaw, withheld, (f) => f.path);
      const policyFiles = sanitize(policyRaw.map((p) => ({ ...p, path: p.file })), withheld, (f) => f.file).map(({ path: _p, ...p }) => p);
      const decisionPath = path.join(dir, 'decision.json');
      const criteria = fs.existsSync(decisionPath) ? (JSON.parse(readGuarded(decisionPath)).criteria ?? []) : [];
      const eventsPath = path.join(dir, 'events.jsonl');
      const eventsText = fs.existsSync(eventsPath) ? readGuarded(eventsPath) : null;
      view = buildDataRoomView({ run, criteria, eventsText, caseFiles, policyFiles });
      view.withheld = withheld;
    }
    const file = `${run.runId}__${run.caseId}.json`.replace(/[^A-Za-z0-9_.-]/g, '_');
    assertAllowedPath(file);
    files.set(file, view);
    entries.push({ runId: run.runId, caseId: run.caseId, available: view.available, file });
  }
  files.set('index.json', { runs: entries });

  const serialized = [...files].map(([name, obj]) => [name, JSON.stringify(obj, null, 1) + '\n']);
  for (const [name, text] of serialized) {
    const hits = findForbiddenTokens(text);
    if (hits.length) throw new Error(`REFUSED: output dataroom/${name} contains answer-key name(s): ${hits.join(', ')}`);
  }
  fs.mkdirSync(out, { recursive: true });
  for (const f of fs.readdirSync(out)) if (f.endsWith('.json')) fs.rmSync(path.join(out, f));
  for (const [name, text] of serialized) fs.writeFileSync(path.join(out, name), text);
  return { out, count: entries.length, files: serialized.map(([n]) => n) };
}

function parseArgs(argv) {
  const opts = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--runs') opts.runs = argv[++i].split(',');
    else if (argv[i] === '--data') opts.dataDir = path.resolve(argv[++i]);
    else if (argv[i] === '--out') opts.out = path.resolve(argv[++i]);
    else throw new Error(`unknown argument: ${argv[i]}`);
  }
  return opts;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const opts = parseArgs(process.argv.slice(2));
    const res = buildDataRooms({ ...opts, cwd: opts.runs ? process.cwd() : repoRoot });
    console.log(`wrote ${res.count} data room(s) and index.json to ${res.out}`);
  } catch (err) {
    console.error(String(err.message ?? err));
    process.exit(1);
  }
}
