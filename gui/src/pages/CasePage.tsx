import { useEffect, useState } from 'react';
import { Link, useLocation, useParams, useSearchParams } from 'react-router-dom';
import { useDataRoom, useIndexState, useRun, type RunState } from '../data/DataContext';
import { caseIds, caseSides, dataRoomFile, dataRoomRuns, decisionLabel, runLabel } from '../data/select';
import type { IndexEntry, RunView } from '../data/types';
import { Chip } from '../components/Chip';
import { DataRoom } from '../components/DataRoom/DataRoom';
import { CriteriaTab } from '../components/CriteriaTab';
import { RunPanel } from '../components/RunPanel';
import { Tabs } from '../components/Tabs';
import { TraceTab } from '../components/TraceTab';

const TABS = [
  { id: 'before-after', label: 'Before & After' },
  { id: 'criteria', label: 'Criteria' },
  { id: 'trace', label: 'Trace' },
  { id: 'dataroom', label: 'Data room' },
];

function RunSelect({ label, entries, value, onChange }: { label: string; entries: IndexEntry[]; value: string; onChange: (file: string) => void }) {
  const id = `sel-${label.replace(/\W+/g, '-')}`;
  return (
    <div className="select">
      <label htmlFor={id} className="select__label">{label}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} disabled={entries.length < 2}>
        {entries.map((r) => (
          <option key={r.file} value={r.file}>{runLabel(r)}</option>
        ))}
      </select>
    </div>
  );
}

/** One link per cached case; keeps the current tab. */
function CaseSwitcher({ ids, current }: { ids: string[]; current: string }) {
  const { search } = useLocation();
  if (ids.length < 2) return null;
  return (
    <nav className="case-switch" aria-label="Cases">
      <span className="case-switch__label">Case</span>
      {ids.map((id) => (
        <Link key={id} to={{ pathname: `/case/${id}`, search }} aria-current={id === current ? 'page' : undefined}>{id}</Link>
      ))}
    </nav>
  );
}

function DataRoomTab({ runs }: { runs: IndexEntry[] }) {
  const [file, setFile] = useState('');
  useEffect(() => {
    setFile(runs[0] ? dataRoomFile(runs[0]) : '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runs.map((r) => r.file).join('|')]);
  const state = useDataRoom(file || null);
  if (runs.length === 0) return <p className="notice">No recorded run yet for this case.</p>;
  const id = 'sel-dataroom-run';
  return (
    <div>
      <div className="select select--inline">
        <label htmlFor={id} className="select__label">Show the data room for:</label>
        <select id={id} value={file} onChange={(e) => setFile(e.target.value)} disabled={runs.length < 2}>
          {runs.map((r) => <option key={r.file} value={dataRoomFile(r)}>{runLabel(r)}</option>)}
        </select>
      </div>
      {state.status === 'loading' && <p className="muted">Loading the data room</p>}
      {state.status === 'error' && <p className="notice">The data room is not available for this run: the case documents were not found.</p>}
      {state.status === 'ready' && !state.view.available && <p className="notice">The data room is not available for this run: the case documents were not found.</p>}
      {state.status === 'ready' && state.view.available && <DataRoom key={`${state.view.runId}/${state.view.caseId}`} view={state.view} />}
    </div>
  );
}

const ready = (s: RunState): RunView | null => (s.status === 'ready' ? s.run : null);

function Side({ state, empty }: { state: RunState; empty: string }) {
  if (state.status === 'ready') return <RunPanel run={state.run} />;
  if (state.status === 'error') return <p className="notice notice--error" role="alert">{state.message}</p>;
  return <p className="muted">{empty}</p>;
}

export function CasePage() {
  const { caseId = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const index = useIndexState();
  const tab = TABS.some((t) => t.id === params.get('tab')) ? params.get('tab')! : 'before-after';

  const sides = index.status === 'ready' ? caseSides(index.index, caseId) : { left: [], right: [], leftIsStandin: false };
  const [leftFile, setLeftFile] = useState('');
  const [rightFile, setRightFile] = useState('');
  useEffect(() => {
    setLeftFile(sides.left[0]?.file ?? '');
    setRightFile(sides.right[0]?.file ?? '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index.status, caseId]);

  const leftEntry = sides.left.find((r) => r.file === leftFile) ?? sides.left[0];
  const rightEntry = sides.right.find((r) => r.file === rightFile) ?? sides.right[0];
  const left = useRun(leftEntry?.file ?? null);
  const right = useRun(rightEntry?.file ?? null);
  const lead = ready(right) ?? ready(left);

  return (
    <section>
      <p className="eyebrow">Case</p>
      <h2 className="page-title">Same case, two ways of working.</h2>
      <CaseSwitcher ids={index.status === 'ready' ? caseIds(index.index) : []} current={caseId} />

      {index.status === 'loading' && <p className="muted">Loading cached data</p>}
      {index.status === 'error' && <p className="notice notice--error" role="alert">{index.message}</p>}
      {index.status === 'ready' && !leftEntry && !rightEntry && (
        <p className="notice">No recorded run yet for case {caseId}. <Link to="/">Back to Home</Link></p>
      )}

      {lead && (
        <p className="case-chips" aria-label="Case facts">
          <Chip>Case {lead.caseId}</Chip>
          <Chip>Denial {lead.denialCode}</Chip>
          <Chip>Policy {lead.policyId}</Chip>
          {lead.actionDeadline && <Chip>Action by {lead.actionDeadline}</Chip>}
          <Chip tone="green">{decisionLabel(lead.decision)}</Chip>
        </p>
      )}

      {sides.leftIsStandin && sides.left.length > 0 && (
        <p className="notice">No no-tools baseline run is cached for this case, so the left side shows the pre-sandbox stand-in agent against Hermes.</p>
      )}

      {(leftEntry || rightEntry) && (
        <>
          {tab !== 'dataroom' && <div className="selects">
            {sides.left.length > 0 && <RunSelect label="Left run" entries={sides.left} value={leftEntry?.file ?? ''} onChange={setLeftFile} />}
            {sides.right.length > 0 && <RunSelect label="Right run" entries={sides.right} value={rightEntry?.file ?? ''} onChange={setRightFile} />}
          </div>}

          <Tabs tabs={TABS} active={tab} label="Case views" onChange={(id) => setParams(id === 'before-after' ? {} : { tab: id }, { replace: true })}>
            {tab === 'before-after' && (
              <div className="panels">
                <Side state={left} empty={leftEntry ? 'Loading run' : 'No run to show'} />
                {rightEntry ? <Side state={right} empty="Loading run" /> : <p className="notice">No Hermes run is cached for this case.</p>}
              </div>
            )}
            {tab === 'criteria' && <CriteriaTab left={ready(left)} right={ready(right)} />}
            {tab === 'dataroom' && <DataRoomTab runs={index.status === 'ready' ? dataRoomRuns(index.index, caseId) : []} />}
            {tab === 'trace' && <TraceTab run={ready(right) ?? (sides.leftIsStandin ? ready(left) : null)} />}
          </Tabs>
        </>
      )}
    </section>
  );
}
