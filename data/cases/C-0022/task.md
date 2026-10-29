# Task

Please look at the denial on claim 6681849 (P-8650). Pull the relevant payer policy and the chart, tell me what we should do about it, and write it up. If we appeal, I need the letter ready to send; if not, a brief memo explaining why.

Today's date for this review is 2026-12-06.

Case files: /sandbox/data/cases/C-0022/docs/ . Payer policy library: /sandbox/data/policy_library/ .

Output format. Write two files to /sandbox/work/output/C-0022/ :
- deliverable.md: the appeal letter, or a short decision memo. State the source document for each factual statement; list anything you could not verify under "Gaps".
- decision.json: {"decision": one of APPEAL | CORRECT_AND_RESUBMIT | DO_NOT_APPEAL | ESCALATE_MISSING_DOCS, "denial_code", "appeal_deadline", "deadline_ok", "criteria": [{"id" (policy section, e.g. 3.2(a)), "status": met|unmet|unknown, "evidence"}], "enclosures": [], "gaps": []}

SYNTHETIC DATA - NOT REAL PHI
