# Task

Review claim 6479059 for P-7771. Read the denial and remit, find the governing payer policy, check the clinical documentation against it, and check the deadlines. Produce whatever deliverable the situation calls for (appeal letter or decision memo). List anything missing or inconsistent.

Today's date for this review is 2027-03-02.

Case files: /sandbox/data/cases/C-0026/docs/ . Payer policy library: /sandbox/data/policy_library/ .

Output format. Write two files to /sandbox/work/output/C-0026/ :
- deliverable.md: the appeal letter, or a short decision memo. State the source document for each factual statement; list anything you could not verify under "Gaps".
- decision.json: {"decision": one of APPEAL | CORRECT_AND_RESUBMIT | DO_NOT_APPEAL | ESCALATE_MISSING_DOCS, "denial_code", "appeal_deadline", "deadline_ok", "criteria": [{"id" (policy section, e.g. 3.2(a)), "status": met|unmet|unknown, "evidence"}], "enclosures": [], "gaps": []}

SYNTHETIC DATA - NOT REAL PHI
