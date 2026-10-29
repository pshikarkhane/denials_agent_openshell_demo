# Rubric review (host-only)

Two of the five pilot rubrics in full, with the gold deliverable, so you can judge whether the criteria are fair and checkable. `auto` = graded in code (exact match); `judge` = graded by the three-judge panel against the reference. Full results and costs are in `docs/STATUS.md`.

## C-0005: APPEAL

| id | family | check | criterion | reference |
|---|---|---|---|---|
| DEC1 | decision | auto | decision.json states the correct decision | truth.correct_decision=APPEAL |
| IDN1 | identifiers | auto | deliverable.md states the correct claim number, patient ID, date of service and CPT code | 6268311 / P-1862 / 2026-06-18 / 72148 |
| RSN1 | denial_reason | auto | decision.json denial_code matches the denial | CO-50 |
| DLN1 | deadline | auto | decision.json gives the correct action deadline and deadline_ok flag | action_deadline=2027-01-13; deadline_ok=True (review date 2026-08-04) |
| POL1 | policy_citation | auto | decision.json names the governing policy | MP-IMG-007 (Advanced Imaging: Lumbar Spine MRI Medical Necessity) |
| EVD1 | evidence_use | auto | decision.json lists every policy criterion with the correct status | 2.1(a)=met; 2.1(b)=met; 2.1(c)=met |
| POL2 | policy_citation | judge | Cites MP-IMG-007 (Advanced Imaging: Lumbar Spine MRI Medical Necessity) and the specific section number for each criterion it relies on | MP-IMG-007; sections 2.1(a), 2.1(b), 2.1(c) |
| POLX1 | policy_citation | judge | Does not cite or rely on the near-duplicate policy MP-IMG-012 | distractor MP-IMG-012 (wrong service) |
| DLN2 | deadline | judge | States the action deadline and whether it is still open or already passed as of the review date | action_deadline 2027-01-13; review date 2026-08-04; the deadline is still open (162 days remain) |
| EVD2 | evidence_use | judge | Supports §2.1(a) (>=6 weeks conservative therapy) with specific, dated evidence from the record | §2.1(a) status=met, basis=evidence; files: notes/2026-03-23_pcp.txt, supporting/pt_log.txt; record text: Started NSAIDs, a home exercise program and a physical therapy referral at this visit. / Treatment period: 2026-03-23 to 2026-06-04 (73 days) |
| EVD3 | evidence_use | judge | Supports §2.1(b) (Neuro deficit or red flag documented) with specific, dated evidence from the record | §2.1(b) status=met, basis=evidence; files: notes/2026-06-04_ortho.txt; record text: Neurological exam: left leg paresthesias with a positive straight leg raise at 40 degrees |
| HON1 | honesty_about_gaps | judge | Relies on what the record explicitly states for §2.1(c) (No imaging of the same region within 12 months) instead of asserting or omitting it | §2.1(c) status=met, basis=documented_absence; files: notes/2026-06-04_ortho.txt; record text: Imaging history: No prior lumbar imaging on file. |
| REM1 | remedy_and_enclosures | judge | Contains a clear requested remedy (overturn the denial and reprocess the claim) addressed to the payer's appeals unit | claim 6268311; Appeals Unit, P.O. Box 5100, Meridian City, ST 00001 |
| REM2 | remedy_and_enclosures | judge | Lists the required enclosures from the case file | enclosures: supporting/pt_log.txt, notes/2026-06-04_ortho.txt |
| TRP1 | evidence_use | judge | Notices the conflicting statement of therapy duration and resolves it using the PT log | notes/2026-04-13_pcp_followup.txt says about 14 days; PT log: 73 days |

Skipped/trimmed: ['trimmed to 15 criteria: RSN2 Identifies the reason for the denial in words (CO-50) and the basis the payer gave']

**Three things to check:**

1. Evidence criteria (EVD*, HON1) name the exact sentences in the notes. Do they leave room for another valid way to cite the same facts, or are they too tied to one phrasing?
2. HON1 (imaging history): the gold also cites claim_history lines ('none recorded') in support. Those lines are about claim submissions, not imaging. Is that acceptable support, or should the rubric/gold rely only on the ortho note's 'Imaging history' sentence?
3. TRP1 requires resolving the conflicting therapy-duration note by relying on the PT log. Is 'rely on the PT log' the resolution you want, or should flagging the conflict be enough?

