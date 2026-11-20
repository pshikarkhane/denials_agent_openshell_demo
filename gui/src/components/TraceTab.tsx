import { useState } from 'react';
import type { RunView, Step } from '../data/types';
import { Chip } from './Chip';

const asText = (v: unknown) => (typeof v === 'string' ? v : JSON.stringify(v, null, 2));

function StepRow({ step, maxMs, run }: { step: Step; maxMs: number; run: RunView }) {
  const [open, setOpen] = useState(false);
  const id = `step-${run.runId}-${step.n}`;
  const expandable = step.detail !== null || step.rawCommand !== null;
  const tone = step.status === 'error' ? 'amber' : step.status === 'denied' ? 'red' : 'neutral';
  const width = maxMs > 0 ? Math.max(2, Math.round((step.durationMs / maxMs) * 100)) : 0;

  return (
    <li className="step">
      <h4 className="step__head">
        <button type="button" className="step__btn" aria-expanded={open} aria-controls={id} disabled={!expandable} onClick={() => setOpen(!open)}>
          <span className="step__n">{step.n}</span>
          <span className="step__kind">{step.kind.replace('_', ' ')}</span>
          <span className="step__name">{step.name}</span>
          {step.hermesTool && step.hermesTool !== step.name && <span className="muted step__via">via {step.hermesTool}</span>}
          <Chip tone={tone}>{step.status}</Chip>
          <span className="step__ms">{step.durationMs.toLocaleString('en-US')} ms</span>
        </button>
      </h4>
      <div className="step__bar" aria-hidden="true"><span style={{ width: `${width}%` }} /></div>
      <p className="step__sum muted">{step.argsSummary && <span className="mono">{step.argsSummary}</span>}{step.argsSummary && step.resultSummary ? ' → ' : ''}<span className="mono">{step.resultSummary}</span></p>
      {open && (
        <div id={id} className="step__detail">
          {step.rawCommand && (
            <>
              <p className="step__label">Raw terminal command</p>
              <pre className="code" tabIndex={0}>{step.rawCommand}</pre>
            </>
          )}
          {step.detail?.arguments !== undefined && (
            <>
              <p className="step__label">Arguments</p>
              <pre className="code" tabIndex={0}>{asText(step.detail.arguments)}</pre>
            </>
          )}
          {step.detail?.result !== undefined && (
            <>
              <p className="step__label">{step.kind === 'model' ? 'Assistant text' : 'Result (first 4000 characters)'}</p>
              <pre className="code" tabIndex={0}>{step.detail.result}</pre>
            </>
          )}
        </div>
      )}
    </li>
  );
}

export function TraceTab({ run }: { run: RunView | null }) {
  if (!run) return <p className="muted">No agent run is cached for this case.</p>;
  if (!run.steps.length) return <p className="muted">This run has no trace.</p>;
  const maxMs = Math.max(...run.steps.map((s) => s.durationMs));
  return (
    <div>
      <p className="muted">
        {run.runId}: {run.steps.length} steps, {run.metrics.toolErrors} tool errors. Select a step to see its arguments and result.
      </p>
      <ol className="steps">
        {run.steps.map((s) => (
          <StepRow key={s.n} step={s} maxMs={maxMs} run={run} />
        ))}
      </ol>
    </div>
  );
}
