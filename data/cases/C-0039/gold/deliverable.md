# Decision Memo: Claim 9475884 (Patient P-6876)

## Claim identification
- Claim number: 9475884 (source: denial_letter.txt)
- Patient ID: P-6876; Member ID: MBR883497256 (source: denial_letter.txt)
- Date of service: 2026-06-29 (source: denial_letter.txt)
- Service/CPT: 99213 – Established patient visit, low (source: denial_letter.txt)
- Payer: Terravista Health (source: denial_letter.txt)
- Review date: 2026-09-02 (source: task)

## Determination
The payer issued an adverse determination on 2026-07-29 with reason code CO-16, "The claim lacks information needed for adjudication" (source: denial_letter.txt). The specific defect is that the rendering provider identifier was missing on the claim (source: denial_letter.txt). The 835 remittance confirms the denial with CO-16 adjustment of 172.84 and shows "Rendering provider: (not provided)" (source: eob_835.txt).

## Missing/invalid item and correction
- Missing item: rendering provider identifier on the claim (source: denial_letter.txt; source: eob_835.txt).
- Correction: resubmit the claim as a corrected claim with the rendering provider identifier populated. The encounter was performed by a provider within Burns Medical Group (source: notes/2026-06-29_visit.txt).

## Governing policy
- Policy: MP-CLM-004, "Claim Submission Requirements, Duplicate Claims and Edit Rules" (source: policy MP-CLM-004).
- Section 2.1: a claim must contain all required data elements at the time of submission; this element was not present as submitted (unmet) (source: policy MP-CLM-004; source: eob_835.txt).
- Section 2.2: a corrected claim may be filed within the payer corrected-claim window (source: policy MP-CLM-004; source: denial_letter.txt).
- Section 3: "An appeal does not cure missing or invalid claim data." When a claim is denied for missing or invalid required information, the provider should submit a corrected claim (source: policy MP-CLM-004).

## Why correct-and-resubmit, not appeal
The denial is for missing required claim data (CO-16), not a coverage or payment dispute (source: denial_letter.txt). Per Section 3 of MP-CLM-004, an appeal does not cure missing or invalid claim data; the correct route is a corrected claim (source: policy MP-CLM-004). The appeal deadline shown on the notice (2026-10-27) is therefore not the governing deadline for this action (source: denial_letter.txt).

## Governing deadline
The corrected claim must be received within 180 days of the date of the notice (source: policy MP-CLM-004, Section 7.3). The notice date is 2026-07-29 (source: denial_letter.txt); 180 days from that notice date is 2027-01-25 (source: denial_letter.txt). As of the review date 2026-09-02, this deadline is met with time remaining (source: task).

## Next action
Burns Medical Group should prepare and submit a corrected claim for claim 9475884 with the rendering provider identifier populated, to be received by Terravista Health no later than 2027-01-25 (source: denial_letter.txt; source: policy MP-CLM-004).

## Gaps
- The specific rendering provider identifier value (e.g., NPI) to enter on the corrected claim is not provided in any case document; the 835 shows "Rendering provider: (not provided)" (source: eob_835.txt).