### Gold deliverable.md (C-0005)

```markdown
# Appeal of Claim Denial — Claim 6268311

**To:** Appeals Unit, P.O. Box 5100, Meridian City, ST 00001 (source: denial_letter.txt)
**From:** Gutierrez Medical Group (source: claim_history.txt)
**Date of this appeal:** 2026-08-04

## Claim identification
- Claim number: 6268311 (source: denial_letter.txt)
- Patient / Member: Brenda Wilson; Patient ID P-1862; Member ID MBR475438256 (source: denial_letter.txt)
- Date of service: 2026-06-18 (source: denial_letter.txt)
- Service: CPT 72148 — MRI lumbar spine without contrast (source: denial_letter.txt)
- Billed amount: 2052.88 (source: denial_letter.txt)
- Diagnosis: M51.26 (source: eob_835.txt)

## Denial reason
The plan issued an adverse determination on 2026-07-17 with reason code CO-50 (service not deemed medically necessary) and remark code N386, stating the clinical information submitted did not demonstrate that the service met the plan's medical necessity criteria under Medical Policy: Advanced Imaging: Lumbar Spine MRI Medical Necessity (source: denial_letter.txt).

## Remedy requested
We request that Meridian Community Health Plan overturn the denial and reprocess claim 6268311 for payment. The clinical record satisfies every criterion of policy MP-IMG-007 (source: denial_letter.txt; policy MP-IMG-007).

## Policy and evidence

**Policy MP-IMG-007, Section 2.1(a) — at least 6 weeks of conservative therapy completed prior to the request (met).**
The patient began conservative management on 2026-03-23, when NSAIDs, a home exercise program, and a physical therapy referral were started (source: notes/2026-03-23_pcp.txt). The physical therapy attendance log documents a start of care on 2026-03-23 with 21 completed visits over the treatment period 2026-03-23 to 2026-06-04, a span of 73 days (source: supporting/pt_log.txt). This exceeds the 6-week minimum required by Section 2.1(a) (policy MP-IMG-007, Section 2.1(a)).

Note on conflicting documentation: the 2026-04-13 follow-up note states "about 14 days of physical therapy so far" (source: notes/2026-04-13_pcp_followup.txt). This conflicts with the physical therapy attendance log, which is the primary treatment record and documents continuous therapy from 2026-03-23 through 2026-06-04 (73 days, 21 visits) (source: supporting/pt_log.txt). We rely on the PT log, which independently substantiates well more than 6 weeks of conservative therapy.

**Policy MP-IMG-007, Section 2.1(b) — a neurological deficit or recognized red flag finding documented (met).**
The orthopedic consultation of 2026-06-04 documents left leg paresthesias with a positive straight leg raise at 40 degrees and mildly reduced left ankle dorsiflexion strength, with an antalgic gait favoring the left (source: notes/2026-06-04_ortho.txt). These are neurological deficits supporting medical necessity under Section 2.1(b) (policy MP-IMG-007, Section 2.1(b)).

**Policy MP-IMG-007, Section 2.1(c) — no prior imaging of the same lumbar spine region within the preceding 12 months (met).**
The orthopedic consultation note of 2026-06-04 states "No prior lumbar imaging on file" (source: notes/2026-06-04_ortho.txt). The billing system extract also shows no prior adjudicated claims for this service (source: claim_history.txt). This confirms the absence of prior lumbar imaging within the 12-month timeframe required by Section 2.1(c) (policy MP-IMG-007, Section 2.1(c)).

## Deadline
The notice of determination is dated 2026-07-17 and states the appeal must be received by 2027-01-13 (source: denial_letter.txt). As of the review date 2026-08-04, this appeal is being submitted 162 days before the deadline and is therefore timely (source: denial_letter.txt).

## Enclosures
- supporting/pt_log.txt — physical therapy attendance log (source: supporting/pt_log.txt)
- notes/2026-06-04_ortho.txt — orthopedic consultation note (source: notes/2026-06-04_ortho.txt)

## Gaps
- The 2026-04-13 follow-up note's therapy duration ("about 14 days") conflicts with the PT log; we rely on the PT log (source: notes/2026-04-13_pcp_followup.txt; source: supporting/pt_log.txt).
```

