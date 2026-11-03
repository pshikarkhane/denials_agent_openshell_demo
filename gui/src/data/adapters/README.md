# Run adapters

Each adapter implements `RunSource` (`../types.ts`) and turns one run folder into a `RunView`. They are TypeScript that
`scripts/build_cache.mjs` runs directly (Node 22.18+ strips the types; vitest handles them in tests). The app never imports them:
it only fetches the JSON the builder wrote. All file reads go through `../guard.ts`.

| file | reads | notes |
|---|---|---|
| `standin.ts` | `decision.json`, `events.jsonl`, `trace.json`, optional `deliverable.md`, `judge_verdicts.json` (no `audit.jsonl`) | pre-sandbox tool loop; empty audit |
| `hermes.ts` | the same plus `audit.jsonl` and optional `summary.json` | keeps the raw terminal command, skill name, Hermes tool per step; audit events keep their `tag` (`run`, `background`, `post_run`); Hermes extras |
| `baseline.ts` | `decision.json`, `summary.json`, `deliverable.md`, `judge_verdicts.json` | no tools, no trace |

`canRead` is exclusive across the three (audit.jsonl vs events.jsonl), so the builder picks one per folder.
Without `summary.json` the Hermes extras are derived from the events and `backgroundReview` is `null` ("unknown"); with it, `skill_calls_total`, `skill_errors`, `hermes_tools_by_name` and `background_review` are used.
`skill_view` results (Hermes reading a skill page) are replaced by a one-line note: they are agent-facing documentation that names the refused files, so they are neither useful in a UI nor allowed past the answer-key guard.
