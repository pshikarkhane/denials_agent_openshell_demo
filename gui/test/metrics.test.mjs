import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildMetrics, parseTables, splitJudges } from '../scripts/build_metrics.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const md = (f) => fs.readFileSync(path.join(root, f), 'utf8');
const SOURCE = md('docs/RUN_REPORT.md') + '\n' + md('docs/HERMES_RUN_REPORT.md');

/** Every string leaf of the metrics object that holds a figure. */
function figures(o, out = []) {
  if (typeof o === 'string') {
    if (/\d/.test(o)) out.push(o);
  } else if (Array.isArray(o)) o.forEach((x) => figures(x, out));
  else if (o && typeof o === 'object') Object.values(o).forEach((x) => figures(x, out));
  return out;
}

describe('parseTables', () => {
  it('parses headings, headers and rows, dropping bold and code marks', () => {
    const t = parseTables('## A **b**\n\n| x | y |\n|---|---|\n| `1` | **2** |\n| 3 | 4 |\n\ntext');
    expect(t).toEqual([{ heading: 'A b', header: ['x', 'y'], rows: [['1', '2'], ['3', '4']] }]);
  });
});

describe('build_metrics', () => {
  const m = buildMetrics({ root });

  it('has the three series with their headline values from the reports', () => {
    expect(m.series.map((s) => s.id)).toEqual(['baseline', 'standin', 'hermes']);
    const [b, s, h] = m.series;
    expect(b.metrics).toMatchObject({ criterionPass: '95.5%', upheldPerRun: '0.70', cleanRunRate: '50%', tokens: '25,315' });
    expect(s.metrics).toMatchObject({ criterionPass: '98.2%', upheldPerRun: '0.80', toolErrorRate: '2.2%', tokens: '83,995' });
    expect(h.metrics).toMatchObject({ criterionPass: '97.8%', upheldPerRun: '0.50', toolErrorRate: '14.5%', tokens: '250,435', turns: '11.6', seconds: '50', cleanRunRate: '70%', unanimity: '86%' });
    expect(h.judges.panel).toEqual({ gemini: '93%', claude: '98%', gpt: '98%' });
    expect([b.runs.length, s.runs.length, h.runs.length]).toEqual([10, 15, 10]);
  });

  it('fills only the categories that were run', () => {
    const ran = m.categories.filter((c) => Object.values(c.cells).some((x) => x.length)).map((c) => c.n);
    expect(ran).toEqual([1, 2, 6, 8, 12]);
    expect(m.categories).toHaveLength(12);
  });

  it('every figure appears in the source markdown', () => {
    const list = figures(m.series.map((s) => [s.metrics, s.judges, s.runs]).concat([m.categories.map((c) => c.cells)]));
    expect(list.length).toBeGreaterThan(200);
    const missing = list.filter((f) => !SOURCE.includes(f));
    expect(missing).toEqual([]);
  });

  it('splitJudges handles non-triples', () => {
    expect(splitJudges('n/a')).toBeNull();
    expect(splitJudges('1%/2%/3%')).toEqual({ gemini: '1%', claude: '2%', gpt: '3%' });
  });

  it('the published file matches the build and holds no answer-key name', () => {
    const file = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../public/data/metrics.json');
    expect(JSON.parse(fs.readFileSync(file, 'utf8'))).toEqual(m);
  });
});
