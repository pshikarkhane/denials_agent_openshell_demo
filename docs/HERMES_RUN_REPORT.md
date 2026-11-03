# HERMES_RUN_REPORT: the six skills through the real Hermes agent in the OpenShell sandbox

**Hermes in OpenShell, 5 dev cases, not a benchmark.** Host-only document (shows truth labels). Same cases, same skills (restaged from the current `skills/`), same scoring as docs/RUN_REPORT.md (judge panel Gemini 3.1 Pro / Claude Opus 4.8 / GPT-5.5 plus the two-stage hallucination check). Caveat: the Claude judge is the same model as the document-generation model. Pre-sandbox numbers are the p3 / new-rubric agent row of RUN_REPORT.md (15 runs); the raw pre-sandbox run folders are not in this checkout, so they are quoted, not recomputed.

Agent: Hermes Agent 0.21.3 in sandbox `my-hermes`, upstream model `nvidia/nvidia/nemotron-3.5-super-text-preview` (route set by NemoClaw; temperature not exposed). Prompt (`scripts/hermes/prompts/hermes_system.md`) hash `def5c6e55eac`, git `77b188a5`. Runs: hermes-p1-r1, hermes-p1-r2; judge runs: judge-hermes-p1-r1, judge-hermes-p1-r2.

## What happened to the runs

| measure | count |
|---|---|
| runs started | 10 |
| runs that finished (stream completed) | 10 |
| runs that wrote both files (deliverable.md and decision.json) | 10 |
| runs whose final files pass `self_check` (run by the harness after the run) | 10 |
| runs whose agent's own last self_check call passed | 10 |
| runs that used the revision step (a failing self_check followed by another) | 4 |
| runs that needed a gateway-restart retry | 0 |
| runs where Hermes persisted anything beyond the baseline before our reset (excluding `.curator_state`) | 2 |

## Side by side: Hermes vs the pre-sandbox stand-in (p3, new rubric)

| measure | Hermes in OpenShell | pre-sandbox stand-in (p3) |
|---|---|---|
| runs | 10 | 15 |
| decision correct (auto) | 100% | 100% |
| decision.json valid | 100% | 100% |
| criterion pass, panel (all) | 97.8% | 98.2% |
| per judge gem/cla/gpt | 93%/98%/98% | 96%/100%/98% |
| content pass (judge criteria only) | 96.2% | 96.9% |
| per judge content | 87%/96%/97% | 94%/99%/96% |
| upheld material hallucinations / run | 0.50 | 0.80 |
| clean-run rate (0 upheld material) | 70% | 67% |
| judge unanimity | 86% | 94% |
| tool error rate (skill + other Hermes tools) | 14.5% | 2.2% (skills only) |
| tool error rate, skill calls only | 20.7% | 2.2% |
| malformed skill calls | 3 | 0 |
| mean turns (model calls) | 11.6 | 9.0 |
| mean tool calls (all Hermes tools) | 13.8 | 9.0 (skills only) |
| mean skill calls | 8.2 | 9.0 |
| mean tokens / run (run's own model calls) | 250,435 | 83,995 |
| Hermes fixed prompt overhead (first call prompt tokens, mean) | 13,307 | about 2,750 |
| mean tokens / run in Hermes' post-run background review (NOT in the line above) | 57,365 | n/a |
| mean wall-clock seconds / run | 50 | 72 |
| revision rate | 40% | 0% |
| repeat SD of pass rate (per case) | 2.2% | 0.7% |
| same decision across repeats | 5/5 | 5/5 |

Clean-run rate = share of runs with zero upheld material hallucinations. Stand-in `revision rate` is harness-enforced (self_check failure triggers a revision request); in Hermes it is inferred from the agent's own calls (EVENTS_SPEC, Hermes runs).

## Per case

| case | truth | run | model decision | decision ok | decision.json valid | panel pass | content pass | upheld material | minor | turns | skill calls | other tools | tokens | s | final self_check | revisions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C-0005 | APPEAL | hermes-p1-r1 | APPEAL | yes | yes | 100% | 100% | 0 | 1 | 9 | 7 | 3 | 182059 | 50.6 | pass | 0 |
| C-0007 | DO_NOT_APPEAL | hermes-p1-r1 | DO_NOT_APPEAL | yes | yes | 100% | 100% | 0 | 0 | 14 | 10 | 6 | 280433 | 51.8 | pass | 0 |
| C-0030 | DO_NOT_APPEAL | hermes-p1-r1 | DO_NOT_APPEAL | yes | yes | 100% | 100% | 1 | 1 | 10 | 7 | 6 | 219365 | 42.1 | pass | 1 |
| C-0039 | CORRECT_AND_RESUBMIT | hermes-p1-r1 | CORRECT_AND_RESUBMIT | yes | yes | 100% | 100% | 2 | 1 | 9 | 7 | 4 | 198711 | 40.2 | pass | 1 |
| C-0056 | APPEAL | hermes-p1-r1 | APPEAL | yes | yes | 100% | 100% | 0 | 0 | 7 | 7 | 2 | 139370 | 31.3 | pass | 0 |
| C-0005 | APPEAL | hermes-p1-r2 | APPEAL | yes | yes | 93% | 89% | 0 | 1 | 16 | 8 | 7 | 326420 | 72.9 | pass | 0 |
| C-0007 | DO_NOT_APPEAL | hermes-p1-r2 | DO_NOT_APPEAL | yes | yes | 100% | 100% | 0 | 0 | 13 | 9 | 8 | 300889 | 53.9 | pass | 1 |
| C-0030 | DO_NOT_APPEAL | hermes-p1-r2 | DO_NOT_APPEAL | yes | yes | 93% | 88% | 0 | 0 | 8 | 8 | 4 | 156538 | 31.8 | pass | 0 |
| C-0039 | CORRECT_AND_RESUBMIT | hermes-p1-r2 | CORRECT_AND_RESUBMIT | yes | yes | 92% | 86% | 2 | 3 | 11 | 8 | 4 | 213416 | 40.6 | pass | 0 |
| C-0056 | APPEAL | hermes-p1-r2 | APPEAL | yes | yes | 100% | 100% | 0 | 0 | 19 | 11 | 12 | 487153 | 81.6 | pass | 1 |

## Failed criteria (any judge)

- C-0005: TRP1; C-0007: HON1; C-0030: POL2, POLX1, RSN2, TRP1; C-0039: REM1, EVD3, POL2, REM1; C-0056: RSN2, RSN2

## Upheld material hallucination flags

1. **hermes-p1-r1 C-0030**: "The $236.93 denied amount remains the patient's responsibility per the EOB (source: eob_835.txt, patient_responsibility $0.00 and paid $0.00 reflect the full denial)." | problem: The deliverable claims the denied amount is the patient's responsibility, but the EOB explicitly states patient responsibility is 0.00.
2. **hermes-p1-r1 C-0039**: "Section 2.4 (diagnosis supports the billed procedure per payer edit): the billed diagnosis M54.50 aligns with CPT 99213 (source: eob_835.txt; notes/2026-06-29_visit.txt)." | problem: Asserts that a policy criterion is met without evidence. The evidence does not contain the payer edit rules to confirm that M54.50 aligns with CPT 99213.
3. **hermes-p1-r1 C-0039**: "{
      "id": "2.4",
      "status": "met",
      "evidence": "notes/2026-06-29_visit.txt"
    }" | problem: Asserts that the payer edit criterion is met based on the visit note, which does not contain payer edit rules.
