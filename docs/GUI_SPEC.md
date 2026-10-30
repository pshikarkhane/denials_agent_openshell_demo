# GUI_SPEC: locally hosted demo GUI (`gui/`)

Cached mode only in this slice: no backend, no model calls, no keys, no network at runtime. Dark theme only; tokens in `gui/src/styles/tokens.css`.
No NVIDIA logos or brand assets (the mark is a plain 28px green square). All case content is synthetic; results are from a small pilot, not a benchmark.

## Routes and screens
| route | screen | status |
|---|---|---|
| `/` | Home: hero, runtime card, six scenario cards, footer note | built |
| `/case/:caseId` | Case | placeholder ("Next step"): shows case id, source, decision, step count |
| `/containment` | Containment | placeholder: table of cached runs (source, decision, steps, audit events) |
| `/scorecard` | Scorecard | placeholder: same table |

Header on every page: mark, "Denial Appeals Agent", "R1 x NVIDIA demo", nav (Home, Case, Containment, Scorecard; `aria-current="page"`), a "Cached | Live demo" control
(Live disabled, tooltip "Not available yet") and a SANDBOXED pill.
Home cards 1 and 2 read decision, denial code and policy id from the cached run for C-0005 / C-0030 and show "No recorded run yet" when the case is not in the cache. Card 6 (Live) is not a link.

## Data model
`gui/src/data/types.ts`. `RunView { runId, caseId, source: 'standin'|'hermes', model, startedAt, decision, denialCode, policyId, actionDeadline, deliverableMarkdown, steps[], verdicts[], flags[], audit[], metrics }`
- `steps`: `{ n, kind, name, argsSummary, resultSummary, durationMs, status }` from `trace.json`.
- `verdicts`: per criterion `{ criterionId, text?, judges: { claude, gemini, gpt, auto? -> { verdict, reason } }, panel }`. `text` exists only for failed criteria (that is all the verdict file carries).
- `flags`: hallucination flags `{ id, quote, severity: minor|material|null, upheld, problems, raisedBy }`.
- `audit`: `{ time, eventClass, target, result, reason, background }`; empty for the stand-in.
- `metrics`: `{ turns, tokens {prompt, completion, total}, wallClockSeconds, toolErrors }` (from `run_end` and the steps).
Adapters implement `RunSource { kind, canRead(dir), read(dir) }`: `standin` (EVENTS_SPEC.md format) and `hermes` (stub).

## Data rules
1. The app loads only `/data/index.json` (and the run files it lists) from its own origin.
2. `scripts/build_cache.mjs` never reads or copies `truth.json`, `rubric.json`, or anything under `gold/` or `attacks/`; it fails loudly (before reading or writing anything) if one is in the input, and refuses output text that names them.
3. Judge verdict files are allowed. The rubric-derived `reference` hint inside them is dropped; the criterion text of failed criteria is kept.
4. Tests: refusal tests for each forbidden name, and a scan of `gui/public/data` after a build.

## Next slices
1. Case: before (denial, chart evidence) and after (deliverable, decision), plus a criteria tab (verdicts, flags).
2. Containment: agent trace and OCSF audit log split screen (needs Hermes audit data; the attack run).
3. Scorecard: metrics, judge panel, by-category results.
4. Hermes adapter: join the Hermes trace, session messages and `audit.jsonl` from `docs/samples/hermes_run_*` once the VM work is merged.
