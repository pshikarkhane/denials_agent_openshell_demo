import { renderToStaticMarkup } from 'react-dom/server';
import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { PILOT_NOTE, ScorecardView, type Checkpoint } from '../src/pages/ScorecardPage';
import type { MetricsState } from '../src/data/DataContext';
import type { Metrics } from '../src/data/metrics';

const root = path.resolve(__dirname, '../..');
const metrics: Metrics = JSON.parse(fs.readFileSync(path.join(root, 'gui/public/data/metrics.json'), 'utf8'));
const SOURCE = ['docs/RUN_REPORT.md', 'docs/HERMES_RUN_REPORT.md'].map((f) => fs.readFileSync(path.join(root, f), 'utf8')).join('\n');

const render = (state: MetricsState, checkpoint: Checkpoint = 'base') =>
  renderToStaticMarkup(<ScorecardView state={state} checkpoint={checkpoint} onCheckpoint={() => {}} />);

const ready: MetricsState = { status: 'ready', metrics };
const text = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&[a-z#0-9x]+;/gi, ' ');

describe('Scorecard', () => {
  it('shows the pilot note and the three series', () => {
    const html = render(ready);
    expect(html).toContain(PILOT_NOTE);
    for (const label of ['No tools', 'Stand-in agent', 'Hermes in OpenShell']) expect(html).toContain(label);
    for (const m of ['Criterion pass rate', 'Upheld material flags per run', 'Clean-run rate', 'Tool error rate', 'Tokens per run', 'Turns', 'Seconds per run', 'Judge panel', 'By category']) {
      expect(html).toContain(m);
    }
  });

  it('every number on the page is in the source markdown (or is a static label)', () => {
    // Static numbers: category numbers 1-12 and the figures in the pilot note (5, 0.4).
    const allowed = new Set(['5', '0.4', ...Array.from({ length: 12 }, (_, i) => String(i + 1))]);
    const numbers = text(render(ready)).match(/\d[\d,]*(?:\.\d+)?/g) ?? [];
    const bad = numbers.filter((n) => !allowed.has(n) && !SOURCE.includes(n));
    expect(bad).toEqual([]);
    expect(numbers.length).toBeGreaterThan(100);
  });

  it('values appear only for the categories that were run', () => {
    const html = render(ready);
    expect((html.match(/Not run yet/g) ?? []).length).toBe(7 * 3);
    expect(html).toContain('Medical necessity, record supports');
  });

  it('R1 checkpoint shows a pending empty state and no numbers', () => {
    const html = render(ready, 'r1');
    expect(html).toContain('Pending');
    expect(html).toContain('R1 checkpoint');
    expect(html).not.toContain('Headline numbers');
  });

  it('shows loading and error states', () => {
    expect(render({ status: 'loading' })).toContain('Loading cached metrics');
    expect(render({ status: 'error', message: 'HTTP 404' })).toContain('HTTP 404');
  });
});
