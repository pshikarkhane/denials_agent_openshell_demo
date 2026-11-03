import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { buildDataRooms, readCaseFiles } from '../scripts/build_dataroom.mjs';
import {
  bestExcerpt,
  citedDocs,
  classifyPolicies,
  extractTokens,
  findToken,
  openedFiles,
  orderDocs,
  parseCitations,
  parsePolicy,
  quoteOverlaps,
  referencedSections,
  splitBlocks,
} from '../src/data/dataroom.ts';
import { findForbiddenTokens } from '../src/data/guard.ts';
import { caseListing, dataDir, fx, sample, viewFor } from './dataroom_helpers.mjs';

const policies = () =>
  fs.readdirSync(path.join(dataDir, 'policy_library')).filter((f) => f.endsWith('.txt')).map((f) => parsePolicy(f, fs.readFileSync(path.join(dataDir, 'policy_library', f), 'utf8')));

describe('block splitting', () => {
  it('splits headings, paragraphs and list items in order and strips markdown', () => {
    const md = '# Title\n\nFirst **bold** line\ncontinues here.\n\n---\n\n- item one\n2. item two\n\n## Next\nLast `code`.';
    expect(splitBlocks(md)).toEqual([
      { kind: 'heading', text: 'Title' },
      { kind: 'paragraph', text: 'First bold line continues here.' },
      { kind: 'list_item', text: 'item one' },
      { kind: 'list_item', text: 'item two' },
      { kind: 'heading', text: 'Next' },
      { kind: 'paragraph', text: 'Last code.' },
    ]);
  });
});

describe('citations', () => {
  it('parses "(source: a; b)" and "(sources: a, b)"', () => {
    expect(parseCitations('x (source: a.txt; notes/b.txt) y')).toEqual(['a.txt', 'notes/b.txt']);
    expect(parseCitations('x (sources: a.txt, b.txt)')).toEqual(['a.txt', 'b.txt']);
    expect(parseCitations('no citation here')).toEqual([]);
  });

  it('finds case documents named by path or by file name only', () => {
    const paths = ['denial_letter.txt', 'notes/2026-06-04_ortho.txt', 'supporting/pt_log.txt'];
    expect(citedDocs('see (source: 2026-06-04_ortho.txt) and denial_letter.txt', paths)).toEqual(['denial_letter.txt', 'notes/2026-06-04_ortho.txt']);
    expect(citedDocs('the denial letter says so', paths)).toEqual([]);
  });
});

describe('policy sections', () => {
  const known = ['2.1(a)', '2.1(b)', '7.1'];
  it('links §, "Section" and bare references that exist in the policy', () => {
    expect(referencedSections('§2.1(a) and Section 2.1(b)', known)).toEqual(['2.1(a)', '2.1(b)']);
    expect(referencedSections('allowed by section 7.1 of the policy', known)).toEqual(['7.1']);
  });
  it('never invents a section: unknown ids and amounts are not links', () => {
    expect(referencedSections('section 9.9 and $236.93 and 2052.88', known)).toEqual([]);
  });
  it('parses the real policy into its sections', () => {
    const p = policies().find((x) => x.id === 'MP-IMG-007');
    expect(p.sections.map((s) => s.id)).toEqual(expect.arrayContaining(['2.1(a)', '2.1(b)', '2.1(c)', '7.1']));
    expect(p.sections.find((s) => s.id === '2.1(a)').text).toMatch(/6 weeks/);
  });
});

describe('exact token matching', () => {
  it('extracts dates, money, long ids, CPT, ICD-10 and denial codes, and ignores citations', () => {
    const t = extractTokens('DOS 2026-06-18, CPT 72148, ICD-10 M51.26, denial CO-50, claim 6268311, billed $2,052.88 (source: notes/2026-06-04_ortho.txt)', ['notes/2026-06-04_ortho.txt']).map((x) => x.token);
    expect(t).toEqual(expect.arrayContaining(['2026-06-18', '72148', 'M51.26', 'CO-50', '6268311', '$2,052.88']));
    expect(t).not.toContain('2026-06-04');
  });

  it('reports the real line number of an exact value', () => {
    const lines = fs.readFileSync(path.join(dataDir, 'cases/C-0005/docs/denial_letter.txt'), 'utf8').split('\n');
    const line = findToken(lines, '2026-07-17');
    expect(line).toBe(lines.findIndex((l) => l.includes('2026-07-17')) + 1);
    expect(findToken(lines, '2026-07-1')).toBeNull();
    expect(findToken(lines, '1999-01-01')).toBeNull();
  });
});

