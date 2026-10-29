# Pilot review pack

Host-only: this page states the correct decisions. Do not mount it. Review the 5 pilot cases and the coding tables below, then tell me what to change before I generate clinical documents for the other 55 cases.

How to read a case: open `data/cases/<id>/task.md` first (that is all the agent is told), then the files listed. `truth.json` is the answer key.

## C-0005: category 1, Medical necessity, record supports

- **Correct decision:** APPEAL   |   **Split:** dev   |   **Traps:** deadline_within_7_days, criterion_no_supporting_doc
- **Denial:** CO-50 / N115   |   **Policy:** MP-IMG-007 (MERIDIAN_COMM, effective 2026-04-15)   |   **Appeal deadline:** 2027-01-05   |   **As-of:** 2027-01-03
- **Criteria:** C1 §3.2(a) = met; C2 §3.2(b) = met; C3 §3.2(c) = met
- **Policy file:** `data/policy_library/MP-IMG-007.txt`
- **Files to read:**
  - `data/cases/C-0005/task.md`
  - `data/cases/C-0005/docs/eob_835.txt`
  - `data/cases/C-0005/docs/denial_letter.txt`
  - `data/cases/C-0005/docs/notes/2026-04-08_pcp.txt`
  - `data/cases/C-0005/docs/notes/2026-06-12_ortho.txt`
  - `data/cases/C-0005/docs/supporting/pt_log.txt`

**Check these:**
1. Conservative therapy: does the PCP note cite a start date of 2026-04-08 and does `supporting/pt_log.txt` show a treatment period of 65 days (policy §3.2(a) needs 42+)? Expected status for C1: **met**.
2. Neuro finding (C2 = **met**): does the ortho note's `Neurological exam:` line record a real deficit, and do the PCP/follow-up notes avoid contradicting it?
3. No prior-imaging document exists. Do none of the notes or letters assert or imply a prior study?

## C-0007: category 2, Medical necessity, record does not support

- **Correct decision:** DO_NOT_APPEAL   |   **Split:** dev   |   **Traps:** notes_disagree_therapy_duration
- **Denial:** CO-50 / N115   |   **Policy:** MP-IMG-007 (MERIDIAN_COMM, effective 2026-04-15)   |   **Appeal deadline:** 2026-11-24   |   **As-of:** 2026-07-07
- **Criteria:** C1 §3.2(a) = unmet; C2 §3.2(b) = met; C3 §3.2(c) = met
- **Policy file:** `data/policy_library/MP-IMG-007.txt`
- **Files to read:**
  - `data/cases/C-0007/task.md`
  - `data/cases/C-0007/docs/eob_835.txt`
  - `data/cases/C-0007/docs/denial_letter.txt`
  - `data/cases/C-0007/docs/notes/2026-03-23_pcp.txt`
  - `data/cases/C-0007/docs/notes/2026-04-13_pcp_followup.txt`
  - `data/cases/C-0007/docs/notes/2026-04-17_ortho.txt`
  - `data/cases/C-0007/docs/supporting/prior_imaging.txt`
  - `data/cases/C-0007/docs/supporting/pt_log.txt`

**Check these:**
1. Conservative therapy: does the PCP note cite a start date of 2026-03-23 and does `supporting/pt_log.txt` show a treatment period of 25 days (policy §3.2(a) needs 42+)? Expected status for C1: **unmet**.
2. Neuro finding (C2 = **met**): does the ortho note's `Neurological exam:` line record a real deficit, and do the PCP/follow-up notes avoid contradicting it?
3. Conflict trap: the `pcp_followup` note says about 7 days of PT, the PT log says otherwise. Is the disagreement visible and realistic rather than absurd?

## C-0030: category 6, Timely filing, expired, no proof

- **Correct decision:** DO_NOT_APPEAL   |   **Split:** dev   |   **Traps:** none
- **Denial:** CO-29   |   **Policy:** MP-TF-001 (TERRAVISTA_HEALTH, effective 2026-03-15)   |   **Appeal deadline:** 2026-11-05   |   **As-of:** 2026-08-31
- **Criteria:** C1 §2.1 = unmet; C2 §2.3 = unmet
- **Policy file:** `data/policy_library/MP-TF-001.txt`
- **Files to read:**
  - `data/cases/C-0030/task.md`
  - `data/cases/C-0030/docs/eob_835.txt`
  - `data/cases/C-0030/docs/denial_letter.txt`
  - `data/cases/C-0030/docs/notes/2026-03-13_pcp.txt`
  - `data/cases/C-0030/docs/notes/2026-04-01_visit.txt`