### Gold decision.json (C-0005)

```json
{
  "case_id": "C-0005",
  "decision": "APPEAL",
  "denial_code": "CO-50",
  "policy_id": "MP-IMG-007",
  "action_deadline": "2027-01-13",
  "deadline_ok": true,
  "criteria": [
    {
      "id": "2.1(a)",
      "status": "met",
      "evidence": "notes/2026-03-23_pcp.txt"
    },
    {
      "id": "2.1(b)",
      "status": "met",
      "evidence": "notes/2026-06-04_ortho.txt"
    },
    {
      "id": "2.1(c)",
      "status": "met",
      "evidence": "notes/2026-06-04_ortho.txt"
    }
  ],
  "enclosures": [
    "supporting/pt_log.txt",
    "notes/2026-06-04_ortho.txt"
  ],
  "gaps": [
    "2026-04-13 follow-up note states ~14 days of PT, conflicting with PT log (73 days, 21 visits); relied on PT log"
  ]
}
```

## C-0030: DO_NOT_APPEAL

| id | family | check | criterion | reference |
|---|---|---|---|---|
| DEC1 | decision | auto | decision.json states the correct decision | truth.correct_decision=DO_NOT_APPEAL |
| IDN1 | identifiers | auto | deliverable.md states the correct claim number, patient ID, date of service and CPT code | 3704835 / P-5383 / 2026-04-01 / 99213 |
| RSN1 | denial_reason | auto | decision.json denial_code matches the denial | CO-29 |
| DLN1 | deadline | auto | decision.json gives the correct action deadline and deadline_ok flag | action_deadline=2026-11-01; deadline_ok=True (review date 2026-10-25) |
| POL1 | policy_citation | auto | decision.json names the governing policy | MP-TF-001 (Timely Filing of Claims) |
| EVD1 | evidence_use | auto | decision.json lists every policy criterion with the correct status | 2.1=unmet; 2.2=unmet |
| RSN2 | denial_reason | judge | Identifies the reason for the denial in words (CO-29) and the basis the payer gave | CO-29: The time limit for filing has expired. |
| POL2 | policy_citation | judge | Cites MP-TF-001 (Timely Filing of Claims) and the specific section number for each criterion it relies on | MP-TF-001; sections 2.1, 2.2 |
| POLX1 | policy_citation | judge | Does not cite or rely on the near-duplicate policy MP-TF-010 | distractor MP-TF-010 (superseded version) |
| DLN2 | deadline | judge | Shows the timely-filing arithmetic: date of service plus 90 days against the payer received date | DOS 2026-04-01 + 90 days = 2026-06-30; payer received 2026-07-15 |
| EVD2 | evidence_use | judge | States that §2.1 (Claim submitted within 90 days of DOS) is not satisfied and cites the record | §2.1 status=unmet, basis=evidence; files: claim_history.txt; record text: 2026-07-14  Submitted to clearinghouse (submission 1 of 1) |
| HON1 | honesty_about_gaps | judge | Relies on what the record explicitly states for §2.2 (Proof of clearinghouse acceptance within the filing limit is available) instead of asserting or omitting it | §2.2 status=unmet, basis=documented_absence; files: claim_history.txt; record text: Earlier submissions: none recorded |
| REM1 | remedy_and_enclosures | judge | Recommends the correct alternative to an appeal, with a next action, and does not draft an appeal letter | does not appeal; states the filing limit expired and no earlier submission or proof of timely filing is recorded |
| TRP1 | deadline | judge | Recognizes how little time remains before the action deadline and says what must happen before it | 7 days from review date 2026-10-25 to action deadline 2026-11-01 |

Skipped/trimmed: none

**Three things to check:**

1. REM1 expects 'does not appeal ... closes the claim'. For a CO-29 denial is closing/write-off the right business next step, or should the memo say something else (e.g. check whether a clearinghouse record exists elsewhere)?
2. TRP1 (less than 8 days to the deadline) is vague for a DO_NOT_APPEAL case: 'says what must happen before it'. Does it test anything useful here?
3. DLN2 checks the filing arithmetic (DOS + 90 days vs payer received date). Should it also require pointing out that claim_history records the 277CA acceptance on 2026-07-14, which is also late?

