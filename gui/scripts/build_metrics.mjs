#!/usr/bin/env node
// Builds gui/public/data/metrics.json for the Scorecard by parsing the markdown
// tables of docs/RUN_REPORT.md (stand-in agent and no-tools baseline) and
// docs/HERMES_RUN_REPORT.md (Hermes). Every value is kept as the exact string
// written in the report, so nothing on the Scorecard is computed or rounded
// here (test/metrics.test.mjs checks that each one appears in the markdown).
//
// Two more docs are read only for labels, never for numbers:
//   docs/PILOT_REVIEW.md  headings "## C-0005: category 1, ..." (case -> category)
//   docs/DEMO_SPEC.md     the category list table in 3.2 (number and name only)
// Usage: node scripts/build_metrics.mjs [--out <dir>]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { findForbiddenTokens } from '../src/data/guard.ts';

const here = path.dirname(fileURLToPath(import.meta.url));
const guiRoot = path.resolve(here, '..');
const repoRoot = path.resolve(guiRoot, '..');

const clean = (s) => s.replace(/\*\*/g, '').replace(/`/g, '').trim();

/** Every pipe table in a markdown text, with the nearest preceding "##" heading. */
export function parseTables(md) {
  const lines = md.split('\n');
  const tables = [];
  let heading = '';
  for (let i = 0; i < lines.length; i++) {
    const h = /^#{2,3}\s+(.*)$/.exec(lines[i]);
    if (h) heading = clean(h[1]);
    const isRow = (l) => l?.trim().startsWith('|');
    if (isRow(lines[i]) && /^\|[\s:|-]+\|?\s*$/.test(lines[i + 1] ?? '')) {
      const split = (l) => l.trim().replace(/^\||\|$/g, '').split('|').map(clean);
      const header = split(lines[i]);
      const rows = [];
      let j = i + 2;
      while (isRow(lines[j])) rows.push(split(lines[j++]));
      tables.push({ heading, header, rows });
      i = j - 1;
    }
  }
  return tables;
}

const norm = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();

// Row label (normalized) -> metric key. First match wins; Hermes labels are listed too.
const KEYS = [
  ['runs', 'runs'],
  ['decision correct auto', 'decisionCorrect'],
  ['decision json valid', 'decisionJsonValid'],
  ['criterion pass panel all', 'criterionPass'],
  ['per judge gem cla gpt', 'perJudge'],
  ['content pass judge criteria only', 'contentPass'],
  ['per judge content', 'perJudgeContent'],
  ['upheld material run', 'upheldPerRun'],
  ['upheld material hallucinations run', 'upheldPerRun'],
  ['clean run rate', 'cleanRunRate'],
  ['clean run rate 0 upheld material', 'cleanRunRate'],
  ['unanimity', 'unanimity'],
  ['judge unanimity', 'unanimity'],
  ['tool error rate', 'toolErrorRate'],
  ['tool error rate skill other hermes tools', 'toolErrorRate'],
  ['tool error rate skill calls only', 'toolErrorRateSkillOnly'],
  ['mean turns', 'turns'],
  ['mean turns model calls', 'turns'],
  ['mean tool calls', 'toolCalls'],
  ['mean tool calls all hermes tools', 'toolCalls'],
  ['mean tokens', 'tokens'],
  ['mean tokens run run s own model calls', 'tokens'],
  ['mean seconds', 'seconds'],
  ['mean wall clock seconds run', 'seconds'],
  ['revision rate', 'revisionRate'],
  ['hermes fixed prompt overhead first call prompt tokens mean', 'promptOverheadTokens'],
  ['mean tokens run in hermes post run background review not in the line above', 'backgroundReviewTokens'],
];
const keyFor = (label) => KEYS.find(([l]) => l === norm(label))?.[1] ?? null;

/** Per-case table row -> a plain record keyed by the column header. */
function perRun(table, variantOverride) {
  return table.rows.map((r) => {
    const o = Object.fromEntries(table.header.map((h, i) => [norm(h), r[i]]));
    return {
      caseId: o.case,
      runId: o.run,
      variant: variantOverride ?? o.variant,
      decision: o['model decision'],
      panelPass: o['panel pass'],
      contentPass: o['content pass'],
      upheldMaterial: o['upheld material'],
      minor: o.minor,
      turns: o.turns,
      tokens: o.tokens,
      seconds: o.s,
    };
  });
}

/** The p3 row of the two RUN_REPORT tables of a section, merged into one record. */
function runReportMetrics(tables, headingStart) {
  const metrics = {};
  for (const t of tables.filter((t) => t.heading.startsWith(headingStart))) {
    const row = t.rows.find((r) => r[0] === 'p3 / new rubric');
    if (!row) continue;
    t.header.forEach((h, i) => {
      const k = keyFor(h);
      if (k && i > 0 && row[i] !== undefined) metrics[k] = row[i];
    });
  }
  return metrics;
}

/** "93%/98%/98%" -> { gemini, claude, gpt } (the report orders them gem/cla/gpt). */
export function splitJudges(s) {
  const parts = (s ?? '').split('/').map((p) => p.trim());
  return parts.length === 3 ? { gemini: parts[0], claude: parts[1], gpt: parts[2] } : null;
}

export function buildMetrics({ root = repoRoot } = {}) {
  const read = (f) => fs.readFileSync(path.join(root, f), 'utf8');
  const run = parseTables(read('docs/RUN_REPORT.md'));
  const her = parseTables(read('docs/HERMES_RUN_REPORT.md'));

  // Hermes: the "Side by side" table, column 1 = Hermes, column 2 = stand-in.
  const side = her.find((t) => t.heading.startsWith('Side by side'));
  const hermesMetrics = {};
  for (const r of side.rows) {
    const k = keyFor(r[0]);
    if (k && !(k in hermesMetrics)) hermesMetrics[k] = r[1];
  }

  const perCaseRun = run.find((t) => t.heading.startsWith('Per case'));
  const perCaseHer = her.find((t) => t.heading === 'Per case');
  const runs = perRun(perCaseRun);

  const series = [
    {
      id: 'baseline',
      label: 'No tools',
      detail: 'one prompt with every document pasted in',
      runtime: 'standin',
      configuration: 'p3 / new rubric',
      source: 'docs/RUN_REPORT.md',
      metrics: runReportMetrics(run, 'Baseline'),
      runs: runs.filter((r) => r.variant === 'baseline'),
    },
    {
      id: 'standin',
      label: 'Stand-in agent',
      detail: 'pre-sandbox tool loop over the six skills',
      runtime: 'standin',
      configuration: 'p3 / new rubric',
      source: 'docs/RUN_REPORT.md',
      metrics: runReportMetrics(run, 'Agent'),
      runs: runs.filter((r) => r.variant === 'agent'),
    },
    {
      id: 'hermes',
      label: 'Hermes in OpenShell',
      detail: 'the same skills driven by the real Hermes agent in the sandbox',
      runtime: 'hermes',
      configuration: 'hermes-p1',
      source: 'docs/HERMES_RUN_REPORT.md',
      metrics: hermesMetrics,
      runs: perRun(perCaseHer, 'agent'),
    },
  ];
  for (const s of series) {
    s.judges = { panel: splitJudges(s.metrics.perJudge), content: splitJudges(s.metrics.perJudgeContent) };
  }

  // Categories: case -> category from the pilot review headings, names from the spec table.
  const caseCategory = {};
  for (const m of read('docs/PILOT_REVIEW.md').matchAll(/^##\s+(C-\d{4}):\s+category\s+(\d+)\b/gm)) caseCategory[m[1]] = Number(m[2]);
  const names = parseTables(read('docs/DEMO_SPEC.md'))
    .filter((t) => t.header[0] === '#' && t.header[1].startsWith('Category'))
    .flatMap((t) => t.rows.map((r) => [Number(r[0]), r[1]]));
  const categories = names.map(([n, name]) => {
    const cases = Object.keys(caseCategory).filter((c) => caseCategory[c] === n);
    return {
      n,
      name,
      cases,
      cells: Object.fromEntries(
        series.map((s) => [
          s.id,
          s.runs.filter((r) => cases.includes(r.caseId)).map(({ caseId, runId, panelPass, upheldMaterial }) => ({ caseId, runId, panelPass, upheldMaterial })),
        ]),
      ),
    };
  });

  return {
    sources: ['docs/RUN_REPORT.md', 'docs/HERMES_RUN_REPORT.md'],
    series,
    categories,
  };
}

function main() {
  const i = process.argv.indexOf('--out');
  const out = i > 0 ? path.resolve(process.argv[i + 1]) : path.join(guiRoot, 'public/data');
  const metrics = buildMetrics();
  const text = JSON.stringify(metrics, null, 1) + '\n';
  const hits = findForbiddenTokens(text);
  if (hits.length) throw new Error(`REFUSED: metrics contain answer-key name(s): ${hits.join(', ')}`);
  fs.mkdirSync(out, { recursive: true });
  fs.writeFileSync(path.join(out, 'metrics.json'), text);
  console.log(`wrote ${path.join(out, 'metrics.json')} (${metrics.series.length} series)`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (err) {
    console.error(String(err.message ?? err));
    process.exit(1);
  }
}
