// Shape of public/data/containment.json (scripts/build_containment.mjs). Every
// value is an exact string from docs/CONTAINMENT_REPORT.md, docs/POLICY_HARDENING.md
// or docs/HERMES_RUN_REPORT.md; null means "could not be parsed" (the page then says
// "See the report").
import type { ContainmentIndexEntry } from './types';

export interface NaturalRow {
  fixture: string;
  scenario: string;
  runs: string;
  seen: string;
  attempted: string;
  blocked: string;
  audit: string;
  correct: string;
  egress: string;
}

export interface ScriptedRow {
  fixture: string;
  scenario: string;
  runs: string;
  blocked: string;
  audit: string;
  correct: string;
  egress: string;
}

export interface Containment {
  sources: string[];
  runs: ContainmentIndexEntry[];
  summary: {
    runs: string | null;
    naturalRuns: string | null;
    scriptedRuns: string | null;
    injectionSeen: string | null;
    naturalAttempts: string | null;
    allowedOther: string | null;
    allowedOtherRuns: string | null;
  };
  natural: NaturalRow[] | null;
  scripted: ScriptedRow[] | null;
  hardening: {
    removed: string[] | null;
    remaining: { modelEndpoint: string; internal: string } | null;
    modelHost: string | null;
    rows: { entry: string; hosts: string; before: string; after: string }[];
  };
  nemotron: { decisionCorrect: string | null; criterionPass: string | null; runs: string | null };
  limits: string[] | null;
  proves: string[] | null;
  /** Parts that could not be parsed from the reports. */
  missing: string[];
}
