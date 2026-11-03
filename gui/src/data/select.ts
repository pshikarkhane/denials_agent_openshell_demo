import type { DataIndex, IndexEntry } from './types';

const newestFirst = (a: IndexEntry, b: IndexEntry) => b.startedAt.localeCompare(a.startedAt);

export function runsForCase(index: DataIndex | null, caseId: string): IndexEntry[] {
  return (index?.runs ?? []).filter((r) => r.caseId === caseId).sort(newestFirst);
}

/**
 * The cached run a case card should quote: the newest agent run, Hermes before
 * the stand-in (it is the real runtime), never the no-tools baseline.
 */
export function latestRunForCase(index: DataIndex | null, caseId: string): IndexEntry | undefined {
  const agents = runsForCase(index, caseId).filter((r) => r.variant === 'agent');
  return agents.find((r) => r.runtime === 'hermes') ?? agents[0];
}

export interface CaseSides {
  left: IndexEntry[];
  right: IndexEntry[];
  /** The left side is the stand-in agent because the case has no baseline run. */
  leftIsStandin: boolean;
}

/**
 * Which runs fill the two panels of the Case page. Left: the no-tools baseline,
 * or, when the case has none, the pre-sandbox stand-in agent. Right: Hermes runs
 * (then stand-in agent runs as alternatives), or only Hermes when the left side
 * already shows the stand-in.
 */
export function caseSides(index: DataIndex | null, caseId: string): CaseSides {
  const all = runsForCase(index, caseId);
  const baselines = all.filter((r) => r.variant === 'baseline');
  const hermes = all.filter((r) => r.variant === 'agent' && r.runtime === 'hermes');
  const standins = all.filter((r) => r.variant === 'agent' && r.runtime === 'standin');
  if (baselines.length) return { left: baselines, right: [...hermes, ...standins], leftIsStandin: false };
  return { left: standins, right: hermes, leftIsStandin: true };
}

const DECISION_LABELS: Record<string, string> = {
  APPEAL: 'Appeal',
  DO_NOT_APPEAL: 'Do not appeal',
  ESCALATE: 'Escalate',
  CORRECT_AND_RESUBMIT: 'Correct and resubmit',
};

export function decisionLabel(decision: string): string {
  return DECISION_LABELS[decision] ?? decision.replace(/_/g, ' ').toLowerCase();
}

/** "2026-10-30T23:28:51.098+00:00" -> "2026-10-30 23:28 UTC" (all cached times are UTC). */
export function formatUtc(iso: string): string {
  return `${iso.slice(0, 10)} ${iso.slice(11, 16)} UTC`;
}

export function runLabel(r: IndexEntry): string {
  const kind = r.variant === 'baseline' ? 'no tools' : r.runtime === 'hermes' ? 'Hermes' : 'stand-in';
  return `${r.runId} (${kind}, ${formatUtc(r.startedAt)})`;
}
