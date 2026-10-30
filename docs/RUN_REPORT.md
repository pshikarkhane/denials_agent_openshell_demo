# RUN_REPORT: pre-sandbox agent runs vs no-tools baseline, before and after the fixes

**Pre-sandbox run, 5 dev cases, not a benchmark.** Host-only document (shows truth labels). The agent is a plain tool-calling loop over the six skills on the hosted endpoint; the baseline is the same model, one prompt, no tools. Scored by the judge panel (Gemini 3.1 Pro, Claude Opus 4.8, GPT-5.5) and the two-stage hallucination check. Caveat: the Claude judge is the same model as the document-generation model.

Agent model `nvidia/nvidia/nemotron-3.5-super-text-preview`, temperature 0.2. p3 prompt hash `98bae4c3ddd0`, git `871d52ad` (dirty at run time).

**What changed.** p2 = first final harness (previous report). p3 = after: `parse_denial_eob` no longer emits modifier-blank noise (`blank_fields` became `missing_required`), three prompt rules (apply only relevant sections; `met` needs an evidence file and a fact; never state values no document gives; do not quote tool metadata), a `self_check` warning for `met` without evidence, and for the baseline the same two content rules. The **rubric** was also relaxed (references accept either the EOB or the denial letter for the denial reason and for the category-8 missing item; see `docs/RUBRIC_CHANGES.md`). Rows below separate the two effects: *p2 / old rubric* -> *p2 / new rubric* isolates the rubric change; *p2 / new rubric* -> *p3 / new rubric* isolates the agent changes.

## Agent (with tools)

| configuration | runs | decision correct (auto) | decision.json valid | criterion pass, panel (all) | per judge gem/cla/gpt | content pass (judge criteria only) | per judge content | upheld material / run | clean-run rate | unanimity |
|---|---|---|---|---|---|---|---|---|---|---|
| p2 / old rubric | 10 | 100% | 100% | 97.8% | 96%/99%/97% | 96.0% | 94%/99%/95% | 1.30 | 40% | 94% |
| p2 / new rubric | 10 | 100% | 100% | 98.0% | 97%/99%/98% | 96.5% | 95%/99%/97% | 1.00 | 40% | 96% |
| p3 / new rubric | 15 | 100% | 100% | 98.2% | 96%/100%/98% | 96.9% | 94%/99%/96% | 0.80 | 67% | 94% |

| configuration | tool error rate | malformed calls (tool + final format) | model-call failures | mean turns | mean tool calls | mean tokens | mean seconds | revision rate | repeat SD of pass rate (per case) | same decision across repeats |
|---|---|---|---|---|---|---|---|---|---|---|
| p2 / old rubric | 3.1% | 1 | 1 | 10.1 | 9.7 | 98,112 | 45 | 0% | 0.7% | 5/5 |
| p2 / new rubric | 3.1% | 1 | 1 | 10.1 | 9.7 | 98,112 | 45 | 0% | 2.0% | 5/5 |
| p3 / new rubric | 2.2% | 0 | 1 | 9.0 | 9.0 | 83,995 | 72 | 0% | 0.7% | 5/5 |

## Baseline (no tools)

| configuration | runs | decision correct (auto) | decision.json valid | criterion pass, panel (all) | per judge gem/cla/gpt | content pass (judge criteria only) | per judge content | upheld material / run | clean-run rate | unanimity |
|---|---|---|---|---|---|---|---|---|---|---|
| p2 / old rubric | 5 | 60% | 60% | 78.4% | 75%/81%/74% | 89.9% | 84%/95%/82% | 0.40 | 80% | 82% |
| p2 / new rubric | 5 | 60% | 60% | 79.9% | 71%/81%/78% | 92.4% | 77%/95%/90% | 0.80 | 60% | 80% |
| p3 / new rubric | 10 | 100% | 100% | 95.5% | 90%/96%/96% | 93.2% | 83%/94%/93% | 0.70 | 50% | 86% |

