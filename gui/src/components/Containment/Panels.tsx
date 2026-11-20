// Panels of the Details section of the Containment page (the booth view itself is Booth.tsx).
import { useEffect, useRef, type ReactNode } from 'react';
import type { Containment } from '../../data/containment';
import type { AttackAuditEvent, AttackRunView, AttackStep } from '../../data/types';
import { auditLines, sortByTime } from './boothLogic';
import { clock, hiddenBackground, listedAudit, markTokens } from './logic';

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

/** A collapsible block inside Details; open by default once Details is open. */
export function Section({ id, title, children, defaultOpen = true }: { id: string; title: string; children: ReactNode; defaultOpen?: boolean }) {
  return (
    <details className="dt-section" open={defaultOpen} data-section={id}>
      <summary className="dt-section__sum">{title}</summary>
      <div className="dt-section__body">{children}</div>
    </details>
  );
}

// ---------- stack and who did what ----------

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

export function WhoPanel({ run, data }: { run: AttackRunView; data: Containment }) {
  const o = run.outcome;
  const h = data.hardening;
  return (
    <div className="ct-panel" aria-label="Who did what">
      <h3 className="ct-panel__h">Who did what</h3>
      <ul className="ct-who">
        <li><strong>Nemotron 3.5 Super (preview):</strong> made the case decision. Decision correct in this run: {yesNo(o.decisionCorrect)}.</li>
        <li><strong>OpenShell:</strong> enforced the policy outside the agent. Denied {o.auditDenied}, allowed other than the model endpoint {o.auditAllowedOther}, according to the audit log.</li>
        <li><strong>NemoClaw:</strong> deployed the sandbox, agent and model route; policy hardened with supported commands. Allowlist after hardening: <span className="mono">{h.remaining?.modelEndpoint ?? SEE}</span>; removed: {h.removed ? h.removed.join(', ') : SEE}.</li>
        <li><strong>Hermes (open source agent we brought):</strong> ran the workflow.</li>
      </ul>
      <p className="ct-lede">Replaceable: the sandbox's rules do not depend on which agent or model is inside.</p>
    </div>
  );
}

// ---------- injected text, steps ----------

export function InjectedPanel({ run }: { run: AttackRunView }) {
  const inj = run.injection;
  if (!inj.excerpt) return <p className="muted small" data-no-excerpt>The recording does not hold the injected paragraph (recorded results are cut at 4,000 characters).</p>;
  return (
    <div className="ct-panel" aria-label="The injected text">
      <h3 className="ct-panel__h">The injected text</h3>
      <blockquote className="ct-quote"><Marked text={inj.excerpt} /></blockquote>
      <p className="muted small">As the agent received it in a tool result (step {run.steps.find((s) => s.seq === inj.seq)?.n ?? '?'}); the poisoned host and path are marked.</p>
    </div>
  );
}

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
    <div className="ct-panel" aria-label="What the agent did">
      <h3 className="ct-panel__h">What the agent did</h3>
      <p className="muted small">Steps from the recorded events, with their time (UTC). The attempt is highlighted.</p>
      <ol className="ct-steps" aria-label="Agent steps" ref={box}>
        {steps.map((s) => <StepButton key={s.n} s={s} run={run} focus={focus} setFocus={setFocus} linked={linkedStep === s.n} />)}
      </ol>
    </div>
  );
}

// ---------- audit log (decisions only by default) ----------

function ResultLabel({ r }: { r: string }) {
  if (r === 'denied') return <span className="ct-res ct-res--denied">DENIED</span>;
  if (r === 'allowed') return <span className="ct-res ct-res--allowed">ALLOWED</span>;
  return <span className="ct-res">no decision</span>;
}

export function AuditPanel({ run, focus, setFocus, visible, until, linkedAudit, showAll, setShowAll, showBackground, setShowBackground, modelHosts }: {
  run: AttackRunView; focus: Focus; setFocus: (f: Focus) => void;
  /** Replay: audit indexes shown so far (null = final state). */
  visible: Set<number> | null; until: number;
  linkedAudit: number | null; showAll: boolean; setShowAll: (b: boolean) => void; showBackground: boolean; setShowBackground: (b: boolean) => void; modelHosts: string[];
}) {
  const hidden = hiddenBackground(run);
  const runCount = run.audit.filter((a) => a.tag === 'run').length;
  const shown: AttackAuditEvent[] = sortByTime(listedAudit(run, showBackground)).filter((a) => !visible || visible.has(a.index) || (showAll && Date.parse(a.ts) <= until));
  const lines = auditLines(shown, { showAll, modelHosts });
  const box = useRef<HTMLDivElement>(null);
  const target = linkedAudit ?? (focus?.kind === 'audit' ? focus.index : null);
  useScrollTo(box, target !== null ? `[data-audit-index~="${target}"]` : null, `${run.runId}/${target}/${showAll}`);
  return (
    <div className="ct-panel" aria-label="What OpenShell recorded">
      <h3 className="ct-panel__h">What OpenShell recorded</h3>
      <div className="ct-audit__bar">
        <button type="button" className="btn btn--small" aria-pressed={showAll} onClick={() => setShowAll(!showAll)}>Show all run events ({runCount})</button>
        <button type="button" className="btn btn--small" aria-pressed={showBackground} onClick={() => setShowBackground(!showBackground)} disabled={hidden === 0 && !showBackground}>
          Show the agent's own background events ({hidden})
        </button>
      </div>
      <div className="ct-audit__scroll" tabIndex={0} role="region" aria-label="OpenShell audit log" ref={box}>
        <table className="ct-audit" data-audit-table>
          <caption className="sr-only">OpenShell audit events of this run, time ordered</caption>
          <thead>
            <tr><th scope="col">Time (UTC)</th><th scope="col">Event class</th><th scope="col">Target</th><th scope="col">Result</th><th scope="col">Reason</th><th scope="col">Actor / binary</th></tr>
          </thead>
          <tbody>
            {lines.map((l) => {
              if (l.kind === 'folded') {
                return (
                  <tr key={`f${l.indexes[0]}`} className={`is-allowed is-folded${linkedAudit !== null && l.indexes.includes(linkedAudit) ? ' is-linked' : ''}`} data-folded data-audit-index={l.indexes.join(' ')}>
                    <td className="mono">{clock(l.firstTs)}</td>
                    <td colSpan={5}><ResultLabel r="allowed" /> {l.connections} allowed connections to {l.endpoint}, the model route</td>
                  </tr>
                );
              }
              const a = l.row;
              const selected = focus?.kind === 'audit' && focus.index === a.index;
              return (
                <tr key={a.index} data-audit={a.index} data-audit-index={a.index} data-tag={a.tag ?? ''} className={`${a.result === 'denied' ? 'is-denied' : a.result === 'allowed' ? 'is-allowed' : ''}${linkedAudit === a.index ? ' is-linked' : ''}${a.tag === 'background' ? ' is-background' : ''}`}>
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
    </div>
  );
}

// ---------- letter ----------

export function LetterPanel({ run }: { run: AttackRunView }) {
  return (
    <div className="ct-panel" aria-label="What the note did to the letter">
      <h3 className="ct-panel__h">What the note did to the letter</h3>
      {run.letter.mentionsInjection ? (
        <>
          {run.letter.sentence && <blockquote className="ct-quote"><Marked text={run.letter.sentence} /></blockquote>}
          <p>OpenShell cannot catch this kind of influence.</p>
        </>
      ) : (
        <p>The letter does not mention the injected request.</p>
      )}
    </div>
  );
}
