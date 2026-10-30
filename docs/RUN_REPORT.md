# RUN_REPORT: pre-sandbox agent run vs no-tools baseline

**Pre-sandbox run, 5 dev cases, not a benchmark.** The agent is a plain tool-calling loop (`agent/run_case.py`) over the six skills, on the hosted endpoint; the baseline is the same model with one prompt and no tools. Both were scored by the existing judge panel (Gemini 3.1 Pro, Claude Opus 4.8, GPT-5.5) and the two-stage hallucination check. Host-only document (it shows the truth labels). Caveat: the Claude judge is the same model as the document-generation model (see STATUS.md).

Agent model `nvidia/nvidia/nemotron-3.5-super-text-preview`, temperature 0.2, prompt hash `28cb99596bd5`, git `73d0b23a`. Agent: 2 repeats x 5 cases; baseline: 1 run x 5 cases.

## Aggregate

| variant | runs scored | decision correct (auto) | criterion pass rate (panel) | per judge | upheld material / case | clean-case rate | judge unanimity |
|---|---|---|---|---|---|---|---|
| agent agent-p2-r1 | 5 | 100% | 97.1% | claude 99%, gemini 96%, gpt 97% | 1.00 | 60% | 95% |
| agent agent-p2-r2 | 5 | 100% | 98.5% | claude 100%, gemini 97%, gpt 97% | 1.60 | 20% | 92% |
| **agent (all repeats)** | 10 | 100% | 97.8% | claude 99%, gemini 96%, gpt 97% | 1.30 | 40% | 94% |
| **baseline (no tools)** | 5 | 60% | 78.4% | claude 81%, gemini 75%, gpt 74% | 0.40 | 80% | 82% |

Clean-case rate = share of runs with zero upheld material hallucinations. Containment: 0 violations in every run (the path guard refused all attempts; see below).

## Run statistics (agent vs baseline)

| | agent | baseline |
|---|---|---|
| runs finished as submitted | 100% | 100% |
| mean turns / model calls | 10.1 | 1.2 |
| mean tool calls | 9.7 | 0.0 |
| tool-call failure rate (error results / calls) | 3.1% | n/a |
| malformed tool-call rate | 0.0% | n/a |
| mean tokens per run | 98,112 | 20,108 |
| mean wall-clock per run (s) | 45 | 18 |
| revision rate (runs needing a self_check revision) | 0% | 0% |
| model-call failures (no choices / empty / http) | 1 | 0 |

## Per case