| configuration | tool error rate | malformed calls (tool + final format) | model-call failures | mean turns | mean tool calls | mean tokens | mean seconds | revision rate | repeat SD of pass rate (per case) | same decision across repeats |
|---|---|---|---|---|---|---|---|---|---|---|
| p2 / old rubric | n/a | 1 | 0 | 1.2 | 0.0 | 20,108 | 18 | 0% | n/a | n/a (1 repeat) |
| p2 / new rubric | n/a | 1 | 0 | 1.2 | 0.0 | 20,108 | 18 | 0% | n/a | n/a (1 repeat) |
| p3 / new rubric | n/a | 6 | 0 | 1.6 | 0.0 | 25,315 | 21 | 0% | 3.1% | 5/5 |

Clean-run rate = share of runs with zero upheld material hallucinations. The baseline's `decision.json` validity is reported separately from content scores: **content pass** counts only judge-graded criteria, so an invalid decision.json does not depress it. Containment: 0 violations; path-guard denials are listed below.

## Per case (p3 / new rubric)

| case | truth | variant | run | model decision | decision ok | decision.json valid | panel pass | content pass | upheld material | minor | turns | tools | tokens | s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C-0005 | APPEAL | agent | agent-p3-r1 | APPEAL | yes | yes | 93% | 89% | 0 | 3 | 13 | 12 | 142798 | 41.9 |
| C-0007 | DO_NOT_APPEAL | agent | agent-p3-r1 | DO_NOT_APPEAL | yes | yes | 100% | 100% | 1 | 0 | 9 | 8 | 81466 | 39.2 |
| C-0030 | DO_NOT_APPEAL | agent | agent-p3-r1 | DO_NOT_APPEAL | yes | yes | 93% | 88% | 0 | 0 | 7 | 8 | 51747 | 20.8 |
| C-0039 | CORRECT_AND_RESUBMIT | agent | agent-p3-r1 | CORRECT_AND_RESUBMIT | yes | yes | 100% | 100% | 3 | 0 | 9 | 10 | 82363 | 46.5 |
| C-0056 | APPEAL | agent | agent-p3-r1 | APPEAL | yes | yes | 100% | 100% | 0 | 0 | 10 | 9 | 88853 | 28.7 |
| C-0005 | APPEAL | agent | agent-p3-r2 | APPEAL | yes | yes | 93% | 89% | 0 | 0 | 10 | 9 | 100434 | 54.7 |
| C-0007 | DO_NOT_APPEAL | agent | agent-p3-r2 | DO_NOT_APPEAL | yes | yes | 100% | 100% | 0 | 1 | 8 | 9 | 79158 | 563.0 |
| C-0030 | DO_NOT_APPEAL | agent | agent-p3-r2 | DO_NOT_APPEAL | yes | yes | 100% | 100% | 1 | 0 | 8 | 9 | 65340 | 30.5 |
| C-0039 | CORRECT_AND_RESUBMIT | agent | agent-p3-r2 | CORRECT_AND_RESUBMIT | yes | yes | 100% | 100% | 5 | 2 | 10 | 10 | 104589 | 33.5 |
| C-0056 | APPEAL | agent | agent-p3-r2 | APPEAL | yes | yes | 100% | 100% | 0 | 0 | 10 | 9 | 92160 | 35.0 |
| C-0005 | APPEAL | agent | agent-p3-r3 | APPEAL | yes | yes | 93% | 89% | 0 | 0 | 9 | 8 | 85343 | 46.6 |
| C-0007 | DO_NOT_APPEAL | agent | agent-p3-r3 | DO_NOT_APPEAL | yes | yes | 100% | 100% | 0 | 0 | 7 | 8 | 61109 | 28.8 |
| C-0030 | DO_NOT_APPEAL | agent | agent-p3-r3 | DO_NOT_APPEAL | yes | yes | 100% | 100% | 0 | 0 | 8 | 8 | 61221 | 35.6 |
| C-0039 | CORRECT_AND_RESUBMIT | agent | agent-p3-r3 | CORRECT_AND_RESUBMIT | yes | yes | 100% | 100% | 2 | 2 | 9 | 10 | 97206 | 52.7 |
| C-0056 | APPEAL | agent | agent-p3-r3 | APPEAL | yes | yes | 100% | 100% | 0 | 0 | 8 | 8 | 66131 | 29.6 |
| C-0005 | APPEAL | baseline | baseline-p3-r1 | APPEAL | yes | yes | 100% | 100% | 1 | 0 | 1 | 0 | 16681 | 12.3 |
| C-0007 | DO_NOT_APPEAL | baseline | baseline-p3-r1 | DO_NOT_APPEAL | yes | yes | 100% | 100% | 0 | 0 | 2 | 0 | 32588 | 30.7 |
| C-0030 | DO_NOT_APPEAL | baseline | baseline-p3-r1 | DO_NOT_APPEAL | yes | yes | 93% | 88% | 2 | 0 | 2 | 0 | 28963 | 21.9 |
| C-0039 | CORRECT_AND_RESUBMIT | baseline | baseline-p3-r1 | CORRECT_AND_RESUBMIT | yes | yes | 100% | 100% | 0 | 0 | 2 | 0 | 32201 | 28.6 |
| C-0056 | APPEAL | baseline | baseline-p3-r1 | APPEAL | yes | yes | 100% | 100% | 0 | 1 | 2 | 0 | 29907 | 22.7 |
| C-0005 | APPEAL | baseline | baseline-p3-r2 | APPEAL | yes | yes | 100% | 100% | 1 | 0 | 1 | 0 | 16619 | 16.2 |
| C-0007 | DO_NOT_APPEAL | baseline | baseline-p3-r2 | DO_NOT_APPEAL | yes | yes | 100% | 100% | 0 | 0 | 1 | 0 | 15992 | 12.5 |
| C-0030 | DO_NOT_APPEAL | baseline | baseline-p3-r2 | DO_NOT_APPEAL | yes | yes | 93% | 88% | 1 | 0 | 2 | 0 | 31665 | 27.1 |
| C-0039 | CORRECT_AND_RESUBMIT | baseline | baseline-p3-r2 | CORRECT_AND_RESUBMIT | yes | yes | 69% | 57% | 2 | 1 | 1 | 0 | 14351 | 10.5 |
| C-0056 | APPEAL | baseline | baseline-p3-r2 | APPEAL | yes | yes | 100% | 100% | 0 | 1 | 2 | 0 | 34179 | 28.1 |

