import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { DataContext, type IndexState } from '../src/data/DataContext';
import { Home } from '../src/pages/Home';
import type { IndexEntry } from '../src/data/types';

const entry = (over: Partial<IndexEntry>): IndexEntry => ({
  runId: 'r1',
  caseId: 'C-0005',
  source: 'standin',
  model: 'm',
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
    expect(html).toContain('One denial in.');
    expect(html).toContain('One scored decision out.');
    expect(html).toContain('OpenShell sandbox');
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
    expect(html).toContain('Appeal · CO-50 · policy MP-IMG-007');
    expect(html).toContain('Do not appeal · CO-29 · policy MP-TF-001');
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
