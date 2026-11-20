import type { HallucinationFlag } from '../data/types';

export interface Range {
  start: number;
  end: number;
}

/**
 * Text with the markdown emphasis marks dropped and whitespace collapsed, plus a
 * map from each kept character back to its index in the raw text. Judges quote
 * the deliverable without the `**` and backtick marks it carries.
 */
function squash(raw: string): { text: string; map: number[] } {
  const map: number[] = [];
  let text = '';
  let lastSpace = true; // drops leading whitespace
  for (let i = 0; i < raw.length; i++) {
    const c = raw[i];
    if (c === '*' || c === '`') continue;
    if (/\s/.test(c)) {
      if (lastSpace) continue;
      text += ' ';
      map.push(i);
      lastSpace = true;
    } else {
      text += c;
      map.push(i);
      lastSpace = false;
    }
  }
  return { text, map };
}

/** Where a flag's quote sits in the raw deliverable text, or null when it does not. */
export function findQuote(raw: string, quote: string): Range | null {
  const q = quote.trim();
  if (!q) return null;
  const exact = raw.indexOf(q);
  if (exact >= 0) return { start: exact, end: exact + q.length };
  const s = squash(raw);
  const nq = squash(q).text.trimEnd();
  if (!nq) return null;
  const at = s.text.indexOf(nq);
  if (at < 0) return null;
  return { start: s.map[at], end: s.map[at + nq.length - 1] + 1 };
}

export const isMaterial = (f: HallucinationFlag) => f.upheld && f.severity === 'material';

export interface LocatedFlag {
  flag: HallucinationFlag;
  range: Range | null;
}

/** Upheld material flags with the range of their quote in the text (null if not found). */
export function locateMaterialFlags(raw: string, flags: HallucinationFlag[]): LocatedFlag[] {
  return flags.filter(isMaterial).map((flag) => ({ flag, range: findQuote(raw, flag.quote) }));
}
