# Task

Claim 1894651 for patient P-5006 was denied. Use the attached documents and the payer's policy library to decide our next step. Be explicit about deadlines and about anything that is missing from the file.

Today's date for this review is 2026-09-07.

Case files: /sandbox/data/cases/C-0060/docs/ . Payer policy library: /sandbox/data/policy_library/ .

Output format. Write two files to /sandbox/work/output/C-0060/ :
- deliverable.md: the appeal letter, or a short decision memo. State the source document for each factual statement; list anything you could not verify under "Gaps".
- decision.json: {"decision": one of APPEAL | CORRECT_AND_RESUBMIT | DO_NOT_APPEAL | ESCALATE_MISSING_DOCS, "denial_code", "appeal_deadline", "deadline_ok", "criteria": [{"id" (policy section, e.g. 3.2(a)), "status": met|unmet|unknown, "evidence"}], "enclosures": [], "gaps": []}

SYNTHETIC DATA - NOT REAL PHI
