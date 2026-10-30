import type { DataIndex, IndexEntry } from './types';

/** Most recent cached run for a case, or undefined when the cache has none. */
export function latestRunForCase(index: DataIndex | null, caseId: string): IndexEntry | undefined {
  const runs = (index?.runs ?? []).filter((r) => r.caseId === caseId);
  return runs.sort((a, b) => b.startedAt.localeCompare(a.startedAt))[0];
}

const DECISION_LABELS: Record<string, string> = {
  APPEAL: 'Appeal',
  DO_NOT_APPEAL: 'Do not appeal',
  ESCALATE: 'Escalate',
};

export function decisionLabel(decision: string): string {
  return DECISION_LABELS[decision] ?? decision.replace(/_/g, ' ').toLowerCase();
}
