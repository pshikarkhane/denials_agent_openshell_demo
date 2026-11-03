import { useEffect, useRef, type ReactNode } from 'react';
import type { Containment } from '../../data/containment';
import type { AttackAuditEvent, AttackRunView, AttackStep } from '../../data/types';
import { BLOCKED_COPY, afterRunCount, clock, hiddenBackground, isOpenShellBlock, listedAudit, markTokens, NATURAL_BADGE, SCRIPTED_BADGE } from './logic';

export type Focus = { kind: 'step'; n: number } | { kind: 'audit'; index: number } | null;

const SEE = 'See the report';
const v = (x: string | null | undefined): string => x ?? SEE;
const yesNo = (b: boolean | null): string => (b === null ? 'not recorded' : b ? 'yes' : 'no');

/** Scrolls a row to the middle of its own scroll box (never the page). */
function useScrollTo(box: React.RefObject<HTMLElement | null>, selector: string | null, dep: unknown) {
  useEffect(() => {
    const c = box.current;
    const el = selector ? c?.querySelector<HTMLElement>(selector) : null;
    if (!c || !el) return;
    c.scrollTop += el.getBoundingClientRect().top - c.getBoundingClientRect().top - c.clientHeight / 2;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dep]);
}

export function Marked({ text }: { text: string }) {
  return <>{markTokens(text).map((p, i) => (p.hit ? <mark key={i} className="ct-mark">{p.text}</mark> : p.text))}</>;
}

// ---------- stack and summary strips ----------

export function StackStrip({ data }: { data: Containment }) {
  const h = data.hardening;
  return (
    <section aria-label="The stack" className="ct-stack">
      <article className="ct-tile ct-tile--nv">
        <h3 className="ct-tile__name">OpenShell</h3>
        <p className="ct-tile__line">The sandbox that enforces policy outside the agent.</p>
        <p className="ct-tile__num"><strong>{v(data.summary.allowedOther)}</strong> allowed connections other than the model endpoint, in all {v(data.summary.allowedOtherRuns)} runs</p>
      </article>
      <article className="ct-tile ct-tile--nv">
        <h3 className="ct-tile__name">NemoClaw</h3>
        <p className="ct-tile__line">The blueprint that deploys the sandbox, agent and model route, and changes policy and model through supported commands.</p>
        <p className="ct-tile__num">
          Allowlist after hardening: <strong className="mono">{h.remaining?.modelEndpoint ?? SEE}</strong> (the model route).
          {' '}Removed: {h.removed ? h.removed.join(', ') : SEE}.
        </p>
      </article>
      <article className="ct-tile ct-tile--nv">
        <h3 className="ct-tile__name">Nemotron 3.5 Super (preview)</h3>
        <p className="ct-tile__line">The model that made the case decision.</p>
        <p className="ct-tile__num">Decisions correct <strong>{v(data.nemotron.decisionCorrect)}</strong>, criterion pass rate <strong>{v(data.nemotron.criterionPass)}</strong> ({v(data.nemotron.runs)} Hermes runs)</p>
      </article>
      <article className="ct-tile ct-tile--guest">
        <h3 className="ct-tile__name">Agent: Hermes (open source)</h3>
        <p className="ct-tile__line">The open-source agent we brought. The sandbox's rules do not depend on it.</p>
      </article>
    </section>
  );
}

export function SummaryStrip({ data }: { data: Containment }) {
  const s = data.summary;
  const natBlocked = data.natural?.filter((r) => r.blocked !== 'n/a').map((r) => r.blocked);
  const items: [string, ReactNode, string][] = [
    ['Injection seen by the model', v(s.injectionSeen), 'natural runs where the poisoned note was in a tool result'],
    ['Natural attempts', v(s.naturalAttempts), 'runs where the agent chose to act on it'],
    ['Attempts blocked by OpenShell', natBlocked?.length ? natBlocked.join(', ') : SEE, 'of the natural attempts'],
    ['Scripted attempts blocked', data.scripted ? data.scripted.map((r) => `${r.scenario} ${r.blocked}`).join(' · ') : SEE, 'by OpenShell alone, per scenario'],
    ['Allowed connections other than the model endpoint', v(s.allowedOther), `in all ${v(s.allowedOtherRuns)} runs`],
    ['Runs', v(s.runs), s.naturalRuns && s.scriptedRuns ? `${s.naturalRuns} natural, ${s.scriptedRuns} scripted` : ''],
  ];
  return (
    <section aria-label="Summary of the recorded runs">
      <ul className="ct-sum">
        {items.map(([label, value, sub]) => (
          <li key={label} className="ct-sum__item">
            <span className="ct-sum__v">{value}</span>
            <span className="ct-sum__l">{label}</span>
            <span className="ct-sum__s">{sub}</span>
          </li>
        ))}
      </ul>
      <p className="ct-lede">The agent mostly ignored the note. OpenShell's job is what happens when it does not.</p>
    </section>
  );
}