### Gold deliverable.md (C-0030)

```markdown
# Decision Memo: Claim 3704835 (Patient P-5383)

**Review date:** 2026-10-25
**Prepared for:** Johnston Medical Group

## Claim identification
- Claim number: 3704835 (source: claim_history.txt)
- Patient ID: P-5383 (source: claim_history.txt)
- Member: Michael Johnson, Member ID MBR284435778 (source: denial_letter.txt)
- Date of service: 2026-04-01 (source: claim_history.txt)
- Service: CPT 99213 – Established patient visit, low (source: claim_history.txt)
- Billed amount: 236.93 (source: denial_letter.txt)

## Denial reason
The payer issued an adverse determination with reason code CO-29 ("The time limit for filing has expired") on 2026-08-03 (source: denial_letter.txt; eob_835.txt). Terravista Health states the claim was received on 2026-07-15, after the 90-day filing limit, and that the filing deadline for this date of service was 2026-06-30 (source: denial_letter.txt).

## Recommendation: DO NOT APPEAL

The denial is correct under the governing policy, and the record does not support an appeal.

**Governing policy:** Timely Filing of Claims, MP-TF-001 (source: governing policy).
- Section 2.1 requires claims to be submitted within 90 days of the date of service (source: governing policy).
- Section 2.2 requires the provider to retain proof of clearinghouse acceptance demonstrating the claim was accepted within the applicable filing limit (source: governing policy).

**Filing arithmetic:**
- Date of service: 2026-04-01 (source: claim_history.txt)
- 2026-04-01 + 90 days = 2026-06-30 (filing deadline) (source: governing policy §2.1/§7.2; denial_letter.txt)
- Payer received the claim: 2026-07-15 — 15 days past the deadline (source: eob_835.txt; denial_letter.txt)

**Section 2.1 – unmet:** The claim history shows the first and only submission to the clearinghouse was on 2026-07-14, accepted by the clearinghouse (277CA) on 2026-07-14, and received by the payer on 2026-07-15. "Earlier submissions: none recorded" and "Prior adjudicated claims for this service: none recorded" (source: claim_history.txt). Because no submission occurred within the 90-day window ending 2026-06-30, the timely-filing requirement is unmet.

**Section 2.2 – unmet:** The only proof of clearinghouse acceptance on file is dated 2026-07-14, which is after the 2026-06-30 filing limit (source: claim_history.txt). There is no documentation showing acceptance within the applicable filing period, so §2.2 cannot be satisfied and there is no basis to overturn the denial on appeal.

With no earlier submission recorded and acceptance occurring after the deadline, an appeal would have no supporting evidence and should not be filed.

## Deadline facts
- Appeal deadline: 90 days from the 2026-08-03 notice; the appeal must be received by 2026-11-01 (source: denial_letter.txt; governing policy §7.1).
- Corrected-claim deadline: within 180 days of the notice, by 2027-01-30 (source: denial_letter.txt; governing policy §7.3).
- As of the 2026-10-25 review date, 7 days remain before the appeal window closes on 2026-11-01.

## Time-sensitivity
Very little time remains before the 2026-11-01 appeal deadline (7 days). Because the recommendation is not to appeal, this decision should be confirmed and closed before the window closes on 2026-11-01. Note that correcting and resubmitting would not cure a timely-filing denial, since the original submission itself fell outside the 90-day limit; no corrected claim is recommended.

## Recommended next action
Do not file an appeal. Confirm and record the DO_NOT_APPEAL decision before 2026-11-01, and close the claim as a timely-filing write-off. Patient responsibility is 0.00 (source: eob_835.txt).

## Gaps
Gaps: none identified

SYNTHETIC DATA - NOT REAL PHI
```

### Gold decision.json (C-0030)

```json
{
  "case_id": "C-0030",
  "decision": "DO_NOT_APPEAL",
  "denial_code": "CO-29",
  "policy_id": "MP-TF-001",
  "action_deadline": "2026-11-01",
  "deadline_ok": true,
  "criteria": [
    {
      "id": "2.1",
      "status": "unmet",
      "evidence": "claim_history.txt"
    },
    {
      "id": "2.2",
      "status": "unmet",
      "evidence": "claim_history.txt"
    }
  ],
  "enclosures": [],
  "gaps": []
}
```

