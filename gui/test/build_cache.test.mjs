import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildCache } from '../scripts/build_cache.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const fixture = path.join(here, 'fixtures/agent_run_C-0030');

let tmp;
let runs;
let out;
beforeEach(() => {
  tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'gui-cache-'));
  runs = path.join(tmp, 'runs');
  out = path.join(tmp, 'out');
  fs.cpSync(fixture, path.join(runs, 'agent_run_C-0030'), { recursive: true });
});
afterEach(() => fs.rmSync(tmp, { recursive: true, force: true }));

const build = () => buildCache({ runs: [path.join(runs, 'agent_run_*')], out, cwd: tmp });

describe('build_cache', () => {
  it('writes index.json and one file per run', () => {
    const res = build();
    expect(res.count).toBe(1);
    const index = JSON.parse(fs.readFileSync(path.join(out, 'index.json'), 'utf8'));
    expect(index.mode).toBe('cached');
    expect(index.runs[0]).toMatchObject({ caseId: 'C-0030', decision: 'DO_NOT_APPEAL', source: 'standin' });
    expect(fs.existsSync(path.join(out, index.runs[0].file))).toBe(true);
  });

  for (const name of ['truth.json', 'rubric.json']) {
    it(`refuses ${name} in the input and writes nothing`, () => {
      fs.writeFileSync(path.join(runs, 'agent_run_C-0030', name), '{}');
      expect(build).toThrow(/REFUSED.*answer-key/);
      expect(fs.existsSync(out)).toBe(false);
    });
  }

  for (const dir of ['gold', 'attacks']) {
    it(`refuses a ${dir}/ folder in the input, even nested`, () => {
      const nested = path.join(runs, 'agent_run_C-0030', 'sub', dir);
      fs.mkdirSync(nested, { recursive: true });
      fs.writeFileSync(path.join(nested, 'x.txt'), 'x');
      expect(build).toThrow(/REFUSED.*answer-key/);
      expect(fs.existsSync(out)).toBe(false);
    });
  }

  it('refuses output text that names an answer key', () => {
    fs.appendFileSync(path.join(runs, 'agent_run_C-0030', 'deliverable.md'), '\nsee gold/ for more\n');
    expect(build).toThrow(/REFUSED.*contains answer-key/);
    expect(fs.existsSync(out)).toBe(false);
  });

  it('fails when no run folder matches', () => {
    expect(() => buildCache({ runs: [path.join(tmp, 'none_*')], out, cwd: tmp })).toThrow(/no run folders/);
  });
});
