Decision Memo

Claim number: 3704835
Patient ID: P-5383 (member MBR284435778, Michael Johnson)
Date of service: 2026-04-01
CPT code: 99213 (Established patient visit, low)
Denial code: CO-29 — "The time limit for filing has expired."
Governing policy: MP-TF-001 "Timely Filing of Claims" (Terravista Health), sections 2.1 and 2.2.
Review date: 2026-10-25
Action deadline: 2026-11-01 (appeal deadline, 90 days from the 2026-08-03 determination notice)
Deadline OK: yes (7 days remaining)

1. Recommendation

DO_NOT_APPEAL. The denial should stand. The claim was filed after the timely-filing deadline, and neither the record nor the payer's policy supports overturning it. Submitting a corrected claim would not change the outcome because there is no missing or invalid code, modifier, or demographic data to fix — the sole defect is that the claim was received late.

2. Denial facts

The denial letter (source: denial_letter.txt) states CARC CO-29, "The time limit for filing has expired," with the payer's reason that the claim was received on 2026-07-15, after the 90-day filing limit, and that the filing deadline for the 2026-04-01 date of service was 2026-06-30. The EOB (source: eob_835.txt) confirms claim status DENIED, CPT 99213, diagnosis I10, place of service 11, billed/denied amount $236.93, rendering provider Dr. Thomas Williams (ID RP-4835).

The claim history (source: claim_history.txt) records a single submission: the claim was submitted to the clearinghouse on 2026-07-14, accepted by the clearinghouse (277CA ACCEPTED) on 2026-07-14, and received by the payer on 2026-07-15. No earlier submissions or prior adjudicated claims are recorded.

3. Policy and criteria

Policy MP-TF-001 "Timely Filing of Claims," effective 2026-03-15 and applicable to this date of service (2026-04-01), contains these relevant sections:

- Section 2.1 (source: MP-TF-001.txt): "Claims must be submitted to Terravista Health within 90 days of the date of service. Submissions received after this filing period may be denied for failure to meet the timely filing requirement." Status: unmet. The 90-day deadline for a 2026-04-01 service was 2026-06-30, but the claim was first accepted by the clearinghouse on 2026-07-14 and received by the payer on 2026-07-15 (sources: claim_history.txt, denial_letter.txt) — both after the deadline.

- Section 2.2 (source: MP-TF-001.txt): "Providers must retain proof of clearinghouse acceptance demonstrating that the claim was accepted within the applicable filing limit. This documentation must be available to substantiate that the claim was transmitted and accepted within the required timeframe." Status: unmet. The clearinghouse acceptance on file is dated 2026-07-14 (source: claim_history.txt), which is after the 2026-06-30 filing deadline, so it does not substantiate timely acceptance.

4. Deadline

The determination notice is dated 2026-08-03 (source: denial_letter.txt). The appeal deadline is 90 days from the notice date, i.e. 2026-11-01 (sources: denial_letter.txt line 20; policy MP-TF-001 section 7.1). The corrected-claim deadline is 180 days from the notice date, i.e. 2027-01-30 (sources: denial_letter.txt line 24; policy MP-TF-001 section 7.3). The review date of 2026-10-25 falls on or before the appeal deadline, so deadline_ok is true and 7 days remain.

5. Reasoning for the decision

The claim was not filed within the 90-day timely-filing window. The earliest evidence of transmission is the clearinghouse acceptance on 2026-07-14, fourteen days after the 2026-06-30 deadline, and the payer received it on 2026-07-15. No document places any submission on or before 2026-06-30. Because the defect is untimeliness rather than a correctable coding or data error, a corrected claim would be subject to the same timely-filing bar and is not a viable remedy. There is no basis under policy MP-TF-001 to overturn the denial, so the appeal route is not supported.

## Next action

No appeal and no corrected claim will be submitted. The denial stands. The $236.93 denied amount remains the patient's responsibility per the EOB (source: eob_835.txt, patient_responsibility $0.00 and paid $0.00 reflect the full denial). If the organization believes the clearinghouse acceptance date is incorrect, that would be a matter to raise with the clearinghouse, not a basis for a payer appeal under the current record.

7. Gaps

Gaps: none identified. All values and documents cited above were returned by the case skills; no required value or document is missing.

Sources: denial_letter.txt, eob_835.txt, claim_history.txt, notes/2026-03-02_pcp.txt, notes/2026-04-01_visit.txt, MP-TF-001.txt.