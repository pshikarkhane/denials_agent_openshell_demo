// Pure logic behind the Data room tab: turns one run plus the case documents and
// the payer policy library into a DataRoomView. No file access here (the build
// script reads the allowlisted files); everything is deterministic and exact:
// a link exists only when the text shows it.
import type {
  BlockFlag,
  BlockMatch,
  BlockSectionLink,
  CriterionStatus,
  DataRoomBlock,
  DataRoomDoc,
  DataRoomRow,
  DataRoomView,
  PolicyListing,
  PolicySectionView,
  RowEvidence,
  RowPolicyZone,
  RunView,
} from './types.ts';

export interface RawFile {
  /** Path as shown to the user: "denial_letter.txt", "notes/2026-06-04_ortho.txt", "task.md". */
  path: string;
  text: string;
}

export interface DecisionCriterion {
  id: string;
  status: string;
  evidence?: string;
}

export interface DataRoomInput {
  run: RunView;
  /** decision.json criteria; empty when absent. */
  criteria: DecisionCriterion[];
  /** Raw events.jsonl text; null when the run had no tools (baseline). */
  eventsText: string | null;
  caseFiles: RawFile[];
  /** Library files; `file` is the file name, e.g. MP-IMG-007.txt. */
  policyFiles: { file: string; text: string }[];
}

// ---------- case documents ----------

const FIRST_DOCS = ['denial_letter.txt', 'eob_835.txt'];

export function orderDocs(paths: string[]): string[] {
  const rest = paths.filter((p) => !FIRST_DOCS.includes(p) && p !== 'task.md').sort();
  return [...FIRST_DOCS.filter((p) => paths.includes(p)), ...rest, ...(paths.includes('task.md') ? ['task.md'] : [])];
}

const titleCase = (s: string) => s.toLowerCase().replace(/(^|[\s-])([a-z])/g, (_, a, b) => a + b.toUpperCase());

/** A short descriptor derived from the file itself. */
export function describeDoc(p: string, text: string): string {
  const base = p.split('/').pop() ?? p;
  if (p === 'task.md') return 'Instruction';
  if (/^denial/.test(base)) return 'Denial notice';
  if (/^eob|835|remit/.test(base)) return 'Remittance (835)';
  if (/^claim_history/.test(base)) return 'Claim history';
  if (p.startsWith('notes/')) {
    const lines = text.split('\n').map((l) => l.trim());
    const kind = lines.find((l, i) => i > 0 && /NOTE|VISIT|CONSULT/i.test(l) && l === l.toUpperCase()) ?? '';
    const date = /^Date of encounter:\s*(\d{4}-\d{2}-\d{2})/m.exec(text)?.[1] ?? /\d{4}-\d{2}-\d{2}/.exec(base)?.[0] ?? '';
    return `${kind ? titleCase(kind) : 'Visit note'}${date ? `, ${date}` : ''}`;
  }
  if (p.startsWith('supporting/')) {
    const head = text.split('\n').find((l) => /LOG|REPORT|RECORD/i.test(l));
    return head ? titleCase(head.replace(/^.*?-\s*/, '').trim()) : 'Supporting log';
  }
  return 'Case document';
}

const baseName = (p: string) => p.split('/').pop() ?? p;
const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** True when the text names this file by path or by file name. */
export function mentionsFile(text: string, p: string): boolean {
  const b = baseName(p);
  return new RegExp(`(?<![A-Za-z0-9_.-])${esc(b)}(?![A-Za-z0-9_-])`).test(text);
}

// ---------- policies ----------

export interface ParsedPolicy extends PolicyListing {
  sections: PolicySectionView[];
}

