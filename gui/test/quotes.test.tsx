import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { Deliverable } from '../src/components/Deliverable';
import { findQuote, locateMaterialFlags } from '../src/lib/quotes';
import type { HallucinationFlag } from '../src/data/types';

const flag = (over: Partial<HallucinationFlag>): HallucinationFlag => ({
  id: 'F1', quote: '', severity: 'material', upheld: true, problems: [], raisedBy: [], votes: {}, ...over,
});

const RAW = '# Memo\n\n- **Denial code:** CARC CO-29 (source: denial_letter.txt)\n- Next: close the claim.\n\nThe $236.93 remains owed.';

describe('findQuote', () => {
  it('finds exact text', () => {
    const r = findQuote(RAW, 'close the claim');
    expect(RAW.slice(r!.start, r!.end)).toBe('close the claim');
  });
  it('finds a quote that lacks the bold marks', () => {
    const r = findQuote(RAW, 'Denial code: CARC CO-29');
    expect(RAW.slice(r!.start, r!.end)).toBe('Denial code:** CARC CO-29');
  });
  it('ignores whitespace differences and returns null when absent', () => {
    expect(findQuote(RAW, 'close   the\nclaim')).not.toBeNull();
    expect(findQuote(RAW, 'never written')).toBeNull();
    expect(findQuote(RAW, '   ')).toBeNull();
  });
});

describe('locateMaterialFlags', () => {
  it('keeps only upheld material flags', () => {
    const flags = [flag({}), flag({ id: 'F2', severity: 'minor' }), flag({ id: 'F3', upheld: false })];
    expect(locateMaterialFlags(RAW, flags).map((l) => l.flag.id)).toEqual(['F1']);
  });
});

describe('Deliverable', () => {
  const html = (flags: HallucinationFlag[]) =>
    renderToStaticMarkup(<Deliverable markdown={RAW} flags={locateMaterialFlags(RAW, flags)} />);

  it('renders headings, bullets, bold and citation pills', () => {
    const h = html([]);
    expect(h).toContain('<h3><span>Memo</span></h3>');
    expect(h).toContain('<strong>Denial code:</strong>');
    expect(h).toContain('<span class="cite">source: denial_letter.txt</span>');
    expect(h).not.toContain('<mark');
  });

  it('marks a material flag in place, across bold boundaries', () => {
    const h = html([flag({ quote: 'Denial code: CARC CO-29' })]);
    expect(h).toContain('<mark class="hl hl--material" data-flag="F1">');
    expect(h.match(/<mark/g)!.length).toBeGreaterThanOrEqual(2);
    expect(h.replace(/<[^>]+>/g, '')).toContain('Denial code: CARC CO-29');
  });

  it('marks a flag on a citation as a whole pill', () => {
    const h = html([flag({ quote: '(source: denial_letter.txt)' })]);
    expect(h).toMatch(/<mark[^>]*><span class="cite">source: denial_letter.txt<\/span>/);
  });

  it('does not mark flags whose quote is missing', () => {
    expect(html([flag({ quote: 'not in the text' })])).not.toContain('<mark');
  });
});
