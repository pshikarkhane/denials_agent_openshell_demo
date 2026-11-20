// Shape of public/data/metrics.json (written by scripts/build_metrics.mjs).
// Every value is the exact string from the markdown report it came from.

export interface JudgeTriple {
  gemini: string;
  claude: string;
  gpt: string;
}

export interface MetricRun {
  caseId: string;
  runId: string;
  variant: string;
  decision: string;
  panelPass: string;
  contentPass: string;
  upheldMaterial: string;
  minor: string;
  turns: string;
  tokens: string;
  seconds: string;
}

export interface Series {
  id: 'baseline' | 'standin' | 'hermes';
  label: string;
  detail: string;
  runtime: 'standin' | 'hermes';
  configuration: string;
  source: string;
  /** Keyed by metric name; absent when the report has no value. */
  metrics: Partial<Record<MetricKey, string>>;
  judges: { panel: JudgeTriple | null; content: JudgeTriple | null };
  runs: MetricRun[];
}

export type MetricKey =
  | 'runs'
  | 'decisionCorrect'
  | 'decisionJsonValid'
  | 'criterionPass'
  | 'perJudge'
  | 'contentPass'
  | 'perJudgeContent'
  | 'upheldPerRun'
  | 'cleanRunRate'
  | 'unanimity'
  | 'toolErrorRate'
  | 'toolErrorRateSkillOnly'
  | 'turns'
  | 'toolCalls'
  | 'tokens'
  | 'seconds'
  | 'revisionRate'
  | 'promptOverheadTokens'
  | 'backgroundReviewTokens';

export interface CategoryCell {
  caseId: string;
  runId: string;
  panelPass: string;
  upheldMaterial: string;
}

export interface Category {
  n: number;
  name: string;
  cases: string[];
  cells: Record<Series['id'], CategoryCell[]>;
}

export interface Metrics {
  sources: string[];
  series: Series[];
  categories: Category[];
  /** Yes/no statements read from the Hermes report. */
  notes?: { toolErrorsRecovered: boolean };
}
