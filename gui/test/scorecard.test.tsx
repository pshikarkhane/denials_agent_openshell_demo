import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { PILOT_NOTE, ScorecardView, isDetailsOpen, type Checkpoint } from '../src/pages/ScorecardPage';
import type { ContainmentState, MetricsState } from '../src/data/DataContext';
import type { Containment } from '../src/data/containment';
import type { Metrics } from '../src/data/metrics';
import { SUBTITLE_NEUTRAL, SUBTITLE_POSITIVE, costLine, costRatio, costSentence, decisionsTile, subtitleSupported } from '../src/lib/scorecard';

const root = path.resolve(__dirname, '../..');
const metrics: Metrics = JSON.parse(fs.readFileSync(path.join(root, 'gui/public/data/metrics.json'), 'utf8'));
const contData: Containment = JSON.parse(fs.readFileSync(path.join(root, 'gui/public/data/containment.json'), 'utf8'));
const SOURCE = ['docs/RUN_REPORT.md', 'docs/HERMES_RUN_REPORT.md', 'docs/CONTAINMENT_REPORT.md'].map((f) => fs.readFileSync(path.join(root, f), 'utf8')).join('\n');

const ready: MetricsState = { status: 'ready', metrics };
const cont: ContainmentState = { status: 'ready', data: contData };
const render = (state: MetricsState = ready, over: { details?: boolean; checkpoint?: Checkpoint; containment?: ContainmentState } = {}) =>
  renderToStaticMarkup(
    <MemoryRouter>
      <ScorecardView state={state} containment={over.containment ?? cont} checkpoint={over.checkpoint ?? 'base'} onCheckpoint={() => {}} detailsOpen={over.details ?? false} setDetails={() => {}} />
    </MemoryRouter>,
  );