**Check these:**
1. Filing math: DOS 2026-04-01, limit 90 days, so the deadline is 2026-06-30; the payer received the claim 2026-07-24. Is the denial letter consistent?
2. No proof of timely submission: do the notes avoid any mention of claim submission, billing or a clearinghouse?
3. Anything in the agent-visible files that hints at the answer, or reads unrealistically for a payer/provider document?

## C-0039: category 8, Missing/invalid information or modifier

- **Correct decision:** CORRECT_AND_RESUBMIT   |   **Split:** dev   |   **Traps:** deadline_within_7_days
- **Denial:** CO-16 / MA130   |   **Policy:** MP-CLM-004 (TERRAVISTA_HEALTH, effective 2026-04-05)   |   **Appeal deadline:** 2026-10-25   |   **As-of:** 2026-10-24
- **Criteria:** C1 §3.1 = unmet; C2 §3.4 = met
- **Policy file:** `data/policy_library/MP-CLM-004.txt`
- **Files to read:**
  - `data/cases/C-0039/task.md`
  - `data/cases/C-0039/docs/eob_835.txt`
  - `data/cases/C-0039/docs/denial_letter.txt`
  - `data/cases/C-0039/docs/notes/2026-06-02_pcp.txt`
  - `data/cases/C-0039/docs/notes/2026-06-28_visit.txt`

**Check these:**
1. Missing item: the denial says "place of service code missing". Does the EOB show that item blank/absent (field `place_of_service`)?
2. Visit note: does it document the same service as the claim without adding facts that would change the fix?
3. Deadline trap: task.md says today is 2026-10-24; the appeal deadline is 2026-10-25. Is the remaining time clear and is the correct decision still sensible?

## C-0056: category 12, Frequency / visit-limit exceeded

- **Correct decision:** APPEAL   |   **Split:** dev   |   **Traps:** note_after_dos
- **Denial:** CO-151 / N640   |   **Policy:** MP-PT-011 (HALCYON_PLAN, effective 2026-04-20)   |   **Appeal deadline:** 2026-10-19   |   **As-of:** 2026-07-08
- **Criteria:** C1 §4.2 = met; C2 §4.3 = met; C3 §4.4 = met
- **Policy file:** `data/policy_library/MP-PT-011.txt`
- **Files to read:**
  - `data/cases/C-0056/task.md`
  - `data/cases/C-0056/docs/eob_835.txt`
  - `data/cases/C-0056/docs/denial_letter.txt`
  - `data/cases/C-0056/docs/notes/2026-03-06_initial_eval.txt`
  - `data/cases/C-0056/docs/notes/2026-04-03_referral.txt`
  - `data/cases/C-0056/docs/notes/2026-06-29_followup.txt`
  - `data/cases/C-0056/docs/supporting/pt_log.txt`
  - `data/cases/C-0056/docs/supporting/pt_progress_note.txt`

**Check these:**
1. Visit limit: `supporting/pt_log.txt` shows visit 28 on the date of service. Is that over the limit of 20 and within the exception cap of 30?
2. Exception criteria: does the progress note show measurable functional improvement and does the referral note recertify the plan of care? Is the note content plausible for PT?
3. Post-DOS note (notes/2026-06-29_followup.txt): does it avoid supplying evidence that would only exist after the service?

## Coding review (all 60 cases; mark each line)

Descriptions are my own paraphrases, not AMA/CMS text. **Nothing here has been checked by a coding professional.**

### A. CPT + ICD-10 pairings that are supposed to be valid