export function parsePolicy(file: string, text: string): ParsedPolicy {
  const lines = text.split('\n');
  const field = (name: string) => new RegExp(`^${name}:\\s*(.+)$`, 'm').exec(text)?.[1].trim() ?? '';
  const id = field('Policy ID') || file.replace(/\.txt$/, '');
  const sections: PolicySectionView[] = [];
  let cur: PolicySectionView | null = null;
  for (const raw of lines) {
    const line = raw.trimEnd();
    const head = /^Section\s+(\S+)\s*(.*)$/.exec(line);
    const sub = /^(\d+\.\d+(?:\([a-z]\))?)\s+(\S.*)$/.exec(line);
    if (head) {
      cur = { id: head[1], text: head[2] };
      sections.push(cur);
    } else if (sub) {
      cur = { id: sub[1], text: sub[2] };
      sections.push(cur);
    } else if (cur && line.trim()) {
      cur.text += (cur.text ? '\n' : '') + line.trim();
    } else if (!line.trim()) {
      // a blank line ends a sub-section but not a section header block
      if (cur && /^\d+\.\d+/.test(cur.id)) cur = null;
    }
  }
  return {
    id,
    title: lines[0]?.trim() ?? id,
    payer: field('Payer'),
    effective: field('Effective date'),
    status: 'other',
    considered: false,
    sections,
  };
}

const words = (s: string) => new Set(s.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean));

/** Near-identical title: at least 60% word overlap (Jaccard). */
export function titlesSimilar(a: string, b: string): boolean {
  const x = words(a);
  const y = words(b);
  if (x.size === 0 || y.size === 0) return false;
  let shared = 0;
  for (const w of x) if (y.has(w)) shared++;
  return shared / (x.size + y.size - shared) >= 0.6;
}

/** chosen = the run's policy; lookalike = a different policy with the same or near-identical title. */
export function classifyPolicies(policies: ParsedPolicy[], chosenId: string): ParsedPolicy[] {
  const chosen = policies.find((p) => p.id === chosenId);
  return policies.map((p) => ({
    ...p,
    status: p.id === chosenId ? 'chosen' : chosen && titlesSimilar(p.title, chosen.title) ? 'lookalike' : 'other',
  }));
}

export function consideredPolicyIds(eventsText: string | null): string[] {
  if (!eventsText) return [];
  const ids = new Set<string>();
  for (const line of eventsText.split('\n')) {
    if (!line.trim()) continue;
    let e: { kind?: string; name?: string; data?: { result?: unknown } };
    try {
      e = JSON.parse(line);
    } catch {
      continue;
    }
    if (e.kind !== 'tool_result' || e.name !== 'retrieve_payer_policy') continue;
    for (const m of String(e.data?.result ?? '').matchAll(/\bMP-[A-Z]+-\d+\b/g)) ids.add(m[0]);
  }
  return [...ids].sort();
}

/** true when the file name occurs in a tool call or tool result; null when the run had no events. */
export function openedFiles(eventsText: string | null, paths: string[]): Record<string, boolean | null> {
  if (eventsText === null) return Object.fromEntries(paths.map((p) => [p, null]));
  let hay = '';
  for (const line of eventsText.split('\n')) {
    if (!line.trim()) continue;
    try {
      const e = JSON.parse(line) as { kind?: string; data?: unknown };
      if (e.kind === 'tool_call' || e.kind === 'tool_result') hay += JSON.stringify(e.data) + '\n';
    } catch {
      /* skip a damaged line */
    }
  }
  return Object.fromEntries(paths.map((p) => [p, mentionsFile(hay, p) || hay.includes(p)]));
}

// ---------- the letter ----------

