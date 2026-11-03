// Baseline adapter: the no-tools variant (one prompt with every document pasted
// in). Exported folders hold deliverable.md, decision.json, summary.json and
// judge_verdicts.json; there is no trace, so `steps` is empty.
import fs from 'node:fs';
import path from 'node:path';
import type { RunSource, RunView } from '../types.ts';
import { normalizeFlags, normalizeVerdicts, num, readIfExists, readJson } from './common.ts';

export const baseline: RunSource = {
  kind: 'standin',

  canRead(runDir) {
    const has = (f: string) => fs.existsSync(path.join(runDir, f));
    return has('decision.json') && has('summary.json') && !has('events.jsonl');
  },

  read(runDir): RunView {
    const decision = readJson(path.join(runDir, 'decision.json'));
    const summary = readJson(path.join(runDir, 'summary.json'));
    if (summary.variant !== 'baseline') throw new Error(`${runDir}: summary.json is not a baseline run`);
    const verdicts = readIfExists(runDir, 'judge_verdicts.json');
    const judgeFile = verdicts ? JSON.parse(verdicts) : null;
    const usage = summary.usage ?? {};

    return {
      runId: summary.run_id,
      caseId: decision.case_id ?? summary.case_id,
      source: 'standin',
      runtime: 'standin',
      variant: 'baseline',
      model: summary.model_id ?? 'unknown',
      startedAt: summary.started,
      decision: decision.decision,
      denialCode: decision.denial_code,
      policyId: decision.policy_id,
      actionDeadline: decision.action_deadline ?? null,
      deliverableMarkdown: readIfExists(runDir, 'deliverable.md') ?? '',
      steps: [],
      verdicts: normalizeVerdicts(judgeFile),
      flags: normalizeFlags(judgeFile),
      audit: [],
      metrics: {
        turns: num(summary.turns),
        tokens: { prompt: num(usage.prompt_tokens), completion: num(usage.completion_tokens), total: num(usage.total_tokens) },
        wallClockSeconds: num(summary.seconds),
        toolErrors: num(summary.tool_errors),
        toolCalls: num(summary.tool_calls_total),
        revisions: num(summary.revisions),
      },
      hermes: null,
    };
  },
};
