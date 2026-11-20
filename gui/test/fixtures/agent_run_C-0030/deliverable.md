# Decision Memo — Denied Claim Review

**Case:** C-0030  
**Claim number:** 3704835  
**Patient ID:** P-5383 (Michael Johnson)  
**Date of service:** 2026-04-01  
**CPT code:** 99213 (Established patient visit, low)  
**ICD-10:** I10  
**Denial code:** CO-29 — The time limit for filing has expired.  
**Payer:** Terravista Health  
**Governing policy:** MP-TF-001, "Timely Filing of Claims" (effective 2026-03-15), sections 2.1 and 2.2  
**Review date:** 2026-10-25  
**Action deadline:** 2026-11-01 (appeal deadline, 90 days from notice date 2026-08-03)  
**Deadline OK:** Yes — review date 2026-10-25 is on or before 2026-11-01.

## Recommendation

**DO_NOT_APPEAL.** The denial should stand. No appeal letter is warranted, and a corrected claim would not change the outcome.

## Reasoning

The payer denied the claim under CARC CO-29 for failure to meet the timely filing requirement (source: denial_letter.txt). The denial notice states the claim was received by the payer on 2026-07-15, after the 90-day filing limit, and that the filing deadline for the date of service was 2026-06-30 (source: denial_letter.txt).

Policy MP-TF-001 §2.1 requires claims to be submitted within 90 days of the date of service (source: MP-TF-001). The date of service was 2026-04-01, so the filing deadline was 2026-06-30 (source: denial_letter.txt; MP-TF-001 §7.2). The claim was submitted to the clearinghouse on 2026-07-14 and accepted the same day; the payer received it on 2026-07-15 (source: claim_history.txt). All of these dates fall after the 2026-06-30 deadline. No earlier submission is recorded (source: claim_history.txt). Therefore §2.1 is unmet.

Policy MP-TF-001 §2.2 requires providers to retain proof of clearinghouse acceptance demonstrating the claim was accepted within the applicable filing limit (source: MP-TF-001). The clearinghouse acceptance occurred on 2026-07-14, which is after the 2026-06-30 filing limit (source: claim_history.txt). That acceptance cannot substantiate timely filing, so §2.2 is unmet.

Because the record confirms the claim was filed after the timely filing deadline and no policy exception applies, the denial is supported by policy and the record. A corrected claim would not alter the filing date, so CORRECT_AND_RESUBMIT is not appropriate. There is no basis to ask the payer to overturn the denial.

## Deadline

The appeal deadline is 2026-11-01 (90 days from the notice date of 2026-08-03), per MP-TF-001 §7.1 and the denial notice (source: denial_letter.txt). The review date of 2026-10-25 is on or before the deadline, so deadline_ok is true. Since we recommend not appealing, no appeal filing is required; the deadline is noted for completeness.

## Next action

Let the denial stand. No appeal and no corrected claim. (Disposition of the billed amount — patient billing or write-off per contract — is outside the scope of this review.)

## Gaps

Gaps: none identified.
<<<DELIVERABLE>>>