4. **hermes-p1-r2 C-0039**: "{
      "id": "2.2",
      "status": "met",
      "evidence": "denial_letter.txt"
    }" | problem: Asserts that Section 2.2 is met, but a corrected claim has not yet been submitted.
5. **hermes-p1-r2 C-0039**: "- Section 2.4 (the billed diagnosis must support the billed procedure per payer edit rules): met — the clinical record documents M54.50 for the CPT 99213 visit (source: notes/2026-06-29_visit.txt; eob" | problem: Unsupported that Section 2.4 is met under payer edit rules. The cited documents show the diagnosis and procedure, but do not state the applicable payer edit rule or that M54.50 supports CPT 99213 under that rule.

## Repeat variance (same case, two repeats)

| case | decisions | panel pass | skill calls | tokens | s |
|---|---|---|---|---|---|
| C-0005 | APPEAL / APPEAL | 100% / 93% | 7 / 8 | 182059 / 326420 | 50.6 / 72.9 |
| C-0007 | DO_NOT_APPEAL / DO_NOT_APPEAL | 100% / 100% | 10 / 9 | 280433 / 300889 | 51.8 / 53.9 |
| C-0030 | DO_NOT_APPEAL / DO_NOT_APPEAL | 100% / 93% | 7 / 8 | 219365 / 156538 | 42.1 / 31.8 |
| C-0039 | CORRECT_AND_RESUBMIT / CORRECT_AND_RESUBMIT | 100% / 92% | 7 / 8 | 198711 / 213416 | 40.2 / 40.6 |
| C-0056 | APPEAL / APPEAL | 100% / 100% | 7 / 11 | 139370 / 487153 | 31.3 / 81.6 |

## Containment and audit

- Path-guard denials in all runs: 0. Denied egress attributable to the run (tag `run`): 0. Hermes background denials (github.com, openrouter.ai; tag `background`): 6 events across all runs.
- Non-skill terminal commands: 6; reads/searches outside the skills (`read_file`, `search_files`): 4.
- State left behind by Hermes (before our reset), per run: hermes-p1-r2 C-0005: {"skills_added": [".curator_ledger.jsonl", "healthcare/appeals-claim-review/SKILL.md"]}; hermes-p1-r2 C-0056: {"skills_added": [".curator_ledger.jsonl", "appeals-workflow/SKILL.md", "appeals-workflow/references/decision-logic.md"]}.
- Background self-review: 2 of 10 runs started one (mean 6.5 model calls, 273,006 prompt tokens each).

