# Denial Appeals Agent: demo GUI (first slice, cached mode)

Vite + React + TypeScript, plain CSS. No backend calls, no API keys, no model calls, no network at runtime:
the app only fetches `/data/index.json` and run files from its own origin. Needs Node 20+.

```
cd gui
npm install
npm run cache      # docs/samples/agent_run_*  ->  public/data/  (committed; rerun after adding runs)
npm run dev        # http://localhost:5173
npm run build && npm run preview     # preview on http://localhost:4173
npm test           # offline
```

## Add runs
Put a run folder (`decision.json`, `events.jsonl`, `trace.json`, optionally `deliverable.md` and `judge_verdicts.json`; see `docs/EVENTS_SPEC.md`) next to the samples and run
`npm run cache`, or point at other folders: `node scripts/build_cache.mjs --runs "path/to/agent_run_*,other/dir" [--out dir]`.
The builder **refuses** (non-zero exit, nothing written) if its input contains `truth.json`, `rubric.json`, or anything under a folder named `gold` or `attacks`,
and refuses to write output whose text names them. `test/answer_key_guard.test.mjs` re-checks `public/data` after a build.

## Layout
- `src/styles/tokens.css`: design tokens (colors, radii, type, spacing, focus ring). `global.css`: base and component styles.
- `src/data/types.ts`: `RunView` and friends. `src/data/adapters/`: `standin.mjs` (working), `hermes.mjs` (stub; see its README).
- `scripts/build_cache.mjs`: run folders to normalized JSON. `src/pages/`, `src/components/`: UI.
- Tests in `test/` (vitest, node environment; Home is rendered to static markup, no browser needed).
