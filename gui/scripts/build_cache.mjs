#!/usr/bin/env node
// Builds the cached data the GUI loads at runtime:
//   gui/public/data/index.json plus one normalized JSON per run.
// Usage: node scripts/build_cache.mjs [--runs <glob-or-folder>[,<more>]] [--out <dir>]
// Default --runs: docs/samples/agent_run_*   Default --out: gui/public/data
//
// HARD RULES: never reads or copies truth.json, rubric.json, or anything under
// a folder named gold or attacks. If one is present in an input folder the
// build fails loudly (non-zero exit) and writes nothing.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { assertAllowedPath, assertTreeClean, findForbiddenTokens } from '../src/data/guard.mjs';
import { standin } from '../src/data/adapters/standin.mjs';
import { hermes } from '../src/data/adapters/hermes.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const guiRoot = path.resolve(here, '..');
const repoRoot = path.resolve(guiRoot, '..');
const SOURCES = [standin, hermes];

/** Expands one pattern: a folder, or a path whose last segment contains "*". */
function expand(pattern, cwd) {
  const abs = path.resolve(cwd, pattern);
  if (!path.basename(abs).includes('*')) return [abs];
  const re = new RegExp('^' + path.basename(abs).replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*') + '$');
  const dir = path.dirname(abs);
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.isDirectory() && re.test(e.name))
    .map((e) => path.join(dir, e.name))
    .sort();
}

export function buildCache({ runs = ['docs/samples/agent_run_*'], out = path.join(guiRoot, 'public/data'), cwd = repoRoot } = {}) {
  const dirs = runs.flatMap((p) => expand(p, cwd));
  if (dirs.length === 0) throw new Error(`no run folders matched: ${runs.join(', ')}`);

  // Refuse before reading anything.
  for (const d of dirs) assertTreeClean(d);

  const views = [];
  for (const dir of dirs) {
    const source = SOURCES.find((s) => s.canRead(dir));
    if (!source) {
      console.warn(`skip (no adapter can read it): ${dir}`);
      continue;
    }
    views.push(source.read(dir));
  }
  if (views.length === 0) throw new Error('no readable runs');

  views.sort((a, b) => a.caseId.localeCompare(b.caseId) || a.startedAt.localeCompare(b.startedAt));
  const files = new Map();
  const entries = views.map((v) => {
    const file = `run_${v.runId}__${v.caseId}.json`.replace(/[^A-Za-z0-9_.-]/g, '_');
    assertAllowedPath(file);
    files.set(file, v);
    return {
      runId: v.runId,
      caseId: v.caseId,
      source: v.source,
      model: v.model,
      startedAt: v.startedAt,
      decision: v.decision,
      denialCode: v.denialCode,
      policyId: v.policyId,
      stepCount: v.steps.length,
      auditCount: v.audit.length,
      file,
    };
  });
  files.set('index.json', { mode: 'cached', runs: entries });

  // Serialize and scan everything before touching the output folder.
  const serialized = [...files].map(([name, obj]) => [name, JSON.stringify(obj, null, 1) + '\n']);
  for (const [name, text] of serialized) {
    const hits = findForbiddenTokens(text);
    if (hits.length) throw new Error(`REFUSED: output ${name} contains answer-key name(s): ${hits.join(', ')}`);
  }

  fs.rmSync(out, { recursive: true, force: true });
  fs.mkdirSync(out, { recursive: true });
  for (const [name, text] of serialized) fs.writeFileSync(path.join(out, name), text);
  return { out, count: views.length, files: serialized.map(([n]) => n) };
}

function parseArgs(argv) {
  const opts = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--runs') opts.runs = argv[++i].split(',');
    else if (argv[i] === '--out') opts.out = path.resolve(argv[++i]);
    else throw new Error(`unknown argument: ${argv[i]}`);
  }
  return opts;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const opts = parseArgs(process.argv.slice(2));
    // CLI paths are relative to where the user typed them.
    const res = buildCache({ ...opts, cwd: opts.runs ? process.cwd() : repoRoot });
    console.log(`wrote ${res.count} run(s) and index.json to ${res.out}`);
  } catch (err) {
    console.error(String(err.message ?? err));
    process.exit(1);
  }
}