## Why the numbers differ from the pre-sandbox stand-in

Read these as observations from 10 Hermes runs against 15 stand-in runs. Judge noise alone moved upheld-material counts by about +/-0.4 per run in the polish pass (RUN_REPORT.md), so differences of that size are not findings.

**Quality: no measurable difference.** Decision correct 100% in both, decision.json valid 100%, panel pass 97.8% vs 98.2%, upheld material 0.50 vs 0.80 per run (clean-run rate 70% vs 67%). The one visible dip is the Gemini judge (93% vs 96%; content 87% vs 94%). Three of its failures on `hermes-p1-r2` C-0030 (RSN2, POL2, POLX1) are the quote rule: Gemini quoted `Denial code: CARC CO-29 ...` without the markdown bold markers the deliverable has (`**Denial code:** CARC CO-29 ...`), so "quote not found in deliverable" turned a PASS into a FAIL. That is a judge-side matching artefact, not a Hermes error; the Hermes model writes markdown bold more often than the stand-in did. The upheld flags that remain are the known C-0039 pattern (Sections 2.4 / 2.2 marked `met` on weak evidence), 4 of 5 flags, plus one C-0030 claim that the denied amount "remains the patient's responsibility" while the EOB shows $0.00 patient responsibility.

**Tokens: 250k vs 84k per run (about 3x).** Hermes' own prompt is the main cause. The first model call of every run carries 13.3k prompt tokens (identity, the index of about 330 bundled skills, tool definitions, our instructions) against about 2.75k for the stand-in. Over a mean of 11.6 calls that fixed block alone is about 154k tokens of the 250k. Of all prompt tokens, 60% were served from the endpoint's prompt cache (agent.log `cache=`), which lowers cost and latency but not the token count. Smaller contributors: Hermes loads skill pages with `skill_view` (about 1.3 calls per run), and the answer is written through `write_file` and fixed with `patch` instead of one final message. **Not in these numbers:** Hermes forks a background self-review after a run (EVENTS_SPEC); it fired in 2 of 10 runs (8 and 5 model calls, 322k and 224k prompt tokens) and each time created a skill file. On average that adds 57k tokens per run (shown separately in the table).

**Tool errors: 14.5% of all tool calls, 20.7% of skill calls, vs 2.2%.** Terminal-call style, not skill failures. Of the 20 errors, 10 are `bad_input` schema errors on `retrieve_payer_policy` and `assess_appealability`: through the terminal wrapper the model composes the JSON from a skill page instead of being handed a typed function schema, and it sometimes passes wrong field names or an object where a string is expected (for example `payer`). 3 are shell-quoting failures: free text containing an apostrophe ("the plan's criteria") inside the single-quoted JSON argument breaks the shell command before it reaches the skill; the agent recovered each time by writing the arguments to a file and passing `"$(cat file)"` (6 calls used that form). 4 are `pull_clinical_notes` not_found (the model asked for a letter or a history file, which are not notes; the stand-in made the same mistake), 1 `execute_code` call blocked by Hermes, 2 stray terminal calls (one tried `run_skill ... skill_view`, which is not a skill). Every error was recovered within the run. No path-guard denial occurred.

**Turns and tool calls: 11.6 turns vs 9.0, 13.8 tool calls (8.2 skill calls) vs 9.0.** Extra turns are the file-writing steps (a `write_file` for each of the two files, `patch` when fixing) and `skill_view`; skill calls themselves are about the same as the stand-in (8.2 vs 9.0).

**Revision rate: 40% vs 0%, with a different meaning.** In the stand-in the harness runs self_check after each final answer and none of the 15 runs failed it. In Hermes the agent runs self_check itself on the files it wrote, and 4 of 10 failed once (`citations` x3, `section_next_action` x1, `section_remedy` x1 in one run); each was fixed with one `patch` and passed on the next call, so the second allowed revision was never used. Likely reasons (not tested): the agent writes the memo by hand rather than from the `render_skeleton` output, and the ported prompt asks for self_check on files rather than on an answer message. All 10 final files pass the harness-run self_check.

**Wall-clock: 50 s vs 72 s mean.** The stand-in mean is inflated by one 563 s timeout run; stand-in median is about 36 s against 46 s for Hermes. Hermes model calls average 4.1 s each and runs include a 30 s wait for the post-run review, which is not counted in the per-run seconds.

**Repeat variance.** SD of the per-case pass rate is 2.2% vs 0.7%, produced by two runs (C-0005 r2: one TRP1 failure; C-0030 r2: the Gemini quote artefact). Same decision in both repeats for all 5 cases. Run length varies a lot between repeats of the same case (C-0056: 7 vs 19 model calls, 139k vs 487k tokens).

**What this does not show.** 5 cases, 2 repeats, one model, one judge panel that shares a model with the generator; no statistical test. It shows the six skills can be driven end to end by the real Hermes agent inside the sandbox with the same answer quality on these cases, at about 3x the tokens, with a different, more error-prone call style that the agent works around.