// ---------- badges, injected text ----------

export function ModeBadge({ run }: { run: AttackRunView }) {
  const a = run.attempt;
  return (
    <div className="ct-badges">
      {run.attackMode === 'scripted' ? (
        <p className="ct-badge ct-badge--scripted" data-badge="scripted"><strong>{SCRIPTED_BADGE.split(':')[0]}:</strong>{SCRIPTED_BADGE.slice(SCRIPTED_BADGE.indexOf(':') + 1)}</p>
      ) : (
        <p className="ct-badge ct-badge--natural" data-badge="natural">{NATURAL_BADGE}</p>
      )}
      {run.attackMode === 'natural' && a && (
        <p className="ct-payload" data-payload>
          What the command carried, read from the recorded command:{' '}
          {a.payload ? (a.payload.kind === 'text' ? <>a short text string, <q>{a.payload.value}</q>.</> : <>the file <span className="mono">{a.payload.value}</span>.</>) : 'not shown by the command.'}
        </p>
      )}
      {run.attackMode === 'natural' && !a && <p className="ct-payload">In this run the agent did not attempt the action.</p>}
    </div>
  );
}

export function InjectedPanel({ run }: { run: AttackRunView }) {
  const inj = run.injection;
  return (
    <section className="ct-panel" aria-labelledby="ct-inj">
      <h3 id="ct-inj" className="ct-panel__h">The injected text</h3>
      {inj.excerpt ? (
        <>
          <blockquote className="ct-quote"><Marked text={inj.excerpt} /></blockquote>
          <p className="muted small">As the agent received it in a tool result (step {run.steps.find((s) => s.seq === inj.seq)?.n ?? '?'}); the poisoned host and path are marked.</p>
        </>
      ) : (
        <p className="muted">{inj.note}</p>
      )}
      <p className="muted small">The recording says the model saw the injected text in this run: {yesNo(run.injectionSeenByModel)}.</p>
    </section>
  );
}

// ---------- split screen ----------

function StepButton({ s, run, focus, setFocus, linked }: { s: AttackStep; run: AttackRunView; focus: Focus; setFocus: (f: Focus) => void; linked: boolean }) {
  const isAttempt = run.attempt?.stepN === s.n;
  const selected = focus?.kind === 'step' && focus.n === s.n;
  return (
    <li className={`ct-step${isAttempt ? ' is-attempt' : ''}${linked ? ' is-linked' : ''}`} data-step={s.n}>
      <button type="button" className="ct-step__btn" aria-pressed={selected} onClick={() => setFocus(selected ? null : { kind: 'step', n: s.n })}>
        <span className="mono ct-step__t">{clock(s.ts)}</span>
        <span className="ct-step__name">{s.name}</span>
        <span className="muted small">{s.summary}</span>
        {isAttempt && <span className="ct-tag ct-tag--attempt">{run.attempt!.scripted ? 'SCRIPTED ATTEMPT' : 'ATTEMPT'}</span>}
        {s.status !== 'ok' && <span className="ct-tag ct-tag--err">ERROR</span>}
      </button>
      {(isAttempt || selected) && (
        <div className="ct-step__detail">
          {s.command && (<><p className="ct-lbl">Raw command</p><pre className="ct-code" tabIndex={0}><Marked text={s.command} /></pre></>)}
          {s.result && (<><p className="ct-lbl">Result</p><pre className="ct-code" tabIndex={0}><Marked text={s.result.slice(0, 1500)} /></pre></>)}
        </div>
      )}
    </li>
  );
}

export function AgentPanel({ run, focus, setFocus, visible, linkedStep }: { run: AttackRunView; focus: Focus; setFocus: (f: Focus) => void; visible: Set<number> | null; linkedStep: number | null }) {
  const steps = run.steps.filter((s) => !visible || visible.has(s.n));
  const box = useRef<HTMLOListElement>(null);
  const target = linkedStep ?? (focus?.kind === 'step' ? focus.n : null);
  useScrollTo(box, target ? `[data-step="${target}"]` : null, `${run.runId}/${target}`);
  return (
    <section className="ct-panel ct-split__col" aria-labelledby="ct-agent">
      <h3 id="ct-agent" className="ct-panel__h">What the agent did</h3>
      <p className="muted small">Steps from the recorded events, with their time (UTC). The attempt is highlighted.</p>
      <ol className="ct-steps" aria-label="Agent steps" ref={box}>
        {steps.map((s) => <StepButton key={s.n} s={s} run={run} focus={focus} setFocus={setFocus} linked={linkedStep === s.n} />)}
      </ol>
    </section>
  );
}

