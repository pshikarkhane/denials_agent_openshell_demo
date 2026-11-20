import { beforeAll, describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildCache } from '../scripts/build_cache.mjs';
import { FORBIDDEN_TOKENS, findForbiddenTokens } from '../src/data/guard.ts';

const dataDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../public/data');

function listFiles(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? listFiles(path.join(dir, e.name)) : [path.join(dir, e.name)],
  );
}

describe('answer-key guard on gui/public/data', () => {
  beforeAll(() => {
    buildCache(); // default inputs: docs/samples/agent_run_*, default output: public/data
  });

  it('has data to scan', () => {
    expect(listFiles(dataDir).length).toBeGreaterThan(1);
  });

  it('no file name or text contains an answer-key name', () => {
    for (const file of listFiles(dataDir)) {
      const rel = path.relative(dataDir, file);
      expect(findForbiddenTokens(rel), `file name ${rel}`).toEqual([]);
      expect(rel.split(path.sep).some((s) => ['gold', 'attacks'].includes(s)), rel).toBe(false);
      expect(findForbiddenTokens(fs.readFileSync(file, 'utf8')), `text of ${rel}`).toEqual([]);
    }
  });

  it('scans for the full forbidden list', () => {
    expect(FORBIDDEN_TOKENS).toEqual(['truth.json', 'rubric.json', 'gold/', 'attacks/']);
  });
});