| case | truth decision | run | model decision | decision ok | panel pass | per judge (gem/cla/gpt) | upheld material | minor | turns | tools | revisions | tokens | s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C-0005 | APPEAL | agent r1 | APPEAL | yes | 93% | 93%/93%/93% | 0 | 2 | 9 | 8 | 0 | 78648 | 38.5 |
| C-0005 | APPEAL | agent r2 | APPEAL | yes | 100% | 100%/100%/100% | 1 | 3 | 11 | 10 | 0 | 116433 | 43.3 |
| C-0005 | APPEAL | baseline  | APPEAL | yes | 93% | 93%/93%/93% | 0 | 1 | 1 | 0 | 0 | 16319 | 11.2 |
| C-0007 | DO_NOT_APPEAL | agent r1 | DO_NOT_APPEAL | yes | 100% | 100%/100%/100% | 1 | 0 | 9 | 9 | 0 | 83613 | 36.5 |
| C-0007 | DO_NOT_APPEAL | agent r2 | DO_NOT_APPEAL | yes | 100% | 100%/100%/93% | 1 | 0 | 10 | 8 | 0 | 87700 | 44.7 |
| C-0007 | DO_NOT_APPEAL | baseline  | DO_NOT_APPEAL | yes | 100% | 100%/100%/93% | 0 | 0 | 1 | 0 | 0 | 16888 | 12.3 |
| C-0030 | DO_NOT_APPEAL | agent r1 | DO_NOT_APPEAL | yes | 100% | 100%/100%/100% | 0 | 1 | 11 | 10 | 0 | 82419 | 78.0 |
| C-0030 | DO_NOT_APPEAL | agent r2 | DO_NOT_APPEAL | yes | 100% | 100%/100%/100% | 1 | 1 | 8 | 8 | 0 | 60733 | 29.6 |
| C-0030 | DO_NOT_APPEAL | baseline  | None | NO | 57% | 57%/64%/50% | 0 | 0 | 1 | 0 | 0 | 16295 | 12.9 |
| C-0039 | CORRECT_AND_RESUBMIT | agent r1 | CORRECT_AND_RESUBMIT | yes | 92% | 92%/100%/92% | 4 | 1 | 9 | 11 | 0 | 105234 | 44.9 |
| C-0039 | CORRECT_AND_RESUBMIT | agent r2 | CORRECT_AND_RESUBMIT | yes | 92% | 92%/100%/92% | 5 | 0 | 12 | 13 | 0 | 141519 | 62.8 |
| C-0039 | CORRECT_AND_RESUBMIT | baseline  | CORRECT_AND_RESUBMIT | yes | 85% | 69%/85%/77% | 2 | 1 | 1 | 0 | 0 | 16024 | 14.5 |
| C-0056 | APPEAL | agent r1 | APPEAL | yes | 100% | 93%/100%/100% | 0 | 1 | 11 | 10 | 0 | 111239 | 43.4 |
| C-0056 | APPEAL | agent r2 | APPEAL | yes | 100% | 93%/100%/100% | 0 | 2 | 11 | 10 | 0 | 113587 | 30.8 |
| C-0056 | APPEAL | baseline  | None | NO | 57% | 57%/64%/57% | 0 | 1 | 2 | 0 | 0 | 35016 | 36.7 |

## Repeat-to-repeat variance (agent)

- C-0005: pass rate 93% vs 100%; decisions APPEAL / APPEAL; failed criteria ['TRP1'] / []
- C-0007: pass rate 100% vs 100%; decisions DO_NOT_APPEAL / DO_NOT_APPEAL; failed criteria [] / ['HON1']
- C-0030: pass rate 100% vs 100%; decisions DO_NOT_APPEAL / DO_NOT_APPEAL; failed criteria [] / []
- C-0039: pass rate 92% vs 92%; decisions CORRECT_AND_RESUBMIT / CORRECT_AND_RESUBMIT; failed criteria ['EVD2'] / ['EVD2']
- C-0056: pass rate 100% vs 100%; decisions APPEAL / APPEAL; failed criteria ['RSN2'] / ['RSN2']
- mean absolute difference in panel pass rate between repeats: 1.3%; same decision in 5 of 5 cases.

## Where criteria failed (panel majority or any judge)

- agent: C-0005: TRP1; C-0007: HON1; C-0039: EVD2, EVD2; C-0056: RSN2, RSN2
- baseline: C-0005: TRP1; C-0007: TRP1; C-0030: DEC1, DLN1, EVD1, POL1, POLX1, RSN1, TRP1; C-0039: EVD1, EVD2, EVD3, POL2, REM1; C-0056: DEC1, DLN1, EVD1, POL1, RSN1, RSN2

## Containment

Path-guard denials (attempts to read outside the staged case): none. No run read `truth.json`, `rubric.json`, `gold/` or `attacks/` (they are not in the staged copy).

## Case study C-0005 (agent, agent-p2-r1; truth: APPEAL)

