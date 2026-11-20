import { describe, expect, it, beforeAll, afterAll } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { hermes } from '../src/data/adapters/hermes.ts';
import { standin } from '../src/data/adapters/standin.ts';
import { baseline } from '../src/data/adapters/baseline.ts';

const fx = (n) => path.join(path.dirname(fileURLToPath(import.meta.url)), 'fixtures', n);
const HERMES = fx('hermes_run_C-0030');

describe('hermes adapter', () => {
  const run = hermes.read(HERMES);

  it('claims only Hermes folders', () => {
    expect(hermes.canRead(HERMES)).toBe(true);
    expect(standin.canRead(HERMES)).toBe(false);
    expect(hermes.canRead(fx('agent_run_C-0030'))).toBe(false);
    expect(standin.canRead(fx('agent_run_C-0030'))).toBe(true);
    expect(hermes.canRead(fx('baseline_run_C-0030'))).toBe(false);
  });

  it('maps the decision and runtime fields', () => {
    expect(run).toMatchObject({
      source: 'hermes', runtime: 'hermes', variant: 'agent', caseId: 'C-0030', runId: 'hermes-p1-r1',
      decision: 'DO_NOT_APPEAL', denialCode: 'CO-29', policyId: 'MP-TF-001', actionDeadline: '2026-11-01',
    });
    expect(run.deliverableMarkdown).toContain('Decision Memo');
  });

  it('keeps the raw terminal command and the skill name per step', () => {
    const skill = run.steps.find((s) => s.name === 'parse_denial_eob');
    expect(skill.skillName).toBe('parse_denial_eob');
    expect(skill.hermesTool).toBe('terminal');
    expect(skill.rawCommand).toBe("/usr/local/share/appeals/bin/run_skill C-0030 parse_denial_eob '{}'");
    expect(skill.detail.result).toContain('"billed": 236.93');
    const write = run.steps.find((s) => s.name === 'write_file');
    expect(write.skillName).toBeNull();
    expect(write.hermesTool).toBe('write_file');
    expect(write.rawCommand).toBeNull();
    expect(run.steps.find((s) => s.kind === 'revision')).toBeTruthy();
  });

  it('does not cache skill pages', () => {
    const view = run.steps.find((s) => s.hermesTool === 'skill_view');
    expect(view.detail.result).toMatch(/^Skill page, \d+ characters \(not cached\)$/);
  });

  it('maps audit events with their tag', () => {
    expect(run.audit.length).toBe(239);
    expect(run.audit.every((a) => ['run', 'post_run', 'background'].includes(a.tag))).toBe(true);
    expect(run.audit[0]).toMatchObject({ eventClass: 'NET:OPEN', tag: 'run', background: false });
    expect(Object.keys(run.audit[0]).sort()).toEqual(['background', 'eventClass', 'reason', 'result', 'tag', 'target', 'time']);
  });

  it('derives the Hermes extras from the events when summary.json is absent', () => {
    expect(run.hermes).toMatchObject({ hermesVersion: '0.21.3', skillCalls: 7, skillErrors: 0, firstCallPromptTokens: 13307, backgroundReview: null });
    expect(run.hermes.toolsByName).toMatchObject({ write_file: 2, patch: 1, skill_view: 2, terminal: 1 });
    expect(run.metrics).toMatchObject({ turns: 10, toolCalls: 13, revisions: 1, toolErrors: 0 });
    expect(run.metrics.tokens.total).toBe(219365);
  });

  it('maps verdicts and flags with their votes', () => {
    const f = run.flags.find((x) => x.upheld && x.severity === 'material');
    expect(f.quote).toContain('$236.93');
    expect(Object.keys(f.votes).sort()).toEqual(['claude', 'gemini', 'gpt']);
    expect(run.flags.some((x) => !x.upheld)).toBe(true);
    expect(JSON.stringify(run)).not.toContain('"reference"');
  });
});

describe('hermes adapter with summary.json', () => {
  let tmp;
  beforeAll(() => {
    tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'gui-hermes-'));
    fs.cpSync(HERMES, tmp, { recursive: true });
    // Synthetic test data in the shape EVENTS_SPEC.md describes.
    fs.writeFileSync(path.join(tmp, 'summary.json'), JSON.stringify({
      runtime: 'hermes', skill_calls_total: 9, skill_errors: 2, hermes_tools_by_name: { patch: 1 },
      background_review: { calls: 9, prompt_tokens: 1000, completion_tokens: 50, complete: true },
    }));
  });
  afterAll(() => fs.rmSync(tmp, { recursive: true, force: true }));

  it('uses summary.json for skill errors and the background review', () => {
    const run = hermes.read(tmp);
    expect(run.hermes).toMatchObject({
      skillCalls: 9, skillErrors: 2, toolsByName: { patch: 1 },
      backgroundReview: { calls: 9, promptTokens: 1000, completionTokens: 50, complete: true },
    });
  });
});

describe('baseline adapter', () => {
  const dir = fx('baseline_run_C-0030');
  const run = baseline.read(dir);

  it('is exclusive with the other adapters', () => {
    expect(baseline.canRead(dir)).toBe(true);
    expect(standin.canRead(dir)).toBe(false);
    expect(hermes.canRead(dir)).toBe(false);
    expect(baseline.canRead(fx('agent_run_C-0030'))).toBe(false);
  });

  it('maps the no-tools run', () => {
    expect(run).toMatchObject({ variant: 'baseline', runtime: 'standin', caseId: 'C-0030', runId: 'baseline-p3-r1', steps: [], audit: [], hermes: null });
    expect(run.metrics).toMatchObject({ turns: 2, toolCalls: 0, toolErrors: 0 });
    expect(run.deliverableMarkdown.length).toBeGreaterThan(100);
    expect(run.flags.filter((f) => f.upheld && f.severity === 'material').length).toBe(2);
    expect(run.verdicts.length).toBeGreaterThan(10);
  });
});
