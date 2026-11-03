import { useState } from 'react';
import { useMetrics, type MetricsState } from '../data/DataContext';
import type { Metrics, MetricKey, Series } from '../data/metrics';

export const PILOT_NOTE = 'Pilot: 5 dev cases, not a benchmark. Judge noise is about 0.4 flags per run, so differences that small are not findings.';

const JUDGES: ['gemini' | 'claude' | 'gpt', string][] = [['gemini', 'Gemini'], ['claude', 'Claude'], ['gpt', 'GPT']];

interface Row {
  key: MetricKey;
  label: string;
  /** Draw a bar (value is a percentage). */
  bar?: boolean;
}

const ROWS: Row[] = [
  { key: 'criterionPass', label: 'Criterion pass rate (panel, all criteria)', bar: true },
  { key: 'upheldPerRun', label: 'Upheld material flags per run' },
  { key: 'cleanRunRate', label: 'Clean-run rate (no upheld material flag)', bar: true },
  { key: 'toolErrorRate', label: 'Tool error rate' },
  { key: 'tokens', label: 'Tokens per run' },
  { key: 'turns', label: 'Turns (model calls) per run' },
  { key: 'seconds', label: 'Seconds per run' },
];

const pct = (v: string | undefined) => {
  const n = v ? parseFloat(v) : NaN;
  return Number.isFinite(n) && v?.includes('%') ? Math.min(100, n) : null;
};

function Cell({ s, row }: { s: Series; row: Row }) {
  const v = s.metrics[row.key];
  if (v === undefined) return <span className="muted">not reported</span>;
  const w = row.bar ? pct(v) : null;
  return (
    <>
      <span className="val">{v}</span>
      {w !== null && <span className="bar" aria-hidden="true"><span style={{ width: `${w}%` }} /></span>}
      {row.key === 'toolErrorRate' && s.metrics.toolErrorRateSkillOnly && <span className="sub">{s.metrics.toolErrorRateSkillOnly} of skill calls</span>}
      {row.key === 'tokens' && s.metrics.promptOverheadTokens && <span className="sub">{s.metrics.promptOverheadTokens} fixed prompt overhead per run</span>}
      {row.key === 'tokens' && s.metrics.backgroundReviewTokens && <span className="sub">+ {s.metrics.backgroundReviewTokens} in the post-run review (not included)</span>}
    </>
  );
}

