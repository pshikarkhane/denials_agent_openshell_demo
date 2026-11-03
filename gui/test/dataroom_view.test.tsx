import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { DataRoom, CITE_NOTE } from '../src/components/DataRoom/DataRoom';
import { chainFor, defaultSelection, statusLine, toggle, HINT, type Selection } from '../src/components/DataRoom/selection';
import { CasePage } from '../src/pages/CasePage';
import { caseIds, dataRoomFile, dataRoomRuns } from '../src/data/select';
import { DataContext } from '../src/data/DataContext';
import type { DataIndex, DataRoomView, IndexEntry } from '../src/data/types';
// @ts-expect-error plain .mjs helper
import { fx, sample, viewFor } from './dataroom_helpers.mjs';

const v05: DataRoomView = viewFor(sample('hermes_run_C-0005'));
const v30: DataRoomView = viewFor(fx('hermes_run_C-0030'));
const render = (view: DataRoomView, initial?: Selection | 'default') => renderToStaticMarkup(<DataRoom view={view} initial={initial} />);
const rowsInChain = (html: string) => [...html.matchAll(/<button[^>]*data-row="(B\d+)"[^>]*data-in-chain="true"/g)].map((m) => m[1]);
const count = (html: string, re: RegExp) => (html.match(re) ?? []).length;

