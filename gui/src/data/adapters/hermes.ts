// Hermes adapter: reads a run folder recorded by scripts/hermes/run_case.py
// (docs/EVENTS_SPEC.md, "Hermes runs"): events.jsonl and trace.json (same
// schema as the stand-in), audit.jsonl (OpenShell events with a `tag`),
// decision.json, deliverable.md, judge_verdicts.json and, when present,
// summary.json. summary.json is optional: without it the Hermes extras are
// derived from the events and the background review is reported as unknown.
// Nothing under hermes_raw/ is opened.
import fs from 'node:fs';
import path from 'node:path';
import type { AuditEvent, AuditTag, HermesExtras, RunSource, RunView } from '../types.ts';
import { normalizeFlags, normalizeVerdicts, num, readIfExists, readJson, readJsonl, stepsFromTrace, type Json } from './common.ts';

const TAGS: AuditTag[] = ['run', 'background', 'post_run'];

function auditFrom(dir: string): AuditEvent[] {
  const text = readIfExists(dir, 'audit.jsonl');
  if (!text) return [];
  return text
    .split('\n')
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l))
    .map((a): AuditEvent => {
      const tag = TAGS.includes(a.tag) ? (a.tag as AuditTag) : null;
      return {
        time: a.ts ?? '',
        eventClass: a.event_class ?? '',
        target: a.target ?? '',
        result: a.result ?? '',
        reason: a.reason ?? '',
        background: tag === 'background',
        tag,
      };
    });
}

function extrasFrom(events: Json[], start: Json, end: Json, summary: Json | null): HermesExtras {
  const calls = events.filter((e) => e.kind === 'tool_call');
  const results = new Map<string, Json>(events.filter((e) => e.kind === 'tool_result').map((e) => [e.data.tool_call_id, e]));
  const skillCalls = calls.filter((c) => c.data.skill);
  const toolsByName: Record<string, number> = {};
  for (const c of calls.filter((c) => !c.data.skill)) {
    const t = c.data.hermes_tool ?? c.name;
    toolsByName[t] = (toolsByName[t] ?? 0) + 1;
  }
  const bg = summary?.background_review;
  return {
    hermesRunId: start.data?.hermes_run_id ?? summary?.hermes_run_id ?? null,
    hermesVersion: start.data?.hermes_version ?? summary?.hermes_version ?? null,
    skillCalls: summary?.skill_calls_total ?? skillCalls.length,
    skillErrors: summary?.skill_errors ?? skillCalls.filter((c) => results.get(c.data.tool_call_id)?.status !== 'ok').length,
    toolsByName: summary?.hermes_tools_by_name ?? toolsByName,
    firstCallPromptTokens: end?.data?.usage?.first_call_prompt_tokens ?? summary?.usage?.first_call_prompt_tokens ?? null,
    backgroundReview: bg
      ? { calls: num(bg.calls), promptTokens: num(bg.prompt_tokens), completionTokens: num(bg.completion_tokens), complete: Boolean(bg.complete) }
      : null,
  };
}

export const hermes: RunSource = {
  kind: 'hermes',

  canRead(runDir) {
    const has = (f: string) => fs.existsSync(path.join(runDir, f));
    return has('decision.json') && has('events.jsonl') && has('trace.json') && has('audit.jsonl');
  },

  read(runDir): RunView {
    const decision = readJson(path.join(runDir, 'decision.json'));
    const events = readJsonl(path.join(runDir, 'events.jsonl'));
    const trace = readJson(path.join(runDir, 'trace.json'));
    const summaryText = readIfExists(runDir, 'summary.json');
    const summary = summaryText ? JSON.parse(summaryText) : null;
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
      source: 'hermes',
      runtime: 'hermes',
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
      audit: auditFrom(runDir),
      metrics: {
        turns: num(end?.data?.turns),
        tokens: { prompt: num(usage.prompt_tokens), completion: num(usage.completion_tokens), total: num(usage.total_tokens) },
        wallClockSeconds: Math.round(num(end?.duration_ms) / 100) / 10,
        toolErrors: steps.filter((s) => s.kind === 'tool' && s.status !== 'ok').length,
        toolCalls: num(end?.data?.tool_calls),
        revisions: num(end?.data?.revisions),
      },
      hermes: extrasFrom(events, start, end, summary),
    };
  },
};
