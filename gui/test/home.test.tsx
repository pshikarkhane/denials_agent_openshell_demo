import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { DataContext, type IndexState } from '../src/data/DataContext';
import { Home } from '../src/pages/Home';
import type { IndexEntry } from '../src/data/types';

const entry = (over: Partial<IndexEntry>): IndexEntry => ({
  runId: 'r1',
  caseId: 'C-0005',
  source: 'hermes',
  runtime: 'hermes',
  variant: 'agent',
  actionDeadline: '2027-01-13',
  model: 'nvidia/nvidia/nemotron-3.5-super-text-preview',
  startedAt: '2026-10-30T00:00:00.000+00:00',
  decision: 'APPEAL',
  denialCode: 'CO-50',
  policyId: 'MP-IMG-007',
  stepCount: 3,
  auditCount: 0,
  file: 'run_r1__C-0005.json',
  ...over,
});

const render = (state: IndexState) =>
  renderToStaticMarkup(
    <MemoryRouter>
      <DataContext.Provider value={state}>
        <Home />
      </DataContext.Provider>
    </MemoryRouter>,
  );

const both: IndexState = {
  status: 'ready',
  index: {
    mode: 'cached',
    runs: [
      entry({}),
      entry({ caseId: 'C-0030', decision: 'DO_NOT_APPEAL', denialCode: 'CO-29', policyId: 'MP-TF-001', file: 'run_r1__C-0030.json' }),
    ],
  },
};

const hrefsOf = (html: string) => [...html.matchAll(/<a\b[^>]*\bhref="([^"]+)"/g)].map((m) => m[1]);

describe('Home', () => {
  it('renders the hero copy and six scenario cards', () => {
    const html = render(both);
    expect(html).toContain('Denials agent, inside OpenShell.');
    expect(html).toContain('Built for RCM optimization.');
    expect(html).toContain('NemoClaw deploys it, and Nemotron 3.5 Super (preview) does the reasoning.');
    expect(html).not.toContain('R1 x NVIDIA');
    expect(html).toContain('Blueprint: NemoClaw. Sandbox: OpenShell. Model: Nemotron 3.5 Super (preview). Agent: Hermes (open source).');
    expect(html).not.toContain('PHI stays inside');
    expect((html.match(/class="card__title"/g) ?? []).length).toBe(7); // six cards + runtime card
    expect((html.match(/grid__item/g) ?? []).length).toBe(6);
    expect(html).toContain('All case content is synthetic.');
  });

  it('links five cards to the right routes and the Live card is not a link', () => {
    const html = render(both);
    const cardLinks = hrefsOf(html);
    expect(cardLinks).toEqual(['/case/C-0005', '/case/C-0030', '/containment', '/scorecard', '/scorecard']);
    const live = html.slice(html.indexOf('Run it yourself') - 400);
    expect(live).toContain('Live mode comes later');
    expect(live).toContain('aria-disabled="true"');
  });

  it('takes decision, code and policy from the cached run', () => {
    const html = render(both);
    expect(html).toContain('Appeal · CO-50 · policy MP-IMG-007 · action by 2027-01-13');
    expect(html).toContain('Do not appeal · CO-29 · policy MP-TF-001 · action by 2027-01-13');
    expect(html).not.toContain('No recorded run yet');

    const changed = render({
      status: 'ready',
      index: { mode: 'cached', runs: [entry({ denialCode: 'CO-97', policyId: 'MP-X-999' })] },
    });
    expect(changed).toContain('CO-97 · policy MP-X-999');
    expect(changed).not.toContain('CO-50');
  });

  it('says "No recorded run yet" for a missing case', () => {
    const onlyOne = render({ status: 'ready', index: { mode: 'cached', runs: [entry({})] } });
    expect((onlyOne.match(/No recorded run yet/g) ?? []).length).toBe(1);
    const none = render({ status: 'ready', index: { mode: 'cached', runs: [] } });
    expect((none.match(/No recorded run yet/g) ?? []).length).toBe(2);
    const failed = render({ status: 'error', message: 'HTTP 404' });
    expect((failed.match(/No recorded run yet/g) ?? []).length).toBe(2);
  });

  it('does not claim a missing run while still loading', () => {
    expect(render({ status: 'loading' })).not.toContain('No recorded run yet');
  });
});

describe('Home data rules', () => {
  it('quotes Hermes before the stand-in and never the baseline', () => {
    const html = render({
      status: 'ready',
      index: {
        mode: 'cached',
        runs: [
          entry({ runId: 'base-1', variant: 'baseline', runtime: 'standin', source: 'standin', decision: 'DO_NOT_APPEAL', denialCode: 'CO-99' }),
          entry({ runId: 'agent-1', runtime: 'standin', source: 'standin', startedAt: '2026-10-31T00:00:00.000+00:00', denialCode: 'CO-51' }),
          entry({ runId: 'hermes-1', denialCode: 'CO-50' }),
        ],
      },
    });
    expect(html).toContain('Hermes run hermes-1');
    expect(html).not.toContain('CO-99');
    expect(html).not.toContain('CO-51');
  });

  it('does not claim an appeal when the cached decision is not APPEAL', () => {
    const html = render({ status: 'ready', index: { mode: 'cached', runs: [entry({ decision: 'DO_NOT_APPEAL' })] } });
    expect(html).not.toContain('dated evidence');
    expect(html).toContain('Do not appeal · CO-50');
  });

  it('shows the model route of the cached runs', () => {
    const html = render({ status: 'ready', index: { mode: 'cached', runs: [entry({ model: 'acme/other-model' })] } });
    expect(html).toContain('Model: acme/other-model.');
  });
});
