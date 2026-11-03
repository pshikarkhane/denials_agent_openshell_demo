import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAttackRun, useContainment } from '../data/DataContext';
import type { Containment } from '../data/containment';
import type { AttackMode, AttackRunView, ContainmentIndexEntry } from '../data/types';
import { Booth } from '../components/Containment/Booth';
import { SCENARIOS, LIMITS } from '../components/Containment/boothLogic';
import { AgentPanel, AuditPanel, InjectedPanel, LetterPanel, Section, StackStrip, WhoPanel, type Focus } from '../components/Containment/Panels';
import { Replay } from '../components/Containment/Replay';
import { buildTimeline, listedAudit, nearestAudit, nearestStep, shownAt } from '../components/Containment/logic';

/** ?details=1 opens the Details section; it is closed otherwise. */
export const isDetailsOpen = (params: URLSearchParams): boolean => params.get('details') === '1';

/** Runs of one scenario by mode; the natural sample of A1 is a variant (A1b) of the fixture. */
export function sampleFor(runs: ContainmentIndexEntry[], scenario: string, mode: AttackMode): ContainmentIndexEntry | undefined {
  return runs.find((r) => r.scenario === scenario && r.attackMode === mode);
}

/** The Details section: closed by default, every block collapsible. */
export function DetailsBody({ data, run }: { data: Containment; run: AttackRunView }) {
  const [focus, setFocus] = useState<Focus>(null);
  const [showBackground, setShowBackground] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [pos, setPos] = useState(Number.MAX_SAFE_INTEGER);

  const attemptStep = run.attempt?.stepN ?? null;
  useEffect(() => {
    setFocus(attemptStep ? { kind: 'step', n: attemptStep } : null);
    setPos(Number.MAX_SAFE_INTEGER);
  }, [run.runId, run.attackMode, attemptStep]);

  const timeline = useMemo(() => buildTimeline(run, showBackground), [run, showBackground]);
  const total = timeline.length;
  const p = Math.min(pos, total);
  const shown = p >= total ? null : shownAt(timeline, p);
  const rows = listedAudit(run, showBackground);
  const linkedStep = focus?.kind === 'audit' ? nearestStep(run, focus.index) : null;
  const linkedAudit = focus?.kind === 'step' ? nearestAudit(run, focus.n, rows) : null;
  const modelHosts = data.hardening.modelHost ? [data.hardening.modelHost] : [];

  return (
    <>
      <p className="muted small">Fixture {run.attackId}, run {run.runId}, case {run.caseId}.</p>
      <Section id="stack" title="The stack and who did what">
        <StackStrip data={data} />
        <WhoPanel run={run} data={data} />
      </Section>
      <Section id="steps" title="The agent's steps and the injected text">
        <InjectedPanel run={run} />
        <AgentPanel run={run} focus={focus} setFocus={setFocus} visible={shown?.steps ?? null} linkedStep={linkedStep} />
      </Section>
      <Section id="audit" title="The OpenShell audit log">
        <AuditPanel run={run} focus={focus} setFocus={setFocus} visible={shown?.audit ?? null} until={shown?.until ?? Infinity} linkedAudit={linkedAudit} showAll={showAll} setShowAll={setShowAll} showBackground={showBackground} setShowBackground={setShowBackground} modelHosts={modelHosts} />
      </Section>
      <Section id="replay" title="Replay and the letter">
        <Replay total={total} pos={p} setPos={setPos} />
        <LetterPanel run={run} />
      </Section>
      <Section id="limits" title="Limits">
        <ul className="ct-list" data-limits>{LIMITS.map((t) => <li key={t}>{t}</li>)}</ul>
        <p className="muted small">Full report: docs/CONTAINMENT_REPORT.md</p>
      </Section>
    </>
  );
}

export function ContainmentPage() {
  const state = useContainment();
  const [params, setParams] = useSearchParams();
  const data = state.status === 'ready' ? state.data : null;

  // The three natural samples tell which scenarios have a natural attempt to show.
  const naturalFile = (id: string) => (data ? sampleFor(data.runs, id, 'natural')?.file ?? null : null);
  const n1 = useAttackRun(naturalFile(SCENARIOS[0].id));
  const n2 = useAttackRun(naturalFile(SCENARIOS[1].id));
  const n3 = useAttackRun(naturalFile(SCENARIOS[2].id));
  const naturals = [n1, n2, n3];
  const naturalReady = naturals.every((n, i) => !naturalFile(SCENARIOS[i].id) || n.status !== 'loading');
  const naturalAvailable: Record<string, boolean> = {};
  SCENARIOS.forEach((x, i) => {
    const n = naturals[i];
    naturalAvailable[x.id] = Boolean(naturalFile(x.id)) && n.status === 'ready' && n.run.attempt !== null;
  });

  const scenario = SCENARIOS.some((s) => s.id === params.get('scenario')) ? params.get('scenario')! : SCENARIOS[0].id;
  const asked: AttackMode = params.get('mode') === 'scripted' ? 'scripted' : 'natural';
  // Natural only where the recording holds an attempt; otherwise Scripted stays selected.
  const mode: AttackMode = asked === 'natural' && naturalAvailable[scenario] ? 'natural' : 'scripted';
  const detailsOpen = isDetailsOpen(params);

  const idx = SCENARIOS.findIndex((s) => s.id === scenario);
  const scriptedEntry = data ? sampleFor(data.runs, scenario, 'scripted') : undefined;
  const scripted = useAttackRun(mode === 'scripted' && scriptedEntry ? scriptedEntry.file : null);
  const naturalState = naturals[idx];
  const current = mode === 'natural' ? naturalState : scripted;
  const run = current.status === 'ready' ? current.run : null;

  const update = (next: Record<string, string | null>) => {
    const p = new URLSearchParams(params);
    for (const [k, v] of Object.entries(next)) v === null ? p.delete(k) : p.set(k, v);
    setParams(p, { replace: true });
  };

  return (
    <>
      {state.status === 'loading' && <p className="muted">Loading cached data</p>}
      {state.status === 'error' && <p className="notice notice--error" role="alert">Could not load containment.json ({state.message}). Run npm run cache.</p>}
      {data && !naturalReady && <p className="muted">Loading the recorded runs</p>}
      {data && naturalReady && (
        <Booth
          data={data}
          scenario={scenario}
          mode={mode}
          run={run}
          naturalAvailable={naturalAvailable}
          setScenario={(id) => update({ scenario: id })}
          setMode={(m) => update({ mode: m })}
          detailsOpen={detailsOpen}
          setDetails={(open) => update({ details: open ? '1' : null })}
        >
          {run ? <DetailsBody data={data} run={run} /> : <p className="muted">Loading the recorded run</p>}
        </Booth>
      )}
      {data && data.missing.length > 0 && <p className="notice notice--error" role="alert">See the report: {data.missing.join(', ')} could not be read from the report.</p>}
    </>
  );
}
