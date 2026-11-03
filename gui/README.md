# Denial Appeals Agent: demo GUI (slice 2, cached mode)

Vite + React + TypeScript, plain CSS. No backend calls, no API keys, no model calls, no network at runtime:
the app only fetches `/data/index.json`, `/data/metrics.json` and run files from its own origin.
Node 22.18+ (the cache scripts run TypeScript adapters directly; the app and tests build on any recent Node).

```
cd gui
npm install
npm run cache      # docs/samples/{agent,hermes,baseline}_run_* -> public/data/ run files + index.json,
                   # then docs/*_REPORT.md tables -> public/data/metrics.json (all committed; rerun after changes)
npm run dev        # http://localhost:5173
npm run build && npm run preview     # preview on http://localhost:4173
npm test           # offline
```

## Add runs
Put a run folder next to the samples and run `npm run cache`, or point at other folders:
`node scripts/build_cache.mjs --runs "path/to/agent_run_*,other/dir" [--out dir]`. The adapter is picked by the folder's files:
- `hermes_run_*`: `decision.json`, `events.jsonl`, `trace.json`, `audit.jsonl`; optional `deliverable.md`, `judge_verdicts.json`, `summary.json` (see "Hermes runs" in `docs/EVENTS_SPEC.md`). `hermes_raw/` is never opened.
- `agent_run_*` (stand-in): the same without `audit.jsonl`.
- `baseline_run_*` (no tools): `decision.json`, `summary.json`, `deliverable.md`, `judge_verdicts.json`; no trace.

The Scorecard numbers are the exact strings of the tables in `docs/RUN_REPORT.md` and `docs/HERMES_RUN_REPORT.md` (`scripts/build_metrics.mjs`); update the reports, then `npm run cache`.
The builder **refuses** (non-zero exit, nothing written) if its input contains `truth.json`, `rubric.json`, or anything under a folder named `gold` or `attacks`,
and refuses to write output whose text names them. `test/answer_key_guard.test.mjs` re-checks `public/data` after a build.

## Data room tab
`/case/:caseId?tab=dataroom` shows the case documents, how each sentence of the letter maps to them (citation and exact-value matching) and to the payer policy, and the letter itself.
`scripts/build_dataroom.mjs` (run by `npm run cache`, or alone: `node scripts/build_dataroom.mjs [--runs ...] [--data <dir>] [--out <dir>]`) writes `public/data/dataroom/<runId>__<caseId>.json` per run.
It reads only `data/cases/<case>/task.md`, `data/cases/<case>/docs/**` and `data/policy_library/*.txt`, never the case folder root. A text that names a scoring file is replaced by a one-line note and listed under `withheld`; the guard is not loosened.
A case switcher (all cached cases, keeps the tab) sits under the page headline.

## Containment page
`/containment?scenario=A1&mode=natural` shows what the agent did and what OpenShell recorded for the recorded attack runs in `docs/samples/hermes_attack_*/{natural,scripted}`.
`scripts/build_containment.mjs` (run by `npm run cache`) writes `public/data/containment.json` (parsed from `docs/CONTAINMENT_REPORT.md`, `docs/POLICY_HARDENING.md`, `docs/HERMES_RUN_REPORT.md`; nothing typed) and `public/data/containment/<attack>__<mode>.json` (adapter `src/data/adapters/attack.ts`). It refuses the same answer-key names as the other builders, and any step text that names one is replaced by a note. If a table cannot be parsed the page says "See the report" and `npm test` fails.

## Layout
- `src/styles/tokens.css`: design tokens (colors, radii, type, spacing, focus ring). `global.css`: base and component styles.
- `src/data/types.ts`: `RunView` and friends; `src/data/metrics.ts`: the shape of `metrics.json`. `src/data/adapters/`: `standin.ts`, `hermes.ts`, `baseline.ts` (see its README).
- `scripts/build_cache.mjs`: run folders to normalized JSON. `scripts/build_metrics.mjs`: report tables to `metrics.json`. `src/pages/`, `src/components/`, `src/lib/quotes.ts` (finds flag quotes in the text): UI. `scripts/build_containment.mjs` + `src/data/adapters/attack.ts` + `src/components/Containment/` (panels, replay, pure `logic.ts`); `scripts/build_dataroom.mjs` + `src/data/dataroom.ts` (pure mapping logic) + `src/components/DataRoom/` (view, `selection.ts` chain logic, details panel).
- Tests in `test/` (vitest, node environment; Home is rendered to static markup, no browser needed).