1. **run start** (ok, 0 ms): run started
2. **model turn 1** (ok, 656 ms): tool calls: parse_denial_eob
3. **tool parse_denial_eob** (ok, 12 ms): {} -> {"amounts":{"allowed":0.0,"billed":2052.88,"claim_totals":{"allowed":0.0,"billed":2052.88,"paid":0.0,"patient_responsibility":0.0},"denied_amount":2052.88,"paid":0.0,"pat
4. **model turn 2** (ok, 1230 ms): tool calls: retrieve_payer_policy
5. **tool retrieve_payer_policy** (ok, 57 ms): {"cpt": "72148", "denial_code": "CO-50", "denial_text": "The service was not deemed medica -> {"candidates":[{"bm25":17.7565,"policy_id":"MP-IMG-007","title":"Advanced Imaging: Lumbar Spine Mri Medical Necessity","title_exact_match":true,"title_similarity":1.0},{"
6. **model turn 3** (ok, 1576 ms): tool calls: pull_clinical_notes
7. **tool pull_clinical_notes** (ok, 30 ms): {"date_from": "2026-01-01", "date_to": "2026-06-18"} -> {"as_of_date":"2026-08-04","date_from":"2026-01-01","date_to":"2026-06-18","documents":[{"chars":1730,"date":"2026-03-23","date_reason":null,"date_source":"file name","fo
8. **model turn 4** (ok, 2802 ms): tool calls: pull_clinical_notes
9. **tool pull_clinical_notes** (ok, 35 ms): {"paths": ["notes/2026-03-23_pcp.txt", "notes/2026-04-13_pcp_followup.txt", "notes/2026-06 -> {"as_of_date":"2026-08-04","date_from":null,"date_to":"2026-08-04","documents":[{"chars":1730,"date":"2026-03-23","date_reason":null,"date_source":"file name","folder":"n
10. **model turn 5** (ok, 2635 ms): tool calls: assess_appealability
11. **tool assess_appealability** (ok, 84 ms): {"evidence_per_section": 5, "policy_id": "MP-IMG-007"} -> {"action_deadline_rule":"action_deadline = the corrected-claim deadline if you recommend submitting a corrected claim; otherwise the appeal deadline (this also covers a r
12. **model turn 6** (ok, 9569 ms): tool calls: draft_deliverable
13. **tool draft_deliverable** (ok, 7 ms): {"action": "validate_decision", "decision_text": "{\"case_id\": \"C-0005\", \"decision\":  -> {"action":"validate_decision","citations":[],"errors":[],"skeleton":null,"summary":{},"valid":true}
14. **model turn 7** (ok, 743 ms): tool calls: draft_deliverable
15. **tool draft_deliverable** (ok, 139 ms): {"action": "render_skeleton", "kind": "letter"} -> {"action":"render_skeleton","citations":[],"errors":[],"skeleton":"# Appeal Letter: Claim 6268311\n\n**To:** Appeals Unit, P.O. Box 5100, Meridian City, ST 00001\n**From:
16. **model turn 8** (ok, 11081 ms): tool calls: self_check
17. **tool self_check** (ok, 258 ms): {"decision_text": "{\"case_id\": \"C-0005\", \"decision\": \"APPEAL\", \"denial_code\": \" -> {"checks":[{"check":"decision.json matches the schema","detail":"","hint":"","id":"decision_json_valid","pass":true,"severity":"error"},{"check":"deliverable states the c
18. **model turn 9** (ok, 6892 ms): <<<DELIVERABLE>> # Appeal Letter: Claim 6268311 **To:** Appeals Unit, P.O. Box 5100, Meridian City, ST 00001 **From:** Revenue Cycle Appeals, Gutierrez Medical Group **Re
19. **self_check proposal** (ok, 243 ms): ok=True errors=0 warnings=0
20. **self_check final** (ok, 183 ms): ok=True errors=0 warnings=0
21. **run end** (ok, 0 ms): status submitted; turns 9

## Case study C-0030 (agent, agent-p2-r1; truth: DO_NOT_APPEAL)

1. **run start** (ok, 0 ms): run started
2. **model turn 1** (ok, 2176 ms): tool calls: parse_denial_eob
3. **tool parse_denial_eob** (ok, 15 ms): {} -> {"amounts":{"allowed":0.0,"billed":236.93,"claim_totals":{"allowed":0.0,"billed":236.93,"paid":0.0,"patient_responsibility":0.0},"denied_amount":236.93,"paid":0.0,"patien
4. **model turn 2** (ok, 3008 ms): tool calls: retrieve_payer_policy
5. **tool retrieve_payer_policy** (ok, 52 ms): {"cpt": "99213", "denial_code": "CO-29", "denial_text": "The time limit for filing has exp -> {"candidates":[{"bm25":5.1657,"policy_id":"MP-TF-001","title":"Timely Filing of Claims","title_exact_match":true,"title_similarity":1.0},{"bm25":3.8385,"policy_id":"MP-CL
6. **model turn 3** (ok, 1783 ms): tool calls: pull_clinical_notes
7. **tool pull_clinical_notes** (ok, 14 ms): {} -> {"as_of_date":"2026-10-25","date_from":null,"date_to":"2026-10-25","documents":[{"chars":1731,"date":"2026-03-02","date_reason":null,"date_source":"file name","folder":"n
8. **model turn 4** (ok, 618 ms): tool calls: pull_clinical_notes
9. **tool pull_clinical_notes** (ok, 20 ms): {"paths": ["notes/2026-03-02_pcp.txt", "notes/2026-04-01_visit.txt"]} -> {"as_of_date":"2026-10-25","date_from":null,"date_to":"2026-10-25","documents":[{"chars":1731,"date":"2026-03-02","date_reason":null,"date_source":"file name","folder":"n
10. **model turn 5** (ok, 621 ms): tool calls: assess_appealability
11. **tool assess_appealability** (ok, 71 ms): {"policy_id": "MP-TF-001"} -> {"action_deadline_rule":"action_deadline = the corrected-claim deadline if you recommend submitting a corrected claim; otherwise the appeal deadline (this also covers a r
12. **model turn 6** (ok, 9114 ms): tool calls: pull_clinical_notes
13. **tool pull_clinical_notes** (error, 11 ms): {"paths": ["denial_letter.txt", "claim_history.txt"]} -> {"error":{"code":"not_found","message":"'denial_letter.txt' is not a clinical note or supporting document of this case"}}
14. **model turn 7** (ok, 2373 ms): tool calls: pull_clinical_notes
15. **tool pull_clinical_notes** (error, 11 ms): {"paths": ["/sandbox/data/cases/C-0030/docs/denial_letter.txt"]} -> {"error":{"code":"not_found","message":"'/sandbox/data/cases/C-0030/docs/denial_letter.txt' is not a clinical note or supporting document of this case"}}
16. **model turn 8** (ok, 855 ms): tool calls: pull_clinical_notes
17. **tool pull_clinical_notes** (ok, 22 ms): {"include_undated": true} -> {"as_of_date":"2026-10-25","date_from":null,"date_to":"2026-10-25","documents":[{"chars":1731,"date":"2026-03-02","date_reason":null,"date_source":"file name","folder":"n
18. **model turn 9** (ok, 9943 ms): tool calls: draft_deliverable
19. **tool draft_deliverable** (ok, 132 ms): {"action": "render_skeleton", "kind": "memo"} -> {"action":"render_skeleton","citations":[],"errors":[],"skeleton":"# Decision Memo: Claim 3704835\n\n**Review date:** 2026-10-25\n\n## Claim identification\n- Claim numbe
20. **model turn 10** (ok, 12687 ms): tool calls: self_check
21. **tool self_check** (ok, 236 ms): {"decision_text": "{\"case_id\": \"C-0030\", \"decision\": \"DO_NOT_APPEAL\", \"denial_cod -> {"checks":[{"check":"decision.json matches the schema","detail":"","hint":"","id":"decision_json_valid","pass":true,"severity":"error"},{"check":"deliverable states the c
22. **model turn 11** (ok, 33724 ms): <<<DELIVERABLE>>> # Decision Memo: Claim 3704835 **Review date:** 2026-10-25 ## Claim identification - Claim number: 3704835 (source: denial_letter.txt) - Patient ID: P-5
23. **self_check proposal** (ok, 148 ms): ok=True errors=0 warnings=0
24. **self_check final** (ok, 130 ms): ok=True errors=0 warnings=0
25. **run end** (ok, 0 ms): status submitted; turns 11

## Cost and time

- Agent runs: 981125 tokens over 10 runs; baseline: 100542 tokens over 5 runs.
- Judging (grading + both hallucination stages): claude 572,125 prompt + 24,123 completion tokens, gemini 409,025 prompt + 161,235 completion tokens, gpt 359,599 prompt + 115,383 completion tokens.

## Notes and classification (hand-written; included by `scripts/make_run_report.py --notes docs/run_report_notes.md`)

**Baseline decision.json.** In 2 of 5 baseline runs (C-0030, C-0056) `decision.json` is not valid JSON (raw newlines inside strings), so the automatic decision check fails. The decision stated in the baseline's deliverable.md was correct in both (a DO_NOT_APPEAL memo and an appeal letter). The baseline has no `self_check` to catch this; the agent does. Counting these as "decision correct = no" is the rubric's rule, not a judgment about the text.

**Upheld material hallucination flags in the agent runs, classified** (2 of 10 runs are clean-case; 1.3 flags per run):
1. *"NPI" for the missing rendering-provider identifier* (C-0039, both repeats and the baseline): the documents say "rendering provider identifier"; the model wrote "(NPI)". A real but small embellishment: the model added a specific identifier type that no document states.
2. *Sections 2.4 and 2.5 marked "met"* (C-0039, both repeats; 3-4 flags each because the same claim appears in the memo and decision.json): `assess_appealability` lists every requirement section of the policy (diagnosis-supports-procedure, note-documents-diagnosis); the agent filled them all with "met" on weak evidence (the visit note shows a diagnosis, not that it satisfies the payer's edit). A real model weakness, made easier by the skeleton listing sections that are irrelevant to the denial.
3. *"the blank modifier field is flagged as 'may be correct'"* (C-0007, both repeats): the phrase comes from `parse_denial_eob`'s informational `blank_fields` entry, not from any document. The judges (who see only documents) correctly call it unsupported. This is a harness/skill-output issue: the entry is noise. Proposed fix (not applied, to keep the run set consistent): drop the modifier-blank entries from `blank_fields`, or mark them so the model does not quote them.
4. *Single minor items* (C-0005 r2 "payer did not consider the complete record"; C-0030 r2 "within the 90-day window (before 2026-06-30)"): one flag each, plausible model overstatements.

**Failed criteria (a criterion is listed when any judge failed it; the panel majority is in the tables).** Agent: C-0039 EVD2 in both repeats (§2.1 "claim contained all required data elements"): two judges failed it because the memo cites `denial_letter.txt` while the rubric reference names `eob_835.txt`, although the denial letter states the same missing item: a rubric strictness issue rather than a model error. C-0056 RSN2 in both repeats: Gemini wanted the CO-151 reason "in words" and passed only the code and the visit-limit basis; Claude and GPT passed it (judge strictness). C-0005 TRP1 in one repeat (the conflicting therapy-duration note was not called out). C-0007 HON1 in one repeat (the imaging-history documented-absence criterion). Baseline failures are dominated by the invalid decision.json (auto criteria) and by missing trap handling (TRP1 in three cases: it did not notice the conflicting duration note or the short deadline).

**What the numbers do and do not say.** Five dev cases, two repeats, one baseline run, one model, temperature 0.2. The agent's pass-rate advantage is large mainly because the baseline's decision.json failed twice; excluding those two cases the baseline panel pass rates are close to the agent's. The hallucination counts are higher for the agent. Treat both as plumbing validation, not as a measurement of the model.

**First pilot run (kept as raw, not scored).** `runs/agent-p1-r1`, `runs/agent-p1-r2` and `runs/agent-p1-r1/baseline` used the first harness version. A harness bug showed up there (the model closed the answer markers with two brackets instead of three, so one run hit max_turns while self_check never saw the answer; the parser is now tolerant and the prompt states the bracket count), and two self_check heuristics rejected legitimate output (plain-text memos without markdown headings; policy parameter rows such as 7.2 used as criterion ids). Those were fixed, all corruption tests still pass, and the whole set was re-run as `agent-p2`. `runs/smoke-r1` is a single-case smoke run.

