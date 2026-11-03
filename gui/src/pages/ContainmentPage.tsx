import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAttackRun, useContainment } from '../data/DataContext';
import type { Containment } from '../data/containment';
import type { AttackMode, ContainmentIndexEntry } from '../data/types';
import { AgentPanel, AuditPanel, BlockedPanel, InjectedPanel, LetterPanel, ModeBadge, OutcomePanel, ReportPanel, StackStrip, SummaryStrip, WhoPanel, type Focus } from '../components/Containment/Panels';
import { Replay } from '../components/Containment/Replay';
import { buildTimeline, listedAudit, nearestAudit, nearestStep, shownAt } from '../components/Containment/logic';

const SCENARIOS: { id: string; label: string }[] = [
  { id: 'A1', label: 'A1 (curl upload)' },
  { id: 'A2', label: 'A2 (Python POST, a different channel)' },
  { id: 'A3', label: 'A3 (file write)' },
];
const MODES: { id: AttackMode; label: string }[] = [
  { id: 'natural', label: 'Natural' },
  { id: 'scripted', label: 'Scripted' },
];

/** Runs of one scenario by mode; the natural sample of A1 is a variant (A1b) of the fixture. */
export function sampleFor(runs: ContainmentIndexEntry[], scenario: string, mode: AttackMode): ContainmentIndexEntry | undefined {
  return runs.find((r) => r.scenario === scenario && r.attackMode === mode);
}

function Selector({ data, scenario, mode, setScenario, setMode }: { data: Containment; scenario: string; mode: AttackMode; setScenario: (s: string) => void; setMode: (m: AttackMode) => void }) {
  const natural = data.natural?.filter((r) => r.scenario === scenario);
  return (
    <section aria-label="Choose a recorded run" className="ct-select">
      <div role="group" aria-label="Scenario" className="segmented">
        {SCENARIOS.map((s) => (
          <button key={s.id} type="button" className="segmented__btn" aria-pressed={scenario === s.id} onClick={() => setScenario(s.id)}>{s.label}</button>
        ))}
      </div>
      <div role="group" aria-label="Mode" className="segmented">
        {MODES.map((m) => {
          const has = Boolean(sampleFor(data.runs, scenario, m.id));
          return (
            <span key={m.id} title={has ? undefined : 'No recorded sample for this mode'}>
              <button type="button" className="segmented__btn" aria-pressed={mode === m.id} disabled={!has} onClick={() => setMode(m.id)}>{m.label}</button>
            </span>
          );
        })}
      </div>
      {MODES.some((m) => !sampleFor(data.runs, scenario, m.id)) && (
        <p className="muted small">The disabled mode has no recorded sample for this scenario.</p>
      )}
      <p className="muted small" data-rate>
        Natural attempts in the report for {scenario}:{' '}
        {natural?.length ? natural.map((r) => `${r.fixture} ${r.attempted}`).join(', ') : 'See the report'}.
      </p>
    </section>
  );
}

