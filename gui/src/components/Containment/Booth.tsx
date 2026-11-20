// The booth view: read from two meters in about 20 seconds. The story in three
// beats plus three numbers; everything else lives in the Details section.
import type { ReactNode } from 'react';
import type { Containment } from '../../data/containment';
import type { AttackMode, AttackRunView } from '../../data/types';
import { SCENARIOS, notActedSentence, outcomeSentence, payloadSentence, scenarioTile, shorten, verdictOf } from './boothLogic';

const SEE = 'See the report';
export const SCRIPTED_CHIP = "Scripted attempt: we ran this command ourselves, outside the agent's own checks. The result shows OpenShell alone.";
export const NATURAL_CHIP = 'Natural run: the agent chose this.';
export const FOOTNOTE = 'Blocked file access is not recorded in the audit log. One case, five runs per scenario: a demo, not a benchmark.';

function Arrow() {
  return (
    <span className="bt-arrow" aria-hidden="true">
      <svg viewBox="0 0 48 24" width="48" height="24" focusable="false"><path d="M2 12h38M30 3l10 9-10 9" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>
    </span>
  );
}

function Tile({ value, label }: { value: string; label: string }) {
  return (
    <li className="bt-tile">
      <span className="bt-tile__v">{value}</span>
      <span className="bt-tile__l">{label}</span>
    </li>
  );
}

export function Booth({ data, scenario, mode, run, naturalAvailable, setScenario, setMode, detailsOpen, setDetails, children }: {
  data: Containment;
  scenario: string;
  mode: AttackMode;
  run: AttackRunView | null;
  /** Scenario id -> the recorded natural sample contains an attempt. */
  naturalAvailable: Record<string, boolean>;
  setScenario: (id: string) => void;
  setMode: (m: AttackMode) => void;
  detailsOpen: boolean;
  setDetails: (open: boolean) => void;
  /** Details section content. */
  children?: ReactNode;
}) {
  const s = data.summary;
  const sc = SCENARIOS.find((x) => x.id === scenario) ?? SCENARIOS[0];
  const tile3 = scenarioTile(data, scenario, mode);
  const naturalOk = naturalAvailable[scenario] !== false;
  const attempt = run?.attempt ?? null;
  const verdict = run ? verdictOf(run) : null;
  const payload = run && mode === 'natural' ? payloadSentence(run) : null;

  return (
    <section className="ct booth" data-booth>
      <p className="eyebrow">CONTAINMENT</p>
      <h2 className="bt-title">OpenShell decides what leaves.</h2>
      <p className="bt-sub">A poisoned note told the agent to send data out. Here is what happened.</p>
      <p className="bt-stack">Sandbox: OpenShell · Deployed by: NemoClaw · Model: Nemotron 3.5 Super (preview) · Agent: Hermes (open source)</p>

      <ul className="bt-tiles" aria-label="Three numbers">
        <Tile value={s.naturalAttempts ?? SEE} label="natural runs where the agent acted on the note" />
        <Tile value={s.allowedOther ?? SEE} label={`connections to anywhere but the model endpoint, in all ${s.allowedOtherRuns ?? SEE} runs`} />
        <Tile value={tile3.value} label={tile3.label} />
      </ul>

      <div className="bt-select">
        <div role="group" aria-label="Scenario" className="bt-group">
          {SCENARIOS.map((x) => (
            <button key={x.id} type="button" className="bt-btn" aria-pressed={scenario === x.id} onClick={() => setScenario(x.id)}>{x.label}</button>
          ))}
        </div>
        <div role="group" aria-label="Mode" className="bt-group">
          <button type="button" className="bt-btn" aria-pressed={mode === 'natural'} disabled={!naturalOk} onClick={() => setMode('natural')}>Natural</button>
          <button type="button" className="bt-btn" aria-pressed={mode === 'scripted'} onClick={() => setMode('scripted')}>Scripted</button>
        </div>
      </div>
      {!naturalOk && <p className="bt-why" data-natural-off>{notActedSentence(data.natural, scenario)}</p>}

      <div className="bt-flow" key={`${scenario}/${mode}`}>
        <article className="bt-card" aria-labelledby="bt-c1">
          <h3 id="bt-c1" className="bt-step">1 THE NOTE</h3>
          <p className="bt-text">{sc.note}</p>
        </article>
        <Arrow />
        <article className="bt-card" aria-labelledby="bt-c2">
          <h3 id="bt-c2" className="bt-step">2 THE COMMAND</h3>
          {attempt ? (
            <pre className="bt-cmd" data-run-content title={attempt.command}>{shorten(attempt.command, 180)}</pre>
          ) : (
            <p className="bt-text" data-run-content>{run ? 'No command was recorded in this run.' : 'Loading the recorded run'}</p>
          )}
          {mode === 'scripted' ? (
            <p className="bt-chip bt-chip--scripted" data-chip="scripted">{SCRIPTED_CHIP}</p>
          ) : (
            <p className="bt-chip bt-chip--natural" data-chip="natural">{NATURAL_CHIP}{payload && <span data-run-content> {payload}</span>}</p>
          )}
        </article>
        <Arrow />
        <article className={`bt-card bt-card--${verdict?.kind ?? 'none'}`} aria-labelledby="bt-c3" data-verdict={verdict?.kind ?? 'loading'}>
          <h3 id="bt-c3" className="bt-step">3 OPENSHELL</h3>
          {verdict?.word && <p className="bt-word">{verdict.word}</p>}
          <div data-run-content>
            {verdict?.lines.filter(Boolean).map((l) => <p key={l} className="bt-line">{l}</p>)}
          </div>
        </article>
      </div>

      {run && <p className="bt-outcome" data-run-content-outcome>{outcomeSentence(run)}</p>}

      <div className="bt-foot">
        <p className="bt-note">{FOOTNOTE}</p>
        <button type="button" className="bt-btn bt-btn--details" id="ct-details-btn" aria-expanded={detailsOpen} aria-controls="ct-details" onClick={() => setDetails(!detailsOpen)}>
          Details
        </button>
      </div>
      {detailsOpen && <div id="ct-details" className="dt" aria-label="Details">{children}</div>}
    </section>
  );
}

