// Shared by the Data room tests: builds a DataRoomView from a run folder plus the
// repo's case documents and policy library (read through the same allowlisted readers).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { hermes } from '../src/data/adapters/hermes.ts';
import { standin } from '../src/data/adapters/standin.ts';
import { baseline } from '../src/data/adapters/baseline.ts';
import { buildDataRoomView } from '../src/data/dataroom.ts';
import { readCaseFiles, readPolicyFiles } from '../scripts/build_dataroom.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
export const repoRoot = path.resolve(here, '../..');
export const dataDir = path.join(repoRoot, 'data');
export const fx = (n) => path.join(here, 'fixtures', n);
export const sample = (n) => path.join(repoRoot, 'docs/samples', n);

export function viewFor(runDir) {
  const source = [hermes, standin, baseline].find((s) => s.canRead(runDir));
  const run = source.read(runDir);
  const decisionPath = path.join(runDir, 'decision.json');
  const eventsPath = path.join(runDir, 'events.jsonl');
  return buildDataRoomView({
    run,
    criteria: fs.existsSync(decisionPath) ? JSON.parse(fs.readFileSync(decisionPath, 'utf8')).criteria ?? [] : [],
    eventsText: fs.existsSync(eventsPath) ? fs.readFileSync(eventsPath, 'utf8') : null,
    caseFiles: readCaseFiles(dataDir, run.caseId),
    policyFiles: readPolicyFiles(dataDir),
  });
}

/** Every file under data/cases/<case>/docs plus task.md, as the case folder shows them. */
export function caseListing(caseId) {
  const docs = path.join(dataDir, 'cases', caseId, 'docs');
  const walk = (d, rel) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name), `${rel}${e.name}/`) : [`${rel}${e.name}`]));
  return [...walk(docs, ''), 'task.md'];
}