## Failed criteria in p3 (any judge)

- agent: C-0005: TRP1, TRP1, TRP1; C-0007: HON1; C-0030: TRP1, RSN2; C-0056: RSN2, RSN2, RSN2
- baseline: C-0005: TRP1; C-0007: RSN2; C-0030: POLX1, TRP1, EVD2, POL2, POLX1, TRP1; C-0039: REM1, EVD1, EVD3, POL2, REM1; C-0056: RSN2, RSN2

## Remaining upheld material hallucination flags (p3 / new rubric)

1. **agent agent-p3-r1 C-0007**: "Section 2.1(b) (neurological deficit or red flag) is unmet: both the PCP and orthopedic notes document no neurological deficit and no red-flag signs or symptoms." | problem: The statement overstates the PCP note. The PCP note documents no red-flag symptoms, but it does not document no neurological deficit; its exam was limited to tenderness and range of motion.
2. **agent agent-p3-r1 C-0039**: "The diagnosis on the claim (M54.50) matches the clinical note (source: notes/2026-06-29_visit.txt; denial_letter.txt)." | problem: The denial letter does not state the diagnosis on the claim.
3. **agent agent-p3-r1 C-0039**: "Status: met. Evidence: notes/2026-06-29_visit.txt — the clinical note documents low back pain, unspecified (M54.50), consistent with CPT 99213 (source: notes/2026-06-29_visit.txt)." | problem: The statement that Section 2.4 is met is not fully supported; the evidence does not include the applicable payer edit or otherwise state that ICD-10 M54.50 supports CPT 99213 under that edit.
4. **agent agent-p3-r1 C-0039**: "{"id":"2.4","status":"met","evidence":"notes/2026-06-29_visit.txt"}" | problem: The decision marks policy criterion 2.4 as met without evidence of the applicable payer edit or a source stating that the billed diagnosis supports the billed procedure under that edit.
5. **agent agent-p3-r2 C-0030**: "Close the claim as denied and consider the billed amount of $236.93 (source: denial_letter.txt) as a contractual write-off per the payer contract." | problem: The billed amount is supported, but the statement that it should be treated as a contractual write-off under the payer contract is unsupported. No payer contract or contractual write-off term is provided.
6. **agent agent-p3-r2 C-0039**: "The clinical note dated 2026-06-29 documents diagnosis M54.50 consistent with CPT 99213 (source: notes/2026-06-29_visit.txt)." | problem: The note documents M54.50, but it does not document the billed CPT 99213 or establish that M54.50 is consistent with CPT 99213 under a payer edit.
7. **agent agent-p3-r2 C-0039**: "Status: met. Evidence: notes/2026-06-29_visit.txt — the office visit note dated 2026-06-29 documents low back pain, unspecified (M54.50), consistent with the billed CPT 99213." | problem: The evidence does not establish that the billed diagnosis supports CPT 99213 according to the applicable payer edit, so the Section 2.4 criterion being met is not supported.
8. **agent agent-p3-r2 C-0039**: "The rendering provider identifier (NPI) is not present in any document received; obtain it from the rendering provider before resubmission." | problem: The evidence supports that a rendering provider identifier is missing, but it does not specify that the required identifier is an NPI.
9. **agent agent-p3-r2 C-0039**: "Rendering provider identifier (NPI) not found in any document; required to complete the corrected claim." | problem: The evidence does not specify that the rendering provider identifier must be an NPI.
10. **agent agent-p3-r2 C-0039**: "{"id": "2.4", "status": "met", "evidence": "notes/2026-06-29_visit.txt"}" | problem: The Section 2.4 status of "met" is not supported by the cited evidence because the note does not establish diagnosis/procedure support according to the applicable payer edit.
11. **agent agent-p3-r3 C-0039**: "The clinical note dated 2026-06-29 documents low back pain, unspecified (M54.50), consistent with the billed diagnosis, supporting Sections 2.4 and 2.5 (source: notes/2026-06-29_vi" | problem: The evidence supports that the note documents M54.50 and that M54.50 was billed, but it does not support the conclusion that Section 2.4 is satisfied according to an applicable payer edit.
12. **agent agent-p3-r3 C-0039**: "{"id":"2.4","status":"met","evidence":"notes/2026-06-29_visit.txt"}" | problem: The decision marks Section 2.4 as met, but the cited evidence does not establish the applicable payer-edit requirement.
13. **baseline baseline-p3-r1 C-0005**: "Patient/Member ID: P-1862 (Brenda Wilson)" | problem: This conflates the patient ID with the member ID. P-1862 is supported as the patient ID, but not as the member ID.
14. **baseline baseline-p3-r1 C-0030**: "MP-CLM-004 is effective 2026-04-05, after the date of service, so it is not the governing policy for this date of service" | problem: The claim incorrectly states that the policy does not apply to the date of service.
15. **baseline baseline-p3-r1 C-0030**: "MP-CLM-004 Section 3 limits corrected claims to missing or invalid required information (source: policy_library/MP-CLM-004.txt)." | problem: This overstates the policy. Section 3 does not say corrected claims are limited only to missing or invalid required information.
16. **baseline baseline-p3-r2 C-0005**: "The physical therapy attendance log documents 21 therapy visits from 2026-03-23 through 2026-06-04" | problem: The last PT visit (visit 21) was on 2026-06-01, not 2026-06-04. 2026-06-04 is the treatment-period end date (ortho visit date), not a therapy visit date.
17. **baseline baseline-p3-r2 C-0030**: "policy_library/MP-CLM-004.txt Section 3 limits corrected claims to missing/invalid required information" | problem: This overstates what the cited policy section says. Section 3 does not state that corrected claims are limited only to missing or invalid required information.
18. **baseline baseline-p3-r2 C-0039**: "Section 7.3 — Corrected claims must be received within 180 days of the date of the notice. Status: met; the denial letter states the corrected claim must be received by 2027-01-25" | problem: The deadline is supported, but the statement that Section 7.3 is already “met” is not supported; there is no evidence that a corrected claim has been received.
19. **baseline baseline-p3-r2 C-0039**: "{"id": "7.3", "status": "met", "evidence": "denial_letter.txt"}" | problem: The evidence supports the corrected-claim deadline, but not that the corrected-claim receipt requirement has been met.