/** Plain text of a markdown fragment: no emphasis, code ticks, heading or list markers. */
function plain(s: string): string {
  return s.replace(/\*\*|__/g, '').replace(/`/g, '').replace(/\s+/g, ' ').trim();
}

export interface RawBlock {
  kind: DataRoomBlock['kind'];
  text: string;
}

export function splitBlocks(markdown: string): RawBlock[] {
  const out: RawBlock[] = [];
  let para: string[] = [];
  const flush = () => {
    if (para.length) out.push({ kind: 'paragraph', text: plain(para.join(' ')) });
    para = [];
  };
  for (const raw of markdown.split('\n')) {
    const line = raw.trimEnd();
    if (!line.trim() || /^\s*([-*_])\1{2,}\s*$/.test(line)) {
      flush();
      continue;
    }
    const heading = /^\s{0,3}#{1,6}\s+(.*)$/.exec(line);
    const item = /^\s*(?:[-*+]|\d+[.)])\s+(.*)$/.exec(line);
    if (heading) {
      flush();
      out.push({ kind: 'heading', text: plain(heading[1]) });
    } else if (item) {
      flush();
      out.push({ kind: 'list_item', text: plain(item[1]) });
    } else para.push(line.trim());
  }
  flush();
  return out.filter((b) => b.text);
}

/** File names named in "(source: a; b)" / "(sources: a, b)" parentheses. */
export function parseCitations(text: string): string[] {
  const parts: string[] = [];
  for (const m of text.matchAll(/\(\s*sources?\s*:\s*([^)]*)\)/gi)) parts.push(...m[1].split(/[;,]/).map((p) => p.trim()).filter(Boolean));
  return parts;
}

/** Case documents the block cites or names by path or file name. */
export function citedDocs(text: string, paths: string[]): string[] {
  return paths.filter((p) => mentionsFile(text, p));
}

const CITATION_RE = /\(\s*sources?\s*:[^)]*\)/gi;

export interface TokenSpec {
  token: string;
  /** What is searched for in the documents (money without "$"). */
  needle: string;
}

/** Exact values worth matching: dates, money, long ids, CPT/ICD-10 style codes, denial codes. */
export function extractTokens(text: string, paths: string[] = []): TokenSpec[] {
  let t = text.replace(CITATION_RE, ' ');
  for (const p of paths) t = t.split(p).join(' ');
  const found = new Map<string, TokenSpec>();
  const add = (token: string, needle = token) => {
    if (!found.has(token)) found.set(token, { token, needle });
  };
  for (const m of t.matchAll(/(?<![A-Za-z0-9])\d{4}-\d{2}-\d{2}(?![A-Za-z0-9])/g)) add(m[0]);
  for (const m of t.matchAll(/\$\s?\d[\d,]*(?:\.\d{2})?/g)) add(m[0].replace(/\s/g, ''), m[0].replace(/[$\s]/g, ''));
  for (const m of t.matchAll(/(?<![A-Za-z0-9$.,])\d{1,3}(?:,\d{3})*\.\d{2}(?![A-Za-z0-9])/g)) add(m[0]);
  for (const m of t.matchAll(/(?<![A-Za-z0-9])[A-Z]{2,}-?\d{5,}(?![A-Za-z0-9])/g)) add(m[0]);
  for (const m of t.matchAll(/(?<![A-Za-z0-9.,$-])\d{6,}(?![A-Za-z0-9])/g)) add(m[0]);
  for (const m of t.matchAll(/(?<![A-Za-z0-9.,$-])\d{5}(?![A-Za-z0-9.-])/g)) add(m[0]);
  for (const m of t.matchAll(/(?<![A-Za-z0-9])[A-TV-Z]\d{2}(?:\.\d{1,4})?(?![A-Za-z0-9])/g)) add(m[0]);
  for (const m of t.matchAll(/(?<![A-Za-z0-9])(?:CO|PR|OA|PI|CR)-\d{1,3}(?![A-Za-z0-9])/g)) add(m[0]);
  for (const m of t.matchAll(/(?<![A-Za-z0-9])N\d{3}(?![A-Za-z0-9])/g)) add(m[0]);
  return [...found.values()];
}

/** First line (1-based) of a document that contains the value exactly, or null. */
export function findToken(lines: string[], needle: string): number | null {
  const re = new RegExp(`(?<![A-Za-z0-9])${esc(needle)}(?![A-Za-z0-9])`);
  const i = lines.findIndex((l) => re.test(l));
  return i < 0 ? null : i + 1;
}

const SECTION_RE = [
  /§\s*(\d+(?:\.\d+)?(?:\([a-z]\))?)/g,
  /\bSections?\s+(\d+(?:\.\d+)?(?:\([a-z]\))?)/gi,
  /(?<![\d.$,/-])(\d+\.\d+(?:\([a-z]\))?)(?![\d])/g,
];

/** Section ids named in the text that exist in the chosen policy. */
export function referencedSections(text: string, known: string[]): string[] {
  const set = new Set(known);
  const hit = new Set<string>();
  for (const re of SECTION_RE) for (const m of text.matchAll(re)) if (set.has(m[1])) hit.add(m[1]);
  // "sections 2.1(a), 2.1(b), 2.1(c)" and "2.1(a) and (b)" stay exact: only full ids count.
  return known.filter((k) => hit.has(k));
}

const STOP = new Set('that this with from have been were does not the and for are was has had its into than then them they their there which also only any per all'.split(' '));
const sigWords = (s: string) => [...new Set(s.toLowerCase().split(/[^a-z0-9]+/).filter((w) => w.length >= 4 && !STOP.has(w)))];

/** Squashed (no emphasis, ticks or whitespace) lower-case form, for quote overlap. */
const squash = (s: string) => s.replace(/[*`_\s]+/g, '').toLowerCase();

