# GUI_SPEC: locally hosted demo GUI (`gui/`)

Cached mode only: no backend, no model calls, no keys, no network at runtime. Dark theme only; tokens in `gui/src/styles/tokens.css`.
No NVIDIA logos or brand assets (the mark is a plain 28px green square). All case content is synthetic; results are from a small pilot, not a benchmark.

## Routes and screens
| route | screen | status |
|---|---|---|
| `/` | Home: hero, runtime card, six scenario cards, footer note | built (slice 1, data-driven in slice 2) |
| `/case/:caseId` | Case: before and after, criteria, trace | built (slice 2) |
| `/scorecard` | Scorecard: headline numbers, judge panel, by-category grid, Base Super / R1 toggle | built (slice 2) |
| `/containment` | Containment | placeholder ("Next step"): table of cached runs |

Header on every page: mark, "Denial Appeals Agent", "R1 x NVIDIA demo", nav (`aria-current="page"`), a "Cached | Live demo" control (Live disabled, tooltip "Not available yet") and a SANDBOXED pill.

### Home
Cards 1 and 2 quote the newest agent run of C-0005 / C-0030 (Hermes before the stand-in, never the baseline): decision, denial code, policy id, action deadline and the run id come from the cache, and the description's claims (e.g. "drafts the appeal") are only shown when the cached decision says so. "No recorded run yet" when the case is not cached. The model-route line comes from the cached runs. Card 6 (Live) is not a link; the attack card links to `/containment`.

