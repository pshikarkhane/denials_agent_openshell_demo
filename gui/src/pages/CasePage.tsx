import { Link, useParams } from 'react-router-dom';
import { useIndexState, useRun } from '../data/DataContext';
import { latestRunForCase } from '../data/select';
import { RunSummary } from '../components/RunSummary';

export function CasePage() {
  const { caseId = '' } = useParams();
  const state = useIndexState();
  const entry = state.status === 'ready' ? latestRunForCase(state.index, caseId) : undefined;
  const run = useRun(entry?.file ?? null);

  return (
    <section>
      <p className="eyebrow">Next step</p>
      <h2 className="page-title">Case {caseId}</h2>
      {state.status === 'loading' && <p className="muted">Loading cached data</p>}
      {state.status === 'error' && <p className="notice notice--error" role="alert">{state.message}</p>}
      {state.status === 'ready' && !entry && <p className="notice">No recorded run yet</p>}
      {entry && run.status === 'loading' && <p className="muted">Loading run</p>}
      {entry && run.status === 'error' && <p className="notice notice--error" role="alert">{run.message}</p>}
      {entry && run.status === 'ready' && <RunSummary run={run.run} />}
      <p className="muted spaced">
        This page will show the before and after view and the criteria tab. <Link to="/">Back to Home</Link>
      </p>
    </section>
  );
}