/** The quote and the block share a run of at least min(40, quote length) characters. */
export function quoteOverlaps(blockText: string, quote: string): boolean {
  const b = squash(blockText);
  const q = squash(quote);
  if (!b || !q) return false;
  if (b.includes(q) || q.includes(b)) return true;
  const w = Math.min(40, q.length);
  for (let i = 0; i + w <= q.length; i++) if (b.includes(q.slice(i, i + w))) return true;
  return false;
}

/** Best excerpt of a file for a block: the matched line, else the line with the most shared words. */
export function bestExcerpt(lines: string[], blockText: string, matchedLine: number | null): { line: number | null; excerpt: string; excerptFound: boolean } {
  if (matchedLine) return { line: matchedLine, excerpt: lines[matchedLine - 1].trim(), excerptFound: true };
  const want = sigWords(blockText);
  let best = 0;
  let bestLine = -1;
  lines.forEach((l, i) => {
    const have = new Set(sigWords(l));
    const n = want.filter((w) => have.has(w)).length;
    if (n > best) {
      best = n;
      bestLine = i;
    }
  });
  if (bestLine < 0 || best < 2) return { line: null, excerpt: '', excerptFound: false };
  return { line: bestLine + 1, excerpt: lines[bestLine].trim(), excerptFound: true };
}

const clip = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s);

// ---------- assembly ----------

