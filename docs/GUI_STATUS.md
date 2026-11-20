# GUI_STATUS: demo GUI, slice 2 (branch `gui-v1`, folder `gui/`)

Cached mode only: no network at runtime, no keys, no model calls. Synthetic data. Pilot of 5 dev cases, not a benchmark.
Related: [GUI_SPEC.md](GUI_SPEC.md) (screens, data model, rules), `gui/README.md` (install, cache, run, test), [STATUS.md](STATUS.md) (project-wide).

State: committed as dbcf793 on `gui-v1`. `npm run build` succeeds; `npm test` passes offline (63 tests in 9 files).

## How to view it
```
cd gui
npm run dev          # http://localhost:5173
```
Try `/case/C-0005`, `/case/C-0030` (tabs: `?tab=criteria`, `?tab=trace`) and `/scorecard`. For the production build: `npm run build && npm run preview` (port 4173).

## Step 0: baseline samples
The no-tools baseline runs were not in this worktree. They were in the main checkout's `runs/` folder (`baseline-p3-r1` and `judge-baseline-p3-r1`), read from there and exported to `docs/samples/baseline_run_C-0005` and `baseline_run_C-0030`: deliverable, decision, summary, and judge verdicts with flags. Nothing under `staged/` was copied.

## What was built
- **Adapters** (`gui/src/data/adapters/`): `hermes.ts` (replaces the stub), `baseline.ts` (new), `standin.ts` (kept working). Hermes steps keep the raw terminal command, skill name and Hermes tool; audit events keep their `tag` (`run`, `background`, `post_run`); Hermes extras (skill calls and errors, tools used, first-call prompt tokens, background review when `summary.json` exists).
- **Case page** (`/case/:caseId`): headline "Same case, two ways of working."
  - Left panel: the no-tools baseline (or the stand-in agent, with a visible note, when a case has no baseline). Right panel: Hermes in the OpenShell sandbox, with stand-in runs as alternatives. A run selector per side picks among repeats.
  - Deliverable rendered from markdown. Upheld material flags are marked in red where their quote is found; flags whose quote is not found are labelled in the flags list. `(source: ...)` citations are green pills. The flags list shows severity, quote and each judge's reason. The agent panel has a row of trace chips (errors amber).
  - Tabs: Before & After; Criteria (three judges as PASS/FAIL chips per variant, criterion text only where the verdict file has it, rubric `reference` never carried); Trace (steps with timings, expandable arguments, result and raw terminal command).
- **Scorecard** (`/scorecard`): `gui/scripts/build_metrics.mjs` parses the tables in `docs/RUN_REPORT.md` and `docs/HERMES_RUN_REPORT.md` into `gui/public/data/metrics.json`. Series: no-tools baseline, stand-in agent, Hermes. Rows: criterion pass rate, upheld material flags per run, clean-run rate, tool error rate, tokens, turns, seconds; judge panel per judge; by-category grid with values for categories 1, 2, 6, 8, 12 and "Not run yet" for the other seven. Pilot note shown verbatim. Base Super / R1 checkpoint toggle; R1 shows a pending empty state.
- **Home**: cards 1 and 2 take decision, denial code, policy id, action deadline and run id from the cache (Hermes run preferred, never the baseline); claims such as "drafts the appeal" appear only when the cached decision says so; the model-route line comes from the cached runs. The attack card still links to `/containment` (placeholder).
- **Accessibility and polish**: tabs with arrow-key, Home and End support; focus rings; scrolling text regions focusable; responsive down to phone width; reduced motion respected; no emoji.

## Verified
- `npm run build`, `npm test` (offline).
- Tests cover: all three adapters on fixtures; quote matching and highlight rendering; Case panels, Criteria and Trace render; run-side selection; every number in `metrics.json` and on the rendered Scorecard appears in the source markdown (static labels excepted: category numbers 1-12 and the pilot note's 5 and 0.4); cache-builder refusals for `truth.json`, `rubric.json`, `gold/`, `attacks/`; scan of `gui/public/data` for those names.
- Screenshots in `docs/samples/` (headless Chrome, 1440px): `gui_home_desktop.png`, `gui_case_before_after.png`, `gui_case_criteria.png`, `gui_case_trace.png`, `gui_scorecard.png`. Case and Scorecard were also viewed at 390px (not saved). `gui_home_phone.png` is the older slice 1 screenshot.
- Contrast of every token pair used is at least 4.5:1 (computed).

## Not verified
- Keyboard-only use in a real browser, screen readers, browsers other than Chrome.
- `npm run dev` was not tried in a browser; screenshots came from the built app via `npm run preview`.
- The `summary.json` path on real Hermes data (the samples have none); it was tested on a synthetic file.

## Things to know
1. **No `summary.json` in the Hermes samples.** Skill errors are derived from the events and the background review shows as unknown. Export `summary.json` with the next Hermes samples.
2. **Skill pages are not cached.** The answer-key text guard tripped on Hermes `skill_view` results because the skill page text names the refused files. Those results are replaced by a one-line note; the guard was not loosened.
3. **Node 22.18+ for `npm run cache`.** The adapters are TypeScript run directly by Node. The app and tests do not need it.
4. **Citation pills are on both variants.** The request named the agent deliverable; the baseline also writes `(source: ...)`.
5. **Tool error rates count different things.** Hermes 14.5% covers all tools; the stand-in's 2.2% covers skill calls only. The page also shows Hermes' skill-only 20.7%. The page makes no claim about which side has fewer errors.
6. **Case page coverage.** Only C-0005 and C-0030 have exported run folders, so only those two populate the Case page. The Scorecard covers all five dev cases through the report tables.
7. **Category labels.** Case-to-category mapping comes from the `docs/PILOT_REVIEW.md` headings (C-0005, C-0007, C-0030, C-0039, C-0056 are categories 1, 2, 6, 8, 12); category names come from the `docs/DEMO_SPEC.md` table (number and name only).

## Decisions needed
1. Is replacing skill pages with a note acceptable, or should the guard be handled differently?
2. Keep citation pills on both variants, or restrict them to the agent deliverable?

## Next slices
1. Containment: agent trace and OCSF audit log split screen (`audit` and `tag` are already in the data; hide `background` by default). Needs a Hermes attack run recording.
2. Model swap: R1 checkpoint series once those runs exist (the toggle is a placeholder).
3. Case: more cases once more runs are exported.
4. Live mode (disabled in this slice).