- 27447 (Total knee arthroplasty) + M17.11 (Primary OA, right knee)  | categories [3, 11]  | [ ] correct  [ ] incorrect  Notes: 
- 27447 (Total knee arthroplasty) + M17.12 (Primary OA, left knee)  | categories [3, 4]  | [ ] correct  [ ] incorrect  Notes: 
- 29881 (Knee arthroscopy with meniscectomy) + M23.221 (Old meniscus tear, post horn medial, right knee)  | categories [4]  | [ ] correct  [ ] incorrect  Notes: 
- 63030 (Lumbar laminotomy/discectomy) + M51.16 (Disc disorder w/ radiculopathy, lumbar)  | categories [3, 4, 11]  | [ ] correct  [ ] incorrect  Notes: 
- 63030 (Lumbar laminotomy/discectomy) + M51.17 (Disc disorder w/ radiculopathy, lumbosacral)  | categories [4, 11]  | [ ] correct  [ ] incorrect  Notes: 
- 72148 (MRI lumbar spine without contrast) + M51.16 (Disc disorder w/ radiculopathy, lumbar)  | categories [1, 2]  | [ ] correct  [ ] incorrect  Notes: 
- 72148 (MRI lumbar spine without contrast) + M51.17 (Disc disorder w/ radiculopathy, lumbosacral)  | categories [1, 2]  | [ ] correct  [ ] incorrect  Notes: 
- 72148 (MRI lumbar spine without contrast) + M51.26 (Other disc displacement, lumbar)  | categories [1, 2]  | [ ] correct  [ ] incorrect  Notes: 
- 72148 (MRI lumbar spine without contrast) + M54.16 (Radiculopathy, lumbar)  | categories [1]  | [ ] correct  [ ] incorrect  Notes: 
- 72148 (MRI lumbar spine without contrast) + M54.17 (Radiculopathy, lumbosacral)  | categories [1, 2]  | [ ] correct  [ ] incorrect  Notes: 
- 73721 (MRI lower-extremity joint without contrast) + M23.221 (Old meniscus tear, post horn medial, right knee)  | categories [6]  | [ ] correct  [ ] incorrect  Notes: 
- 73721 (MRI lower-extremity joint without contrast) + M23.222 (Old meniscus tear, post horn medial, left knee)  | categories [5, 6]  | [ ] correct  [ ] incorrect  Notes: 
- 73721 (MRI lower-extremity joint without contrast) + M25.561 (Pain in right knee)  | categories [5]  | [ ] correct  [ ] incorrect  Notes: 
- 73721 (MRI lower-extremity joint without contrast) + M25.562 (Pain in left knee)  | categories [10]  | [ ] correct  [ ] incorrect  Notes: 
- 76942 (Ultrasound guidance for needle placement) + M17.12 (Primary OA, left knee)  | categories [9]  | [ ] correct  [ ] incorrect  Notes: 
- 76942 (Ultrasound guidance for needle placement) + M25.562 (Pain in left knee)  | categories [9]  | [ ] correct  [ ] incorrect  Notes: 
- 85025 (Complete blood count with differential) + I10 (Essential hypertension)  | categories [7]  | [ ] correct  [ ] incorrect  Notes: 
- 93000 (ECG with interpretation) + I10 (Essential hypertension)  | categories [11]  | [ ] correct  [ ] incorrect  Notes: 
- 97110 (Therapeutic exercise) + M25.511 (Pain in right shoulder)  | categories [8]  | [ ] correct  [ ] incorrect  Notes: 
- 97110 (Therapeutic exercise) + M25.561 (Pain in right knee)  | categories [12]  | [ ] correct  [ ] incorrect  Notes: 
- 97110 (Therapeutic exercise) + M25.562 (Pain in left knee)  | categories [8, 12]  | [ ] correct  [ ] incorrect  Notes: 
- 97110 (Therapeutic exercise) + M54.16 (Radiculopathy, lumbar)  | categories [10]  | [ ] correct  [ ] incorrect  Notes: 
- 97110 (Therapeutic exercise) + M62.81 (Muscle weakness)  | categories [12]  | [ ] correct  [ ] incorrect  Notes: 
- 97112 (Neuromuscular re-education) + M25.561 (Pain in right knee)  | categories [12]  | [ ] correct  [ ] incorrect  Notes: 
- 97112 (Neuromuscular re-education) + M54.16 (Radiculopathy, lumbar)  | categories [12]  | [ ] correct  [ ] incorrect  Notes: 
- 97140 (Manual therapy) + M51.16 (Disc disorder w/ radiculopathy, lumbar)  | categories [9]  | [ ] correct  [ ] incorrect  Notes: 
- 97140 (Manual therapy) + M54.16 (Radiculopathy, lumbar)  | categories [9]  | [ ] correct  [ ] incorrect  Notes: 
- 99213 (Established patient visit, low) + E78.5 (Hyperlipidemia)  | categories [7]  | [ ] correct  [ ] incorrect  Notes: 
- 99213 (Established patient visit, low) + J02.9 (Acute pharyngitis)  | categories [8]  | [ ] correct  [ ] incorrect  Notes: 
- 99213 (Established patient visit, low) + J06.9 (Acute upper respiratory infection)  | categories [7]  | [ ] correct  [ ] incorrect  Notes: 
- 99213 (Established patient visit, low) + M54.50 (Low back pain, unspecified)  | categories [8]  | [ ] correct  [ ] incorrect  Notes: 
- 99214 (Established patient visit, moderate) + E11.9 (Type 2 diabetes without complications)  | categories [6, 10]  | [ ] correct  [ ] incorrect  Notes: 
- 99214 (Established patient visit, moderate) + I10 (Essential hypertension)  | categories [6, 7, 8, 10]  | [ ] correct  [ ] incorrect  Notes: 
- 99214 (Established patient visit, moderate) + J02.9 (Acute pharyngitis)  | categories [5]  | [ ] correct  [ ] incorrect  Notes: 
- 99214 (Established patient visit, moderate) + J06.9 (Acute upper respiratory infection)  | categories [5]  | [ ] correct  [ ] incorrect  Notes: 
- 99214 (Established patient visit, moderate) + M54.50 (Low back pain, unspecified)  | categories [5, 7]  | [ ] correct  [ ] incorrect  Notes: 

