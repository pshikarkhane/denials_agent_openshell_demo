// Pure logic of the Containment page: timeline, step/audit linking, block texts.
import type { AttackAuditEvent, AttackRunView, BlockedBy } from '../../data/types';

export const ms = (iso: string): number => Date.parse(iso);

/** "2026-11-03T02:44:03.427Z" -> "02:44:03.427" (all recorded times are UTC). */
export const clock = (iso: string): string => iso.slice(11, 23);

/** Run-tagged rows, plus background rows when asked; after-run rows are never listed. */
export function listedAudit(view: AttackRunView, showBackground: boolean): AttackAuditEvent[] {
  return view.audit.filter((a) => a.tag === 'run' || (showBackground && a.tag === 'background'));
}

export const hiddenBackground = (view: AttackRunView): number => view.audit.filter((a) => a.tag === 'background').length;
export const afterRunCount = (view: AttackRunView): number => view.audit.filter((a) => a.tag === 'post_run').length;

export type TimelineItem = { kind: 'step'; n: number; t: number } | { kind: 'audit'; index: number; t: number };

/** Steps and listed audit events in one time-ordered list (a step sorts before an event at the same time). */
export function buildTimeline(view: AttackRunView, showBackground: boolean): TimelineItem[] {
  const items: TimelineItem[] = [
    ...view.steps.map((s): TimelineItem => ({ kind: 'step', n: s.n, t: ms(s.ts) })),
    ...listedAudit(view, showBackground).map((a): TimelineItem => ({ kind: 'audit', index: a.index, t: ms(a.ts) })),
  ];
  return items.sort((a, b) => a.t - b.t || (a.kind === b.kind ? 0 : a.kind === 'step' ? -1 : 1));
}

/** Items shown at replay position `pos` (the first `pos` items of the timeline). */
export function shownAt(timeline: TimelineItem[], pos: number): { steps: Set<number>; audit: Set<number> } {
  const steps = new Set<number>();
  const audit = new Set<number>();
  for (const it of timeline.slice(0, pos)) (it.kind === 'step' ? steps : audit).add(it.kind === 'step' ? it.n : it.index);
  return { steps, audit };
}

/** The step an audit event belongs to: the one whose time window holds it, else the closest in time. */
export function nearestStep(view: AttackRunView, auditIndex: number): number | null {
  const a = view.audit[auditIndex];
  if (!a || view.steps.length === 0) return null;
  const t = ms(a.ts);
  const toolLike = view.steps.filter((s) => s.kind === 'tool' || s.kind === 'model');
  const inside = toolLike.find((s) => s.endTs && t >= ms(s.ts) && t <= ms(s.endTs));
  if (inside) return inside.n;
  let best = view.steps[0];
  for (const s of view.steps) if (Math.abs(ms(s.ts) - t) < Math.abs(ms(best.ts) - t)) best = s;
  return best.n;
}

/** The recorded OpenShell row closest to a step: a denied row inside its window first, else the closest decision row. */
export function nearestAudit(view: AttackRunView, stepN: number, rows: AttackAuditEvent[]): number | null {
  const s = view.steps.find((x) => x.n === stepN);
  if (!s || rows.length === 0) return null;
  // The attempt links to its evidence row; an attempt with none (a file block) links to nothing rather than to a nearby unrelated row.
  if (view.attempt && view.attempt.stepN === stepN) return view.evidenceAudit[0] ?? null;
  const lo = ms(s.ts) - 500;
  const hi = ms(s.endTs ?? s.ts) + 500;
  const inWindow = rows.filter((a) => a.result !== '' && ms(a.ts) >= lo && ms(a.ts) <= hi);
  if (inWindow.length) return (inWindow.find((a) => a.result === 'denied') ?? inWindow[0]).index;
  const decided = rows.filter((a) => a.result !== '');
  const pool = decided.length ? decided : rows;
  let best = pool[0];
  for (const a of pool) if (Math.abs(ms(a.ts) - ms(s.ts)) < Math.abs(ms(best.ts) - ms(s.ts))) best = a;
  return best.index;
}

export const SCRIPTED_BADGE =
  "Scripted attempt: the harness ran this command inside the sandbox, outside the agent's own checks. The result shows OpenShell alone.";
export const NATURAL_BADGE = 'Natural run: the agent chose this';

export const BLOCKED_COPY: Record<BlockedBy, { title: string; lines: string[] }> = {
  openshell_network: {
    title: 'Blocked by OpenShell (network)',
    lines: ["OpenShell's network policy denied the connection.", 'Recorded in the OpenShell audit log: yes.'],
  },
  openshell_file: {
    title: 'Blocked by OpenShell (file permissions)',
    lines: ["Blocked by OpenShell's file permissions. Not recorded in the audit log. Evidence: the tool error in the trace."],
  },
  agent_safeguard: {
    title: 'Stopped by an agent-side safeguard',
    lines: [
      'An agent-side safeguard stopped this before it reached the network, so OpenShell and its audit log never saw it. It is not part of the NVIDIA stack and is not counted as an OpenShell block.',
    ],
  },
  unknown: {
    title: 'Layer not determined',
    lines: ['The layer that stopped this attempt could not be determined from the recording.'],
  },
  none: {
    title: 'No attempt in this run',
    lines: ['The agent did not attempt the action in this run, so there was nothing for OpenShell to block.'],
  },
};

export const isOpenShellBlock = (b: BlockedBy): boolean => b === 'openshell_network' || b === 'openshell_file';

/** Splits a text so each *.invalid host, URL and /var path can be marked. */
export function markTokens(text: string): { text: string; hit: boolean }[] {
  const re = /https?:\/\/[A-Za-z0-9.-]+\.invalid(?::\d+)?(?:\/[^\s"'<>)\\…]*)?|[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.invalid|\/var\/[\w./-]*\w/g;
  const out: { text: string; hit: boolean }[] = [];
  let last = 0;
  for (const m of text.matchAll(re)) {
    if (m.index! > last) out.push({ text: text.slice(last, m.index), hit: false });
    out.push({ text: m[0], hit: true });
    last = m.index! + m[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last), hit: false });
  return out;
}
