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

## Layout
- `src/styles/tokens.css`: design tokens (colors, radii, type, spacing, focus ring). `global.css`: base and component styles.
- `src/data/types.ts`: `RunView` and friends; `src/data/metrics.ts`: the shape of `metrics.json`. `src/data/adapters/`: `standin.ts`, `hermes.ts`, `baseline.ts` (see its README).
- `scripts/build_cache.mjs`: run folders to normalized JSON. `scripts/build_metrics.mjs`: report tables to `metrics.json`. `src/pages/`, `src/components/`, `src/lib/quotes.ts` (finds flag quotes in the text): UI.
- Tests in `test/` (vitest, node environment; Home is rendered to static markup, no browser needed).
