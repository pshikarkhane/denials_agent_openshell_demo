// Normalized, source-independent view of one agent run. Everything the GUI
// renders comes from this shape; adapters (src/data/adapters) produce it.

export type RunSourceKind = 'standin' | 'hermes';
export type StepKind = 'run' | 'model' | 'tool' | 'self_check' | 'revision';
export type StepStatus = 'ok' | 'error' | 'denied';

export interface Step {
  n: number;
  kind: StepKind;
  name: string;
  argsSummary: string;
  resultSummary: string;
  durationMs: number;
  status: StepStatus;
}

export type VerdictLabel = 'PASS' | 'FAIL';

export interface JudgeVote {
  verdict: VerdictLabel;
  reason: string;
}

export interface CriterionVerdict {
  criterionId: string;
  /** Criterion text; only present when the verdict file carries it (failed criteria). */
  text?: string;
  /** Per judge (claude, gemini, gpt, or "auto" for rule-checked criteria). */
  judges: Record<string, JudgeVote>;
  panel: VerdictLabel;
}

export type FlagSeverity = 'minor' | 'material';

export interface HallucinationFlag {
  id: string;
  quote: string;
  /** Null when no judge upheld the flag. */
  severity: FlagSeverity | null;
  upheld: boolean;
  problems: string[];
  raisedBy: string[];
}

export interface AuditEvent {
  time: string;
  eventClass: string;
  target: string;
  result: string;
  reason: string;
  background: boolean;
}

export interface TokenUsage {
  prompt: number;
  completion: number;
  total: number;
}

export interface Metrics {
  turns: number;
  tokens: TokenUsage;
  wallClockSeconds: number;
  toolErrors: number;
}

export interface RunView {
  runId: string;
  caseId: string;
  source: RunSourceKind;
  model: string;
  startedAt: string;
  decision: string;
  denialCode: string;
  policyId: string;
  actionDeadline: string | null;
  deliverableMarkdown: string;
  steps: Step[];
  verdicts: CriterionVerdict[];
  flags: HallucinationFlag[];
  /** Empty for the stand-in source (no sandbox, so no audit log). */
  audit: AuditEvent[];
  metrics: Metrics;
}

/** One row of public/data/index.json: enough for list pages without loading the run. */
export interface IndexEntry {
  runId: string;
  caseId: string;
  source: RunSourceKind;
  model: string;
  startedAt: string;
  decision: string;
  denialCode: string;
  policyId: string;
  stepCount: number;
  auditCount: number;
  /** File name under /data/. */
  file: string;
}

export interface DataIndex {
  mode: 'cached';
  runs: IndexEntry[];
}

/** An adapter turns one run folder into a RunView. */
export interface RunSource {
  readonly kind: RunSourceKind;
  /** True when this source can read the given run folder. */
  canRead(runDir: string): boolean;
  read(runDir: string): RunView;
}
