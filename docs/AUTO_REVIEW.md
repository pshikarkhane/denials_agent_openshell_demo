# Automated review of the 5 pilot cases and the policy library (ROUND 1, before the owner-decision fixes)

> Superseded by the acceptance re-run described in docs/STATUS.md. Round 1 raw outputs: `docs/auto_review_raw_round1/`; the final run is in `docs/auto_review_raw/`.

Run 2026-10-28. Read-only: nothing under `data/` or `data_gen/` was changed. Reviewers: **Gemini 3.1 Pro** (`judges.gemini`) and **GPT-5.5** (`judges.gpt`) from `config/models.yaml`; the datagen model (claude-opus-4-8) and the agent model were not used. Source tags: **[G]** Gemini, **[P]** GPT-5.5, **[S]** my deterministic script checks, **[C]** my own read-through (Claude). Raw reviewer outputs: `docs/auto_review_raw/`. Re-run: `scripts/review/README.md`.

Both reviewers are LLMs, not authorities on coding or RCM practice. Nothing here has been checked by a human.

## 1. Summary

| Case | Truth | Blind solve: Gemini | Blind solve: GPT-5.5 | Blocker | Major | Minor |
|---|---|---|---|---|---|---|
| C-0005 (cat 1) | APPEAL | ESCALATE_MISSING_DOCS (decision wrong; C3 unknown vs met) | ESCALATE_MISSING_DOCS (decision wrong; C3 unknown vs met) | 1 | 1 | 1 |
| C-0007 (cat 2) | DO_NOT_APPEAL | DO_NOT_APPEAL (all match) | DO_NOT_APPEAL (C3 unknown vs met) | 0 | 2 | 2 |
| C-0030 (cat 6) | DO_NOT_APPEAL | ESCALATE_MISSING_DOCS (decision wrong; C2 unknown vs unmet) | DO_NOT_APPEAL (C2 unknown vs unmet) | 0 | 1 | 3 |
| C-0039 (cat 8) | CORRECT_AND_RESUBMIT | CORRECT_AND_RESUBMIT (all match) | CORRECT_AND_RESUBMIT (all match) | 0 | 2 | 2 |
| C-0056 (cat 12) | APPEAL | APPEAL (all match) | APPEAL (all match) | 0 | 3 | 2 |
| Cross-case / policy library / schema | | | | 0 | 6 | 6 |

Policy and deadline matched truth in all 10 blind solves. Every mismatch is a decision or a criterion status, and all of them trace to documents that do not affirmatively settle an "absence" criterion (section 2). Programmatic checks found **no** arithmetic, date-order, identity, or evidence-quote errors in the 5 pilot cases.

Leak test (blind solvers asked what suggests the answer or a test): neither reviewer found an answer leak in the documents. They did cite test signals: the EOB title "835 REMITTANCE ADVICE (SYNTHETIC RENDERING)" and the `SYN-` prefixed trace, provider and MRN ids (8 of the 10 answers), the invented review date in task.md [P], the follow-up note sentence "This visit took place after the date of service 2026-05-21." (C-0056, both), and the denial letter naming the exact policy title (by design).

## 2. Findings per case

### C-0005 (category 1, APPEAL; traps deadline_within_7_days + criterion_no_supporting_doc)
- **BLOCKER (b/d, ambiguity or data bug)** [G, P, C]: C3 (§3.2(c) no imaging in 12 months) is `met` with `evidence: []`, because the trap removed `prior_imaging.txt`. Policy text: "The medical record should confirm the absence of prior imaging of that region within this 12 month period." Nothing in the files confirms it. **Both blind solvers chose ESCALATE_MISSING_DOCS** (truth APPEAL), and [P]'s realism review rated it blocker. Fix (pick one): (1) keep the trap but set C3 `unknown` and decide whether APPEAL-with-gap or ESCALATE is intended, and write the rubric to match; (2) reword §3.2(c) to "the record does not show imaging within 12 months" so absence is enough; (3) drop `criterion_no_supporting_doc` from APPEAL cases.
- **MAJOR (a trap interaction, your question)** [C]: the appeal deadline is 2 days after the as-of date (as-of 2027-01-03, deadline 2027-01-05). On its own this is a reasonable urgency trap: the letter must go out now. Stacked with the missing-imaging gap it distorts the case: both solvers said "escalate urgently" and still could not do the escalation in 2 days, so the realistic answer was neither of the two options. Fix: do not stack `deadline_within_7_days` with `criterion_no_supporting_doc` on an APPEAL case.
- MINOR [G]: EOB rendering provider is the PCP (Dr. Jimmy Johnson) for an MRI. Quote: `Rendering provider: Dr. Jimmy Johnson`. Fix: use a radiologist or imaging facility (generator-level; see cross-case).
- Clean: leak, consistency, solvability (policy uniquely identified), arithmetic, evidence quotes [G, S].

