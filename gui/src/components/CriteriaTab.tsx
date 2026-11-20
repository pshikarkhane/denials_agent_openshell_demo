import { Fragment, useState } from 'react';
import type { CriterionVerdict, RunView } from '../data/types';
import { Chip, verdictTone } from './Chip';
import { runTitle } from './RunPanel';

const JUDGES: [string, string][] = [['gemini', 'Gemini'], ['claude', 'Claude'], ['gpt', 'GPT']];

function Verdicts({ v }: { v: CriterionVerdict | undefined }) {
  if (!v) return <span className="muted">not scored</span>;
  const auto = v.judges.auto;
  return (
    <span className="verdicts">
      {auto ? (
        <Chip tone={verdictTone(auto.verdict)} title="Checked by rule, not by the judges">Rule {auto.verdict}</Chip>
      ) : (
        JUDGES.map(([k, label]) => v.judges[k] && <Chip key={k} tone={verdictTone(v.judges[k].verdict)} title={label}>{label} {v.judges[k].verdict}</Chip>)
      )}
      <Chip tone={verdictTone(v.panel)}>Panel {v.panel}</Chip>
    </span>
  );
}

function Reasons({ v }: { v: CriterionVerdict | undefined }) {
  if (!v) return <p className="muted">Not scored.</p>;
  return (
    <ul className="reasons">
      {Object.entries(v.judges).map(([k, j]) => (
        <li key={k}><strong>{k === 'auto' ? 'Rule' : (JUDGES.find(([id]) => id === k)?.[1] ?? k)}</strong> <span className="muted">{j.verdict}:</span> {j.reason}</li>
      ))}
    </ul>
  );
}

export function CriteriaTab({ left, right }: { left: RunView | null; right: RunView | null }) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const runs = [left, right].filter((r): r is RunView => r !== null);
  const ids: string[] = [];
  for (const r of runs) for (const v of r.verdicts) if (!ids.includes(v.criterionId)) ids.push(v.criterionId);
  const find = (r: RunView | null, id: string) => r?.verdicts.find((v) => v.criterionId === id);
  const text = (id: string) => runs.map((r) => find(r, id)?.text).find(Boolean);
  const rate = (r: RunView | null) => {
    if (!r || !r.verdicts.length) return null;
    return `${r.verdicts.filter((v) => v.panel === 'PASS').length} of ${r.verdicts.length} criteria pass`;
  };

  if (!ids.length) return <p className="muted">No judge verdicts are cached for the selected runs.</p>;

  return (
    <div>
      <p className="muted">
        Criterion text is shown where the verdict file carries it (criteria that failed); for the others, open the row to read each judge&rsquo;s reason. Rule-checked criteria are not graded by the judges.
      </p>
      <div className="table-wrap">
        <table className="table table--criteria">
          <caption className="sr-only">Per-criterion verdicts for the two selected runs</caption>
          <thead>
            <tr>
              <th scope="col">Criterion</th>
              {runs.map((r) => (
                <th scope="col" key={r.runId}>
                  {runTitle(r)}
                  <span className="th-sub">{rate(r)}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ids.map((id) => (
              <Fragment key={id}>
                <tr>
                  <th scope="row">
                    <button type="button" className="row-toggle" aria-expanded={!!open[id]} onClick={() => setOpen({ ...open, [id]: !open[id] })}>
                      <span className="row-toggle__caret" aria-hidden="true">{open[id] ? '▾' : '▸'}</span>
                      <span className="mono">{id}</span>
                    </button>
                    {text(id) && <span className="crit-text">{text(id)}</span>}
                  </th>
                  {runs.map((r) => (
                    <td key={r.runId}><Verdicts v={find(r, id)} /></td>
                  ))}
                </tr>
                {open[id] && (
                  <tr className="row-detail">
                    <td />
                    {runs.map((r) => (
                      <td key={r.runId}><Reasons v={find(r, id)} /></td>
                    ))}
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
