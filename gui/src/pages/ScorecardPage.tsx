import { Fragment, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useContainment, useMetrics, type ContainmentState, type MetricsState } from '../data/DataContext';
import type { Containment } from '../data/containment';
import { SUBTITLE_NEUTRAL, SUBTITLE_POSITIVE, containmentTile, costLine, costSentence, decisionsTile, seriesOf, subtitleSupported } from '../lib/scorecard';
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

function Headline({ series, recovered }: { series: Series[]; recovered: boolean }) {
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
              <Fragment key={r.key}>
                <tr>
                  <th scope="row">{r.label}</th>
                  {series.map((s) => (
                    <td key={s.id}><Cell s={s} row={r} /></td>
                  ))}
                </tr>
                {r.key === 'toolErrorRate' && recovered && (
                  <tr data-tool-error-note>
                    <td colSpan={series.length + 1} className="muted small">Hermes issues each skill call by typing a command; every error was recovered within the run.</td>
                  </tr>
                )}
              </Fragment>
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

const SEE = 'See the report';

function Tile({ value, label, to }: { value: string; label: string; to?: string }) {
  const body = (
    <>
      <span className="sb-tile__v">{value}</span>
      <span className="sb-tile__l">{label}</span>
      {to && <span className="sb-tile__cta">Open containment →</span>}
    </>
  );
  return <li className="sb-tile-item">{to ? <Link className="card card--link sb-tile" to={to}>{body}</Link> : <div className="card sb-tile">{body}</div>}</li>;
}

/** Three ways of working: the only table of the booth view. */
function Compare({ metrics, containment }: { metrics: Metrics; containment: Containment | null }) {
  const cols: { id: 'baseline' | 'standin' | 'hermes'; head: string; sandbox: boolean }[] = [
    { id: 'baseline', head: 'No tools: one prompt', sandbox: false },
    { id: 'standin', head: 'Same agent, no sandbox', sandbox: false },
    { id: 'hermes', head: 'Agent in OpenShell', sandbox: true },
  ];
  const confined = containment?.summary.allowedOther === '0';
  return (
    <section aria-labelledby="sb-three">
      <h3 id="sb-three" className="section-title sb-section">Three ways of working</h3>
      <div className="table-wrap">
        <table className="table table--score sb-table" data-compare>
          <caption className="sr-only">Three ways of working compared</caption>
          <thead>
            <tr>
              <td />
              {cols.map((c) => <th scope="col" key={c.id} className={c.sandbox ? 'sb-hl' : undefined}>{c.head}</th>)}
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">Checklist criteria passed</th>
              {cols.map((c) => <td key={c.id} className={c.sandbox ? 'sb-hl' : undefined}><span className="val">{seriesOf(metrics, c.id)?.metrics.criterionPass ?? SEE}</span></td>)}
            </tr>
            <tr>
              <th scope="row">Runs inside OpenShell</th>
              {cols.map((c) => <td key={c.id} className={c.sandbox ? 'sb-hl' : undefined}><span className="val">{c.sandbox ? 'Yes' : 'No'}</span></td>)}
            </tr>
            <tr>
              <th scope="row">Network limited to the model endpoint</th>
              {cols.map((c) => <td key={c.id} className={c.sandbox ? 'sb-hl' : undefined}><span className="val">{c.sandbox ? (confined ? 'Yes' : SEE) : 'No sandbox'}</span></td>)}
            </tr>
          </tbody>
        </table>
      </div>
      <p className="muted small">R1&rsquo;s post-trained checkpoint will appear here as another column.</p>
    </section>
  );
}

function Details({ metrics, checkpoint, onCheckpoint }: { metrics: Metrics; checkpoint: Checkpoint; onCheckpoint: (c: Checkpoint) => void }) {
  return (
    <div id="sc-details" className="sb-details" aria-label="Details">
      <Headline series={metrics.series} recovered={Boolean(metrics.notes?.toolErrorsRecovered)} />
      <Judges series={metrics.series} />
      <Categories metrics={metrics} />
      <section aria-labelledby="sb-ckpt">
        <h3 id="sb-ckpt" className="section-title">Model checkpoint</h3>
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
      </section>
      <p className="muted small">Sources: {metrics.sources.join(', ')}. The Claude judge is the same model as the document-generation model.</p>
    </div>
  );
}

export function ScorecardView({ state, containment, checkpoint, onCheckpoint, detailsOpen, setDetails }: {
  state: MetricsState;
  containment: ContainmentState;
  checkpoint: Checkpoint;
  onCheckpoint: (c: Checkpoint) => void;
  detailsOpen: boolean;
  setDetails: (open: boolean) => void;
}) {
  const metrics = state.status === 'ready' ? state.metrics : null;
  const c = containment.status === 'ready' ? containment.data : null;
  const decisions = metrics ? decisionsTile(metrics) : null;
  const pass = metrics ? seriesOf(metrics, 'hermes')?.metrics.criterionPass : undefined;
  const standin = metrics ? seriesOf(metrics, 'standin')?.metrics.criterionPass : undefined;
  const contain = containmentTile(c);
  return (
    <section className="sb" data-scorecard>
      <p className="eyebrow">SCORECARD</p>
      <h2 className="page-title">The same answers, inside the sandbox.</h2>
      {state.status === 'loading' && <p className="muted">Loading cached metrics</p>}
      {state.status === 'error' && <p className="notice notice--error" role="alert">Could not load metrics ({state.message}). Run npm run cache.</p>}
      {metrics && decisions && (
        <>
          <p className="sb-sub" data-subtitle>{subtitleSupported(metrics) ? SUBTITLE_POSITIVE : SUBTITLE_NEUTRAL}</p>
          <ul className="sb-tiles" aria-label="Three numbers">
            <Tile value={decisions.value} label={decisions.label} />
            <Tile value={pass ?? SEE} label={`of checklist criteria passed. The same agent without a sandbox: ${standin ?? SEE}.`} />
            <Tile value={contain.value} label={contain.label} to="/containment" />
          </ul>
          <Compare metrics={metrics} containment={c} />
          <p className="sb-cost" data-cost>{costSentence(costLine(metrics))}</p>
          <div className="sb-foot">
            <p className="muted small">{PILOT_NOTE}</p>
            <button type="button" className="btn" id="sc-details-btn" aria-expanded={detailsOpen} aria-controls="sc-details" onClick={() => setDetails(!detailsOpen)}>Details</button>
          </div>
          {detailsOpen && <Details metrics={metrics} checkpoint={checkpoint} onCheckpoint={onCheckpoint} />}
        </>
      )}
    </section>
  );
}

/** ?details=1 opens the Details section; it is closed otherwise. */
export const isDetailsOpen = (params: URLSearchParams): boolean => params.get('details') === '1';

export function ScorecardPage() {
  const state = useMetrics();
  const containment = useContainment();
  const [checkpoint, setCheckpoint] = useState<Checkpoint>('base');
  const [params, setParams] = useSearchParams();
  return (
    <ScorecardView
      state={state}
      containment={containment}
      checkpoint={checkpoint}
      onCheckpoint={setCheckpoint}
      detailsOpen={isDetailsOpen(params)}
      setDetails={(open) => setParams(open ? { details: '1' } : {}, { replace: true })}
    />
  );
}