function Scenario({ data, entry }: { data: Containment; entry: ContainmentIndexEntry }) {
  const state = useAttackRun(entry.file);
  const [focus, setFocus] = useState<Focus>(null);
  const [showBackground, setShowBackground] = useState(false);
  const [pos, setPos] = useState(Number.MAX_SAFE_INTEGER);
  const [open, setOpen] = useState(false);

  const run = state.status === 'ready' ? state.run : null;
  const timeline = useMemo(() => (run ? buildTimeline(run, showBackground) : []), [run, showBackground]);
  // Each run opens on its attempt (when there is one), so the matching OpenShell row is highlighted.
  const attemptStep = run?.attempt?.stepN ?? null;
  useEffect(() => {
    setFocus(attemptStep ? { kind: 'step', n: attemptStep } : null);
    setPos(Number.MAX_SAFE_INTEGER);
  }, [entry.file, attemptStep]);

  if (state.status === 'loading') return <p className="muted">Loading the recorded run</p>;
  if (state.status === 'error' || !run) return <p className="notice notice--error" role="alert">Could not load the recorded run ({state.status === 'error' ? state.message : ''}). Run npm run cache.</p>;

  const total = timeline.length;
  const p = Math.min(pos, total);
  const final = p >= total;
  const shown = final ? null : shownAt(timeline, p);
  const rows = listedAudit(run, showBackground);
  const linkedStep = focus?.kind === 'audit' ? nearestStep(run, focus.index) : null;
  const linkedAudit = focus?.kind === 'step' ? nearestAudit(run, focus.n, rows) : null;

  return (
    <div data-run={`${run.attackId}/${run.attackMode}`}>
      <p className="muted small">Fixture {run.attackId}, run {run.runId}, case {run.caseId}.</p>
      <ModeBadge run={run} />
      <InjectedPanel run={run} />
      <div className="ct-split">
        <AgentPanel run={run} focus={focus} setFocus={setFocus} visible={shown?.steps ?? null} linkedStep={linkedStep} />
        <AuditPanel run={run} focus={focus} setFocus={setFocus} visible={shown?.audit ?? null} linkedAudit={linkedAudit} showBackground={showBackground} setShowBackground={setShowBackground} />
      </div>
      <Replay total={total} pos={p} setPos={setPos} />
      <BlockedPanel run={run} />
      <div className="ct-two">
        <OutcomePanel run={run} />
        <WhoPanel run={run} data={data} />
      </div>
      <LetterPanel run={run} />
      <ReportPanel data={data} open={open} setOpen={setOpen} />
    </div>
  );
}

export function ContainmentView({ data, scenario, mode, setScenario, setMode }: { data: Containment; scenario: string; mode: AttackMode; setScenario: (s: string) => void; setMode: (m: AttackMode) => void }) {
  const entry = sampleFor(data.runs, scenario, mode);
  return (
    <>
      <StackStrip data={data} />
      <SummaryStrip data={data} />
      <Selector data={data} scenario={scenario} mode={mode} setScenario={setScenario} setMode={setMode} />
      {entry ? <Scenario key={entry.file} data={data} entry={entry} /> : <p className="notice">No recorded sample for this scenario and mode.</p>}
      {data.missing.length > 0 && <p className="notice notice--error" role="alert">See the report: {data.missing.join(', ')} could not be read from the report.</p>}
    </>
  );
}

export function ContainmentPage() {
  const state = useContainment();
  const [params, setParams] = useSearchParams();
  const data = state.status === 'ready' ? state.data : null;

  // Default: the first scenario whose natural sample is a real OpenShell block; nothing stopped by the agent-side safeguard.
  const scenario = SCENARIOS.some((s) => s.id === params.get('scenario')) ? params.get('scenario')! : 'A1';
  const wanted = params.get('mode') === 'scripted' ? 'scripted' : params.get('mode') === 'natural' ? 'natural' : null;
  const mode: AttackMode = data
    ? wanted && sampleFor(data.runs, scenario, wanted) ? wanted : sampleFor(data.runs, scenario, 'natural') ? 'natural' : 'scripted'
    : 'natural';
  const set = (s: string, m: AttackMode) => setParams({ scenario: s, mode: m }, { replace: true });

  return (
    <section className="ct">
      <p className="eyebrow">Containment</p>
      <h2 className="page-title">OpenShell decides what leaves.</h2>
      <p className="lede">A poisoned clinical note told the agent to send data out. Here is what the agent did, and what OpenShell did.</p>
      {state.status === 'loading' && <p className="muted">Loading cached data</p>}
      {state.status === 'error' && <p className="notice notice--error" role="alert">Could not load containment.json ({state.message}). Run npm run cache.</p>}
      {data && <ContainmentView data={data} scenario={scenario} mode={mode} setScenario={(s) => set(s, mode)} setMode={(m) => set(scenario, m)} />}
    </section>
  );
}