function Headline({ series }: { series: Series[] }) {
  return (
    <section aria-labelledby="sc-head">
      <h3 id="sc-head" className="section-title">Headline numbers</h3>
      <div className="table-wrap">
        <table className="table table--score">
          <caption className="sr-only">Headline metrics by series</caption>
          <thead>
            <tr>
              <th scope="col">Measure</th>
              {series.map((s) => (
                <th scope="col" key={s.id}>
                  {s.label}
                  <span className="th-sub">{s.metrics.runs} runs · {s.configuration}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r) => (
              <tr key={r.key}>
                <th scope="row">{r.label}</th>
                {series.map((s) => (
                  <td key={s.id}><Cell s={s} row={r} /></td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted small">
        {series.map((s) => `${s.label}: ${s.detail}`).join('. ')}. Tool error rates count different things: see each report.
      </p>
    </section>
  );
}

function Judges({ series }: { series: Series[] }) {
  const group = (kind: 'panel' | 'content', title: string) => (
    <div className="table-wrap">
      <table className="table table--score">
        <caption>{title}</caption>
        <thead>
          <tr>
            <th scope="col">Judge</th>
            {series.map((s) => <th scope="col" key={s.id}>{s.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {JUDGES.map(([k, label]) => (
            <tr key={k}>
              <th scope="row">{label}</th>
              {series.map((s) => <td key={s.id}>{s.judges[kind]?.[k] ?? <span className="muted">not reported</span>}</td>)}
            </tr>
          ))}
          {kind === 'panel' && (
            <tr>
              <th scope="row">Judge agreement</th>
              {series.map((s) => <td key={s.id}>{s.metrics.unanimity ?? <span className="muted">not reported</span>}</td>)}
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
  return (
    <section aria-labelledby="sj-head">
      <h3 id="sj-head" className="section-title">Judge panel</h3>
      <div className="two-up">
        {group('panel', 'Pass rate per judge, all criteria')}
        {group('content', 'Pass rate per judge, judge-graded criteria only')}
      </div>
    </section>
  );
}

function Categories({ metrics }: { metrics: Metrics }) {
  const { series, categories } = metrics;
  return (
    <section aria-labelledby="sk-head">
      <h3 id="sk-head" className="section-title">By category</h3>
      <p className="muted small">Panel pass rate of each run, and its upheld material flags. Only the categories that were run have values.</p>
      <div className="table-wrap">
        <table className="table table--score">
          <caption className="sr-only">Results by case category</caption>
          <thead>
            <tr>
              <th scope="col">Category</th>
              {series.map((s) => <th scope="col" key={s.id}>{s.label}</th>)}
            </tr>
          </thead>
          <tbody>
            {categories.map((c) => {
              const ran = c.cases.length > 0 && series.some((s) => c.cells[s.id].length > 0);
              return (
                <tr key={c.n}>
                  <th scope="row"><span className="mono">{c.n}</span> {c.name}</th>
                  {series.map((s) => (
                    <td key={s.id}>
                      {!ran || c.cells[s.id].length === 0 ? (
                        <span className="muted">Not run yet</span>
                      ) : (
                        <ul className="cells">
                          {c.cells[s.id].map((x) => (
                            <li key={x.runId}>
                              <span className="val">{x.panelPass}</span>
                              <span className="sub">{x.upheldMaterial} upheld material · {x.runId}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export type Checkpoint = 'base' | 'r1';

export function ScorecardView({ state, checkpoint, onCheckpoint }: { state: MetricsState; checkpoint: Checkpoint; onCheckpoint: (c: Checkpoint) => void }) {
  return (
    <section>
      <p className="eyebrow">Scorecard</p>
      <h2 className="page-title">Three judges grade every criterion</h2>
      <p className="notice notice--note" role="note">{PILOT_NOTE}</p>

      <div className="segmented segmented--block" role="group" aria-label="Model checkpoint">
        <button type="button" className="segmented__btn" aria-pressed={checkpoint === 'base'} onClick={() => onCheckpoint('base')}>Base Super</button>
        <button type="button" className="segmented__btn" aria-pressed={checkpoint === 'r1'} onClick={() => onCheckpoint('r1')}>R1 checkpoint</button>
      </div>

      {checkpoint === 'r1' && (
        <div className="empty" role="status">
          <h3 className="card__title">Pending</h3>
          <p className="muted">No runs with R1&rsquo;s post-trained checkpoint behind the route yet. When they exist, the same cases, skills and judges will be scored here next to Base Super.</p>
        </div>
      )}

      {checkpoint === 'base' && state.status === 'loading' && <p className="muted">Loading cached metrics</p>}
      {checkpoint === 'base' && state.status === 'error' && (
        <p className="notice notice--error" role="alert">Could not load metrics ({state.message}). Run npm run cache.</p>
      )}
      {checkpoint === 'base' && state.status === 'ready' && (
        <>
          <Headline series={state.metrics.series} />
          <Judges series={state.metrics.series} />
          <Categories metrics={state.metrics} />
          <p className="muted small">Sources: {state.metrics.sources.join(', ')}. The Claude judge is the same model as the document-generation model.</p>
        </>
      )}
    </section>
  );
}

export function ScorecardPage() {
  const state = useMetrics();
  const [checkpoint, setCheckpoint] = useState<Checkpoint>('base');
  return <ScorecardView state={state} checkpoint={checkpoint} onCheckpoint={setCheckpoint} />;
}
