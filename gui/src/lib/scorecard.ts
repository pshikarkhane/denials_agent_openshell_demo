// Derivations of the Scorecard booth view. Every figure is an exact string from
// metrics.json / containment.json, except the token ratio (rounded here) and the
// "N of N" spelling of a 100% decision rate.
import type { Containment } from '../data/containment';
import type { Metrics, Series } from '../data/metrics';

export const seriesOf = (m: Metrics, id: Series['id']): Series | undefined => m.series.find((s) => s.id === id);

/** "250,435" -> 250435; null when it is not a figure. */
export const toNumber = (v: string | undefined): number | null => {
  const n = v ? Number(v.replace(/,/g, '')) : NaN;
  return Number.isFinite(n) ? n : null;
};

export const percent = (v: string | undefined): number | null => (v && v.includes('%') ? toNumber(v.replace('%', '')) : null);

/**
 * The positive subtitle needs decisions correct = 100% for the sandbox series AND its
 * criterion pass rate within 1.0 point of the same agent without a sandbox.
 */
export function subtitleSupported(m: Metrics): boolean {
  const h = seriesOf(m, 'hermes');
  const s = seriesOf(m, 'standin');
  const hp = percent(h?.metrics.criterionPass);
  const sp = percent(s?.metrics.criterionPass);
  if (!h || !s || hp === null || sp === null) return false;
  return h.metrics.decisionCorrect === '100%' && Math.abs(hp - sp) <= 1.0;
}

export const SUBTITLE_POSITIVE =
  'On a five-case pilot, the agent running in OpenShell reached the right decision every time, and matched the checklist as well as the same agent running without a sandbox.';
export const SUBTITLE_NEUTRAL = 'A five-case pilot of the agent running in OpenShell.';

/** "10 of 10" when the report says 100%; otherwise the report's own percentage. */
export function decisionsTile(m: Metrics): { value: string; label: string } {
  const h = seriesOf(m, 'hermes');
  const runs = h?.metrics.runs;
  const rate = h?.metrics.decisionCorrect;
  const cases = new Set(h?.runs.map((r) => r.caseId)).size;
  const per = cases && runs ? Number(runs) / cases : 0;
  const detail = cases && Number.isInteger(per) ? ` (${cases} cases, ${per} runs each)` : '';
  if (!rate || !runs) return { value: 'See the report', label: 'decisions correct' };
  return { value: rate === '100%' ? `${runs} of ${runs}` : rate, label: `decisions correct${detail}` };
}

/** Rounded ratio of Hermes tokens to the stand-in's, or null when either is missing. */
export function costRatio(m: Metrics): number | null {
  const h = toNumber(seriesOf(m, 'hermes')?.metrics.tokens);
  const s = toNumber(seriesOf(m, 'standin')?.metrics.tokens);
  return h !== null && s ? Math.round(h / s) : null;
}

export interface CostLine {
  n: number | null;
  hermes: string | null;
  standin: string | null;
  /** Shown only when the Hermes report parses a fixed prompt overhead. */
  builtInPrompt: boolean;
}

export function costLine(m: Metrics): CostLine {
  const h = seriesOf(m, 'hermes')?.metrics;
  return { n: costRatio(m), hermes: h?.tokens ?? null, standin: seriesOf(m, 'standin')?.metrics.tokens ?? null, builtInPrompt: Boolean(h?.promptOverheadTokens) };
}

export const costSentence = (c: CostLine): string =>
  c.n === null || !c.hermes || !c.standin
    ? 'What it costs: see the full numbers in Details.'
    : `What it costs: about ${c.n} times the tokens per run (${c.hermes} against ${c.standin} for the same agent without a sandbox)${c.builtInPrompt ? ", mostly the agent's own built-in prompt" : ''}.`;

export const containmentTile = (c: Containment | null): { value: string; label: string } =>
  c?.summary.allowedOther && c.summary.allowedOtherRuns
    ? { value: c.summary.allowedOther, label: `connections to anywhere but the model endpoint, in all ${c.summary.allowedOtherRuns} attack runs` }
    : { value: 'See the report', label: 'connections to anywhere but the model endpoint' };