### Case (`/case/:caseId`, `?tab=criteria|trace|dataroom`)
Headline "Same case, two ways of working." Chips from the run: case, denial code, policy id, action deadline, decision.
Left panel: the no-tools baseline ("No tools: one prompt with every document pasted in"); if the case has no baseline run, the stand-in agent instead, with a visible note. Right panel: "Agent: Hermes in the OpenShell sandbox" (stand-in runs are listed as alternatives). A run selector per side picks among repeats (newest first).
Each panel: the deliverable rendered from markdown; upheld **material** hallucination flags marked in red where their quote is found (judges quote without markdown marks, so matching ignores `**` and backticks and collapses whitespace; flags whose quote is not found are labelled in the list below); every `(source: ...)` citation as a green pill (both variants); the flags list (severity, quote, each judge's reason; not-upheld flags are listed too); for the agent a row of trace chips in order (skill names; errors amber, denied red). Counts (tool errors, tokens, seconds) are shown as data; the page makes no claim about which side errs less.
Tabs: **Before & After**; **Criteria** (per criterion, the three judges as PASS/FAIL chips for each variant, rule-checked criteria as "Rule", panel verdict; criterion text only where the verdict file has it, i.e. failed criteria; rows expand to each judge's reason; the rubric `reference` field is never carried); **Trace** (steps with timings; a step expands to its arguments and result; Hermes steps also show the raw terminal command).

### Scorecard
Pilot note (verbatim): "Pilot: 5 dev cases, not a benchmark. Judge noise is about 0.4 flags per run, so differences that small are not findings." Series: no-tools baseline, stand-in agent, Hermes. Rows: criterion pass rate, upheld material flags per run, clean-run rate, tool error rate (Hermes also shows the skill-calls-only rate), tokens per run (Hermes also shows the fixed prompt overhead and the post-run review, which is not included), turns, seconds. Judge tables per judge (all criteria; judge-graded only). By-category grid of the 12 categories: values (per-run panel pass and upheld material count) only for the categories run (1, 2, 6, 8, 12), "Not run yet" for the rest. Toggle: Base Super (data) / R1 checkpoint (pending empty state).
Every value is the exact string from the markdown reports (`scripts/build_metrics.mjs`); nothing is computed. Test: every number in `metrics.json` and on the rendered page appears in the source markdown (static labels excepted: category numbers 1-12 and the pilot note's 5 and 0.4).

### Data room tab (`/case/:caseId?tab=dataroom`)
Three columns, left to right: **1 DATA ROOM** (case documents numbered, the chosen policy `P`, look-alike policies dashed, "N other policies"), **2 MATCHING** (one card per letter block: violet POLICY zone over amber CASE zone), **3 THE LETTER** (one card per block, aligned with its matching card; red FLAGGED chip for upheld material flags; "No source or policy link found" when unlinked). Selecting a document, the policy, a matching card or a letter block selects a chain; connectors (SVG, aria-hidden) are drawn only for the chain; the rest dims to 0.4. A status line (role=status), a details panel (policy section text, evidence lines with numbers and matched values highlighted, flags with judges' reasons, Clear selection) and a "How the policy is chosen" note sit below. Under 1100px the columns stack, connectors are hidden, and the documents are a collapsible list.
Own run selector ("Show the data room for:": Hermes, stand-in, baseline runs of the case).

**DataRoomView** (`public/data/dataroom/<runId>__<caseId>.json`, type in `src/data/types.ts`): `available`, `chosenPolicyId`, `consideredPolicyIds` (ids in the run's `retrieve_payer_policy` results), `caseDocs[]` (number, path, descriptor, `lines`, `opened` true/false/null, `citedBy`, `matchedBy`), `policies[]` (id, title, payer, effective, `status` chosen/lookalike/other, `considered`), `chosenSections[]`, `blocks[]` (id, kind, text, `links`: `cited`, `matched` {token,file,line}, `sections` {id,status,evidence}, `policy`, `flags`), `rows[]` (one per block: `policy` zone, `evidence` with excerpt, line, `excerptFound`), `summary`, `withheld`. `available: false` stubs have empty lists.
**Mapping rules and limits.** Document order: denial letter, EOB, the rest alphabetically, task.md last. Blocks: headings, paragraphs (consecutive lines joined), list items; markdown marks stripped. *Cited*: a case file named by path or file name anywhere in the block (including `(source: a; b)`). *Matched*: another case file containing an exact value from the block (dates YYYY-MM-DD, money, ids of 6+ digits or letters+5+ digits, 5-digit CPT, ICD-10 style, CO/PR/OA/PI/CR-n codes, RARC Nnnn), citations and paths excluded; first line per file. Shared values (a claim number, a date) match several files: that is real but weak evidence. *Sections*: only full ids that exist in the chosen policy (`§2.1(a)`, `Section 2.1`, bare `2.1`); `2.1` does not expand to `2.1(a)`. Status comes from decision.json criteria (null when not a criterion). *Policy zone*: the sections, else the chosen policy name when the block names it, else none. *Excerpt*: the exact matched line, else the line sharing the most words (4+ letters, at least 2), else `excerptFound: false`. *Flags*: upheld material flags whose quote shares a 40-character run (whitespace, `*` and backticks ignored) with the block. *Look-alike*: a non-chosen policy whose title shares at least 60% of its words with the chosen one. *Opened*: the file name appears in a tool call or result (results are truncated, so false means "no trace"); null for the no-tools baseline (all documents were pasted in).

## Data model
`gui/src/data/types.ts`. `RunView { runId, caseId, source, runtime, variant: 'agent'|'baseline', model, startedAt, decision, denialCode, policyId, actionDeadline, deliverableMarkdown, steps[], verdicts[], flags[], audit[], metrics, hermes }`.
- `steps`: `{ n, kind, name, argsSummary, resultSummary, durationMs, status, skillName, hermesTool, rawCommand, detail {arguments, result} }`. `detail` is joined from `events.jsonl` by order; `rawCommand` is the verbatim Hermes terminal command.
- `verdicts`: `{ criterionId, text?, judges { claude, gemini, gpt, auto? -> { verdict, reason } }, panel }`.
- `flags`: `{ id, quote, severity, upheld, problems, raisedBy, votes { judge -> { upheld, severity, reason } } }`.
- `audit`: `{ time, eventClass, target, result, reason, background, tag: run|background|post_run }`; empty for the stand-in and the baseline.
- `metrics`: `{ turns, tokens, wallClockSeconds, toolErrors, toolCalls, revisions }`.
- `hermes`: `{ hermesRunId, hermesVersion, skillCalls, skillErrors, toolsByName, firstCallPromptTokens, backgroundReview | null }`. `backgroundReview` comes from `summary.json` only (null = unknown).
Adapters (`standin.ts`, `hermes.ts`, `baseline.ts`) implement `RunSource { kind, canRead(dir), read(dir) }`.

## Data rules
1. The app loads only `/data/index.json`, `/data/metrics.json` and the run files the index lists, from its own origin.
2. `scripts/build_cache.mjs` never reads or copies `truth.json`, `rubric.json`, or anything under `gold/` or `attacks/`; it fails loudly (before reading or writing anything) if one is in the input, and refuses any output whose text names them. `build_metrics.mjs` applies the same text check.
3. Judge verdict files are allowed. The rubric-derived `reference` hint is dropped; criterion text of failed criteria is kept.
4. Hermes `skill_view` pages are not cached (they describe the refused file names).
5. Tests: refusal tests per forbidden name, a scan of `gui/public/data` after a build, the metrics-vs-markdown test.

## Next slices
1. Containment: agent trace and OCSF audit log split screen (the `audit` field and `tag` are already in the data; hide `background` by default). Needs a Hermes attack run recording.
2. Model swap: R1 checkpoint series once those runs exist (the Scorecard toggle is a placeholder).
3. Case: more cases once more runs are exported (today only C-0005 and C-0030 have run folders; the Scorecard covers all five dev cases through the reports).
4. Live mode (disabled in this slice).
