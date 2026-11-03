// Normalized, source-independent view of one run. Everything the GUI renders
// comes from this shape; adapters (src/data/adapters) produce it.

export type RunSourceKind = 'standin' | 'hermes';
/** `baseline` = one prompt with every document pasted in, no tools. */
export type Variant = 'agent' | 'baseline';
export type StepKind = 'run' | 'model' | 'tool' | 'self_check' | 'revision';
export type StepStatus = 'ok' | 'error' | 'denied';

export interface StepDetail {
  /** Parsed tool arguments (object) or the raw string when it was not valid JSON. */
  arguments?: unknown;
  /** Tool output or assistant text; at most 4000 characters (EVENTS_SPEC). */
  result?: string;
}

export interface Step {
  n: number;
  kind: StepKind;
  name: string;
  argsSummary: string;
  resultSummary: string;
  durationMs: number;
  status: StepStatus;
  /** Skill the step ran (tool steps; for Hermes parsed from the run_skill wrapper). */
  skillName: string | null;
  /** Hermes tool that carried the call: terminal, write_file, patch, skill_view, ... */
  hermesTool: string | null;
  /** Hermes: the raw terminal command, kept verbatim. */
  rawCommand: string | null;
  detail: StepDetail | null;
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

export interface FlagVote {
  upheld: boolean;
  severity: FlagSeverity | null;
  reason: string;
}

export interface HallucinationFlag {
  id: string;
  quote: string;
  /** Null when no judge upheld the flag. */
  severity: FlagSeverity | null;
  upheld: boolean;
  problems: string[];
  raisedBy: string[];
  votes: Record<string, FlagVote>;
}

export type AuditTag = 'run' | 'background' | 'post_run';

export interface AuditEvent {
  time: string;
  eventClass: string;
  target: string;
  result: string;
  reason: string;
  /** Hermes' own housekeeping traffic; hidden in the UI by default. */
  background: boolean;
  tag: AuditTag | null;
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
  toolCalls: number;
  revisions: number;
}

export interface BackgroundReview {
  calls: number;
  promptTokens: number;
  completionTokens: number;
  complete: boolean;
}

/** Hermes-only facts (summary.json plus counts derived from the events). */
export interface HermesExtras {
  hermesRunId: string | null;
  hermesVersion: string | null;
  skillCalls: number;
  /** Skill calls whose result was an error. */
  skillErrors: number;
  /** Non-skill Hermes tools used (write_file, patch, skill_view, ...), by count. */
  toolsByName: Record<string, number>;
  firstCallPromptTokens: number | null;
  /** From summary.json; null when the run folder has none. */
  backgroundReview: BackgroundReview | null;
}

export interface RunView {
  runId: string;
  caseId: string;
  source: RunSourceKind;
  /** Which runtime produced the run; mirrors `source`. */
  runtime: RunSourceKind;
  variant: Variant;
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
  /** Empty for the stand-in and the baseline (no sandbox, so no audit log). */
  audit: AuditEvent[];
  metrics: Metrics;
  hermes: HermesExtras | null;
}

/** One row of public/data/index.json: enough for list pages without loading the run. */
export interface IndexEntry {
  runId: string;
  caseId: string;
  source: RunSourceKind;
  runtime: RunSourceKind;
  variant: Variant;
  model: string;
  startedAt: string;
  decision: string;
  denialCode: string;
  policyId: string;
  actionDeadline: string | null;
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

// ---- Data room (public/data/dataroom/<run>.json), built by scripts/build_dataroom.mjs ----

export type DataRoomDocKind = 'case' | 'task';
export type OpenedState = boolean | null;

export interface DataRoomDoc {
  /** Badge number, stable: denial letter, EOB, the rest alphabetically, task.md last. */
  number: number;
  /** Path under the case docs folder (task.md for the instruction). */
  path: string;
  descriptor: string;
  /** Full text, one entry per line; line numbers are index + 1. */
  lines: string[];
  /** true: its file name appears in a tool call or result; false: no trace; null: the run had no tools. */
  opened: OpenedState;
  citedBy: string[];
  matchedBy: string[];
}

export type PolicyStatus = 'chosen' | 'lookalike' | 'other';

export interface PolicyListing {
  id: string;
  title: string;
  payer: string;
  effective: string;
  status: PolicyStatus;
  /** The id appears in a retrieve_payer_policy result of the run. */
  considered: boolean;
}

export interface PolicySectionView {
  id: string;
  text: string;
}

export type CriterionStatus = 'met' | 'unmet' | 'unknown';

export interface BlockSectionLink {
  id: string;
  /** From decision.json; null when the section is not one of its criteria. */
  status: CriterionStatus | null;
  evidence: string | null;
}

export interface BlockMatch {
  token: string;
  file: string;
  line: number;
}

export interface BlockFlag {
  id: string;
  severity: FlagSeverity;
  /** Reasons of the judges who upheld it. */
  reasons: string[];
}

export interface DataRoomBlock {
  id: string;
  kind: 'heading' | 'paragraph' | 'list_item';
  text: string;
  links: {
    cited: string[];
    matched: BlockMatch[];
    sections: BlockSectionLink[];
    /** The block names the chosen policy (id or title). */
    policy: boolean;
    flags: BlockFlag[];
  };
}

export interface RowPolicyZone {
  kind: 'sections' | 'policy' | 'none';
  sectionIds: string[];
  /** Section texts in the same order as sectionIds. */
  texts: string[];
}

export interface RowEvidence {
  file: string;
  via: 'cited' | 'matched';
  /** Matched values found in this file for the block (empty for a citation with no value match). */
  tokens: string[];
  line: number | null;
  excerpt: string;
  excerptFound: boolean;
}

export interface DataRoomRow {
  blockId: string;
  title: string;
  policy: RowPolicyZone;
  evidence: RowEvidence[];
}

export interface DataRoomSummary {
  blocks: number;
  linkedBlocks: number;
  citedFiles: number;
  matchedFiles: number;
  flags: number;
}

export interface DataRoomView {
  available: boolean;
  runId: string;
  caseId: string;
  variant: Variant;
  runtime: RunSourceKind;
  chosenPolicyId: string;
  /** Policy ids seen in the run's retrieve_payer_policy results. */
  consideredPolicyIds: string[];
  caseDocs: DataRoomDoc[];
  policies: PolicyListing[];
  chosenSections: PolicySectionView[];
  blocks: DataRoomBlock[];
  rows: DataRoomRow[];
  summary: DataRoomSummary;
  /** Files whose text was replaced by a note because it tripped the answer-key guard. */
  withheld: string[];
}

/** One row of public/data/dataroom/index.json. */
export interface DataRoomIndexEntry {
  runId: string;
  caseId: string;
  available: boolean;
  file: string;
}
