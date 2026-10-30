// Stand-in adapter: reads a pre-sandbox run folder written by agent/run_case.py
// (format in docs/EVENTS_SPEC.md) and returns a RunView (src/data/types.ts).
// Files used: decision.json, deliverable.md, events.jsonl, trace.json and,
// when present, judge_verdicts.json. Nothing else is opened.
import fs from 'node:fs';
import path from 'node:path';
import { readGuarded } from '../guard.mjs';

/** @typedef {import('../types').RunView} RunView */
/** @typedef {import('../types').RunSource} RunSource */

const readJson = (file) => JSON.parse(readGuarded(file));

function readEvents(file) {
  return readGuarded(file)
    .split('\n')
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));
}

const num = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : 0);

function normalizeSteps(trace) {
  return trace.map((s) => ({
    n: s.n,
    kind: s.kind,
    name: s.name,
    argsSummary: s.args_summary ?? '',
    resultSummary: s.result_summary ?? '',
    durationMs: num(s.duration_ms),
    status: s.status,
  }));
}

function normalizeVerdicts(judgeFile) {
  const panel = judgeFile?.panel;
  if (!panel?.panel) return [];
  const failed = panel.failed_criteria ?? {};
  const auto = panel.auto ?? {};
  return Object.entries(panel.panel).map(([criterionId, label]) => {
    /** @type {Record<string, {verdict: 'PASS'|'FAIL', reason: string}>} */
    const judges = {};
    for (const [name, j] of Object.entries(panel.judges ?? {})) {
      const v = j?.verdicts?.[criterionId];
      if (v) judges[name] = { verdict: v.verdict, reason: v.reason ?? '' };
    }
    if (auto[criterionId]) {
      judges.auto = { verdict: auto[criterionId].pass ? 'PASS' : 'FAIL', reason: auto[criterionId].detail ?? '' };
    }
    const out = { criterionId, judges, panel: label };
    // The failed-criteria block also carries a "reference" (rubric-derived
    // answer hint); only the criterion text is kept.
    if (failed[criterionId]?.text) out.text = failed[criterionId].text;
    return out;
  });
}

function normalizeFlags(judgeFile) {
  return (judgeFile?.hallucination?.flags ?? []).map((f) => ({
    id: f.id,
    quote: f.quote ?? '',
    severity: f.severity ?? null,
    upheld: Boolean(f.upheld),
    problems: f.problems ?? [],
    raisedBy: f.raised_by ?? [],
  }));
}

/** @type {RunSource} */
export const standin = {
  kind: 'standin',

  canRead(runDir) {
    return ['decision.json', 'events.jsonl', 'trace.json'].every((f) => fs.existsSync(path.join(runDir, f)));
  },

  read(runDir) {
    const decision = readJson(path.join(runDir, 'decision.json'));
    const events = readEvents(path.join(runDir, 'events.jsonl'));
    const trace = readJson(path.join(runDir, 'trace.json'));
    const deliverablePath = path.join(runDir, 'deliverable.md');
    const verdictsPath = path.join(runDir, 'judge_verdicts.json');
    const judgeFile = fs.existsSync(verdictsPath) ? readJson(verdictsPath) : null;

    const start = events.find((e) => e.kind === 'run_start');
    const end = events.findLast((e) => e.kind === 'run_end');
    if (!start) throw new Error(`${runDir}: events.jsonl has no run_start event`);
    const usage = end?.data?.usage ?? {};
    const steps = normalizeSteps(trace);

    return {
      runId: start.run_id,
      caseId: decision.case_id ?? start.case_id,
      source: 'standin',
      model: start.data?.model ?? 'unknown',
      startedAt: start.ts,
      decision: decision.decision,
      denialCode: decision.denial_code,
      policyId: decision.policy_id,
      actionDeadline: decision.action_deadline ?? null,
      deliverableMarkdown: fs.existsSync(deliverablePath) ? readGuarded(deliverablePath) : '',
      steps,
      verdicts: normalizeVerdicts(judgeFile),
      flags: normalizeFlags(judgeFile),
      audit: [],
      metrics: {
        turns: num(end?.data?.turns),
        tokens: {
          prompt: num(usage.prompt_tokens),
          completion: num(usage.completion_tokens),
          total: num(usage.total_tokens),
        },
        wallClockSeconds: Math.round(num(end?.duration_ms) / 100) / 10,
        toolErrors: steps.filter((s) => s.kind === 'tool' && s.status !== 'ok').length,
      },
    };
  },
};
