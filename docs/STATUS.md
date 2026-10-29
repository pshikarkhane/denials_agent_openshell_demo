# STATUS (2026-10-29)

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
