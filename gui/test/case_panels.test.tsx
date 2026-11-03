import { renderToStaticMarkup } from 'react-dom/server';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { hermes } from '../src/data/adapters/hermes.ts';
import { baseline } from '../src/data/adapters/baseline.ts';
import { CriteriaTab } from '../src/components/CriteriaTab';
import { RunPanel } from '../src/components/RunPanel';
import { TraceTab } from '../src/components/TraceTab';
import { caseSides } from '../src/data/select';
import type { DataIndex, IndexEntry } from '../src/data/types';

const fx = (n: string) => path.join(__dirname, 'fixtures', n);
const h = hermes.read(fx('hermes_run_C-0030'));
const b = baseline.read(fx('baseline_run_C-0030'));

describe('RunPanel', () => {
  it('titles, citation pills and trace chips for the Hermes run', () => {
    const html = renderToStaticMarkup(<RunPanel run={h} />);
    expect(html).toContain('Agent: Hermes in the OpenShell sandbox');
    expect(html).toContain('class="cite"');
    expect(html).toContain('aria-label="Steps in order"');
    expect(html).toContain('parse_denial_eob');
    expect(html).toContain('0 tool errors');
  });

  it('marks the upheld material flag in the text, not the minor or not-upheld ones', () => {
    const html = renderToStaticMarkup(<RunPanel run={h} />);
    expect(html.match(/data-flag="F1"/g)?.length).toBeGreaterThan(0);
    expect(html).not.toContain('data-flag="F2"');
    expect(html).not.toContain('data-flag="F3"');
    expect(html).toContain('1 raised but not upheld');
  });

  it('lists a material flag whose quote is not in the text below it', () => {
    const run = { ...h, deliverableMarkdown: 'Nothing quoted here.' };
    const html = renderToStaticMarkup(<RunPanel run={run} />);
    expect(html).not.toContain('<mark');
    expect(html).toContain('Quote not found in the text above');
  });

  it('shows the baseline without a trace and with its own title', () => {
    const html = renderToStaticMarkup(<RunPanel run={b} />);
    expect(html).toContain('No tools: one prompt with every document pasted in');
    expect(html).not.toContain('Steps in order');
    expect(html).not.toContain('tool errors');
  });
});

describe('CriteriaTab', () => {
  const html = renderToStaticMarkup(<CriteriaTab left={b} right={h} />);
  it('shows the three judges as chips for each variant and the criterion text only where present', () => {
    expect(html).toContain('Gemini PASS');
    expect(html).toContain('GPT FAIL');
    expect(html).toContain('Rule PASS');
    expect(html).toContain('Does not cite or rely on the near-duplicate policy');
  });
  it('never carries the rubric reference field', () => {
    expect(html.toLowerCase()).not.toContain('reference');
  });
});

describe('TraceTab', () => {
  it('lists steps with timings and collapsed details; shows the raw command only when expanded', () => {
    const html = renderToStaticMarkup(<TraceTab run={h} />);
    expect(html).toContain('aria-expanded="false"');
    expect(html).toContain('202 ms');
    expect(html).toContain('via terminal');
    expect(html).not.toContain('Raw terminal command');
  });
  it('explains an empty trace', () => {
    expect(renderToStaticMarkup(<TraceTab run={b} />)).toContain('no trace');
  });
});

describe('caseSides', () => {
  const e = (over: Partial<IndexEntry>): IndexEntry => ({
    runId: 'x', caseId: 'C-1', source: 'standin', runtime: 'standin', variant: 'agent', model: 'm', startedAt: '2026-10-30T00:00:00.000Z',
    decision: 'APPEAL', denialCode: 'CO-50', policyId: 'P', actionDeadline: null, stepCount: 1, auditCount: 0, file: 'f', ...over,
  });
  const idx = (runs: IndexEntry[]): DataIndex => ({ mode: 'cached', runs });

  it('baseline left, Hermes then stand-in right', () => {
    const s = caseSides(idx([e({ runId: 'b', variant: 'baseline', file: 'b' }), e({ runId: 's', file: 's' }), e({ runId: 'h', runtime: 'hermes', source: 'hermes', file: 'h' })]), 'C-1');
    expect(s.leftIsStandin).toBe(false);
    expect(s.left.map((r) => r.runId)).toEqual(['b']);
    expect(s.right.map((r) => r.runId)).toEqual(['h', 's']);
  });
  it('without a baseline, stand-in left against Hermes right', () => {
    const s = caseSides(idx([e({ runId: 's', file: 's' }), e({ runId: 'h', runtime: 'hermes', source: 'hermes', file: 'h' })]), 'C-1');
    expect(s.leftIsStandin).toBe(true);
    expect(s.left.map((r) => r.runId)).toEqual(['s']);
    expect(s.right.map((r) => r.runId)).toEqual(['h']);
  });
  it('repeats are listed newest first', () => {
    const s = caseSides(idx([e({ runId: 'r1', variant: 'baseline', file: 'a' }), e({ runId: 'r2', variant: 'baseline', startedAt: '2026-10-31T00:00:00.000Z', file: 'b' })]), 'C-1');
    expect(s.left.map((r) => r.runId)).toEqual(['r2', 'r1']);
  });
});
