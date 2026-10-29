# Task

New denial in the queue: 9127066 (P-3735, Terravista Health). Please figure out whether this is worth pursuing, and if so how. Cite the policy sections and the record for every point, and note where documentation is lacking.

Today's date for this review is 2027-02-09.

Case files: /sandbox/data/cases/C-0036/docs/ . Payer policy library: /sandbox/data/policy_library/ .

Output format. Write two files to /sandbox/work/output/C-0036/ :
- deliverable.md: the appeal letter, or a short decision memo. State the source document for each factual statement; list anything you could not verify under "Gaps".
- decision.json: {"decision": one of APPEAL | CORRECT_AND_RESUBMIT | DO_NOT_APPEAL | ESCALATE_MISSING_DOCS, "denial_code", "action_deadline" (the deadline that governs your recommended action: the corrected-claim deadline if you recommend a corrected claim, otherwise the appeal deadline), "deadline_ok", "criteria": [{"id" (policy section, e.g. 2.1(a)), "status": met|unmet|unknown, "evidence"}], "enclosures": [], "gaps": []}

SYNTHETIC DATA - NOT REAL PHI
