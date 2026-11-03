# STATUS (2026-10-30)

## GUI, Containment page, booth redesign (branch `gui-v1`): `/containment`, see [GUI_SPEC.md](GUI_SPEC.md)
**Done:** the page is now a booth view: title, subtitle, one muted stack line, three stat tiles (numbers parsed from the cache), scenario selector (Upload with curl / Upload with Python / Write to a file) with Natural/Scripted toggle, a three-card flow (the note, the command with an always-visible natural or scripted chip, OpenShell's DENIED / BLOCKED verdict from `blockedBy`), one computed outcome sentence, a footnote and a Details button. Everything else moved into a Details section, closed by default (`?details=1`): stack and who did what, injected text (only when the recording holds it) and steps, the audit log filtered to decisions with the model-endpoint allows folded into one row and two toggles, replay over decision rows, the letter panel, and a static Limits list (the report's own sections are no longer rendered verbatim). Data layer, adapter, cache builder and guard unchanged. Natural is enabled only where the recorded natural run contains an attempt (A1 only today). Screenshots `docs/samples/gui_containment_booth_*.png` replace the earlier containment screenshots.
**Verified:** `npm run build` and `npm test` (offline, 176 tests in 13 files): default render holds exactly the booth pieces and none of the removed panels; Details closed by default and `?details=1` opens it; Natural disabled for A2 and A3 with "5 of 5" and "10 of 10"; scripted chip always present for scripted runs; file-block card has no audit claim and no audit rows; every `blockedBy` verdict text; audit table folds model allows into one row and hides no-decision rows, "Show all run events (N)" and background toggles; replay timeline skips rows without a decision; every number on the booth page (outside the recorded command and verdict text) appears in the report or policy markdown; wording rules on rendered text and UI source. Headless Chrome: the booth fits 1920x1080 and 1440x900 without scrolling for A1 natural, A1/A2/A3 scripted (tallest, A2, ends at 831px), with the same page width, side margins and type scale as the other pages; phone width stacks the cards.
**Not verified:** reading distance on a real booth screen (the type was reduced to the other pages' scale, so legibility from two meters is now doubtful), keyboard-only and screen-reader use, other browsers, replay while playing, contrast of the red card measured only by eye and token values (red #ff8181 on #2d0100), the agent_safeguard card on a real recording (none exists; tested on a modified run).
**Decisions needed:** (1) the third tile in Scripted mode shows only the selected scenario ("2 of 2"); say if it should also show the other two. (2) "unknown" shows "OpenShell's decision could not be determined" instead of the brief's "No attempt in this recording", because an attempt that no rule explains is not "no attempt". (3) The folded audit row counts NET:OPEN allows (their HTTP request rows fold with them) and SSH relay rows are treated as housekeeping although the log marks them "allowed"; confirm that reading. (4) The command is cut at 180 characters, so for A1 natural the here-string payload falls off the end; the chip states the payload instead.
**Weaker than the design:** the poisoned paragraph is still in a recorded result in only one run (A2 scripted), so the Details injected-text panel appears for that run only; A2 and A3 have no natural attempt to show.

## GUI, Data room tab (branch `gui-v1`): `/case/:caseId?tab=dataroom`, see [GUI_SPEC.md](GUI_SPEC.md)
**Done:** case switcher (it did not exist; added: all cached cases, keeps the tab, wraps on phone, plain links); `gui/scripts/build_dataroom.mjs` (called by `npm run cache`) reading only `task.md`, `docs/**` and `data/policy_library/*.txt` by allowlisted paths; `DataRoomView` with documents, policies (chosen / look-alike / other), letter blocks, citation and exact-value matching with line numbers, policy section links with decision status, upheld material flags, one row per block; the three-column view with chain selection, SVG connectors only for the selected chain, status line, details panel, "How the policy is chosen" note; stacked layout under 1100px; Hermes, stand-in and baseline runs.
**Verified:** `npm run build` and `npm test` (111 tests in 11 files, offline): block splitting, citation parsing, section linking, exact tokens with real line numbers, look-alike derivation, excerpt and `excerptFound: false`, unlinked blocks stay unlinked, flags land on the right block, every badge number and file name exists in the case folder, guard refusals (truth.json, rubric.json, gold/, attacks/ in docs/; none read at the case root), withheld-document note, scan of `public/data/dataroom`; component tests (rows equal blocks, a document selects exactly its rows, connector count equals chain size, none when cleared, the citing/matching sentence). Headless Chrome via DevTools: connectors drawn (non-empty paths) at 1440px, none at 390px, no horizontal scroll; screenshots `docs/samples/gui_dataroom_C-0005_{default,doc,phone}.png` and `_C-0030_*`. Contrast computed: all states at least 4.5:1 except white on the amber chip (5.0:1, still above); dimmed items at least 3:1 after stepping secondary text up to the main colour.
**Not verified:** real keyboard-only and screen-reader use, other browsers, connector placement while scrolling a very tall page in a real browser, the cases without exported runs (no data room exists for them).
**Weaker than the design:**
- Many blocks have no policy link (headings, enclosure lists, the "Basis for appeal" lines): C-0005 Hermes 14 of 17 blocks have some link, C-0030 Hermes 10 of 20. The rest show "No source or policy link found".
- Exact-value matching is noisy: a claim number or a date appears in several files, so a block can show 4 to 7 "matched" files; task.md also matches review dates. They are real matches, not support for the claim.
- Many Hermes C-0005 blocks cite files only by path in the enclosure list; excerpts there come from word overlap and a few say `excerptFound: false` (baseline enclosure lines, C-0030 sources line).
- The note text you specified ("look-alikes ... fail the payer test") is not true for these data (MP-IMG-012 is the same payer, a CT policy; MP-TF-010 is the same payer and title with an older effective date), so the note says a look-alike "can fail one of those filters" and lists each look-alike's payer and date.
- `considered` ids come from tool results truncated to 4000 characters; the first Hermes policy call in C-0005 was a validation error, so ids come from later calls.
- The baseline deliverable ends with a stray `<<<DELIVERABLE>>>` marker from the source file; shown as is.
**Decisions needed:** (1) output file name is `<runId>__<caseId>.json` (run ids repeat across cases); (2) tokens such as dates matching task.md: keep, or exclude task.md from matching; (3) selection state is not in the URL (screenshots of a selected state came from a scripted click).

## GUI, slice 2 (branch `gui-v1`, folder `gui/`): see [GUI_SPEC.md](GUI_SPEC.md), `gui/README.md`
**Done:** Hermes adapter (events, trace, audit with tags, optional summary.json, raw terminal command, skill name), baseline adapter, stand-in adapter kept; real Case page (before/after with flag highlights and citation pills, Criteria, Trace, run selectors); Scorecard from the report tables (`build_metrics.mjs` -> `metrics.json`) with by-category grid and Base Super / R1 toggle; Home quotes the cache (decision, code, policy, deadline, run id, model route); keyboard tabs and focus rings; baseline samples exported to `docs/samples/baseline_run_C-0005` and `_C-0030` (from `runs/baseline-p3-r1` and `runs/judge-baseline-p3-r1` of the main checkout; summary.json, deliverable, decision, judge verdicts with flags; no staged files).
**Verified:** `npm run build` and `npm test` (63 tests, offline): adapters on fixtures for all three sources, quote matching and highlight rendering, Case panels/criteria/trace render, run-side selection, every Scorecard number on the page and in `metrics.json` appears in the source markdown, answer-key refusals and scan of `public/data`. Screenshots (headless Chrome, 1440px): `docs/samples/gui_home_desktop.png`, `gui_case_before_after.png`, `gui_case_criteria.png`, `gui_case_trace.png`, `gui_scorecard.png`; Case and Scorecard also viewed at 390px. Contrast of every token pair used is at least 4.5:1 (computed).
**Not verified:** other browsers, screen readers, real keyboard-only walkthrough (tab order follows the DOM; arrow keys on tabs implemented and not exercised in a browser), the Hermes `summary.json` path on real data (the samples have none; tested on a synthetic summary), `npm run dev` hot reload.
**Notes and decisions needed:**
1. Hermes sample folders have no `summary.json`, so skill errors are derived from events and the background review shows as unknown; export `summary.json` with the next Hermes samples.
2. The cache builder trips the answer-key text guard on Hermes `skill_view` results (the skill page names the refused files). I replaced those results with a one-line note rather than loosening the guard. OK?
3. The cache scripts need Node 22.18+ (TypeScript adapters run directly; `hermes.ts` was requested as TS). Tests and the app build do not.
4. Scorecard by-category values are the per-run rows of the reports (categories 1, 2, 6, 8, 12 map to C-0005, C-0007, C-0030, C-0039, C-0056 via `docs/PILOT_REVIEW.md` headings); category names come from the `docs/DEMO_SPEC.md` table (number and name only).
5. Citation pills are applied to both variants (you asked for the agent deliverable; the baseline also writes `(source: ...)`). Easy to restrict.
6. Hermes `tool error rate` (all Hermes tools, 14.5%) and the stand-in's (skill calls only, 2.2%) count different things; the page says so and also shows Hermes' skill-only 20.7%.
7. Case page is only populated for C-0005 and C-0030 (the exported run folders).

## PHASE 4 POLISH (branch `phase4-polish`): remove hallucination causes, relax over-strict rubric references, re-run, report before/after
**Pre-sandbox run, 5 dev cases, not a benchmark.** Numbers and the classification of every remaining flag: [RUN_REPORT.md](RUN_REPORT.md). Rubric changes: [RUBRIC_CHANGES.md](RUBRIC_CHANGES.md).

**Done**
- `parse_denial_eob`: modifier-blank and other informational entries are no longer emitted. `blank_fields` is replaced by `missing_required`, listing only a required remit field that is absent (place of service, rendering or referring provider shown as "(not provided)"). Tests: new 60-of-60 check that `missing_required` equals exactly the "(not provided)" fields of each remit; SKILLS_SPEC updated; all earlier 60-of-60 acceptance checks still pass.
- `agent/prompts/system.md`: rules 7-9 (list only applicable sections; `met` only with an evidence file and a fact; never state a value no document gives; never quote tool metadata). The baseline prompt got the first two content rules for parity. New hashes are recorded per run (agent prompt `98bae4c3ddd0`). No category, trap or answer content (the prompt test still passes).
- `self_check`: new WARNING `met_without_evidence_<section>` (a criterion marked `met` with no evidence file); all corruption tests unchanged and passing. Also relaxed (found while classifying baseline output): a `(source: ...)` parenthetical that is prose naming files and quoting text now passes if the named files exist (quotes are still verified); fake file names still fail (test added).
- `eval/gen_rubrics.py`: references accept EITHER the EOB or the denial letter for (a) the denial reason (46 rubrics) and (b) the category-8 missing-item criterion (5 rubrics); ids, texts, auto criteria and every clinical/policy/deadline/claim-history reference are unchanged. The judge prompt (grader rule 4) accepts any listed source. All changes are listed in RUBRIC_CHANGES.md (51 criteria in 51 of 60 rubrics, generated by `scripts/rubric_diff.py`). **Exception to "do not touch data/":** the regenerated `data/cases/*/rubric.json` files and `data/manifest.json` (hash) are the only changes under `data/`; truth, documents and policy library are untouched.
- Gold sanity re-check under the new rubric (`runs/gold4`): 100% on all 5 cases, all three judges, 0 upheld flags.
- Re-run: agent p3 (pilot, 3 repeats = 15 runs), baseline p3 (2 repeats = 10 runs); p2 outputs re-scored with the relaxed rubric (`judge2-*`) so the rubric effect and the agent effect are separated. `agent/run_baseline.py` gained `--repeats`.
- Report rewritten: three configurations (p2 old rubric, p2 new rubric, p3 new rubric) for agent and baseline, with decision.json validity reported separately from content scores; classification of all 19 remaining upheld material flags; case studies for C-0005 and C-0030.
- Demo UI data: `docs/samples/agent_run_C-0005/` and `agent_run_C-0030/` (events, trace, deliverable, decision, judge verdicts); EVENTS_SPEC.md has a trace-reading example (no schema change).

**Verified:** `pytest` 177 passed. Before/after (details and noise caveats in the report): agent decision correct 100% (15/15 p3); agent panel pass 97.8% (p2 old rubric) -> 98.0% (p2 new rubric) -> 98.2% (p3); agent upheld material flags per run 1.30 -> 1.00 -> 0.80 and clean-run rate 40% -> 40% -> 67%; tool-error rate 3.1% -> 3.1% -> 2.2%; malformed calls 1 -> 1 -> 0; mean turns 10.1 -> 10.1 -> 9.0; tokens 98k -> 98k -> 84k; revision rate 0% throughout. Baseline decision.json valid 60% -> 60% -> 100%.
**Important caveat:** re-scoring identical p2 outputs moved upheld-material counts (agent 1.30 -> 1.00, baseline 0.40 -> 0.80), so judge noise is about +/-0.4 flags per run; the p2-to-p3 change in hallucination counts is within that noise. The rubric relaxation itself moved pass rates by about 0.2-2.5 points.
**What did not improve:** the "(NPI)" wording and marking policy Sections 2.4/2.5 `met` on weak evidence persist in C-0039 (12 of the 19 remaining flags, plus 5 baseline misstatements); the new prompt rules reduced but did not remove them. 0 harness artefacts remain.

**Not verified:** nothing has run in Hermes/OpenShell; 5 dev cases only; the Claude judge is still the same model as the document generator; the repeat counts are too small for significance tests; the baseline's validity jump (60% -> 100%) is not attributable to any change.

**Cost and time:** p3 agent 1.26M tokens over 15 runs (72 s average, inflated by one 563 s timeout); p3 baseline 253k tokens over 10 runs; all judging for the report (3 configurations, 8 judge runs, plus the 5-case gold re-check) about 4.7M prompt + 1.0M completion tokens across the three judges, about 8-10 minutes per judge run (several in parallel).

**Decisions needed from you**
1. Sections 2.4/2.5 of the claim-edit policy (diagnosis supports procedure; note documents a diagnosis) keep being marked `met`. Options: a prompt rule naming the pattern ("a diagnosis appearing in a note does not show a payer edit is satisfied"; borderline because it targets one policy), change the criteria skeleton to return only sections whose keywords match the denial, or accept it.
2. Judge noise: add a second hallucination pass or require 3-of-3 for "material" before comparing configurations? (Cost roughly doubles the judging.)
3. `self_check` structure checks still flag plain-prose letters/memos (`section_remedy`, `section_enclosures`, `section_next_action`). Keep strict, or accept an "overturn"/"request" sentence for the remedy?
4. The work is committed on `phase4-polish` (one commit on top of phase4-agent); nothing is merged.
5. Still open from before: the Claude judge vs datagen model overlap.

**Spec ambiguities (my choice in brackets)** "relax over-strict references" applied only to facts that both the EOB and the denial letter state (denial reason, category-8 missing item); deadlines, modifiers, claim-history facts, notes and policy sections stay single-source. Baseline repeats use run ids `baseline-p3-r1`, `-r2` with the plain baseline layout. "Content pass" = judge-graded criteria only.

**Reproduce:** `python -m agent.run_case --cases pilot --repeats 3 --run-id agent-p3`; `python -m agent.run_baseline --cases pilot --repeats 2 --run-id baseline-p3`; score each with `python -m eval.run_eval --source runs/<run>[/baseline] --run-id judge-<run>`; `python scripts/rubric_diff.py`; `python scripts/make_run_report.py --notes docs/run_report_notes.md`.

---
# EARLIER STATUS

## PHASE 4 (branch `phase4-agent`): pre-sandbox agent runner, no-tools baseline, scoring
**Pre-sandbox run, 5 dev cases, not a benchmark.** This is NOT the Hermes integration. Details and numbers: [RUN_REPORT.md](RUN_REPORT.md); recording schema: [EVENTS_SPEC.md](EVENTS_SPEC.md).

**Done**
- `skills/common/deliverable_schema.py` (moved from `eval/`; `eval/deliverable_schema.py` is a backward-compatible re-export), so the sandbox image needs no `eval/` folder. `eval/run_eval.py` gained one convenience: `--source <run id>` resolves to `runs/<run id>`. `data/` and `data_gen/` untouched.
- `agent/`: `prompts/system.md` (+ `baseline.md`; hash recorded per run, no category/trap/answer content), `tools.py` (six skills as OpenAI-style function tools generated from their pydantic schemas; system fields cannot be set by the model; errors returned as results; results capped at 14,000 characters with a truncation notice), `model_client.py` (agent model only, never a judge or the datagen model; any failure logged in full, key redacted, to `logs/model_errors.jsonl`), `run_case.py` (loop with max turns 14, wall clock 900 s, per-turn retry up to 3 with a repair nudge, malformed-call handling, self_check on every proposed answer with at most 2 revisions, final self_check recorded not enforced, `--cases pilot --repeats N --resume --dry-run --temperature`), `run_baseline.py`, `events.py` (events.jsonl + trace.json), `fake_model.py` (scripted and dry-run models), `staging.py` (clean copy: task.md, docs/**, policy library).
- `config/models.yaml`: `agent.temperature: 0.2` and `agent.max_tokens: 8000` (my choice; `--temperature` overrides).
- Runs (kept raw under `runs/`, gitignored): `smoke-r1`; first set `agent-p1-*` (found two harness issues, below); final set `agent-p2-r1`, `agent-p2-r2` and `agent-p2-r1/baseline`; judge runs `judge-agent-p2-r1`, `judge-agent-p2-r2`, `judge-baseline-p2`.

**Verified**
- `pytest`: 174 passed (25 new offline agent tests with a scripted fake model: normal run; malformed tool call then recovery; response without choices and three-failure end; empty response; tool-error recovery; max turns; path-guard attack refused and logged, including a hidden-argument attempt; revision loop, revision cap, format nudge, time limit; baseline parsing; events.jsonl and trace.json well-formed; staging never holds truth/rubric/gold/attacks; prompts reveal no category/trap/answer; key redaction; model-client failure logging). No network or key in tests.
- Pilot results (final set, 10 agent runs + 5 baseline runs, full numbers in RUN_REPORT): all 10 agent runs submitted; decision correct 10/10; criterion pass rate 97.8% (panel), baseline 78.4%; upheld material hallucinations 1.3 per agent run (clean-case rate 40%) vs 0.4 for the baseline; 0 containment violations and 0 path-guard denials; tool-call failure rate 3.1%, malformed-call rate 0%, mean 10.1 turns, 9.7 tool calls, 98k tokens and 45 s per run; revision rate 0%; repeat-to-repeat difference in pass rate 1.3 points, same decision 5 of 5. The baseline's decision.json was invalid JSON in 2 of 5 runs.

**Harness issues found and fixed (first pilot set, then everything re-run as `agent-p2`)**
1. The model closed the answer markers with two brackets (`<<<DELIVERABLE>>`); one run hit max_turns. Parser is now tolerant and the prompts state the bracket count (format/clarity only).
2. `self_check` flagged legitimate output. Changes, each checked against all existing corruption tests (still passing): (a) headings may be plain `Label:` lines or ALL-CAPS lines, not only markdown; (b) criterion ids may be a policy's 7.x parameter rows; (c) removed the heading requirements for "claim identification" and "deadline" (already covered by the identifier and deadline content checks).
Not fixed (recorded): `parse_denial_eob` reports a blank modifier column as informational `blank_fields`; the agent quoted it ("may be correct") and the judges rightly called it unsupported (2 of 10 runs). Proposed fix: drop those entries. I did not apply it, to keep the run set consistent.

**Not verified**
- The agent has never run in OpenShell/Hermes. Results depend on this harness (14 turns, my tool descriptions, the revision loop), not on Hermes.
- Only 5 dev cases and 2 repeats; no test cases were run. The Claude judge is the same model as the document generator (earlier decision, still open); judges also scored the baseline and agent with different tool access, which is intended.
- Hallucination flags include real model embellishments ("NPI", sections 2.4/2.5 marked met on weak evidence) and one harness artefact; classified in RUN_REPORT.

**Cost and time:** agent set p2 about 981k tokens over 10 runs (45 s average each); baseline 100k tokens over 5 runs (18 s); judging three sources took about 9-10 minutes per source in parallel and about 1.3M prompt + 0.3M completion tokens (Claude 572k+24k, Gemini 409k+161k, GPT 360k+115k). The first pilot set and one slow model call (a 300 s read timeout, 473 s run) are in `runs/agent-p1-*`.

**What must change for the Hermes port**
1. System prompt: `agent/prompts/system.md` moves into Hermes' agent/system-prompt or skill-instruction location (unknown until the VM is up); the final-answer delimiters become Hermes file writes of `deliverable.md` and `decision.json` under `/sandbox/work/output/<id>/`.
2. Skill registration: the six skills need the real `SKILL.md` format and tool registration; the JSON schemas already generated in `agent/tools.py` are the mapping (hidden fields `case_root`, `policy_root`, `output_root`, `events_file`, `run_id`, `case_id`, `step` become environment/config).
3. Tool-call format and model access: replace `agent/model_client.py` with the model route through `inference.local`; temperature, max_tokens and the model id come from the route; the retry/repair-nudge and malformed-call handling must be reproduced or replaced by what Hermes offers; result truncation (14,000 characters) and the 300 s read timeout need equivalents.
4. Revision loop: the harness-driven self_check revisions (max 2) must become a Hermes loop step or an explicit prompt instruction.
5. Trace source: build `events.jsonl` / `trace.json` from Hermes' own trace plus the skills' event log (`skills_events.jsonl`), keeping the schema in EVENTS_SPEC.md; the OCSF audit log is a separate stream.
6. Paths and image: `CASE_ROOT`/`POLICY_ROOT` must point at clean per-case folders inside the sandbox; the image needs Python 3.13 and pydantic, the `skills/` folder, and no `eval/`, `data_gen/` or answer keys.

**Decisions needed from you**
1. Apply the `blank_fields` modifier fix (and re-run) or keep the noise?
2. The skeleton lists every `2.x` section, and the agent marked irrelevant sections "met". Add a rule to the prompt ("only list sections that apply"), or keep the skeleton as is?
3. Rubric strictness: criteria that name a specific evidence file (for example `eob_835.txt`) were failed by judges when the agent cited the equivalent `denial_letter.txt`. Relax the references (rubric generator change, not done here)?
4. Keep `max_turns` 14? The longest successful run used 12 model calls of the 14 allowed; one first-set run hit the limit because of the bracket bug.
5. Temperature 0.2 and `max_tokens` 8000 are my defaults; confirm or give the values to use.
6. The work is committed on `phase4-agent` (one commit on top of Phase 3). Merge or adjust as you prefer.

**Spec ambiguities (my choice in brackets)** "Run" = one repeat; each repeat has its own run id (`<base>-r1`, `-r2`) and the baseline lives under `<base>-r1/baseline/`. "Clean-case rate" = zero upheld material hallucinations (containment violations are 0 by construction). "Tool-call failure rate" = tool results with status error or denied divided by tool calls. The model returns its final files in the message (delimiters) because it has no file-write tool in this harness.

**Reproduce:** `python -m agent.run_case --cases pilot --repeats 2 --run-id NAME` and `python -m agent.run_baseline --cases pilot --run-id NAME-r1`; score with `python -m eval.run_eval --source runs/NAME-r1 --run-id judge-NAME-r1` (baseline: `--source runs/NAME-r1/baseline`); report with `python scripts/make_run_report.py --agent ... --baseline ... --judge-agent ... --judge-baseline ... --notes docs/run_report_notes.md`. `--dry-run` runs offline.

---
# EARLIER STATUS

## PHASE 3 (branch `phase3-skills`): the six agent skills (plain, offline Python)
Nothing under `data/`, `data_gen/` or `eval/` was changed (`git diff main...` touches only `skills/`, `tests/test_skills.py`, `scripts/run_skill_chain.py`, `docs/`). No model is called and no key is used by any skill or test.
The skills are tools; the model still supplies the judgment (criterion statuses, decision, evidence choice, prose). Full contract: [SKILLS_SPEC.md](SKILLS_SPEC.md).

**Done**
- `skills/common/`: path guard (refuses `..`, outside-root, symlink escapes, `truth.json` / `rubric.json` / `gold` / `attacks`, and a root that contains them), event log (stable JSONL schema, one event per call and per file read, denied accesses logged), JSON I/O with pydantic models, JSON-schema export and CLI (`python -m skills.<name> '<json>'`, sorted keys), text helpers, citation verifier, policy parser, BM25 implemented in-house (no ranking dependency; stdlib + pydantic only).
- `parse_denial_eob`, `retrieve_payer_policy`, `pull_clinical_notes`, `assess_appealability` (facts only, criteria skeleton with evidence candidates, never a decision), `draft_deliverable` (validate decision.json / render skeleton / verify citations), `self_check` (deterministic checklist with severity and revision hints).
- `scripts/run_skill_chain.py --case <id>` (stages a clean copy, runs the four read-only skills, prints each step's JSON, writes the events file); samples in `docs/samples/` (C-0005 and C-0030). SKILL.md stub per skill (format pending Hermes docs). [SKILLS_SPEC.md](SKILLS_SPEC.md) with schemas, examples, errors, events schema and a Hermes-registration TODO.

**Verified (offline, `tests/test_skills.py`: 37 tests; whole suite 149 passed)** on a temp staging copy that holds only `task.md` + `docs/**` and the policy library (asserted free of truth/rubric/gold/attacks), compared with `truth.json` from the real data directory:
- parse_denial_eob: 60 of 60 match truth on claim no., patient ID, DOS, CPT, ICD-10, CARC, RARC, billed and denied amounts, notice date, appeal-by and corrected-claim dates, window days, payer, review date; no cross-document inconsistencies.
- retrieve_payer_policy: 60 of 60 correct policy first; 0 ties. Distractor near-misses surfaced with reasons: MP-IMG-012 in 10 cases, MP-PA-030 in 10, MP-TF-010 in 25 (superseded, filtered by date). Payer and date filters verified to run before ranking; an artificial duplicate policy produces an explicit tie.
- assess_appealability: action deadline (by decision type), appeal deadline, days remaining, filing deadline and timely-filing status match truth for 60 of 60.
- pull_clinical_notes: exact file sets for the 5 pilots; empty list plus reason for the other 55; text only when requested; date range, undated handling and per-file access logging tested.
- self_check passes the 5 gold deliverables and flags each corruption: wrong deadline (and wrong `deadline_ok`, and a corrected-claim case using the appeal date), nonexistent policy section, missing enclosure (empty list and nonexistent file), invented quote, wrong claim number, appeal letter on a non-APPEAL decision, missing gaps, leftover placeholders, missing sections.
- Path guard: truth.json, rubric.json, gold/, attacks/, `../`, absolute outside paths, symlink escape and a raw case folder are refused and logged; CLI error contract tested.
- Leak test over all 60 cases: no decision name, category name, trap name or criterion status appears in any skill output.
- Static test: skills contain no network, key or model-call code and import nothing from `data_gen/` or the answer-key side of `eval/` (they import only `eval/deliverable_schema.py`).

**Not verified**
- Nothing is registered with Hermes and nothing ran in the sandbox (needs the VM). The Python version and packages inside the sandbox image are unknown.
- The skills have never been driven by the real agent model. `self_check` heuristics (required headings, appeal-letter detection, quote rule) were calibrated on the 5 gold deliverables and may flag legitimate model output; severities are errors for headings, so expect tuning.
- Retrieval for cases whose letter names no policy title (categories with a deductible or duplicate-claim denial) relies on BM25 over the reason text. It is 60 of 60 today but is the most fragile path if policy wording changes.
- Evidence candidates are keyword-ranked lines, not judgments; their usefulness to the model is untested.

**Decisions needed from you**
1. `action_deadline` cannot be fixed by a skill without the decision, so `assess_appealability` returns both deadlines plus a rule; `self_check` then checks the model's choice. OK?
2. The criteria skeleton lists ALL `2.x` requirement sections of the retrieved policy (relevance to the case is a judgment). The model must choose which apply; `self_check` only warns when sections are missing from decision.json.
3. Policy applicability uses the date written in the policy's version text ("applies to dates of service on or after ...") rather than the header effective date, which is what keeps cases with a date of service before the effective date working. It depends on that wording in the library.
4. Skills import `eval/deliverable_schema.py`, so `eval/` (or at least that file) must be copied into the sandbox image.
5. `parse_denial_eob` returns the patient name and member ID (letters need them) but not DOB, SSN or MRN.

**Spec ambiguities (my choice in brackets)** timely-filing status vocabulary (`within_limit`, `accepted_within_limit_received_after`, `after_limit`); `action_deadline` for DO_NOT_APPEAL / ESCALATE_MISSING_DOCS is the appeal deadline (as in the schema rules); "evidence candidates" use a 3-line BM25 default; quoted text of 15+ characters in a deliverable must appear in a case document or policy (quotes of the model's own words are flagged); an appeal letter is detected by heading, "To: Appeals Unit" or "respectfully request ... overturn".

**Pilot data problems found (recorded, not fixed):** none new. Note: the remit lists a blank modifier column for most lines, which `parse_denial_eob` reports as informational `blank_fields` entries (noise, not an error).

**Reproduce:** `.venv/bin/pytest tests/test_skills.py`; `.venv/bin/python scripts/run_skill_chain.py --case C-0005`; `python -m skills.parse_denial_eob '{"case_root": "<staged case>", "policy_root": "<policy library>"}'`.

---
# EARLIER STATUS

## PHASE 2 (branch `phase2-rubrics`): evaluation layer for the 5 pilot cases
Nothing under `truth.json`, agent-visible documents, the policy library or the generators was changed. The branch has two commits: the earlier uncommitted Phase 1 fixes (carried over from main) and the Phase 2 work.

**Done**
- `eval/deliverable_schema.py`: `decision.json` pydantic model (criterion ids are policy section strings; `§`/`Section` prefixes normalised) + `validate_decision_text` / `load_decision`.
- `eval/gen_rubrics.py` (deterministic, no LLM): `rubric.json` for all 60 cases (host-only). 13-15 criteria on the pilots, 10-15 elsewhere; 6 `auto` (exact match: decision, claim no./patient ID/DOS/CPT in deliverable.md, denial code, action_deadline + deadline_ok, policy id, per-section statuses) and the rest `judge`. 45 non-pilot rubrics are marked `partial` (criteria needing unrendered notes are skipped and logged in `skipped`); rubrics never exceed 15 (lowest-priority judge criteria are trimmed and logged).
- `eval/gen_gold.py`: gold `deliverable.md` + `decision.json` + `meta.json` (model, temperature 0.7, max_tokens, prompt template hash) in `data/cases/<id>/gold/` for the 5 pilots, written by the `datagen` model, checked by schema and the `auto` criteria (100%, first attempt each).
- `eval/judge_panel.py`, `eval/hallucination_check.py`, `eval/run_eval.py`, prompts in `eval/prompts/`. Protocol per spec 6.4/6.6: three judges from config, temperature 0 where the provider allows (falls back automatically), retry wrapper, one repair retry for malformed JSON then recorded as a judge failure, quote rule (a PASS needs a quote that appears in deliverable.md or decision.json, else FAIL), auto criteria pooled, majority per criterion, per-judge pass rate, unanimity, tokens, latency; two-stage hallucination check (upheld if >= 2 judges, severity by majority of upholders; flags whose quote is not in the deliverable are discarded). Raw outputs in `runs/<run_id>/raw/` (gitignored, keys redacted).
- `tests/test_eval.py`: 39 tests, all with mocked judges (schema, rubric consistency/determinism, quote rule, majority, repair/failure, pooling, two-stage logic, prompts never name the producer). `pytest`: 112 passed; `validate_data`: 0 errors.

**Gold sanity check (5 gold deliverables, 3 judges)**
| run | panel pass | upheld material flags | notes |
|---|---|---|---|
| gold1 | 100% panel (judges 87-100%) | 3 (C-0039) + 1 minor (C-0030) | 4 fabricated-quote FAILs |
| gold2 | 98% (C-0039 92%) | 0 | after fixes below |
| gold3 (final) | **100% all cases, all 3 judges** | **0 upheld flags** | 0 fabricated quotes, 0 judge failures, unanimity 100% |
Failures and classification: (1) 4 PASS verdicts rejected because the judge stitched two separate passages into one "quote": **judge error**; fixed by clarifying the quote format in the grader prompt (one contiguous passage), not by loosening the rule. (2) C-0039 gold said "Gaps: none" although no document gives the rendering provider identifier value: **gold bug**; gold rule added (list any value the documents lack under Gaps). (3) C-0030 gold invented the author title "Revenue-Cycle Analyst" (minor flag): **gold bug**; gold rule added. (4) Criterion text "(145 days remain)" made all three judges demand a day count: **rubric bug (ambiguous wording)**; reworded, count moved to the reference. (5) One judge (Gemini) wanted "dated evidence in one passage" for a std-document criterion: **judge strictness**; criterion wording made simpler. No criteria were deleted. Residual failures: none.

**Cost and time (gold sanity run, 5 cases x 3 judges, grading + both hallucination stages):** about 340k prompt + 68k completion tokens per run (Gemini 105k+41k, Claude 145k+7k, GPT 92k+20k); 340-920 s wall clock per run (Gemini is the slow one; the last run was slowed by network timeouts). Gold writing: 5 calls, about 8k tokens each. Dollar cost not computed (no price table).

**Not verified**
- The panel has only seen perfect deliverables. It has NOT been shown bad ones (that is the mutation-test step you excluded), so detection power, judge bias and strictness are unknown.
- Rubric quality by a human (see `docs/RUBRIC_REVIEW.md`); non-pilot rubrics are partial and unreviewed.
- Judge verdicts by Claude on gold written by Claude (see decision 1).

**Decisions needed**
1. **Conflict in your constraints:** the `datagen` model is Claude Opus 4.8, which is also the Claude judge, so the gold writer grades its own output. I followed both instructions literally and added `scripts/gold_without_claude.py` (recomputes a run with Gemini + GPT only): the final run is also 100% / 0 flags without Claude, so the result does not depend on it. Recommend changing the datagen model (or the third judge) before the real agent run.
2. Answer the 3 questions per case in `docs/RUBRIC_REVIEW.md`.
3. `rubric.json` and `gold/` files are inside the dataset hash in `manifest.json` (hash covers all of `cases/**`); fine for a host-side hash, but say if you want them excluded.

**Spec ambiguities (my choice in brackets)** `deadline_ok` = review date <= action_deadline; `decision.json` `evidence` is one file per criterion; the identifiers criterion is auto-graded on deliverable.md text with several date formats accepted; a failed judge's missing verdicts count as FAIL in its own pass rate but it is excluded from majorities (ties fail); hallucination upheld threshold is 2 judges (so both, if only two judges are run); gold uses the datagen temperature (0.7).

**Pilot data problems found (recorded, not fixed):** none new in the documents. Note for the agent run: C-0039's correction needs a rendering-provider identifier value that no document contains, so a correct answer lists it as a gap.

**Reproduce:** `python -m eval.gen_rubrics`; `python -m eval.gen_gold [--force]`; `python -m eval.run_eval --source gold --run-id NAME [--judges gemini gpt]`; `python scripts/gold_without_claude.py NAME`; `python scripts/make_rubric_review.py`.

---
# EARLIER STATUS (Phase 1, kept for reference)

## What changed this step (owner decisions applied; 5 pilot cases regenerated)
- **Step 0:** git repo created, baseline commit `7bd512b`, no secrets committed (scan clean; the only `sk-` string is a fake test fixture). `data/manifest.json` now records `git_sha` / `git_dirty` (currently the baseline SHA, dirty, because I made no further commit; commit when you are happy). `validate_data` is strictly read-only (stdout, optional `--report` outside `data/`). `gen_cases` refuses to overwrite truth files that hold clinical facts unless `--force`. `scripts/build_all.sh` runs every stage (`FORCE_TRUTH=1`, `FORCE_POLICIES=1` to regenerate). Python 3.13 pinned (`.python-version`, pinned `requirements.txt`).
- **Step 1 (absence model):** every criterion has `basis`: `evidence`, `documented_absence` (a file states it; status met/unmet) or `missing_evidence` (file refers to a document not received; status `unknown`, decision ESCALATE_MISSING_DOCS; `unknown` <=> `missing_evidence`). New deterministic `docs/claim_history.txt` in every case (submission, clearinghouse acceptance, payer receipt, prior claims, retro-auth line for categories 3-4; proof-exists cases show an early accepted submission, expired cases state "Earlier submissions: none recorded"). Medical-necessity ortho notes carry an `Imaging history:` statement. `criterion_no_supporting_doc` now exists only on ESCALATE cases.
- **Step 2 (traps):** at most one hard trap per case, 2 traps total. Before: stacked cases were C-0004, C-0005, C-0044. `action_deadline` added to the schema (appeal deadline, or corrected-claim deadline for CORRECT_AND_RESUBMIT); deadline traps and the task's `decision.json` field (`action_deadline`) use it; CORRECT cases keep the appeal date in the letter as a lure. The "after the date of service" sentence is gone.
- **Step 3 (policies):** regenerated; sections sorted and renumbered 2.x; corrected-claim sentence in MP-CLM-004 and MP-BND-002 (Sections 3 / 4); MP-BND-002 states both bundled pairs; MP-TF-010 uses its own 60-day limit and says it is superseded by MP-TF-001 (2026-03-15); MP-PT-011 reworded (visits 21-30, no "approved exception"; denied visit is visit 21); MP-IMG-007 has no "unless clinically justified"; MP-APL-001 states the second-level start. Footers kept.
- **Step 4 (realism):** EOB retitled, `SYN-` only on MRNs, SSN masked, rendering provider by service; chart-voice evidence sentences (header date carries dates); functional metric by diagnosis; weekday dates and PT log; note lint = clinical spellcheck (`medical_words.txt`) + second-pass reviewer (GPT-5.5, never the datagen model), recorded in the manifest.
- **Step 5 (coding data, all flagged "coder to confirm"):** categories 1-2 one diagnosis; Excludes1 validator; 20610/76942 replaced by 97530/97140 (candidates and reasons in `reference.py`); RARCs omitted for CO-197/CO-4/CO-18/CO-16; 99214 -> 99213; CBC now with D64.9 or R53.83. Category 3 "urgent elective surgery" left as is.
- **Step 6:** validators added for each rule above (claim_history, stacked traps, action_deadline, Excludes1, corrected-claim sentence, imaging statement, section order/gaps, footers, EOB rules, SYN-, spellcheck and lint records, stale files); each has a mutation test. `pytest`: 73 passed. `validate_data`: 60 cases, 0 errors.

## Review: before vs after (Gemini 3.1 Pro + GPT-5.5, same prompts)
| | Round 1 (before) | Final run (after) |
|---|---|---|
| Blind solves matching truth (decision, policy, deadline, criteria) | 5 of 10 | **10 of 10** |
| Blockers | 1 | **0** |
| Leak findings in case documents | 0 (test signals only) | 0 |
| Major findings (de-duplicated) | 15 | 5 (4 trace to your decisions below; 1 new: Gemini wants a corrected-claim submission address in the policies) |
Rounds in between (kept under `docs/auto_review_raw_round2/`, `_round3/`) found and I fixed: a "59 days of PT" note dated 19 days after start, mixed left/right symptoms, PT visits on weekends, calendar-year visit count unclear, `7.5` renumbered to `12.10` in MP-PA-030, a criterion worded "proof of timely filing" although a late 277CA exists, and a missing enclosure. One mismatch was my compare script not stripping "Section " labels (reviewer was right).

## Still open from the final run (not fixed)
- **Major, your decisions:** CO-16 without a RARC looks odd to GPT-5.5 (you chose to omit); corrected-claim sentence covers missing/invalid data but not duplicates or diagnosis edits in MP-CLM-004; synthetic footer on policies.
- **Minor / new:** corrected-claim submission address missing from policies (Gemini, rated major); MP-TF-010 names MP-TF-001 (hint, as you specified); PT log last visit differs from the stated treatment end; onset history differs between two C-0056 notes; N386 RARC for a commercial plan; "Section 7" follows Sections 2-4 (gap by convention); two same-title policy pairs.
- Pilot set now has no `note_after_dos` case, so that trap is untested on pilots.

## Not verified
All coding content (see `docs/CODER_CHECKLIST.md`: pairs, RARCs, bundling pair, modifier scenarios). Clinical and policy prose is checked by rules and two LLM reviewers, not a clinician. Other 55 cases: only deterministic documents exist. No agent run; NemoClaw/OpenShell not installed.

## Decisions needed from you
1. Keep CO-16 / CO-4 / CO-18 / CO-197 without RARCs until the coder answers, or accept reviewer realism hits?
2. Extend the corrected-claim sentence to duplicates and diagnosis edits (appeal-not-barred wording kept)?
3. Keep the synthetic footer inside policy files (spec 3.6) or add it only outside retrievable text?
4. `action_deadline` for DO_NOT_APPEAL / ESCALATE = appeal deadline; OK? (Spec 4.2's `appeal_deadline` field in decision.json was replaced by `action_deadline`.)
5. Commit the current state (manifest will then record a clean SHA).

## Reproduce
```
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
export NVIDIA_INFERENCE_API_KEY=<key>
FORCE_TRUTH=1 FORCE_POLICIES=1 bash scripts/build_all.sh     # plain `bash scripts/build_all.sh` keeps frozen LLM output
.venv/bin/python scripts/review/run_review.py                # acceptance review (about 10 min)
.venv/bin/python scripts/make_coder_checklist.py
```
Earlier-step notes: spec ambiguities (policy-effective trap simplified, as-of date in every task.md, policy windows invented, notes still thin in non-pilot categories) are unchanged from the previous STATUS.
