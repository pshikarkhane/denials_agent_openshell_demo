import { decisionLabel } from '../data/select';
import type { RunView } from '../data/types';

export function RunSummary({ run }: { run: RunView }) {
  const rows: [string, string][] = [
    ['Case', run.caseId],
    ['Source', run.source],
    ['Decision', decisionLabel(run.decision)],
    ['Denial code', run.denialCode],
    ['Policy', run.policyId],
    ['Steps', String(run.steps.length)],
  ];
  return (
    <dl className="facts">
      {rows.map(([k, v]) => (
        <div key={k} className="facts__row">
          <dt>{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}
