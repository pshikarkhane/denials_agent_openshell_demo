# Task

Handle the denial on claim 7780010, patient P-5266. Summarize why it was denied, whether the payer's own policy supports overturning it, and what we should do next. Draft the letter or memo that goes with your recommendation.

Today's date for this review is 2026-07-07.

Case files: /sandbox/data/cases/C-0007/docs/ . Payer policy library: /sandbox/data/policy_library/ .

Output format. Write two files to /sandbox/work/output/C-0007/ :
- deliverable.md: the appeal letter, or a short decision memo. State the source document for each factual statement; list anything you could not verify under "Gaps".
- decision.json: {"decision": one of APPEAL | CORRECT_AND_RESUBMIT | DO_NOT_APPEAL | ESCALATE_MISSING_DOCS, "denial_code", "appeal_deadline", "deadline_ok", "criteria": [{"id" (policy section, e.g. 3.2(a)), "status": met|unmet|unknown, "evidence"}], "enclosures": [], "gaps": []}

SYNTHETIC DATA - NOT REAL PHI
