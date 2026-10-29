# STATUS (2026-10-28)

## Done this step
- **Step 0:** `ESCALATE_MISSING_DOCS` everywhere (spec §6.5 fixed). Criteria use `status: met|unmet|unknown` (schema, generator, validator, tests); ESCALATE cases carry `unknown`. Python 3.13 pinned (`.python-version`, `requirements.txt` pinned versions). Decisions 2, 4, 7, 8 kept as before.
- **Step 1:** Data Designer spike: works with our endpoint, **NO-GO** for now ([docs/data_designer_spike.md](data_designer_spike.md)). Plain Python + `chat_with_retry` used.
- **Step 2:** `datagen` model = `azure/anthropic/claude-opus-4-8` (not Nemotron; code refuses otherwise). Manifest records model, temperature, per-file sha256 of the prompt-bearing source (no git repo exists, so no git SHA).
- **Step 3:** `eob_835.txt`, `denial_letter.txt`, `task.md` for all 60 cases, deterministic from truth.json + seeded Faker. Every file ends with the synthetic footer.
- **Step 4:** 8 primary + 3 distractor policies (LLM prose, injected windows/ids/dates), frozen, hashed in the manifest.
- **Step 5:** clinical documents for 5 pilot cases only (dev: C-0005 cat 1, C-0007 cat 2, C-0030 cat 6, C-0039 cat 8, C-0056 cat 12). Evidence quotes + line numbers stored in truth.facts.
- **Step 6:** `validate_data` extended (policy library, windows, sections, evidence quotes, leaks, footers, SSN/phone/MRN, mount safety, frozen hashes). [PILOT_REVIEW.md](PILOT_REVIEW.md) written for you.

## Verified
`pytest`: 47 passed (incl. mutation tests proving each new validator fires). `validate_data`: 60 cases, 0 errors, 0 review items. No API key in any file. No clinical docs exist outside the 5 pilot cases (validator enforces).

## Not verified
- **All coding content** (CPT/ICD-10 pairs, CARC/RARC pairs, CARC wording): unreviewed, see PILOT_REVIEW.md tables A–E. Validator only checks consistency with my own table.
- Clinical and policy prose quality is checked by rules (verbatim quotes, allowed dates/codes, no durations/claims words), not by a clinician.
- NemoClaw/OpenShell sandbox: deferred, nothing installed.

## Decisions needed / spec ambiguities (my default in brackets)
1. **`policy_effective_after_dos` trap redefined.** A per-policy effective date is fixed; the trap = DOS before it. The library says requirements "carry forward unchanged from Version 2.0", so the correct policy is still the same document (the agent should note it). If you want a real version switch, the library and truth must model two versions.
2. **as-of date appears in every task.md**, not only deadline_passed cases (otherwise it leaks the trap). Tell me if you disagree.
3. **task.md lists the four decision values** (output format, same in all cases); the leak check allows this only there. `decision.json` criteria `id` = policy section (agent can't see C1/C2).
4. **Denial letters cite the policy by title, not ID**, so retrieval is needed (distractors share titles).
5. **Policy windows** (appeal 90/120/180, filing 90/180/365, corrected-claim 180/365 days) are invented fixed values; the library states them exactly.
6. Cat 6/8 notes: I added a pre-service PCP note to the generator for categories 6 and 8, and an initial-eval note to 12, to meet the "2–5 notes" rule; other categories still have fewer than 2 planned notes in some cases (3, 4, 5, 7, 9, 10, 11). Extend after pilot review.
7. Spec "8 policies + distractors" read as 8 primary + 3 distractors. Datagen model shares a family with the Claude judge (low risk; documents are checked against truth, not graded by it).
8. Pilot cat-2 dev case is DO_NOT_APPEAL (seeded); the ESCALATE_MISSING_DOCS path is generated but has no pilot document.

## Reproduce
```
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m data_gen.gen_cases && .venv/bin/python -m data_gen.render_docs
export NVIDIA_INFERENCE_API_KEY=<rotated key>      # policies/clinical only; files already generated are kept (frozen)
.venv/bin/python -m data_gen.gen_policies && .venv/bin/python -m data_gen.gen_clinical    # --force to regenerate
.venv/bin/python -m data_gen.validate_data && .venv/bin/pytest
.venv/bin/python scripts/make_pilot_review.py
```
Note: re-running `gen_cases` rewrites truth.json without the clinical quotes; re-run the later steps afterwards.

## Automated review of the pilot (2026-10-28; read-only)
- **Report:** [AUTO_REVIEW.md](AUTO_REVIEW.md); raw outputs in `docs/auto_review_raw/`; tooling in `scripts/review/`. Nothing under `data/` or `data_gen/` was changed.
- **Reviewed:** the 5 pilot cases (blind solve + realism/evidence/consistency review, Gemini 3.1 Pro and GPT-5.5), the 11 policies, coding tables A-E, plus script checks and my own read-through (findings labeled by source).
- **Headline:** 5 of 10 blind solves matched truth fully. 3 chose the wrong decision (C-0005 both reviewers, C-0030 Gemini) and 2 had only a criterion-status mismatch (C-0007 and C-0030, GPT). Policy and deadline matched in all 10. Cause: criteria about the *absence* of a document cannot be settled from the files. Also found: a trap-leaking sentence in C-0056, a back-pain metric for a knee patient, a nonsense phrase in C-0039, MP-TF-010 contradicting itself, MP-CLM-004 out of order, no corrected-claim guidance in MP-CLM-004/MP-BND-002, deadline traps measured on the wrong deadline for 7 of 13 CORRECT_AND_RESUBMIT cases, and an Excludes1 diagnosis pair in categories 1-2.
- **Not reviewed:** the other 55 cases' content beyond arithmetic, any real agent run, attack fixtures (none exist), anything by a coding/RCM professional. Reviewers are LLMs and are not authoritative; the coding flags are triage only.
- **Decisions needed from you:** how to model absence criteria (AUTO_REVIEW section 5, items 1-4), whether to keep the synthetic footer on policy files, and whether to fix the generator-level issues (rendering provider, SYN- ids, trap rules) before generating the other 55 cases.