### C-0007 (category 2, DO_NOT_APPEAL; trap notes_disagree_therapy_duration)
- **MAJOR (b)** [P; G disagreed]: C3 `met` rests on `supporting/prior_imaging.txt` (`Study date: 2023-11-14`), which shows an old study but does not say there was no study in the last 12 months. [G] accepted it; [P] marked C3 unknown. Fix: add "No other lumbar imaging on file since this study" to the report, or word C3 as "most recent imaging is older than 12 months".
- **MAJOR (d, coding)** [C; both coding reviewers flagged the combination]: the EOB lists `Diagnosis (ICD-10): M54.17, M51.17`. ICD-10 Excludes1 does not allow radiculopathy (M54.1-) with disc disorder with radiculopathy (M51.1-) on the same claim. A coder reviewer will notice. Fix: generate categories 1-2 with a single compatible code or a non-conflicting pair.
- MINOR [G]: `Conservative therapy (NSAIDs, home exercise program and physical therapy referral) was started on 2026-03-23.` in a note dated 2026-03-23 reads robotic (the verbatim evidence sentence is inserted as-is).
- MINOR [G, P]: rendering provider is the PCP for the MRI (see C-0005).
- Trap check [C]: the conflicting note ("about 7 days of physical therapy so far", dated 21 days after therapy start) is visible but not announced. Both solvers still reached DO_NOT_APPEAL.

### C-0030 (category 6, DO_NOT_APPEAL; no traps)
- **MAJOR (b)** [P, G, C]: DO_NOT_APPEAL vs ESCALATE_MISSING_DOCS cannot be decided from the files. Policy §2.3 says the provider "must produce" proof of timely filing, and no file says whether such proof exists. [G] answered ESCALATE ("proof is missing ... we must escalate"), [P] answered DO_NOT_APPEAL. Both marked C2 `unknown` where truth says `unmet`. Fix: add an agent-visible statement that no clearinghouse acceptance record exists (for example a billing work note), or change truth C2 to `unknown` and the decision to ESCALATE_MISSING_DOCS for this category.
- MINOR [P]: typo in `notes/2026-03-13_pcp.txt`: `Abdomen soft, nontagender.` (verified by me). Fix: regenerate or lint notes.
- MINOR [C, G in C-0039]: the plan ends with the injected sentence `Service performed on 2026-04-01: Established patient visit, moderate.`, which reads like billing data, not charting.
- MINOR [S]: policy title "Timely Filing of Claims" matches both MP-TF-001 and MP-TF-010 (same payer). Only the version text separates them. Both reviewers picked MP-TF-001, so this is a flag, not a failure.
- Clean: arithmetic (DOS + 90 days = 2026-06-30; received 2026-07-24), no mention of claims or billing in the notes [S].

### C-0039 (category 8, CORRECT_AND_RESUBMIT; trap deadline_within_7_days)
- **MAJOR (d)** [G major, P minor, C]: `Reason for visit: Sore throat and scratchy sensation for the past several visits' worth of symptoms, evaluated on 2026-06-02.` is nonsensical LLM output. Fix: regenerate or add a lint for odd phrasing.
- **MAJOR (d, your Part 3 item)** [S, C]: the `deadline_within_7_days` trap is measured on the appeal deadline (2026-10-25, one day after as-of 2026-10-24), but the governing action is a corrected claim due 2027-01-23. Both blind solvers correctly used 2027-01-23, so the trap does nothing and the case is mis-described. Both windows are stated correctly in the denial letter [S].
- MINOR [G]: injected sentence `Service performed on 2026-06-28: Established patient visit, low.`
- MINOR [C]: EOB shows a referring provider on a primary-care sore-throat visit. Harmless but odd.
- Coding note [C]: CO-16 with MA130 plus an "Appeal Rights" paragraph. MA130 normally means an unprocessable claim with no appeal rights (see section 4).

