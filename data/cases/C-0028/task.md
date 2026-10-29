# Task

Claim 7078174 for patient P-9183 was denied (see attached). Review the denial, the payer's policy, and the clinical record. Decide whether we should appeal, correct and resubmit, or not pursue. Prepare the deliverable: an appeal letter if appealing, otherwise a short decision memo. Flag anything missing.

Today's date for this review is 2026-11-19.

Case files: /sandbox/data/cases/C-0028/docs/ . Payer policy library: /sandbox/data/policy_library/ .

Output format. Write two files to /sandbox/work/output/C-0028/ :
- deliverable.md: the appeal letter, or a short decision memo. State the source document for each factual statement; list anything you could not verify under "Gaps".
- decision.json: {"decision": one of APPEAL | CORRECT_AND_RESUBMIT | DO_NOT_APPEAL | ESCALATE_MISSING_DOCS, "denial_code", "appeal_deadline", "deadline_ok", "criteria": [{"id" (policy section, e.g. 3.2(a)), "status": met|unmet|unknown, "evidence"}], "enclosures": [], "gaps": []}

SYNTHETIC DATA - NOT REAL PHI