### B. Pairings that are deliberately INVALID (category 11: the diagnosis is inconsistent with the procedure)

- 27447 (Total knee arthroplasty) + J02.9 (Acute pharyngitis)  | [ ] correct  [ ] incorrect  Notes: 
- 63030 (Lumbar laminotomy/discectomy) + D64.9 (Anemia, unspecified)  | [ ] correct  [ ] incorrect  Notes: 
- 63030 (Lumbar laminotomy/discectomy) + J06.9 (Acute upper respiratory infection)  | [ ] correct  [ ] incorrect  Notes: 
- 93000 (ECG with interpretation) + D64.9 (Anemia, unspecified)  | [ ] correct  [ ] incorrect  Notes: 

### C. CARC / RARC pairings by scenario

- CO-11 (The diagnosis is inconsistent with the procedure.) with RARC M76  | scenario(s): Diagnosis inconsistent with procedure  | [ ] correct  [ ] incorrect  Notes: 
- CO-151 (Payment adjusted because the information submitted does not support this many services or this frequency.) with RARC N640  | scenario(s): Frequency / visit-limit exceeded  | [ ] correct  [ ] incorrect  Notes: 
- CO-16 (The claim lacks information needed for adjudication.) with RARC MA130  | scenario(s): Missing/invalid information or modifier  | [ ] correct  [ ] incorrect  Notes: 
- CO-18 (Exact duplicate of a claim/service already adjudicated.) with RARC N522  | scenario(s): Duplicate claim  | [ ] correct  [ ] incorrect  Notes: 
- CO-197 (Precertification/authorization/notification was absent.) with RARC N54  | scenario(s): No prior auth, retro-auth available; No prior auth, not retro-eligible  | [ ] correct  [ ] incorrect  Notes: 
- CO-29 (The time limit for filing has expired.) with RARC none  | scenario(s): Timely filing, proof exists; Timely filing, expired, no proof  | [ ] correct  [ ] incorrect  Notes: 
- CO-4 (The procedure code is inconsistent with the modifier used, or a required modifier is missing.) with RARC M51  | scenario(s): Missing/invalid information or modifier  | [ ] correct  [ ] incorrect  Notes: 
- CO-50 (The service was not deemed medically necessary by the plan.) with RARC N115  | scenario(s): Medical necessity, record supports; Medical necessity, record does not support  | [ ] correct  [ ] incorrect  Notes: 
- CO-97 (The benefit for this service is included in the payment for another service already adjudicated.) with RARC N20  | scenario(s): Bundling / NCCI-style  | [ ] correct  [ ] incorrect  Notes: 
- PR-1 (Amount applied to the patient's deductible.) with RARC none  | scenario(s): Patient responsibility (deductible)  | [ ] correct  [ ] incorrect  Notes: 

### D. Bundling pairs (column 1 code / denied column 2 code, distinct-service modifier 59)

- 20610 (Major joint injection/aspiration) bundled with denied 76942 (Ultrasound guidance for needle placement)  | 2 case(s)  | [ ] correct  [ ] incorrect  Notes: 
- 97110 (Therapeutic exercise) bundled with denied 97140 (Manual therapy)  | 3 case(s)  | [ ] correct  [ ] incorrect  Notes: 

### E. Category / CARC scenario pairings from the spec

- 1. Medical necessity, record supports: CO-50  | [ ] correct  [ ] incorrect  Notes: 
- 2. Medical necessity, record does not support: CO-50  | [ ] correct  [ ] incorrect  Notes: 
- 3. No prior auth, retro-auth available: CO-197  | [ ] correct  [ ] incorrect  Notes: 
- 4. No prior auth, not retro-eligible: CO-197  | [ ] correct  [ ] incorrect  Notes: 
- 5. Timely filing, proof exists: CO-29  | [ ] correct  [ ] incorrect  Notes: 
- 6. Timely filing, expired, no proof: CO-29  | [ ] correct  [ ] incorrect  Notes: 
- 7. Patient responsibility (deductible): PR-1  | [ ] correct  [ ] incorrect  Notes: 
- 8. Missing/invalid information or modifier: CO-4/CO-16  | [ ] correct  [ ] incorrect  Notes: 
- 9. Bundling / NCCI-style: CO-97  | [ ] correct  [ ] incorrect  Notes: 
- 10. Duplicate claim: CO-18  | [ ] correct  [ ] incorrect  Notes: 
- 11. Diagnosis inconsistent with procedure: CO-11  | [ ] correct  [ ] incorrect  Notes: 
- 12. Frequency / visit-limit exceeded: CO-151  | [ ] correct  [ ] incorrect  Notes: 
