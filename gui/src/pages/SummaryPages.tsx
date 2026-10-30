import type { ReactNode } from 'react';
import { useIndexState } from '../data/DataContext';
import { decisionLabel } from '../data/select';

function Placeholder({ title, blurb, children }: { title: string; blurb: string; children?: ReactNode }) {
  const state = useIndexState();
  return (
    <section>
      <p className="eyebrow">Next step</p>
      <h2 className="page-title">{title}</h2>
      <p className="muted">{blurb}</p>
      {state.status === 'loading' && <p className="muted">Loading cached data</p>}
      {state.status === 'error' && <p className="notice notice--error" role="alert">{state.message}</p>}
      {state.status === 'ready' && (
        <>
          <div className="table-wrap">
            <table className="table">
              <caption className="sr-only">Cached runs</caption>
              <thead>
                <tr>
                  <th scope="col">Case</th>
                  <th scope="col">Source</th>
                  <th scope="col">Decision</th>
                  <th scope="col">Steps</th>
                  <th scope="col">Audit events</th>
                </tr>
              </thead>
              <tbody>
                {state.index.runs.map((r) => (
                  <tr key={r.file}>
                    <th scope="row">{r.caseId}</th>
                    <td>{r.source}</td>
                    <td>{decisionLabel(r.decision)}</td>
                    <td>{r.stepCount}</td>
                    <td>{r.auditCount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {children}
        </>
      )}
    </section>
  );
}

export const ContainmentPage = () => (
  <Placeholder title="Containment" blurb="The trace and audit log split screen will live here. The stand-in runs have no sandbox, so their audit log is empty." />
);

export const ScorecardPage = () => (
  <Placeholder title="Scorecard" blurb="Metrics, the judge panel and by-category results will live here." />
);