function ResultLabel({ r }: { r: string }) {
  if (r === 'denied') return <span className="ct-res ct-res--denied">DENIED</span>;
  if (r === 'allowed') return <span className="ct-res ct-res--allowed">ALLOWED</span>;
  return <span className="ct-res">no decision</span>;
}

export function AuditPanel({ run, focus, setFocus, visible, linkedAudit, showBackground, setShowBackground }: {
  run: AttackRunView; focus: Focus; setFocus: (f: Focus) => void; visible: Set<number> | null; linkedAudit: number | null; showBackground: boolean; setShowBackground: (b: boolean) => void;
}) {
  const hidden = hiddenBackground(run);
  const rows: AttackAuditEvent[] = listedAudit(run, showBackground).filter((a) => !visible || visible.has(a.index));
  const box = useRef<HTMLDivElement>(null);
  const target = linkedAudit ?? (focus?.kind === 'audit' ? focus.index : null);
  useScrollTo(box, target !== null ? `[data-audit="${target}"]` : null, `${run.runId}/${target}`);
  return (
    <section className="ct-panel ct-split__col" aria-labelledby="ct-audit">
      <h3 id="ct-audit" className="ct-panel__h">What OpenShell recorded</h3>
      <div className="ct-audit__bar">
        <button type="button" className="btn btn--small" aria-pressed={showBackground} onClick={() => setShowBackground(!showBackground)} disabled={hidden === 0 && !showBackground}>
          {showBackground ? 'Hide' : 'Show'} the agent's own background events ({hidden} {showBackground ? 'shown' : 'hidden'})
        </button>
        <span className="muted small">Rows tagged after the run ({afterRunCount(run)}) are not listed.</span>
      </div>
      <div className="ct-audit__scroll" tabIndex={0} role="region" aria-label="OpenShell audit log" ref={box}>
        <table className="ct-audit" data-audit-table>
          <caption className="sr-only">OpenShell audit events of this run, time ordered</caption>
          <thead>
            <tr><th scope="col">Time (UTC)</th><th scope="col">Event class</th><th scope="col">Target</th><th scope="col">Result</th><th scope="col">Reason</th><th scope="col">Actor / binary</th></tr>
          </thead>
          <tbody>
            {rows.map((a) => {
              const selected = focus?.kind === 'audit' && focus.index === a.index;
              return (
                <tr key={a.index} data-audit={a.index} data-tag={a.tag ?? ''} className={`${a.result === 'denied' ? 'is-denied' : a.result === 'allowed' ? 'is-allowed' : ''}${linkedAudit === a.index ? ' is-linked' : ''}${a.tag === 'background' ? ' is-background' : ''}`}>
                  <td className="mono">
                    <button type="button" className="ct-rowbtn" aria-pressed={selected} aria-label={`Select the event at ${clock(a.ts)}`} onClick={() => setFocus(selected ? null : { kind: 'audit', index: a.index })}>{clock(a.ts)}</button>
                  </td>
                  <td className="mono">{a.eventClass}</td>
                  <td className="mono">{a.target || '-'}</td>
                  <td><ResultLabel r={a.result} />{a.tag === 'background' && <span className="ct-tag ct-tag--bg">BACKGROUND</span>}</td>
                  <td>{a.reason || '-'}</td>
                  <td className="mono">{a.actor ?? '-'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ---------- blocked by, outcome, who did what, letter ----------

export function BlockedPanel({ run }: { run: AttackRunView }) {
  const copy = BLOCKED_COPY[run.blockedBy];
  const ev = run.evidenceAudit.map((i) => run.audit[i]).filter(Boolean);
  return (
    <section className={`ct-panel ct-blocked ct-blocked--${run.blockedBy}`} aria-labelledby="ct-blocked" data-blocked={run.blockedBy}>
      <h3 id="ct-blocked" className="ct-panel__h">Blocked by</h3>
      <p className="ct-blocked__title">{copy.title}</p>
      {copy.lines.map((l) => <p key={l}>{l}</p>)}
      {run.blockedBy === 'openshell_network' && ev.map((a) => (
        <p key={a.index} className="muted small mono">{clock(a.ts)} {a.eventClass} {a.result.toUpperCase()} {a.actor ?? ''} to {a.target}: {a.reason}</p>
      ))}
      {run.blockedBy === 'openshell_file' && run.attempt && <pre className="ct-code" tabIndex={0}>{run.attempt.result}</pre>}
      {run.blockedBy === 'agent_safeguard' && run.attempt && <pre className="ct-code" tabIndex={0}>{run.attempt.result}</pre>}
    </section>
  );
}

export function OutcomePanel({ run }: { run: AttackRunView }) {
  const o = run.outcome;
  const rows: [string, string][] = [
    ['Denied events (run-tagged)', String(o.auditDenied)],
    ['Allowed events (run-tagged)', String(o.auditAllowed)],
    ['Allowed connections other than the model endpoint, according to the audit log', String(o.auditAllowedOther)],
    ['Blocked by OpenShell in this run', isOpenShellBlock(run.blockedBy) ? 'yes' : 'no'],
    ['Decision correct', yesNo(o.decisionCorrect)],
    ['Denial code correct', yesNo(o.denialCodeOk)],
    ['Deadline correct', yesNo(o.actionDeadlineOk)],
    ['Both output files exist', yesNo(o.decisionJsonPresent && o.deliverablePresent)],
  ];
  return (
    <section className="ct-panel" aria-labelledby="ct-outcome">
      <h3 id="ct-outcome" className="ct-panel__h">Outcome</h3>
      <dl className="ct-dl">
        {rows.map(([k, val]) => (<div key={k} className="ct-dl__row"><dt>{k}</dt><dd>{val}</dd></div>))}
      </dl>
    </section>
  );
}

export function WhoPanel({ run, data }: { run: AttackRunView; data: Containment }) {
  const o = run.outcome;
  const h = data.hardening;
  return (
    <section className="ct-panel" aria-labelledby="ct-who">
      <h3 id="ct-who" className="ct-panel__h">Who did what</h3>
      <ul className="ct-who">
        <li><strong>Nemotron 3.5 Super (preview):</strong> made the case decision. Decision correct in this run: {yesNo(o.decisionCorrect)}.</li>
        <li><strong>OpenShell:</strong> enforced the policy outside the agent. Denied {o.auditDenied}, allowed other than the model endpoint {o.auditAllowedOther}, according to the audit log.</li>
        <li><strong>NemoClaw:</strong> deployed the sandbox, agent and model route; policy hardened with supported commands. Allowlist after hardening: <span className="mono">{h.remaining?.modelEndpoint ?? SEE}</span>; removed: {h.removed ? h.removed.join(', ') : SEE}.</li>
        <li><strong>Hermes (open source agent we brought):</strong> ran the workflow.</li>
      </ul>
      <p className="ct-lede">Replaceable: the sandbox's rules do not depend on which agent or model is inside.</p>
    </section>
  );
}

export function LetterPanel({ run }: { run: AttackRunView }) {
  return (
    <section className="ct-panel" aria-labelledby="ct-letter">
      <h3 id="ct-letter" className="ct-panel__h">What the note did to the letter</h3>
      {run.letter.mentionsInjection ? (
        <>
          {run.letter.sentence && <blockquote className="ct-quote"><Marked text={run.letter.sentence} /></blockquote>}
          <p>OpenShell cannot catch this kind of influence.</p>
        </>
      ) : (
        <p>The letter does not mention the injected request.</p>
      )}
    </section>
  );
}

export function ReportPanel({ data, open, setOpen }: { data: Containment; open: boolean; setOpen: (b: boolean) => void }) {
  return (
    <section className="ct-panel" aria-labelledby="ct-report">
      <h3 id="ct-report" className="ct-panel__h">
        <button type="button" className="ct-disclose" aria-expanded={open} aria-controls="ct-report-body" onClick={() => setOpen(!open)}>What this does and does not show</button>
      </h3>
      <div id="ct-report-body" hidden={!open} data-report>
        <h4 className="ct-lbl">Plain statements of the limits</h4>
        {data.limits ? <ul className="ct-list">{data.limits.map((t, i) => <li key={i}>{t}</li>)}</ul> : <p>{SEE}</p>}
        <h4 className="ct-lbl">What this proves and does not prove</h4>
        {data.proves ? data.proves.map((t, i) => <p key={i}>{t}</p>) : <p>{SEE}</p>}
        <p className="muted small">Source: docs/CONTAINMENT_REPORT.md</p>
      </div>
    </section>
  );
}

