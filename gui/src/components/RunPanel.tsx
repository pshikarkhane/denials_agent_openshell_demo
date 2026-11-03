import { useMemo } from 'react';
import type { HallucinationFlag, RunView, Step } from '../data/types';
import { decisionLabel, formatUtc } from '../data/select';
import { locateMaterialFlags } from '../lib/quotes';
import { Chip } from './Chip';
import { Deliverable } from './Deliverable';

const JUDGE_LABEL: Record<string, string> = { claude: 'Claude', gemini: 'Gemini', gpt: 'GPT' };

export function runTitle(run: RunView): string {
  if (run.variant === 'baseline') return 'No tools: one prompt with every document pasted in';
  return run.runtime === 'hermes' ? 'Agent: Hermes in the OpenShell sandbox' : 'Agent: pre-sandbox stand-in (tool loop, no sandbox)';
}

function FlagItem({ flag, found }: { flag: HallucinationFlag; found: boolean | null }) {
  const votes = Object.entries(flag.votes);
  return (
    <li className={`flag ${flag.upheld ? '' : 'flag--off'}`}>
      <p className="flag__head">
        <span className="flag__id">{flag.id}</span>
        {flag.upheld ? <Chip tone={flag.severity === 'material' ? 'red' : 'amber'}>{flag.severity ?? 'upheld'}</Chip> : <Chip>not upheld</Chip>}
        {found === false && <span className="muted flag__note">Quote not found in the text above</span>}
      </p>
      <blockquote className="flag__quote">{flag.quote}</blockquote>
      {votes.length > 0 && (
        <ul className="flag__votes">
          {votes.map(([judge, v]) => (
            <li key={judge}>
              <strong>{JUDGE_LABEL[judge] ?? judge}</strong>{' '}
              <span className="muted">{v.upheld ? (v.severity ?? 'upheld') : 'not upheld'}:</span> {v.reason}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

/** Trace chips: the agent's steps in order, skill names, errors in amber. */
export function TraceChips({ steps }: { steps: Step[] }) {
  const shown = steps.filter((s) => s.kind === 'tool' || s.kind === 'revision');
  if (!shown.length) return null;
  return (
    <ol className="trace-chips" aria-label="Steps in order">
      {shown.map((s) => (
        <li key={s.n}>
          <Chip tone={s.status === 'error' ? 'amber' : s.status === 'denied' ? 'red' : s.kind === 'revision' ? 'neutral' : 'green'}>
            {s.skillName ?? s.name}
            {s.status !== 'ok' && s.kind === 'tool' ? ` (${s.status})` : ''}
          </Chip>
        </li>
      ))}
    </ol>
  );
}

export function RunPanel({ run }: { run: RunView }) {
  const located = useMemo(() => locateMaterialFlags(run.deliverableMarkdown, run.flags), [run]);
  const foundById = new Map(located.map((l) => [l.flag.id, l.range !== null]));
  const upheld = run.flags.filter((f) => f.upheld);
  const notUpheld = run.flags.filter((f) => !f.upheld);
  const material = upheld.filter((f) => f.severity === 'material').length;
  const m = run.metrics;

  return (
    <article className="panel" aria-label={runTitle(run)}>
      <header className="panel__head">
        <h3 className="panel__title">{runTitle(run)}</h3>
        <p className="muted panel__meta">{run.runId} · {formatUtc(run.startedAt)}</p>
        <p className="panel__chips">
          <Chip tone="green">{decisionLabel(run.decision)}</Chip>
          <Chip>{m.turns} {m.turns === 1 ? 'model call' : 'model calls'}</Chip>
          <Chip>{m.tokens.total.toLocaleString('en-US')} tokens</Chip>
          <Chip>{m.wallClockSeconds} s</Chip>
          {run.variant === 'agent' && <Chip tone={m.toolErrors > 0 ? 'amber' : 'neutral'}>{m.toolErrors} tool errors</Chip>}
        </p>
      </header>

      {run.steps.length > 0 && <TraceChips steps={run.steps} />}

      <Deliverable markdown={run.deliverableMarkdown} flags={located} />

      <section className="panel__flags" aria-label="Hallucination flags">
        <h4 className="panel__sub">Flags</h4>
        <p className="muted">
          {upheld.length} upheld ({material} material){notUpheld.length ? `, ${notUpheld.length} raised but not upheld` : ''}. Material flags are marked in red in the text when their quote is found.
        </p>
        {run.flags.length > 0 && (
          <ul className="flags">
            {[...upheld, ...notUpheld].map((f) => (
              <FlagItem key={f.id} flag={f} found={f.upheld && f.severity === 'material' ? foundById.get(f.id) ?? null : null} />
            ))}
          </ul>
        )}
      </section>
    </article>
  );
}