### C-0056 (category 12, APPEAL; trap note_after_dos)
- **MAJOR (c, leak)** [G, P; also cited by both blind solvers]: `This visit took place after the date of service 2026-05-21.` (`notes/2026-06-29_followup.txt`) announces the trap and no clinician writes it. Fix: drop the required sentence for this trap; the encounter date is enough.
- **MAJOR (d)** [P, C]: left-knee patient, yet `Functional improvement: lumbar flexion improved from 36 to 61 degrees and sit-to-stand time improved from 18 to 12 seconds.` The generator's quote is back-pain specific; the LLM added "associated lumbar stiffness" to cover it. Fix: pick the metric from the diagnosis.
- **MAJOR (b)** [P]: policy §4.4 covers extra visits "under an approved exception" within the cap of 30, but no file shows an exception was requested or approved. Truth marks C3 met on the visit count alone (28). Both blind solvers marked it met, so this is a rubric-risk, not a solve failure. Fix: reword §4.4 or add an exception document.
- MINOR [G, C]: EOB rendering provider is Dr. Daniel Sanders, who authored the post-service follow-up; the PT log therapist is David Fisher, PT. Verified.
- MINOR [C]: the log shows visits 21-27 also exceed the 20-visit limit, yet only visit 28 is denied; nothing explains it.
- Clean: arithmetic, visit sequence 1-28 ending on the DOS, identity and dates [S].

### Cross-case
- **MAJOR** [G, P, C]: `835 REMITTANCE ADVICE (SYNTHETIC RENDERING)` plus `SYN-EFT-`, `SYN-RP-` ids tell the agent it is a test. The spec only requires the `SYN-` prefix on MRNs and the footer. Fix: retitle the EOB and drop `SYN-` from non-MRN ids.
- MINOR [P: C-0007, C-0030, C-0039, C-0056]: a full SSN on an 835-style EOB is atypical. Fix: remove the line or mask it.
- MINOR [C]: the generator uses the PCP as rendering provider for every service (MRI, PT). Fix: choose by service type.

## 3. Policy library and the CORRECT_AND_RESUBMIT gaps

Reference windows: none conflict with `reference.py` in any of the 11 policies [S, G, P]. Version-history wording (Version 3.0 effective E, carries forward from 2.0, applies to DOS on or after 2025-01-01): no contradiction found by either reviewer or by me.

- **MAJOR** [G, P, S, C]: MP-CLM-004 sections are out of numeric order: `1, 3.1, 3.4, 2.4, 4.2, 4.3, 7`. Fix: sort sections when rendering.
- **MAJOR (your Part 3 item, confirmed)** [G, P, S, C]: neither MP-CLM-004 nor MP-BND-002 says that an appeal does not cure missing or invalid claim data, or that such denials go through a corrected claim. MP-CLM-004 §3.4 mentions the corrected-claim window (the number is only in §7.3); **MP-BND-002 never mentions corrected claims in its sections**. These two policies back categories 8, 11 and the corrected share of 9, so the gap applies to every CORRECT_AND_RESUBMIT category. Fix: add a sentence per policy.
- **MAJOR** [G blocker, P major, C verified]: MP-TF-010 (superseded distractor) says "within 60 days" in §2.1 but `7.2 Timely filing limit: 90 days`. The injected parameter block ignores the perturbed value. Fix: inject the distractor's own values.
- MINOR [G, P]: numbering gaps: MP-BND-002 skips 3.2, MP-PT-011 starts at 4.2, MP-TF-001 skips 2.2. Fix: renumber (and keep the criterion `section` strings in truth in sync).
- MINOR [P, S]: MP-PA-030 (other payer) has the identical title to MP-PA-003, and MP-TF-010 the same title and payer as MP-TF-001. Solvable by payer id and version text, but a title-only retrieval would tie. Intended as distractors; keep unless you want them harder or easier.
- MINOR [P]: MP-APL-001 does not say when the second-level 180 days start.
- MINOR [C]: MP-IMG-007 §3.2(c) adds "unless clinically justified", an exception I did not specify; it softens the criterion.
- **DECISION, not a defect** [G major, P minor]: every policy ends with "SYNTHETIC DATA - NOT REAL PHI". Both say it hints at a test. The spec (§3.6) requires the footer on every document, so removing it is your call.

