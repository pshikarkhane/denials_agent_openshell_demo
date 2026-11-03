// Answer-key guard. The GUI must never read, copy or ship the scoring answer
// keys. These names are refused at every read and scanned for in every output.
import fs from 'node:fs';
import path from 'node:path';

export const FORBIDDEN_FILES = ['truth.json', 'rubric.json'];
export const FORBIDDEN_DIRS = ['gold', 'attacks'];

/** Strings that must not appear in any published file name or text. */
export const FORBIDDEN_TOKENS = [...FORBIDDEN_FILES, ...FORBIDDEN_DIRS.map((d) => `${d}/`)];

export class AnswerKeyError extends Error {
  constructor(p: string) {
    super(`REFUSED: answer-key path in input: ${p}`);
    this.name = 'AnswerKeyError';
  }
}

/** Throws if any segment of the path is a forbidden file or folder name. */
export function assertAllowedPath(p: string): void {
  for (const seg of p.split(/[\\/]+/).filter(Boolean)) {
    const s = seg.toLowerCase();
    if (FORBIDDEN_FILES.includes(s) || FORBIDDEN_DIRS.includes(s)) throw new AnswerKeyError(p);
  }
}

/** Walks a folder and throws on the first forbidden entry; never opens a file. */
export function assertTreeClean(root: string): void {
  assertAllowedPath(path.basename(root));
  const walk = (dir: string): void => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      assertAllowedPath(entry.name);
      if (entry.isDirectory()) walk(path.join(dir, entry.name));
    }
  };
  walk(root);
}

/** The only way the adapters read a file. */
export function readGuarded(file: string): string {
  assertAllowedPath(path.basename(file));
  return fs.readFileSync(file, 'utf8');
}

/** Returns the forbidden tokens found in a text (case-insensitive). */
export function findForbiddenTokens(text: string): string[] {
  const lower = text.toLowerCase();
  return FORBIDDEN_TOKENS.filter((t) => lower.includes(t));
}