describe('policy derivation', () => {
  it('marks the chosen policy and its look-alikes, never a different-title policy', () => {
    const c30 = classifyPolicies(policies(), 'MP-TF-001');
    const status = Object.fromEntries(c30.map((p) => [p.id, p.status]));
    expect(status['MP-TF-001']).toBe('chosen');
    expect(status['MP-TF-010']).toBe('lookalike');
    expect(status['MP-CLM-004']).toBe('other');
    const c05 = Object.fromEntries(classifyPolicies(policies(), 'MP-IMG-007').map((p) => [p.id, p.status]));
    expect(c05['MP-IMG-012']).toBe('lookalike');
    expect(c05['MP-PA-003']).toBe('other');
  });
});

describe('excerpts and quotes', () => {
  const lines = ['Patient: Brenda Wilson', 'Imaging history: No prior lumbar imaging on file.', 'Provider: Dr. Henry'];
  it('picks the line with the most shared words', () => {
    expect(bestExcerpt(lines, 'No prior lumbar imaging was found on file', null)).toMatchObject({ line: 2, excerptFound: true });
  });
  it('uses the exact matched line when there is one', () => {
    expect(bestExcerpt(lines, 'anything', 3)).toMatchObject({ line: 3, excerpt: 'Provider: Dr. Henry' });
  });
  it('reports excerptFound false when nothing overlaps', () => {
    expect(bestExcerpt(lines, 'Completely unrelated sentence about billing codes', null)).toEqual({ line: null, excerpt: '', excerptFound: false });
  });
  it('overlap ignores emphasis marks and spacing', () => {
    expect(quoteOverlaps('The denied amount remains the patient responsibility.', '**The denied amount** remains the patient responsibility')).toBe(true);
    expect(quoteOverlaps('Something else entirely', 'The denied amount remains the patient responsibility')).toBe(false);
  });
});

describe('opened by a tool', () => {
  const ev = [
    JSON.stringify({ kind: 'tool_call', data: { arguments: { paths: ['notes/a.txt'] } } }),
    JSON.stringify({ kind: 'model_response', data: { content: 'mentions b.txt' } }),
  ].join('\n');
  it('is true only for a file named in a tool call or result', () => {
    expect(openedFiles(ev, ['notes/a.txt', 'b.txt'])).toEqual({ 'notes/a.txt': true, 'b.txt': false });
  });
  it('is null when the run had no tools', () => {
    expect(openedFiles(null, ['a.txt'])).toEqual({ 'a.txt': null });
  });
});

