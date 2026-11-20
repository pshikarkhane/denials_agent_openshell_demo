#!/usr/bin/env node
// Builds the data of the Containment page:
//   gui/public/data/containment.json         numbers and statements parsed from the reports
//   gui/public/data/containment/<attack>__<mode>.json   one AttackRunView per recorded run
//
// containment.json is parsed from markdown only (nothing typed here):
//   docs/CONTAINMENT_REPORT.md   the two result tables, the run totals in the prose, and the
//                                sections "Plain statements of the limits" and
//                                "What this proves and does not prove"
//   docs/POLICY_HARDENING.md     the before/after allowlist table and the "After:" sentence
//   docs/HERMES_RUN_REPORT.md    decisions correct and criterion pass rate (Hermes column)
// A part that cannot be parsed is left null and named in `missing`; the page then says
// "See the report" and test/containment.test.mjs fails loudly.
//
// The run views come from docs/samples/hermes_attack_*/{natural,scripted} (or any run folder) through the
// attack adapter. The host-only attack manifest is never read. The answer-key guard
// applies to every input folder and to every output text.
// Usage: node scripts/build_containment.mjs [--runs <glob>[,<more>]] [--root <repo>] [--out <dir>]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { assertAllowedPath, assertTreeClean, findForbiddenTokens } from '../src/data/guard.ts';
import { canReadAttackRun, readAttackRun } from '../src/data/adapters/attack.ts';
import { expand } from './build_cache.mjs';
import { parseTables } from './build_metrics.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const guiRoot = path.resolve(here, '..');
const repoRoot = path.resolve(guiRoot, '..');
// One folder per attack with a natural/ and a scripted/ run inside.
const DEFAULT_RUNS = ['docs/samples/hermes_attack_*'];

const clean = (s) => s.replace(/\*\*/g, '').replace(/`/g, '').trim();
const fixtureId = (cell) => /^([A-Z]\d+[a-z]?)/.exec(clean(cell))?.[1] ?? clean(cell);
const scenarioOf = (id) => id.replace(/[a-z]+$/, '');

/** Text of a "## heading" section, up to the next "## " heading, as paragraphs / bullets without markup. */
export function section(md, title) {
  const lines = md.split('\n');
  const i = lines.findIndex((l) => /^##\s+/.test(l) && clean(l.replace(/^##\s+/, '')).startsWith(title));
  if (i < 0) return null;
  const out = [];
  for (let j = i + 1; j < lines.length && !/^##\s+/.test(lines[j]); j++) {
    const t = lines[j].replace(/^\s*[-*]\s+/, '').trim();
    if (t) out.push(clean(t));
  }
  return out.length ? out : null;
}

export function parseContainment(md) {
  const missing = [];
  const tables = parseTables(md);
  const col = (t, re) => t.header.findIndex((h) => re.test(h));

  const nat = tables.find((t) => t.heading.startsWith('Natural behavior'));
  let natural = null;
  if (nat) {
    const c = { runs: col(nat, /^runs/), seen: col(nat, /injection seen/), att: col(nat, /attempted/), blocked: col(nat, /blocked/), audit: col(nat, /in audit log/), ok: col(nat, /decision, denial code/), egress: col(nat, /allowed egress/) };
    natural = nat.rows.map((r) => ({ fixture: fixtureId(r[0]), scenario: scenarioOf(fixtureId(r[0])), runs: r[c.runs], seen: r[c.seen], attempted: r[c.att], blocked: r[c.blocked], audit: r[c.audit], correct: r[c.ok], egress: r[c.egress] }));
  }
  if (!natural?.length) missing.push('natural table');

  const scr = tables.find((t) => t.heading.startsWith('Scripted attempts'));
  let scripted = null;
  if (scr) {
    const c = { runs: col(scr, /^runs/), blocked: col(scr, /^blocked/), audit: col(scr, /in audit log/), correct: col(scr, /agent's decision/), egress: col(scr, /allowed egress/) };
    scripted = scr.rows
      .filter((r) => !/superseded/i.test(r[0]))
      .map((r) => ({ fixture: fixtureId(r[0]), scenario: scenarioOf(fixtureId(r[0])), runs: r[c.runs], blocked: r[c.blocked], audit: r[c.audit], correct: r[c.correct], egress: r[c.egress] }));
  }
  if (!scripted?.length) missing.push('scripted table');

  // Totals live in the prose (the tables are per fixture).
  const flat = md.replace(/\*\*/g, '').replace(/`/g, '');
  const rx = (re) => re.exec(flat);
  const totals = rx(/(\d+) attack runs \((\d+) natural, (\d+) scripted\)/);
  const seen = rx(/read the injected text in (\d+) of (\d+) natural runs/);
  const attempted = rx(/attempted the action in (\d+) of (\d+)\b/);
  const egress = rx(/(\d+) allowed network events other than the model endpoint in all (\d+) runs/);
  if (!totals) missing.push('run totals');
  if (!seen) missing.push('injection seen');
  if (!attempted) missing.push('natural attempts');
  if (!egress) missing.push('allowed egress');

  const limits = section(md, 'Plain statements of the limits');
  const proves = section(md, 'What this proves and does not prove');
  if (!limits) missing.push('limits section');
  if (!proves) missing.push('proves section');

  return {
    natural,
    scripted,
    summary: {
      runs: totals ? totals[1] : null,
      naturalRuns: totals ? totals[2] : null,
      scriptedRuns: totals ? totals[3] : null,
      injectionSeen: seen ? `${seen[1]} of ${seen[2]}` : null,
      naturalAttempts: attempted ? `${attempted[1]} of ${attempted[2]}` : null,
      allowedOther: egress ? egress[1] : null,
      allowedOtherRuns: egress ? egress[2] : null,
    },
    limits,
    proves,
    missing,
  };
}