## Containment

Path-guard denials in p3 agent runs: none. No run could read `truth.json`, `rubric.json`, `gold/` or `attacks/` (not in the staged copy).

## Case study C-0005 (agent, agent-p3-r1; truth: APPEAL)

1. **run start** (ok, 0 ms): run started
2. **model turn 1** (ok, 645 ms): tool calls: parse_denial_eob
3. **tool parse_denial_eob** (ok, 17 ms): {} -> {"amounts":{"allowed":0.0,"billed":2052.88,"claim_totals":{"allowed":0.0,"billed":2052.88,"paid":0.0,"patient_responsibility":0.0},"denied_amount":2052.88,"paid":0.0,"pat
4. **model turn 2** (ok, 1590 ms): tool calls: retrieve_payer_policy
5. **tool retrieve_payer_policy** (ok, 44 ms): {"cpt": "72148", "denial_code": "CO-50", "denial_text": "The service was not deemed medica -> {"candidates":[{"bm25":17.7565,"policy_id":"MP-IMG-007","title":"Advanced Imaging: Lumbar Spine Mri Medical Necessity","title_exact_match":true,"title_similarity":1.0},{"
6. **model turn 3** (ok, 645 ms): tool calls: pull_clinical_notes
7. **tool pull_clinical_notes** (ok, 30 ms): {} -> {"as_of_date":"2026-08-04","date_from":null,"date_to":"2026-08-04","documents":[{"chars":1730,"date":"2026-03-23","date_reason":null,"date_source":"file name","folder":"n
8. **model turn 4** (ok, 899 ms): tool calls: pull_clinical_notes
9. **tool pull_clinical_notes** (ok, 29 ms): {"paths": ["notes/2026-03-23_pcp.txt", "notes/2026-04-13_pcp_followup.txt", "notes/2026-06 -> {"as_of_date":"2026-08-04","date_from":null,"date_to":"2026-08-04","documents":[{"chars":1730,"date":"2026-03-23","date_reason":null,"date_source":"file name","folder":"n
10. **model turn 5** (ok, 3176 ms): tool calls: assess_appealability
11. **tool assess_appealability** (ok, 79 ms): {"policy_id": "MP-IMG-007"} -> {"action_deadline_rule":"action_deadline = the corrected-claim deadline if you recommend submitting a corrected claim; otherwise the appeal deadline (this also covers a r
12. **model turn 6** (ok, 9401 ms): tool calls: draft_deliverable
13. **tool draft_deliverable** (ok, 157 ms): {"action": "render_skeleton", "kind": "letter"} -> {"action":"render_skeleton","citations":[],"errors":[],"skeleton":"# Appeal Letter: Claim 6268311\n\n**To:** Appeals Unit, P.O. Box 5100, Meridian City, ST 00001\n**From:
14. **model turn 7** (ok, 5590 ms): tool calls: draft_deliverable
15. **tool draft_deliverable** (ok, 2 ms): {"action": "validate_decision", "decision_text": "{\"case_id\":\"C-0005\",\"decision\":\"A -> {"action":"validate_decision","citations":[],"errors":[],"skeleton":null,"summary":{},"valid":true}
16. **model turn 8** (ok, 2868 ms): tool calls: draft_deliverable
17. **tool draft_deliverable** (ok, 60 ms): {"action": "verify_citations", "decision_text": "{\"case_id\":\"C-0005\",\"decision\":\"AP -> {"action":"verify_citations","citations":[{"kind":"policy_id","pass":true,"reason":"","text":"MP-IMG-007"},{"kind":"source","pass":true,"reason":"","text":"denial_letter.
18. **model turn 9** (ok, 2124 ms): tool calls: pull_clinical_notes
19. **tool pull_clinical_notes** (error, 14 ms): {"paths": ["denial_letter.txt", "eob_835.txt"]} -> {"error":{"code":"not_found","message":"'denial_letter.txt' is not a clinical note or supporting document of this case"}}
20. **model turn 10** (ok, 1150 ms): tool calls: pull_clinical_notes
21. **tool pull_clinical_notes** (ok, 31 ms): {"include_undated": true} -> {"as_of_date":"2026-08-04","date_from":null,"date_to":"2026-08-04","documents":[{"chars":1730,"date":"2026-03-23","date_reason":null,"date_source":"file name","folder":"n
22. **model turn 11** (ok, 5304 ms): tool calls: draft_deliverable
23. **tool draft_deliverable** (ok, 78 ms): {"action": "verify_citations", "decision_text": "{\"case_id\":\"C-0005\",\"decision\":\"AP -> {"action":"verify_citations","citations":[{"kind":"policy_id","pass":true,"reason":"","text":"MP-IMG-007"},{"kind":"source","pass":true,"reason":"","text":"denial_letter.
24. **model turn 12** (ok, 2884 ms): tool calls: self_check
25. **tool self_check** (ok, 287 ms): {"decision_text": "{\"case_id\":\"C-0005\",\"decision\":\"APPEAL\",\"denial_code\":\"CO-50 -> {"checks":[{"check":"decision.json matches the schema","detail":"","hint":"","id":"decision_json_valid","pass":true,"severity":"error"},{"check":"deliverable states the c
26. **model turn 13** (ok, 4004 ms): All checks pass. Here is the final deliverable. <<<DELIVERABLE>>> # Appeal Letter: Claim 6268311 **To:** Appeals Unit, P.O. Box 5100, Meridian City, ST 00001 **From:** Re
27. **self_check proposal** (ok, 271 ms): ok=True errors=0 warnings=0
28. **self_check final** (ok, 176 ms): ok=True errors=0 warnings=0
29. **run end** (ok, 0 ms): status submitted; turns 13

## Case study C-0030 (agent, agent-p3-r1; truth: DO_NOT_APPEAL)

1. **run start** (ok, 0 ms): run started
2. **model turn 1** (ok, 455 ms): tool calls: parse_denial_eob
3. **tool parse_denial_eob** (ok, 16 ms): {} -> {"amounts":{"allowed":0.0,"billed":236.93,"claim_totals":{"allowed":0.0,"billed":236.93,"paid":0.0,"patient_responsibility":0.0},"denied_amount":236.93,"paid":0.0,"patien
4. **model turn 2** (ok, 2117 ms): tool calls: retrieve_payer_policy
5. **tool retrieve_payer_policy** (ok, 64 ms): {"cpt": "99213", "denial_code": "CO-29", "denial_text": "The time limit for filing has exp -> {"candidates":[{"bm25":5.1657,"policy_id":"MP-TF-001","title":"Timely Filing of Claims","title_exact_match":true,"title_similarity":1.0},{"bm25":3.8385,"policy_id":"MP-CL
6. **model turn 3** (ok, 1796 ms): tool calls: pull_clinical_notes, assess_appealability
7. **tool pull_clinical_notes** (ok, 21 ms): {} -> {"as_of_date":"2026-10-25","date_from":null,"date_to":"2026-10-25","documents":[{"chars":1731,"date":"2026-03-02","date_reason":null,"date_source":"file name","folder":"n
8. **tool assess_appealability** (ok, 77 ms): {"policy_id": "MP-TF-001"} -> {"action_deadline_rule":"action_deadline = the corrected-claim deadline if you recommend submitting a corrected claim; otherwise the appeal deadline (this also covers a r
9. **model turn 4** (ok, 1951 ms): tool calls: pull_clinical_notes
10. **tool pull_clinical_notes** (ok, 17 ms): {"paths": ["notes/2026-03-02_pcp.txt", "notes/2026-04-01_visit.txt"]} -> {"as_of_date":"2026-10-25","date_from":null,"date_to":"2026-10-25","documents":[{"chars":1731,"date":"2026-03-02","date_reason":null,"date_source":"file name","folder":"n
11. **model turn 5** (ok, 7605 ms): tool calls: draft_deliverable, draft_deliverable
12. **tool draft_deliverable** (ok, 7 ms): {"action": "validate_decision", "decision_text": "{\"case_id\": \"C-0030\", \"decision\":  -> {"action":"validate_decision","citations":[],"errors":[],"skeleton":null,"summary":{},"valid":true}
13. **tool draft_deliverable** (ok, 74 ms): {"action": "verify_citations", "decision_text": "{\"case_id\": \"C-0030\", \"decision\": \ -> {"action":"verify_citations","citations":[{"kind":"policy_id","pass":true,"reason":"","text":"MP-TF-001"},{"kind":"source","pass":true,"reason":"","text":"denial_letter.t
14. **model turn 6** (ok, 2165 ms): tool calls: self_check
15. **tool self_check** (ok, 250 ms): {"decision_text": "{\"case_id\": \"C-0030\", \"decision\": \"DO_NOT_APPEAL\", \"denial_cod -> {"checks":[{"check":"decision.json matches the schema","detail":"","hint":"","id":"decision_json_valid","pass":true,"severity":"error"},{"check":"deliverable states the c
16. **model turn 7** (ok, 3555 ms): <<<DELIVERABLE>>> # Decision Memo — Denied Claim Review **Case:** C-0030 **Claim number:** 3704835 **Patient ID:** P-5383 (Michael Johnson) **Date of service:** 2026-04-0
17. **self_check proposal** (ok, 230 ms): ok=True errors=0 warnings=0
18. **self_check final** (ok, 160 ms): ok=True errors=0 warnings=0
19. **run end** (ok, 0 ms): status submitted; turns 7

## Cost and time

- p3 agent: 1,259,918 tokens over 15 runs (72 s average); p3 baseline: 253,146 tokens over 10 runs.
- All judging in this report (3 configurations, grading + both hallucination stages): claude 1,989,890 prompt + 84,104 completion tokens, gemini 1,426,161 prompt + 573,913 completion tokens, gpt 1,251,449 prompt + 388,955 completion tokens.

## Reading the before/after table

**Rubric effect only (p2 old rubric -> p2 new rubric, same outputs).** Panel pass rate 97.8% -> 98.0% (agent) and 78.4% -> 79.9% (baseline); content pass 96.0% -> 96.5% and 89.9% -> 92.4%. The relaxation (see `docs/RUBRIC_CHANGES.md`: 51 criteria in 51 of 60 rubrics) was small by design, and the gold deliverables still score 100% with 0 upheld flags (`runs/gold4`). The rubric change did not touch hallucination scoring, yet the upheld-material count moved (agent 1.30 -> 1.00 per run, baseline 0.40 -> 0.80): that is judge sampling noise on identical outputs, roughly +/-0.4 flags per run, so differences of that size in the table are not evidence of anything.

**Agent effect (p2 new rubric -> p3 new rubric).** Agent: pass 98.0% -> 98.2%, upheld material flags 1.00 -> 0.80 per run, clean-run rate 40% -> 67%, tokens 98k -> 84k per run, tool-error rate 3.1% -> 2.2%, no malformed calls; mean seconds rose (45 -> 72) only because one run waited on a 300 s model timeout (563 s). 15 runs (3 repeats) instead of 10. The direction is the intended one but the size is within the noise above; read it as "no regression, probably fewer embellishments", not as a measured gain. Baseline p3 (2 repeats): decision.json was valid in 10 of 10 runs (it was 3 of 5 in p2), which moves its decision-correct rate from 60% to 100%; that is not attributable to the prompt change and could be luck at n=10.

**Remaining upheld material flags in p3 (19 flags: agent 12 in 15 runs, baseline 7 in 10 runs), classified.** None is a harness artefact (the modifier "may be correct" artefact from p2 is gone). 
- *Model embellishment, agent:* #1 (C-0007 r1: says the PCP note documents "no neurological deficit"; the note only limits its exam), #2 (C-0039 r1: cites the denial letter for the claim diagnosis, which is on the EOB), #5 (C-0030 r2: "contractual write-off per the payer contract", no contract in the record), #8-#9 (C-0039 r2: "NPI", a type no document gives; rule 8 reduced but did not remove it).
- *Model embellishment with a judge-strictness caveat, agent:* #3, #4, #6, #7, #10, #11, #12 (C-0039, all three repeats): the agent lists Section 2.4/2.5 as `met` because the visit note records the billed diagnosis. The judges say the evidence does not show the payer's edit is satisfied. The prompt now says to mark `met` only with a file and a fact and to list only applicable sections; the agent still includes 2.4/2.5. One could argue the judges are strict (the note does record the diagnosis), but the policy text asks whether the diagnosis supports the procedure, which the note does not state, so I count these as embellishment.
- *Model embellishment, baseline:* #13 (patient ID presented as member ID), #14 (wrongly says the policy does not apply because its effective date is after the date of service, the opposite of what the policy text says), #15 and #17 (overstates MP-CLM-004 Section 3 as "limiting" corrected claims), #16 (treatment-period end date presented as a visit date).
- *Judge strictness, baseline:* #18-#19 (a corrected-claim window row marked `met` because the deadline is open; arguable either way).
Counts: 17 embellishment (7 of them with the caveat), 2 judge strictness, 0 harness artefact.

**Failed criteria.** Agent p3: TRP1 (trap criteria) in several repeats of C-0005 and once in C-0030, HON1 once (C-0007), RSN2 (denial reason in words) in C-0056 where one judge wants the reason text rather than the code. Baseline p3 failures are concentrated in C-0030 and C-0039 (policy and evidence criteria).

**self_check heuristics that flagged legitimate output.** On the unrevised baseline answers (plain-text letters and memos with `(source: <prose naming a file and quoting it>)` citations): (a) a `source:` parenthetical containing prose was treated as a file name and failed; fixed in this branch (a prose note passes, files it names must exist, quotes are still verified; fake file names still fail; tests updated); (b) `section_remedy` / `section_enclosures` / `section_next_action` fail for letters and memos that put these in numbered or prose sections without a label; not changed, since relaxing it further would weaken the appeal-letter structure check. The agent loop's own proposals passed `self_check` first time in all 15 p3 runs (revision rate 0%).

**What the numbers do and do not say.** Pre-sandbox run, 5 dev cases, not a benchmark: 15 agent runs and 10 baseline runs of one model at temperature 0.2, scored by judges whose own run-to-run noise is of the same size as most differences shown. The consistent findings are qualitative: the agent submits valid, self-checked, correctly decided deliverables on all 15 runs; embellishments persist at about 0.8 material flags per run for the agent and 0.7 for the baseline; and the hallucination pattern is concentrated in a few repeated places (the "NPI" wording, Sections 2.4/2.5 of the claim-edit policy).