describe('DataRoomView for the cached runs', () => {
  const h30 = viewFor(fx('hermes_run_C-0030'));
  const h05 = viewFor(sample('hermes_run_C-0005'));
  const b05 = viewFor(sample('baseline_run_C-0005'));

  it('orders documents: denial letter, EOB, the rest alphabetically, task.md last', () => {
    expect(h05.caseDocs.map((d) => d.path)).toEqual(['denial_letter.txt', 'eob_835.txt', 'claim_history.txt', 'notes/2026-03-23_pcp.txt', 'notes/2026-04-13_pcp_followup.txt', 'notes/2026-06-04_ortho.txt', 'supporting/pt_log.txt', 'task.md']);
    expect(h05.caseDocs.map((d) => d.number)).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
    expect(orderDocs(['task.md', 'b.txt', 'eob_835.txt', 'a.txt', 'denial_letter.txt'])).toEqual(['denial_letter.txt', 'eob_835.txt', 'a.txt', 'b.txt', 'task.md']);
  });

  it('describes visit notes from their own header', () => {
    expect(h05.caseDocs.find((d) => d.path === 'notes/2026-06-04_ortho.txt').descriptor).toBe('Orthopedic Consultation Note, 2026-06-04');
    expect(h05.caseDocs[0].descriptor).toBe('Denial notice');
    expect(h05.caseDocs.at(-1).descriptor).toBe('Instruction');
  });

  it('has one row per block, in the same order', () => {
    for (const v of [h30, h05, b05]) {
      expect(v.rows.length).toBe(v.blocks.length);
      expect(v.rows.map((r) => r.blockId)).toEqual(v.blocks.map((b) => b.id));
    }
  });

  it('keeps blocks with no links unlinked', () => {
    const heading = h30.blocks.find((b) => b.text === 'Decision Memo');
    expect(heading.links).toEqual({ cited: [], matched: [], sections: [], policy: false, flags: [] });
    expect(h30.rows[h30.blocks.indexOf(heading)]).toMatchObject({ policy: { kind: 'none' }, evidence: [] });
    expect(h30.summary.linkedBlocks).toBeLessThan(h30.summary.blocks);
  });

  it('links a cited section to its policy text and the decision status', () => {
    const b = h05.blocks.find((x) => x.text.startsWith('Section 2.1(b)'));
    expect(b.links.sections).toEqual([{ id: '2.1(b)', status: 'met', evidence: 'notes/2026-06-04_ortho.txt' }]);
    const row = h05.rows[h05.blocks.indexOf(b)];
    expect(row.policy.kind).toBe('sections');
    expect(row.policy.texts[0]).toMatch(/neurological deficit/);
    expect(row.evidence[0]).toMatchObject({ file: 'notes/2026-06-04_ortho.txt', via: 'cited', excerptFound: true });
  });

  it('records the file and real line of each matched value', () => {
    const ms = h05.blocks.flatMap((b) => b.links.matched);
    expect(ms.length).toBeGreaterThan(0);
    for (const m of ms) {
      const doc = h05.caseDocs.find((d) => d.path === m.file);
      expect(doc.lines[m.line - 1]).toContain(m.token.replace(/^\$/, ''));
    }
  });

  it('attaches an upheld material flag to the block that holds its quote, and only that block', () => {
    const flagged = h30.blocks.filter((b) => b.links.flags.length);
    expect(flagged.map((b) => b.links.flags[0].id)).toEqual(['F1']);
    expect(flagged[0].text).toContain('patient');
    expect(flagged[0].links.flags[0].reasons.length).toBeGreaterThan(0);
    expect(h30.summary.flags).toBe(1);
    expect(h05.summary.flags).toBe(0);
  });

  it('every badge number refers to a listed document and every file name exists in the case folder', () => {
    for (const [v, id] of [[h30, 'C-0030'], [h05, 'C-0005'], [b05, 'C-0005']]) {
      const listing = caseListing(id);
      const numbers = new Set(v.caseDocs.map((d) => d.number));
      for (const d of v.caseDocs) expect(listing).toContain(d.path);
      for (const r of v.rows) for (const e of r.evidence) {
        expect(listing).toContain(e.file);
        expect(numbers.has(v.caseDocs.find((d) => d.path === e.file).number)).toBe(true);
      }
      for (const b of v.blocks) for (const f of [...b.links.cited, ...b.links.matched.map((m) => m.file)]) expect(listing).toContain(f);
    }
  });

  it('citedBy and matchedBy mirror the block links', () => {
    for (const d of h05.caseDocs) {
      expect(d.citedBy).toEqual(h05.blocks.filter((b) => b.links.cited.includes(d.path)).map((b) => b.id));
      expect(d.matchedBy).toEqual(h05.blocks.filter((b) => b.links.matched.some((m) => m.file === d.path)).map((b) => b.id));
    }
  });

  it('derives the chosen policy, look-alikes and considered ids', () => {
    const st = Object.fromEntries(h30.policies.map((p) => [p.id, p.status]));
    expect(st['MP-TF-001']).toBe('chosen');
    expect(st['MP-TF-010']).toBe('lookalike');
    expect(h30.policies).toHaveLength(11);
    expect(h30.consideredPolicyIds).toEqual(expect.arrayContaining(['MP-TF-001', 'MP-TF-010']));
    expect(h30.chosenSections.map((s) => s.id)).toEqual(expect.arrayContaining(['2.1', '2.2']));
  });

  it('marks opened as null for the no-tools baseline and true/false for agent runs', () => {
    expect(b05.caseDocs.every((d) => d.opened === null)).toBe(true);
    expect(h05.caseDocs.find((d) => d.path === 'supporting/pt_log.txt').opened).toBe(true);
    expect(h05.caseDocs.find((d) => d.path === 'task.md').opened).toBe(false);
  });
});