export function parseHardening(md) {
  const missing = [];
  const t = parseTables(md).find((x) => x.heading.startsWith('Before / after'));
  const rows = t ? t.rows.map((r) => ({ entry: r[0].replace(/\s*\(.*$/, ''), hosts: r[1], before: r[3], after: r[4] })) : [];
  const removed = rows.filter((r) => /^removed/i.test(r.after)).map((r) => r.entry);
  if (!rows.length) missing.push('allowlist table');
  const flat = md.replace(/\*\*/g, '');
  const after = /After: one real destination, `([^`]+)` \(the model route\), plus the sandbox-internal `([^`]+)`/.exec(flat);
  if (!after) missing.push('after sentence');
  const endpoint = after?.[1] ?? null;
  return {
    removed: removed.length ? removed : null,
    remaining: after ? { modelEndpoint: endpoint, internal: after[2] } : null,
    modelHost: endpoint ? endpoint.replace(/:\d+$/, '') : null,
    rows,
    missing,
  };
}

export function parseNemotron(md) {
  const missing = [];
  const t = parseTables(md).find((x) => x.heading.startsWith('Side by side'));
  const get = (re) => t?.rows.find((r) => re.test(r[0]))?.[1] ?? null;
  const decisionCorrect = get(/^decision correct/);
  const criterionPass = get(/^criterion pass, panel/);
  if (!decisionCorrect) missing.push('decisions correct');
  if (!criterionPass) missing.push('criterion pass rate');
  return { decisionCorrect, criterionPass, runs: get(/^runs$/), missing };
}

export function buildContainment({ runs = DEFAULT_RUNS, root = repoRoot, out = path.join(guiRoot, 'public/data'), cwd = root } = {}) {
  const read = (f) => fs.readFileSync(path.join(root, f), 'utf8');
  const report = parseContainment(read('docs/CONTAINMENT_REPORT.md'));
  const hardening = parseHardening(read('docs/POLICY_HARDENING.md'));
  const nemotron = parseNemotron(read('docs/HERMES_RUN_REPORT.md'));

  const dirs = runs
    .flatMap((p) => expand(p, cwd))
    .flatMap((d) => (canReadAttackRun(d) ? [d] : ['natural', 'scripted'].map((m) => path.join(d, m)).filter((m) => fs.existsSync(m))));
  for (const d of dirs) assertTreeClean(d);
  const files = new Map();
  const index = [];
  for (const dir of dirs) {
    if (!canReadAttackRun(dir)) continue;
    const view = readAttackRun(dir, { modelEndpoints: hardening.modelHost ? [hardening.modelHost] : [] });
    const file = `${view.attackId}__${view.attackMode}.json`.replace(/[^A-Za-z0-9_.-]/g, '_');
    assertAllowedPath(file);
    files.set(`containment/${file}`, view);
    index.push({ attackId: view.attackId, scenario: view.scenario, attackMode: view.attackMode, runId: view.runId, file });
  }
  if (!index.length) throw new Error(`no attack run folders matched: ${runs.join(', ')}`);
  index.sort((a, b) => a.attackId.localeCompare(b.attackId) || a.attackMode.localeCompare(b.attackMode));

  const containment = {
    sources: ['docs/CONTAINMENT_REPORT.md', 'docs/POLICY_HARDENING.md', 'docs/HERMES_RUN_REPORT.md'],
    runs: index,
    summary: report.summary,
    natural: report.natural,
    scripted: report.scripted,
    hardening: { removed: hardening.removed, remaining: hardening.remaining, modelHost: hardening.modelHost, rows: hardening.rows },
    nemotron: { decisionCorrect: nemotron.decisionCorrect, criterionPass: nemotron.criterionPass, runs: nemotron.runs },
    limits: report.limits,
    proves: report.proves,
    missing: [...report.missing, ...hardening.missing, ...nemotron.missing],
  };
  files.set('containment.json', containment);

  const serialized = [...files].map(([name, obj]) => [name, JSON.stringify(obj, null, 1) + '\n']);
  for (const [name, text] of serialized) {
    const hits = findForbiddenTokens(text);
    if (hits.length) throw new Error(`REFUSED: output ${name} contains answer-key name(s): ${hits.join(', ')}`);
  }
  fs.mkdirSync(path.join(out, 'containment'), { recursive: true });
  for (const f of fs.readdirSync(path.join(out, 'containment'))) if (f.endsWith('.json')) fs.rmSync(path.join(out, 'containment', f));
  for (const [name, text] of serialized) fs.writeFileSync(path.join(out, name), text);
  return { out, count: index.length, missing: containment.missing, files: serialized.map(([n]) => n) };
}

function parseArgs(argv) {
  const opts = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--runs') opts.runs = argv[++i].split(',');
    else if (argv[i] === '--root') opts.root = path.resolve(argv[++i]);
    else if (argv[i] === '--out') opts.out = path.resolve(argv[++i]);
    else throw new Error(`unknown argument: ${argv[i]}`);
  }
  return opts;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const opts = parseArgs(process.argv.slice(2));
    const res = buildContainment({ ...opts, cwd: opts.runs ? process.cwd() : opts.root ?? repoRoot });
    console.log(`wrote containment.json and ${res.count} attack run(s) to ${res.out}`);
    if (res.missing.length) console.warn(`NOT PARSED (page will say "See the report"): ${res.missing.join(', ')}`);
  } catch (err) {
    console.error(String(err.message ?? err));
    process.exit(1);
  }
}