const text = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&[a-z#0-9x]+;/gi, ' ');
const withMetrics = (edit: (m: Metrics) => void): MetricsState => {
  const m: Metrics = JSON.parse(JSON.stringify(metrics));
  edit(m);
  return { status: 'ready', metrics: m };
};
const hermes = (m: Metrics) => m.series.find((s) => s.id === 'hermes')!;
const standin = (m: Metrics) => m.series.find((s) => s.id === 'standin')!;

describe('Scorecard booth view', () => {
  const h = render();
  it('has exactly the booth pieces', () => {
    expect(h).toContain('SCORECARD');
    expect(h).toContain('The same answers, inside the sandbox.');
    expect(h).toContain(SUBTITLE_POSITIVE);
    expect((h.match(/sb-tile-item/g) ?? []).length).toBe(3);
    expect(h).toContain('Three ways of working');
    for (const c of ['No tools: one prompt', 'Same agent, no sandbox', 'Agent in OpenShell']) expect(h).toContain(c);
    for (const r of ['Checklist criteria passed', 'Runs inside OpenShell', 'Network limited to the model endpoint']) expect(h).toContain(r);
    expect(h).toContain('R1&#x27;s post-trained checkpoint will appear here as another column.'.replace('&#x27;', '&rsquo;').replace('&rsquo;', '’'));
    expect(h).toContain(PILOT_NOTE);
    expect(h).toContain('>Details<');
  });
  it('shows the three numbers from the data, and the containment tile links to /containment', () => {
    expect(h).toContain('>10 of 10<');
    expect(h).toContain('decisions correct (5 cases, 2 runs each)');
    expect(h).toContain('>97.8%<');
    expect(h).toContain('of checklist criteria passed. The same agent without a sandbox: 98.2%.');
    expect(h).toMatch(/>0<\/span><span class="sb-tile__l">connections to anywhere but the model endpoint, in all 38 attack runs/);
    expect(h).toContain('href="/containment"');
  });
  it('the comparison table has real header scopes and only three rows, with Yes and No in words', () => {
    const table = h.slice(h.indexOf('data-compare'), h.indexOf('</table>', h.indexOf('data-compare')));
    expect((table.match(/<th scope="col"/g) ?? []).length).toBe(3);
    expect((table.match(/<th scope="row"/g) ?? []).length).toBe(3);
    expect((table.match(/<tbody>[\s\S]*<\/tbody>/)?.[0].match(/<tr>/g) ?? []).length).toBe(3);
    expect(table).toContain('>95.5%<');
    expect(table).toContain('>98.2%<');
    expect(table).toContain('>97.8%<');
    expect(table).toContain('>Yes<');
    expect(table).toContain('>No<');
    expect(table).toContain('>No sandbox<');
  });
  it('does not show flags per run, clean-run rate, tool-error rate, turns or seconds', () => {
    for (const s of ['Upheld material flags per run', 'Clean-run rate', 'Tool error rate', 'Turns', 'Seconds per run', 'Judge panel', 'By category', 'Headline numbers', 'Model checkpoint', 'Base Super', 'Not run yet']) expect(h).not.toContain(s);
  });
});

describe('cost sentence', () => {
  it('is always visible in the default view, with N the rounded ratio of the two parsed token numbers', () => {
    const h = render();
    const m = metrics;
    const hermesTokens = Number(hermes(m).metrics.tokens!.replace(/,/g, ''));
    const standinTokens = Number(standin(m).metrics.tokens!.replace(/,/g, ''));
    const n = Math.round(hermesTokens / standinTokens);
    expect(costRatio(m)).toBe(n);
    expect(h).toContain(`What it costs: about ${n} times the tokens per run (${hermes(m).metrics.tokens} against ${standin(m).metrics.tokens} for the same agent without a sandbox), mostly the agent&#x27;s own built-in prompt.`);
  });
  it('follows the data: another ratio gives another N, and no fixed overhead drops the built-in-prompt clause', () => {
    const s = withMetrics((m) => { hermes(m).metrics.tokens = '500,000'; standin(m).metrics.tokens = '100,000'; delete hermes(m).metrics.promptOverheadTokens; });
    const h = render(s);
    expect(h).toContain('about 5 times the tokens per run (500,000 against 100,000 for the same agent without a sandbox).');
    expect(h).not.toContain('built-in prompt');
  });
  it('says where to look when a token number is missing, never guesses', () => {
    const s = withMetrics((m) => { delete hermes(m).metrics.tokens; });
    expect(render(s)).toContain('What it costs: see the full numbers in Details.');
    expect(costSentence(costLine(s.status === 'ready' ? s.metrics : metrics))).toContain('see the full numbers');
  });
});

describe('subtitle', () => {
  it('is the positive sentence only when decisions are 100% and the pass rate is within 1.0 point', () => {
    expect(subtitleSupported(metrics)).toBe(true);
    expect(text(render())).toContain('reached the right decision every time');
  });
  it('falls back to the neutral sentence when a condition is false', () => {
    const lowDecisions = withMetrics((m) => { hermes(m).metrics.decisionCorrect = '90%'; });
    const farPass = withMetrics((m) => { hermes(m).metrics.criterionPass = '90.0%'; });
    for (const s of [lowDecisions, farPass]) {
      const h = render(s);
      expect(h).toContain(SUBTITLE_NEUTRAL);
      expect(h).not.toContain('reached the right decision every time');
    }
    expect(decisionsTile((lowDecisions as { metrics: Metrics }).metrics).value).toBe('90%');
  });
});

describe('Details', () => {
  it('is closed by default and opens with ?details=1', () => {
    expect(render()).toContain('aria-expanded="false"');
    expect(render()).not.toContain('id="sc-details"');
    expect(isDetailsOpen(new URLSearchParams(''))).toBe(false);
    expect(isDetailsOpen(new URLSearchParams('details=1'))).toBe(true);
    const open = render(ready, { details: true });
    expect(open).toContain('aria-expanded="true"');
    expect(open).toContain('id="sc-details"');
  });
  it('holds the full numbers, the judge panel, the category grid and the checkpoint toggle', () => {
    const open = render(ready, { details: true });
    for (const s of ['Headline numbers', 'Upheld material flags per run', 'Clean-run rate', 'Tool error rate', 'Tokens per run', 'Turns', 'Seconds per run', '13,307 fixed prompt overhead', 'post-run review', 'Judge panel', 'By category', 'Model checkpoint', 'Base Super', 'R1 checkpoint']) expect(open).toContain(s);
    expect((open.match(/Not run yet/g) ?? []).length).toBe(7 * 3);
  });
  it('adds the recovered-errors sentence under the tool-error row only when the report says so', () => {
    const open = render(ready, { details: true });
    expect(open).toContain('Hermes issues each skill call by typing a command; every error was recovered within the run.');
    expect(open.indexOf('data-tool-error-note')).toBeGreaterThan(open.indexOf('Tool error rate'));
    expect(open.indexOf('data-tool-error-note')).toBeLessThan(open.indexOf('Tokens per run'));
    const no = render(withMetrics((m) => { m.notes = { toolErrorsRecovered: false }; }), { details: true });
    expect(no).not.toContain('every error was recovered');
  });
  it('R1 checkpoint shows the pending empty state', () => {
    const open = render(ready, { details: true, checkpoint: 'r1' });
    expect(open).toContain('Pending');
  });
});

describe('page rules', () => {
  it('every number on the page is in the source markdown (the ratio N and static labels excepted)', () => {
    const n = String(costRatio(metrics));
    const allowed = new Set([n, '5', '0.4', ...Array.from({ length: 12 }, (_, i) => String(i + 1))]);
    for (const html of [render(), render(ready, { details: true })]) {
      const numbers = text(html).match(/\d[\d,]*(?:\.\d+)?/g) ?? [];
      const bad = numbers.filter((x) => !allowed.has(x) && !SOURCE.includes(x));
      expect(bad).toEqual([]);
      expect(numbers.length).toBeGreaterThan(10);
    }
  });
  it('wording: no banned words, no "better" / "more accurate" / fewer hallucinations', () => {
    for (const html of [render(), render(ready, { details: true })]) {
      const t = text(html);
      expect(t).not.toMatch(/\bsecure\b|\bsafe\b|injection-proof|\bNAT\b/i);
      expect(t).not.toMatch(/\bbetter\b|more accurate|fewer hallucinations|fewer errors/i);
    }
    const src = fs.readFileSync(path.join(root, 'gui/src/pages/ScorecardPage.tsx'), 'utf8') + fs.readFileSync(path.join(root, 'gui/src/lib/scorecard.ts'), 'utf8');
    expect(src).not.toMatch(/\bsecure\b|\bsafe\b|injection-proof|\bNAT\b|more accurate|fewer hallucinations/i);
  });
  it('a missing containment part says "See the report"; loading and error states show', () => {
    expect(render(ready, { containment: { status: 'loading' } })).toContain('See the report');
    expect(render({ status: 'loading' })).toContain('Loading cached metrics');
    expect(render({ status: 'error', message: 'HTTP 404' })).toContain('HTTP 404');
  });
  it('decisions tile spells the report rate as "N of N" only at 100%', () => {
    expect(decisionsTile(metrics).value).toBe('10 of 10');
  });
});