describe('Data room view', () => {
  it('renders one matching card and one letter card per block', () => {
    for (const v of [v05, v30]) {
      const html = render(v, null);
      expect(count(html, /data-row="/g)).toBe(v.blocks.length);
      expect(count(html, /data-block="/g)).toBe(v.blocks.length);
    }
  });

  it('shows the step labels, the legend and the sentence about citing and matching', () => {
    const html = render(v05);
    for (const s of ['1 DATA ROOM', '2 MATCHING', '3 THE LETTER', 'Case folder', 'Payer policies', 'POLICY', 'CASE']) expect(html).toContain(s);
    expect(html).toContain('Dashed: read but not cited, or not chosen');
    expect(html).toContain("Citing a file means the letter points to it. It does not verify the claim. &#x27;Matched&#x27; means the same value appears in that file.");
    expect(CITE_NOTE).toContain('does not verify the claim');
    expect(html).toContain('How the policy is chosen');
    expect(html).toContain('MP-IMG-012'); // a real considered id
  });

  it('selecting a document highlights exactly the rows that link to it', () => {
    const path = 'supporting/pt_log.txt';
    const want = v05.rows.filter((r) => r.evidence.some((e) => e.file === path)).map((r) => r.blockId);
    expect(want.length).toBeGreaterThan(0);
    const html = render(v05, { type: 'doc', path });
    expect(rowsInChain(html)).toEqual(want);
    expect(html).toContain(`${path} supports ${want.length} parts of the letter.`);
  });

  it('draws as many connectors as the chain has links, and none without a selection', () => {
    for (const sel of [{ type: 'doc', path: 'supporting/pt_log.txt' }, { type: 'policy' }, { type: 'row', id: 'B7' }] as Selection[]) {
      const html = render(v05, sel);
      expect(count(html, /data-connector="/g)).toBe(chainFor(v05, sel).connectors.length);
    }
    const none = render(v05, null);
    expect(count(none, /data-connector="/g)).toBe(0);
    expect(none).toContain('data-connectors="0"');
    expect(none).toContain(HINT);
  });

  it('a row selection chains its documents, the policy and its letter block', () => {
    const row = v05.rows.find((r) => r.blockId === 'B7')!;
    const c = chainFor(v05, { type: 'row', id: 'B7' });
    expect([...c.docs].sort()).toEqual(row.evidence.map((e) => e.file).sort());
    expect(c.policy).toBe(true);
    expect(c.connectors.filter((x) => x.kind === 'row-block')).toHaveLength(1);
    expect(statusLine(v05, { type: 'row', id: 'B7' })).toMatch(/is built from .* and matched to policy section 2\.1\(a\)\.$/);
  });

  it('selecting the same item again clears the selection', () => {
    const s: Selection = { type: 'doc', path: 'task.md' };
    expect(toggle(s, { type: 'doc', path: 'task.md' })).toBeNull();
    expect(toggle(s, { type: 'policy' })).toEqual({ type: 'policy' });
  });

  it('defaults to the first row with a policy link and a cited file', () => {
    const sel = defaultSelection(v05) as { type: 'row'; id: string };
    const row = v05.rows.find((r) => r.blockId === sel.id)!;
    expect(row.policy.kind).not.toBe('none');
    expect(row.evidence.some((e) => e.via === 'cited')).toBe(true);
    const earlier = v05.rows.slice(0, v05.rows.indexOf(row));
    expect(earlier.some((r) => r.policy.kind !== 'none' && r.evidence.some((e) => e.via === 'cited'))).toBe(false);
  });

  it('every selectable card is a button with aria-pressed; the overlay is aria-hidden', () => {
    const html = render(v05);
    const pressed = count(html, /aria-pressed="/g);
    expect(pressed).toBe(v05.caseDocs.length + 1 + v05.rows.length * 2);
    expect(html).toMatch(/<svg class="dr-overlay" aria-hidden="true"/);
    expect(html).toContain('role="status"');
    expect(html).toContain('aria-live="polite"');
  });

  it('marks flagged blocks FLAGGED and unlinked blocks with the no-link note', () => {
    expect(render(v30, null)).toContain('FLAGGED');
    expect(render(v05, null)).not.toContain('FLAGGED');
    expect(render(v30, null)).toContain('No source or policy link found');
  });

  it('labels documents that were read but not cited, and unused ones, as dashed', () => {
    const view: DataRoomView = {
      ...v05,
      caseDocs: v05.caseDocs.map((d) => (d.path === 'claim_history.txt' ? { ...d, citedBy: [], matchedBy: [], opened: true } : d.path === 'task.md' ? { ...d, citedBy: [], matchedBy: [], opened: false } : d)),
    };
    const html = render(view, null);
    expect(html).toContain('Read, not cited');
    expect(html).toContain('Not used');
    expect(html).toMatch(/is-dashed[^>]*data-use="read"/);
    expect(html).toContain('opened by a tool');
    expect(html).toContain('no trace of being opened');
    expect(html).toContain('Look-alike, not chosen');
  });

  it('shows the matched values and line numbers in the details of a selected row', () => {
    const html = render(v05, { type: 'row', id: 'B8' });
    expect(html).toContain('Clear selection');
    expect(html).toContain('Case evidence');
    expect(html).toMatch(/dr-lines__n[^>]*>\d+</);
  });
});

describe('case switcher and the Data room tab', () => {
  const entry = (caseId: string, runId: string, runtime: 'hermes' | 'standin', variant: 'agent' | 'baseline'): IndexEntry => ({
    runId, caseId, source: runtime, runtime, variant, model: 'm', startedAt: '2026-10-30T00:00:00+00:00', decision: 'APPEAL', denialCode: 'CO-50', policyId: 'MP-X',
    actionDeadline: null, stepCount: 0, auditCount: 0, file: `run_${runId}__${caseId}.json`,
  });
  const index: DataIndex = { mode: 'cached', runs: [entry('C-0030', 'b1', 'standin', 'baseline'), entry('C-0005', 'h1', 'hermes', 'agent'), entry('C-0005', 's1', 'standin', 'agent'), entry('C-0005', 'b1', 'standin', 'baseline')] };

  it('lists every cached case and keeps the tab in each link', () => {
    expect(caseIds(index)).toEqual(['C-0005', 'C-0030']);
    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={['/case/C-0005?tab=dataroom']}>
        <DataContext.Provider value={{ status: 'ready', index }}><CasePage /></DataContext.Provider>
      </MemoryRouter>,
    );
    // routes need a param; without <Routes> the case id is empty, so the switcher still lists both cases
    expect(html).toContain('aria-label="Cases"');
    expect(html).toContain('href="/case/C-0030?tab=dataroom"');
    expect(html).toContain('href="/case/C-0005?tab=dataroom"');
  });

  it('orders data room runs Hermes, stand-in, then baseline, and maps them to their files', () => {
    const runs = dataRoomRuns(index, 'C-0005');
    expect(runs.map((r) => `${r.runtime}/${r.variant}`)).toEqual(['hermes/agent', 'standin/agent', 'standin/baseline']);
    expect(dataRoomFile(runs[0])).toBe('h1__C-0005.json');
  });
});
