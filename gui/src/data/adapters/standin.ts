// Stand-in adapter: reads a pre-sandbox run folder written by agent/run_case.py
// (format in docs/EVENTS_SPEC.md) and returns a RunView (src/data/types.ts).
// Files used: decision.json, deliverable.md, events.jsonl, trace.json and,
// when present, judge_verdicts.json. Nothing else is opened.
import fs from 'node:fs';
import path from 'node:path';
import type { RunSource, RunView } from '../types.ts';
import { normalizeFlags, normalizeVerdicts, num, readIfExists, readJson, readJsonl, stepsFromTrace } from './common.ts';

export const standin: RunSource = {
  kind: 'standin',

  canRead(runDir) {
    const has = (f: string) => fs.existsSync(path.join(runDir, f));
    return has('decision.json') && has('events.jsonl') && has('trace.json') && !has('audit.jsonl');
  },

  read(runDir): RunView {
    const decision = readJson(path.join(runDir, 'decision.json'));
    const events = readJsonl(path.join(runDir, 'events.jsonl'));
    const trace = readJson(path.join(runDir, 'trace.json'));
    const verdicts = readIfExists(runDir, 'judge_verdicts.json');
    const judgeFile = verdicts ? JSON.parse(verdicts) : null;

    const start = events.find((e) => e.kind === 'run_start');
    const end = events.findLast((e) => e.kind === 'run_end');
    if (!start) throw new Error(`${runDir}: events.jsonl has no run_start event`);
    const usage = end?.data?.usage ?? {};
    const steps = stepsFromTrace(trace, events, start.data?.tools ?? []);

    return {
      runId: start.run_id,
      caseId: decision.case_id ?? start.case_id,
      source: 'standin',
      runtime: 'standin',
      variant: 'agent',
      model: start.data?.model ?? 'unknown',
      startedAt: start.ts,
      decision: decision.decision,
      denialCode: decision.denial_code,
      policyId: decision.policy_id,
      actionDeadline: decision.action_deadline ?? null,
      deliverableMarkdown: readIfExists(runDir, 'deliverable.md') ?? '',
      steps,
      verdicts: normalizeVerdicts(judgeFile),
      flags: normalizeFlags(judgeFile),
      audit: [],
      metrics: {
        turns: num(end?.data?.turns),
        tokens: { prompt: num(usage.prompt_tokens), completion: num(usage.completion_tokens), total: num(usage.total_tokens) },
        wallClockSeconds: Math.round(num(end?.duration_ms) / 100) / 10,
        toolErrors: steps.filter((s) => s.kind === 'tool' && s.status !== 'ok').length,
        toolCalls: num(end?.data?.tool_calls),
        revisions: num(end?.data?.revisions),
      },
      hermes: null,
    };
  },
};