export function buildDataRoomView(input: DataRoomInput): DataRoomView {
  const { run } = input;
  const paths = orderDocs(input.caseFiles.map((f) => f.path));
  const byPath = new Map(input.caseFiles.map((f) => [f.path, f]));
  const opened = openedFiles(input.eventsText, paths);

  const parsed = classifyPolicies(input.policyFiles.map((f) => parsePolicy(f.file, f.text)), run.policyId);
  const considered = consideredPolicyIds(input.eventsText);
  const chosen = parsed.find((p) => p.status === 'chosen');
  const sectionIds = (chosen?.sections ?? []).map((s) => s.id);
  const criteriaById = new Map(input.criteria.map((c) => [c.id, c]));

  const caseDocs: DataRoomDoc[] = paths.map((p, i) => {
    const text = byPath.get(p)!.text;
    return {
      number: i + 1,
      path: p,
      descriptor: describeDoc(p, text),
      lines: text.replace(/\n$/, '').split('\n'),
      opened: opened[p] ?? null,
      citedBy: [],
      matchedBy: [],
    };
  });
  const docByPath = new Map(caseDocs.map((d) => [d.path, d]));

  const material = run.flags.filter((f) => f.upheld && f.severity === 'material');
  const policyNames = chosen ? [chosen.id, chosen.title.toLowerCase()] : [];

  const blocks: DataRoomBlock[] = [];
  const rows: DataRoomRow[] = [];
  splitBlocks(run.deliverableMarkdown).forEach((rb, i) => {
    const id = `B${i + 1}`;
    const cited = citedDocs(rb.text, paths);
    const tokens = extractTokens(rb.text, paths);
    const matched: BlockMatch[] = [];
    for (const d of caseDocs) {
      if (cited.includes(d.path)) continue;
      for (const t of tokens) {
        const line = findToken(d.lines, t.needle);
        if (line) matched.push({ token: t.token, file: d.path, line });
      }
    }
    const secIds = referencedSections(rb.text, sectionIds);
    const sections: BlockSectionLink[] = secIds.map((sid) => {
      const c = criteriaById.get(sid);
      const status = c && ['met', 'unmet', 'unknown'].includes(c.status) ? (c.status as CriterionStatus) : null;
      return { id: sid, status, evidence: c?.evidence ?? null };
    });
    const lower = rb.text.toLowerCase();
    const namesPolicy = policyNames.some((n) => lower.includes(n.toLowerCase()));
    const flags: BlockFlag[] = material
      .filter((f) => quoteOverlaps(rb.text, f.quote))
      .map((f) => ({
        id: f.id,
        severity: 'material' as const,
        reasons: Object.values(f.votes).filter((v) => v.upheld).map((v) => v.reason),
      }));

    for (const p of cited) docByPath.get(p)!.citedBy.push(id);
    for (const p of new Set(matched.map((m) => m.file))) docByPath.get(p)!.matchedBy.push(id);

    blocks.push({ id, kind: rb.kind, text: rb.text, links: { cited, matched, sections, policy: namesPolicy, flags } });

    const evidence: RowEvidence[] = [];
    for (const p of cited) {
      const d = docByPath.get(p)!;
      evidence.push({ file: p, via: 'cited', tokens: [], ...bestExcerpt(d.lines, rb.text, null) });
    }
    for (const p of [...new Set(matched.map((m) => m.file))]) {
      const ms = matched.filter((m) => m.file === p);
      evidence.push({ file: p, via: 'matched', tokens: ms.map((m) => m.token), ...bestExcerpt(docByPath.get(p)!.lines, rb.text, ms[0].line) });
    }
    const policy: RowPolicyZone = secIds.length
      ? { kind: 'sections', sectionIds: secIds, texts: secIds.map((sid) => chosen!.sections.find((s) => s.id === sid)!.text) }
      : namesPolicy
        ? { kind: 'policy', sectionIds: [], texts: [] }
        : { kind: 'none', sectionIds: [], texts: [] };
    rows.push({ blockId: id, title: clip(rb.text, 64), policy, evidence });
  });

  const linked = blocks.filter((b) => b.links.cited.length || b.links.matched.length || b.links.sections.length || b.links.policy);
  const policies: PolicyListing[] = parsed.map(({ sections: _s, ...p }) => ({ ...p, considered: considered.includes(p.id) }));
  return {
    available: true,
    runId: run.runId,
    caseId: run.caseId,
    variant: run.variant,
    runtime: run.runtime,
    chosenPolicyId: run.policyId,
    consideredPolicyIds: considered,
    caseDocs,
    policies,
    chosenSections: chosen?.sections ?? [],
    blocks,
    rows,
    summary: {
      blocks: blocks.length,
      linkedBlocks: linked.length,
      citedFiles: new Set(blocks.flatMap((b) => b.links.cited)).size,
      matchedFiles: new Set(blocks.flatMap((b) => b.links.matched.map((m) => m.file))).size,
      flags: new Set(blocks.flatMap((b) => b.links.flags.map((f) => f.id))).size,
    },
    withheld: [],
  };
}

export function unavailableDataRoom(run: Pick<RunView, 'runId' | 'caseId' | 'variant' | 'runtime' | 'policyId'>): DataRoomView {
  return {
    available: false,
    runId: run.runId,
    caseId: run.caseId,
    variant: run.variant,
    runtime: run.runtime,
    chosenPolicyId: run.policyId,
    consideredPolicyIds: [],
    caseDocs: [],
    policies: [],
    chosenSections: [],
    blocks: [],
    rows: [],
    summary: { blocks: 0, linkedBlocks: 0, citedFiles: 0, matchedFiles: 0, flags: 0 },
    withheld: [],
  };
}
