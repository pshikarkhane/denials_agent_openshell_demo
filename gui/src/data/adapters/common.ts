// Helpers shared by the adapters. Node only (reads run folders).
import fs from 'node:fs';
import path from 'node:path';
import { readGuarded } from '../guard.ts';
import type {
  CriterionVerdict,
  FlagSeverity,
  HallucinationFlag,
  JudgeVote,
  Step,
  StepKind,
  StepStatus,
  VerdictLabel,
} from '../types.ts';

// Run files are JSON written by our own recorders; they are read untyped.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Json = any;

export const readJson = (file: string): Json => JSON.parse(readGuarded(file));

export const readJsonl = (file: string): Json[] =>
  readGuarded(file)
    .split('\n')
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));

export const readIfExists = (dir: string, name: string): string | null => {
  const f = path.join(dir, name);
  return fs.existsSync(f) ? readGuarded(f) : null;
};

export const num = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0);

export function normalizeVerdicts(judgeFile: Json): CriterionVerdict[] {
  const panel = judgeFile?.panel;
  if (!panel?.panel) return [];
  const failed = panel.failed_criteria ?? {};
  const auto = panel.auto ?? {};
  return Object.entries(panel.panel as Record<string, VerdictLabel>).map(([criterionId, label]) => {
    const judges: Record<string, JudgeVote> = {};
    for (const [name, j] of Object.entries<Json>(panel.judges ?? {})) {
      const v = j?.verdicts?.[criterionId];
      if (v) judges[name] = { verdict: v.verdict, reason: v.reason ?? '' };
    }
    if (auto[criterionId]) {
      judges.auto = { verdict: auto[criterionId].pass ? 'PASS' : 'FAIL', reason: auto[criterionId].detail ?? '' };
    }
    const out: CriterionVerdict = { criterionId, judges, panel: label };
    // The failed-criteria block also carries a "reference" (rubric-derived
    // answer hint); only the criterion text is kept.
    if (failed[criterionId]?.text) out.text = failed[criterionId].text;
    return out;
  });
}

export function normalizeFlags(judgeFile: Json): HallucinationFlag[] {
  return (judgeFile?.hallucination?.flags ?? []).map((f: Json): HallucinationFlag => {
    const votes: HallucinationFlag['votes'] = {};
    for (const [judge, v] of Object.entries<Json>(f.votes ?? {})) {
      votes[judge] = { upheld: Boolean(v.upheld), severity: (v.severity ?? null) as FlagSeverity | null, reason: v.reason ?? '' };
    }
    return {
      id: f.id,
      quote: f.quote ?? '',
      severity: f.severity ?? null,
      upheld: Boolean(f.upheld),
      problems: f.problems ?? [],
      raisedBy: f.raised_by ?? [],
      votes,
    };
  });
}

/**
 * Steps from trace.json, each joined (by order) with its events: a tool step
 * with its tool_call/tool_result, a model step with its model_response text.
 */
export function stepsFromTrace(trace: Json[], events: Json[], skillNames: string[]): Step[] {
  const results = events.filter((e) => e.kind === 'tool_result');
  const callById = new Map<string, Json>(events.filter((e) => e.kind === 'tool_call').map((e) => [e.data.tool_call_id, e]));
  const responses = events.filter((e) => e.kind === 'model_response');
  let toolIdx = 0;
  let modelIdx = 0;

  return trace.map((s): Step => {
    const step: Step = {
      n: s.n,
      kind: s.kind as StepKind,
      name: s.name,
      argsSummary: s.args_summary ?? '',
      resultSummary: s.result_summary ?? '',
      durationMs: num(s.duration_ms),
      status: s.status as StepStatus,
      skillName: null,
      hermesTool: null,
      rawCommand: null,
      detail: null,
    };
    if (s.kind === 'tool') {
      const res = results[toolIdx++];
      const call = res ? callById.get(res.data.tool_call_id) : undefined;
      if (res && call && res.name === s.name) {
        step.skillName = call.data.skill ?? (skillNames.includes(s.name) ? s.name : null);
        step.hermesTool = call.data.hermes_tool ?? null;
        step.rawCommand = call.data.command ?? null;
        // Skill pages are agent-facing documentation (they state which files the
        // path guard refuses, by name); they are not cached, so the answer-key
        // guard has nothing to trip on and the UI has no wall of text to show.
        const result =
          step.hermesTool === 'skill_view'
            ? `Skill page, ${num(res.data.result_chars)} characters (not cached)`
            : res.data.result;
        step.detail = { arguments: call.data.arguments, result };
      }
    } else if (s.kind === 'model') {
      const text = responses[modelIdx++]?.data?.content;
      if (typeof text === 'string' && text.trim()) step.detail = { result: text.trim() };
    }
    return step;
  });
}