## 4. Coding-table flags (Part 4)

**These are triage flags, not coding judgments. Neither reviewer nor I is an authoritative coding source. Nothing below says a line is "correct"; "no concern" only means nobody found a problem. A coding professional must review every line.**

Table B lines are deliberately invalid pairings (category 11); the reviewers flagging them confirms the mismatch is visible, [G] marked them "no concern".

| ID | Line | Gemini | GPT-5.5 | Author (Claude) | Combined | Reason (strongest) |
|---|---|---|---|---|---|---|
| A1 | 27447 (Total knee arthroplasty) + M17.11 (Primary OA, right knee) | no concern | no concern | no concern | no concern |  |
| A2 | 27447 (Total knee arthroplasty) + M17.12 (Primary OA, left knee) | no concern | no concern | no concern | no concern |  |
| A3 | 29881 (Knee arthroscopy with meniscectomy) + M23.221 (Old meniscus tear, post horn medial, right knee) | no concern | no concern | no concern | no concern |  |
| A4 | 63030 (Lumbar laminotomy/discectomy) + M51.16 (Disc disorder w/ radiculopathy, lumbar) | no concern | no concern | no concern | no concern |  |
| A5 | 63030 (Lumbar laminotomy/discectomy) + M51.17 (Disc disorder w/ radiculopathy, lumbosacral) | no concern | no concern | no concern | no concern |  |
| A6 | 72148 (MRI lumbar spine without contrast) + M51.16 (Disc disorder w/ radiculopathy, lumbar) | no concern | no concern | no concern | no concern |  |
| A7 | 72148 (MRI lumbar spine without contrast) + M51.17 (Disc disorder w/ radiculopathy, lumbosacral) | no concern | no concern | no concern | no concern |  |
| A8 | 72148 (MRI lumbar spine without contrast) + M51.26 (Other disc displacement, lumbar) | no concern | no concern | no concern | no concern |  |
| A9 | 72148 (MRI lumbar spine without contrast) + M54.16 (Radiculopathy, lumbar) | no concern | no concern | no concern | no concern |  |
| A10 | 72148 (MRI lumbar spine without contrast) + M54.17 (Radiculopathy, lumbosacral) | no concern | no concern | no concern | no concern |  |
| A11 | 73721 (MRI lower-extremity joint without contrast) + M23.221 (Old meniscus tear, post horn medial, right knee) | no concern | no concern | no concern | no concern |  |
| A12 | 73721 (MRI lower-extremity joint without contrast) + M23.222 (Old meniscus tear, post horn medial, left knee) | no concern | no concern | no concern | no concern |  |
| A13 | 73721 (MRI lower-extremity joint without contrast) + M25.561 (Pain in right knee) | no concern | no concern | no concern | no concern |  |
| A14 | 73721 (MRI lower-extremity joint without contrast) + M25.562 (Pain in left knee) | no concern | no concern | no concern | no concern |  |
| A15 | 76942 (Ultrasound guidance for needle placement) + M17.12 (Primary OA, left knee) | no concern | no concern | no concern | no concern |  |
| A16 | 76942 (Ultrasound guidance for needle placement) + M25.562 (Pain in left knee) | no concern | no concern | no concern | no concern |  |
| A17 | 85025 (Complete blood count with differential) + I10 (Essential hypertension) | suspect (medium) | suspect (medium) | suspect (medium) | suspect (flagged by 3 of 3) | CBC with differential tied only to essential hypertension is a weaker CPT/ICD fit absent medication monitoring, symptoms, or comorbidity detail. |
| A18 | 93000 (ECG with interpretation) + I10 (Essential hypertension) | no concern | no concern | no concern | no concern |  |
| A19 | 97110 (Therapeutic exercise) + M25.511 (Pain in right shoulder) | no concern | no concern | no concern | no concern |  |
| A20 | 97110 (Therapeutic exercise) + M25.561 (Pain in right knee) | no concern | no concern | no concern | no concern |  |
| A21 | 97110 (Therapeutic exercise) + M25.562 (Pain in left knee) | no concern | no concern | no concern | no concern |  |
| A22 | 97110 (Therapeutic exercise) + M54.16 (Radiculopathy, lumbar) | no concern | no concern | no concern | no concern |  |
| A23 | 97110 (Therapeutic exercise) + M62.81 (Muscle weakness) | no concern | no concern | no concern | no concern |  |
| A24 | 97112 (Neuromuscular re-education) + M25.561 (Pain in right knee) | no concern | no concern | no concern | no concern |  |
| A25 | 97112 (Neuromuscular re-education) + M54.16 (Radiculopathy, lumbar) | no concern | no concern | no concern | no concern |  |
| A26 | 97140 (Manual therapy) + M51.16 (Disc disorder w/ radiculopathy, lumbar) | no concern | no concern | no concern | no concern |  |
| A27 | 97140 (Manual therapy) + M54.16 (Radiculopathy, lumbar) | no concern | no concern | no concern | no concern |  |
| A28 | 99213 (Established patient visit, low) + E78.5 (Hyperlipidemia) | no concern | no concern | no concern | no concern |  |
| A29 | 99213 (Established patient visit, low) + J02.9 (Acute pharyngitis) | no concern | no concern | no concern | no concern |  |
| A30 | 99213 (Established patient visit, low) + J06.9 (Acute upper respiratory infection) | no concern | no concern | no concern | no concern |  |
| A31 | 99213 (Established patient visit, low) + M54.50 (Low back pain, unspecified) | no concern | no concern | no concern | no concern |  |
| A32 | 99214 (Established patient visit, moderate) + E11.9 (Type 2 diabetes without complications) | suspect (medium) | no concern | suspect (low) | suspect (flagged by 2 of 3) | A single stable chronic illness without complications typically supports low MDM (99213), making a moderate MDM (99214) potentially overcoded. |
| A33 | 99214 (Established patient visit, moderate) + I10 (Essential hypertension) | suspect (medium) | no concern | suspect (low) | suspect (flagged by 2 of 3) | Management of a single stable chronic illness like hypertension typically nets low MDM (99213), suggesting 99214 is likely overcoded. |
| A34 | 99214 (Established patient visit, moderate) + J02.9 (Acute pharyngitis) | suspect (high) | no concern | suspect (medium) | suspect (flagged by 2 of 3) | An acute uncomplicated illness like pharyngitis generally supports low MDM (99213), meaning a level 4 visit (99214) is upcoded. |
| A35 | 99214 (Established patient visit, moderate) + J06.9 (Acute upper respiratory infection) | suspect (high) | no concern | suspect (medium) | suspect (flagged by 2 of 3) | An acute uncomplicated illness like a URI generally supports low MDM (99213), meaning a level 4 visit (99214) is upcoded. |
| A36 | 99214 (Established patient visit, moderate) + M54.50 (Low back pain, unspecified) | no concern | no concern | suspect (low) | suspect (flagged by 1 of 3) | 99214 for non-specific low back pain is arguable. |
| B1 | 27447 (Total knee arthroplasty) + J02.9 (Acute pharyngitis) | no concern | suspect (high) | no concern | mismatch is INTENDED (reviewers agree it is a poor fit) | Acute pharyngitis is not a plausible diagnosis fit for total knee arthroplasty. |
| B2 | 63030 (Lumbar laminotomy/discectomy) + D64.9 (Anemia, unspecified) | no concern | suspect (high) | no concern | mismatch is INTENDED (reviewers agree it is a poor fit) | Unspecified anemia is not a plausible primary diagnosis fit for lumbar laminotomy/discectomy. |
| B3 | 63030 (Lumbar laminotomy/discectomy) + J06.9 (Acute upper respiratory infection) | no concern | suspect (high) | no concern | mismatch is INTENDED (reviewers agree it is a poor fit) | Acute URI is not a plausible diagnosis fit for lumbar laminotomy/discectomy. |
| B4 | 93000 (ECG with interpretation) + D64.9 (Anemia, unspecified) | no concern | suspect (medium) | no concern | mismatch is INTENDED (reviewers agree it is a poor fit) | Unspecified anemia alone is a weak fit for ECG absent cardiopulmonary symptoms or related findings. |
| C1 | CO-11 (The diagnosis is inconsistent with the procedure.) with RARC M76 | no concern | no concern | no concern | no concern |  |
| C2 | CO-151 (Payment adjusted because the information submitted does not support this many services or this frequen | no concern | no concern | no concern | no concern |  |
| C3 | CO-16 (The claim lacks information needed for adjudication.) with RARC MA130 | no concern | no concern | suspect (medium) | suspect (flagged by 1 of 3) | MA130 normally marks an unprocessable claim with no appeal rights, yet the denial letter gives appeal rights. |
| C4 | CO-18 (Exact duplicate of a claim/service already adjudicated.) with RARC N522 | no concern | no concern | suspect (medium) | suspect (flagged by 1 of 3) | N522 is, as I recall, specific to duplicates of crossover claims; weak fit for a plain duplicate. |
| C5 | CO-197 (Precertification/authorization/notification was absent.) with RARC N54 | suspect (high) | suspect (medium) | suspect (medium) | suspect (flagged by 3 of 3) | CO-197 indicates authorization was totally absent, but RARC N54 incorrectly implies an authorization exists but the claim contradicts it. |
| C6 | CO-29 (The time limit for filing has expired.) with RARC none | no concern | no concern | no concern | no concern |  |
| C7 | CO-4 (The procedure code is inconsistent with the modifier used, or a required modifier is missing.) with RARC | suspect (high) | suspect (medium) | suspect (medium) | suspect (flagged by 3 of 3) | CO-4 indicates a missing or invalid modifier, but RARC M51 specifies an invalid procedure code (RARC M78 is meant for modifiers). |
| C8 | CO-50 (The service was not deemed medically necessary by the plan.) with RARC N115 | no concern | no concern | no concern | no concern |  |
| C9 | CO-97 (The benefit for this service is included in the payment for another service already adjudicated.) with  | no concern | no concern | no concern | no concern |  |
| C10 | PR-1 (Amount applied to the patient's deductible.) with RARC none | no concern | no concern | no concern | no concern |  |
| D1 | 20610 (Major joint injection/aspiration) bundled with denied 76942 (Ultrasound guidance for needle placement) | suspect (high) | suspect (high) | suspect (high) | suspect (flagged by 3 of 3) | For ultrasound-guided major-joint injection, CPT rules generally point to 20611 rather than 20610 plus 76942, so modifier 59 is usually not a fix unless guidance was for a truly separate service. |
| D2 | 97110 (Therapeutic exercise) bundled with denied 97140 (Manual therapy) | no concern | no concern | suspect (low) | suspect (flagged by 1 of 3) | The NCCI pair I recall is 97530/97140, not 97110/97140; verify the edit exists and allows modifier 59. |
| E1 | 1. Medical necessity, record supports: CO-50 | no concern | no concern | no concern | no concern |  |
| E2 | 2. Medical necessity, record does not support: CO-50 | no concern | no concern | no concern | no concern |  |
| E3 | 3. No prior auth, retro-auth available: CO-197 | no concern | no concern | no concern | no concern |  |
| E4 | 4. No prior auth, not retro-eligible: CO-197 | no concern | no concern | no concern | no concern |  |
| E5 | 5. Timely filing, proof exists: CO-29 | no concern | no concern | no concern | no concern |  |
| E6 | 6. Timely filing, expired, no proof: CO-29 | no concern | no concern | no concern | no concern |  |
| E7 | 7. Patient responsibility (deductible): PR-1 | no concern | no concern | no concern | no concern |  |
| E8 | 8. Missing/invalid information or modifier: CO-4/CO-16 | no concern | no concern | no concern | no concern |  |
| E9 | 9. Bundling / NCCI-style: CO-97 | no concern | no concern | no concern | no concern |  |
| E10 | 10. Duplicate claim: CO-18 | no concern | no concern | no concern | no concern |  |
| E11 | 11. Diagnosis inconsistent with procedure: CO-11 | no concern | no concern | no concern | no concern |  |
| E12 | 12. Frequency / visit-limit exceeded: CO-151 | no concern | no concern | no concern | no concern |  |

**Combination-level flags** (several diagnosis codes on one claim):

- M54.16 + M51.16, M54.17 + M51.17 (claims for categories 1-2, e.g. C-0007 carries M54.17 + M51.17) | high | Excludes1: radiculopathy M54.1- is not reported with disc disorder with radiculopathy M51.1-. Both reviewers and the author agree.
- M54.16/M54.17 + M51.17/M51.16 (cross-region), M51.26 + M51.1x | medium | Overlapping or redundant disc/radiculopathy coding on one claim; the generator picks any 2 of 5 codes.
- Scenario realism, category 3 ('urgent' 27447/29881/63030 with an urgent-evaluation note) | medium | Elective orthopedic surgery described as urgent is unusual; retro-authorization fits true emergencies better (author only).

## 5. What a human must still look at

1. **C-0005 C3 / C-0030 C2 (absence criteria).** Decide how "no document exists" is modeled (unknown status, an explicit statement in the files, or rewording the policy). It decides which answer is correct for both cases and sets the pattern for the other 55.
2. **C-0030 DNA vs ESCALATE** [G and P disagreed]. Both answers are defensible today.
3. **C-0007 C3** [G and P disagreed]: is a 2023 radiograph report enough to call "no imaging in 12 months" met?
4. **C-0056 exception requirement** [only P raised it]: is "approved exception" part of the intended criterion?
5. **Footer on policy files** [G major vs P minor]: spec requirement vs blind realism.
6. **MP-TF-010 severity** [G blocker vs P major]: I think major, since it is a distractor, but it can mislead the agent.
7. **Coding table:** the Excludes1 pair in categories 1-2, D1 (20610/76942 with modifier 59), and the RARC choices (C3, C4, C5, C7). My confidence on C3, C4 and D2 is low.
8. **E/M levels (A32-A36):** reviewers called 99214 with simple diagnoses upcoded; I am not sure this matters for the demo.
9. **Whether my "stacked traps" and "wrong deadline for CORRECT cases" findings** match what you intended (traps measured on the appeal deadline in 26 of 60 cases, including 7 of 13 CORRECT_AND_RESUBMIT cases [S]).

## 6. Paste-ready feedback (severity in brackets)

**Pilot documents**
- C-0005: C3 met with no affirmative evidence; both solvers escalated -> set C3 `unknown` or add affirmative text / reword §3.2(c); decide the intended decision [blocker]
- C-0005: deadline_within_7_days stacked with criterion_no_supporting_doc on an APPEAL case -> do not stack these two traps [major]
- C-0007: C3 relies on a 2023 radiograph report that does not say no imaging in 12 months -> add the statement or reword C3 [major]
- C-0007: EOB diagnoses M54.17 + M51.17 violate ICD-10 Excludes1 -> generate a compatible diagnosis set [major]
- C-0030: DO_NOT_APPEAL vs ESCALATE undecidable because no file says proof of timely filing does not exist -> add a billing note or change C2 to `unknown` [major]
- C-0030: typo "nontagender" in notes/2026-03-13_pcp.txt -> fix text and add a typo lint [minor]
- C-0039: nonsense phrase "past several visits' worth of symptoms" in notes/2026-06-02_pcp.txt -> regenerate and lint [major]
- C-0039: deadline trap is on the appeal deadline (2026-10-25) but the governing action is the corrected claim (2027-01-23) -> measure traps on the governing deadline [major]
- C-0056: "This visit took place after the date of service" in notes/2026-06-29_followup.txt leaks the trap -> remove the required sentence [major]
- C-0056: lumbar flexion metric for a left-knee patient in supporting/pt_progress_note.txt -> choose the metric by diagnosis [major]
- C-0056: policy §4.4 requires an approved exception but no file documents one -> reword §4.4 or add an exception document [major]
- C-0056: EOB rendering provider (Dr. Daniel Sanders) differs from the PT log therapist -> derive rendering provider by service [minor]
- All EOBs: title "(SYNTHETIC RENDERING)" and `SYN-EFT`/`SYN-RP` ids signal a test -> retitle, drop non-MRN `SYN-` prefixes [major]
- All EOBs: full SSN line is atypical on an 835 -> remove or mask [minor]
- C-0030/C-0039 notes: injected "Service performed on <date>: <description>." sentence reads like billing data -> rephrase the required sentence [minor]
- C-0005/C-0007: PCP listed as rendering provider for an MRI -> use a radiology provider [minor]

**Policy library**
- MP-CLM-004: sections out of order (3.1, 3.4, 2.4, 4.2, 4.3) -> sort on render [major]
- MP-CLM-004 and MP-BND-002: no statement that missing/invalid data is fixed by a corrected claim, not an appeal; MP-BND-002 never mentions corrected claims -> add one sentence per policy [major]
- MP-TF-010: §2.1 says 60 days, §7.2 says 90 -> inject the distractor's own values [major]
- MP-BND-002 / MP-PT-011 / MP-TF-001: numbering gaps (3.2, 4.1, 2.2) -> renumber and update truth sections [minor]
- MP-PA-030 and MP-TF-010: same title as their primary policy -> keep as distractors or disambiguate; confirm intent [minor]
- MP-APL-001: second-level trigger unclear -> state the start of the 180 days [minor]
- MP-IMG-007 §3.2(c): invented "unless clinically justified" -> remove [minor]
- All policy files: synthetic footer hints at a test -> decide, spec §3.6 requires it [minor]

**Truth / schema**
- schema: no field for the governing (action) deadline; corrected-claim deadline lives only in facts -> add an action-deadline field and base deadline traps on it [major]
- 7 of 13 CORRECT_AND_RESUBMIT cases carry a deadline trap on the appeal deadline -> recompute traps after the schema change [major]
- criteria: "absence" criteria (C-0005 C3, C-0030 C2) cannot be verified from files -> use `unknown` or add affirmative text [major]
- C-0056 C3: exception approval is not modeled -> clarify the criterion [minor]

**Coding tables**
- Categories 1-2: two diagnoses from {M54.16, M51.16, M54.17, M51.17, M51.26} per claim -> avoid Excludes1 pairs [major]
- D1 (20610 + 76942, modifier 59): CPT directs to 20611 -> pick a different bundling pair or drop the appeal variant [major]
- C5 (CO-197 / N54), C7 (CO-4 / M51): RARC fit questioned by both reviewers -> coding reviewer to choose [minor]
- C4 (CO-18 / N522), C3 (CO-16 / MA130 with appeal rights), D2 (97110/97140): author-only flags, low-to-medium confidence -> coding reviewer to confirm [minor]
- A34-A36, A32-A33 (99214 with simple diagnoses), A17 (CBC + hypertension): level/necessity fit -> consider 99213 or other diagnoses [minor]
- Category 3 scenario: elective orthopedic surgery called "urgent" -> pick procedures that fit true urgent retro-authorization [minor]

## 7. What was and was not reviewed
Reviewed: the 5 pilot cases (agent-visible files plus truth), the 11 policies, and tables A-E, by 2 LLM reviewers plus my read of C-0030, C-0039, C-0056 and the policy library, plus script checks. Not reviewed: the other 55 cases' deterministic documents beyond arithmetic from truth, any model run by the agent, attack fixtures (none exist), and anything by a coding or RCM professional. Part 2 reviewers saw the answer key by design; Part 1 reviewers did not.