describe('build_dataroom guard', () => {
  let tmp;
  let data;
  let out;
  const runs = () => [path.join(fx('hermes_run_C-0030'))];
  beforeEach(() => {
    tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'gui-dr-'));
    data = path.join(tmp, 'data');
    out = path.join(tmp, 'out');
    fs.cpSync(path.join(dataDir, 'policy_library'), path.join(data, 'policy_library'), { recursive: true });
    fs.mkdirSync(path.join(data, 'cases/C-0030'), { recursive: true });
    fs.cpSync(path.join(dataDir, 'cases/C-0030/docs'), path.join(data, 'cases/C-0030/docs'), { recursive: true });
    fs.copyFileSync(path.join(dataDir, 'cases/C-0030/task.md'), path.join(data, 'cases/C-0030/task.md'));
  });
  afterEach(() => fs.rmSync(tmp, { recursive: true, force: true }));
  const build = () => buildDataRooms({ runs: runs(), out, dataDir: data, cwd: tmp });

  it('writes a data room per run and an index', () => {
    const res = build();
    expect(res.files).toEqual(['hermes-p1-r1__C-0030.json', 'index.json']);
  });

  it('never reads or ships a truth.json, rubric.json, gold/ or attacks/ at the case root', () => {
    const root = path.join(data, 'cases/C-0030');
    fs.writeFileSync(path.join(root, 'truth.json'), '{"secret":"TRUTH-SENTINEL"}');
    fs.writeFileSync(path.join(root, 'rubric.json'), '{"secret":"RUBRIC-SENTINEL"}');
    fs.mkdirSync(path.join(root, 'gold'));
    fs.writeFileSync(path.join(root, 'gold/x.txt'), 'GOLD-SENTINEL');
    fs.mkdirSync(path.join(root, 'attacks'));
    fs.writeFileSync(path.join(root, 'attacks/x.txt'), 'ATTACK-SENTINEL');
    build();
    const text = fs.readdirSync(out).map((f) => fs.readFileSync(path.join(out, f), 'utf8')).join('\n');
    expect(text).not.toMatch(/SENTINEL/);
  });

  for (const name of ['truth.json', 'rubric.json']) {
    it(`refuses ${name} inside docs/ and writes nothing`, () => {
      fs.writeFileSync(path.join(data, 'cases/C-0030/docs', name), '{}');
      expect(build).toThrow(/REFUSED/);
      expect(fs.existsSync(out)).toBe(false);
    });
  }
  for (const dir of ['gold', 'attacks']) {
    it(`refuses a ${dir}/ folder inside docs/`, () => {
      fs.mkdirSync(path.join(data, 'cases/C-0030/docs', dir));
      expect(() => readCaseFiles(data, 'C-0030')).toThrow(/REFUSED/);
    });
  }

  it('replaces a document that names a scoring file with a note and reports it', () => {
    fs.appendFileSync(path.join(data, 'cases/C-0030/docs/claim_history.txt'), '\nsee truth.json for details\n');
    build();
    const view = JSON.parse(fs.readFileSync(path.join(out, 'hermes-p1-r1__C-0030.json'), 'utf8'));
    expect(view.withheld).toEqual(['claim_history.txt']);
    const doc = view.caseDocs.find((d) => d.path === 'claim_history.txt');
    expect(doc.lines).toHaveLength(1);
    expect(doc.lines[0]).toMatch(/^\[Text withheld/);
    expect(findForbiddenTokens(JSON.stringify(view))).toEqual([]);
  });

  it('writes an available:false stub when the case documents are missing', () => {
    fs.rmSync(path.join(data, 'cases/C-0030'), { recursive: true });
    build();
    const view = JSON.parse(fs.readFileSync(path.join(out, 'hermes-p1-r1__C-0030.json'), 'utf8'));
    expect(view).toMatchObject({ available: false, rows: [], caseDocs: [] });
  });
});

describe('answer-key guard on gui/public/data/dataroom', () => {
  it('builds the shipped data rooms and finds no answer-key name in any file name or text', () => {
    const res = buildDataRooms();
    expect(res.count).toBeGreaterThan(0);
    for (const f of res.files) {
      expect(findForbiddenTokens(f), f).toEqual([]);
      expect(findForbiddenTokens(fs.readFileSync(path.join(res.out, f), 'utf8')), f).toEqual([]);
    }
  });
});
