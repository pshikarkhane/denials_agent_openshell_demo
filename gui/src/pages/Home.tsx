import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useIndexState } from '../data/DataContext';
import { decisionLabel, latestRunForCase } from '../data/select';
import type { DataIndex, IndexEntry } from '../data/types';
import { IconCheck, IconClock, IconPlay, IconScore, IconShield, IconSwap } from '../components/Icons';

interface Scenario {
  key: string;
  title: string;
  icon: ReactNode;
  /** Plain description, or a function of the cached run for cards that name a case. */
  description: string | ((run: IndexEntry | undefined) => string);
  tags: (run: IndexEntry | undefined) => string[];
  cta: string;
  to?: string;
  /** Case this card reads from the cache. */
  caseId?: string;
}

const SCENARIOS: Scenario[] = [
  {
    key: 'win',
    title: 'The win',
    icon: <IconCheck />,
    caseId: 'C-0005',
    to: '/case/C-0005',
    description: (r) =>
      `${r ? `${r.denialCode} ` : ''}medical necessity denial; the record supports it. The agent drafts the appeal and cites dated evidence.`,
    tags: (r) => [...(r ? [decisionLabel(r.decision)] : []), 'Case C-0005'],
    cta: 'Open the case',
  },
  {
    key: 'judgment',
    title: 'The judgment call',
    icon: <IconClock />,
    caseId: 'C-0030',
    to: '/case/C-0030',
    description: (r) =>
      `${r ? `${r.denialCode} ` : ''}timely filing expired. The agent shows the deadline math and recommends not appealing.`,
    tags: (r) => [...(r ? [decisionLabel(r.decision)] : []), 'Case C-0030'],
    cta: 'Open the case',
  },
  {
    key: 'attack',
    title: 'The attack',
    icon: <IconShield />,
    to: '/containment',
    description:
      'A poisoned clinical note tells the agent to send the record out. OpenShell blocks the connection and the audit log shows it.',
    tags: () => ['Containment', 'Split screen'],
    cta: 'Open containment',
  },
  {
    key: 'swap',
    title: 'The model swap',
    icon: <IconSwap />,
    to: '/scorecard',
    description:
      "Same agent, same cases, a different model behind the route. Compare base Super with R1's post-trained checkpoint.",
    tags: () => ['V2 placeholder'],
    cta: 'Open the comparison',
  },
  {
    key: 'scorecard',
    title: 'The scorecard',
    icon: <IconScore />,
    to: '/scorecard',
    description:
      'Three judges grade every criterion and a second pass checks each claim against the source documents.',
    tags: () => ['3 judges', 'Hallucination check'],
    cta: 'Open the scorecard',
  },
  {
    key: 'live',
    title: 'Run it yourself',
    icon: <IconPlay />,
    description: 'Pick a case, switch to Live, watch the trace and audit log side by side.',
    tags: () => ['Live'],
    cta: '',
  },
];

function facts(run: IndexEntry): string {
  return `${decisionLabel(run.decision)} · ${run.denialCode} · policy ${run.policyId}`;
}

function Card({ s, index, loaded }: { s: Scenario; index: DataIndex | null; loaded: boolean }) {
  const run = s.caseId ? latestRunForCase(index, s.caseId) : undefined;
  const description = typeof s.description === 'function' ? s.description(run) : s.description;
  const missing = Boolean(s.caseId) && loaded && !run;
  const disabled = !s.to;

  const body = (
    <>
      <span className="card__chip" aria-hidden="true">{s.icon}</span>
      <h3 className="card__title">{s.title}</h3>
      <p className="card__text">{description}</p>
      {s.caseId && run && <p className="card__facts">{facts(run)}</p>}
      {missing && <p className="card__facts card__facts--missing">No recorded run yet</p>}
      <ul className="tags" aria-label="Tags">
        {s.tags(run).map((t) => (
          <li key={t} className="pill">{t}</li>
        ))}
      </ul>
      <p className={disabled ? 'card__cta card__cta--off' : 'card__cta'}>
        {disabled ? 'Live mode comes later' : `${s.cta} →`}
      </p>
    </>
  );

  return (
    <li className="grid__item">
      {disabled ? (
        <div className="card card--disabled" aria-disabled="true">{body}</div>
      ) : (
        <Link className="card card--link" to={s.to!}>{body}</Link>
      )}
    </li>
  );
}

export function Home() {
  const state = useIndexState();
  const index = state.status === 'ready' ? state.index : null;

  return (
    <>
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero__copy">
          <h1 id="hero-title" className="h1">
            One denial in.
            <br />
            <span className="accent">One scored decision out.</span>
          </h1>
          <p className="lede">
            A Hermes agent inside an OpenShell sandbox reads the denial, finds the payer policy, checks the chart, and
            either drafts the appeal or tells you not to file one.
          </p>
        </div>
        <aside className="runtime card" aria-label="Runtime">
          <p className="eyebrow">RUNTIME</p>
          <h2 className="card__title">OpenShell sandbox</h2>
          <p className="muted">Model route: Nemotron 3.5 Super</p>
          <p className="muted">Policy: PHI stays inside; allowlisted egress only</p>
          <p className="muted">Audit: OCSF event log</p>
        </aside>
      </section>

      {state.status === 'error' && (
        <p className="notice notice--error" role="alert">Could not load cached data ({state.message}). Run npm run cache.</p>
      )}

      <section aria-label="Scenarios">
        <ul className="grid">
          {SCENARIOS.map((s) => (
            <Card key={s.key} s={s} index={index} loaded={state.status !== 'loading'} />
          ))}
        </ul>
      </section>

      <p className="footnote">All case content is synthetic. Results shown are from a small pilot, not a benchmark.</p>
    </>
  );
}
