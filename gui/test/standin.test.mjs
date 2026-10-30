import { describe, expect, it } from 'vitest';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { standin } from '../src/data/adapters/standin.mjs';
import { hermes } from '../src/data/adapters/hermes.mjs';

const fixture = path.join(path.dirname(fileURLToPath(import.meta.url)), 'fixtures/agent_run_C-0030');

describe('standin adapter', () => {
  const run = standin.read(fixture);

  it('can read the fixture', () => {
    expect(standin.canRead(fixture)).toBe(true);
    expect(standin.canRead(path.join(fixture, 'nope'))).toBe(false);
  });

  it('maps the decision fields', () => {
    expect(run).toMatchObject({
      source: 'standin',
      caseId: 'C-0030',
      runId: 'agent-p3-r1',
      decision: 'DO_NOT_APPEAL',
      denialCode: 'CO-29',
      policyId: 'MP-TF-001',
      actionDeadline: '2026-11-01',
    });
    expect(run.model).toContain('nemotron');
    expect(run.startedAt).toMatch(/^2026-/);
    expect(run.deliverableMarkdown.length).toBeGreaterThan(100);
  });

  it('maps trace steps to camelCase', () => {
    expect(run.steps.length).toBeGreaterThan(5);
    expect(run.steps[0]).toMatchObject({ n: 1, kind: 'run', name: 'start' });
    const tool = run.steps.find((s) => s.kind === 'tool');
    expect(Object.keys(tool).sort()).toEqual(
      ['argsSummary', 'durationMs', 'kind', 'n', 'name', 'resultSummary', 'status'],
    );
  });

  it('maps verdicts and flags', () => {
    const trp = run.verdicts.find((v) => v.criterionId === 'TRP1');
    expect(trp.panel).toBe('FAIL');
    expect(trp.text).toBeTruthy();
    expect(Object.keys(trp.judges).sort()).toEqual(['claude', 'gemini', 'gpt']);
    expect(run.verdicts.find((v) => v.criterionId === 'DEC1').judges.auto.verdict).toBe('PASS');
    expect(run.flags.length).toBeGreaterThan(0);
    expect(run.flags[0]).toHaveProperty('upheld');
    // the rubric-derived "reference" hint is dropped
    expect(JSON.stringify(run)).not.toContain('"reference"');
  });

  it('has an empty audit log and run metrics', () => {
    expect(run.audit).toEqual([]);
    expect(run.metrics.turns).toBe(7);
    expect(run.metrics.tokens.total).toBe(51747);
    expect(run.metrics.wallClockSeconds).toBeCloseTo(20.8, 1);
    expect(run.metrics.toolErrors).toBe(0);
  });
});

describe('hermes adapter', () => {
  it('is a stub', () => {
    expect(hermes.canRead('anything')).toBe(false);
    expect(() => hermes.read('anything')).toThrow('not implemented yet');
  });
});
