# Task

Denial work item: claim 1795064, patient P-8964, payer Terravista Health. The remit, denial notice and chart documents are in the case folder. Work out what the denial is about, check it against the payer's policy library, and recommend a course of action with the supporting paper. Call out missing documentation rather than assuming it exists.

Today's date for this review is 2026-07-01.

Case files: /sandbox/data/cases/C-0046/docs/ . Payer policy library: /sandbox/data/policy_library/ .

Output format. Write two files to /sandbox/work/output/C-0046/ :
- deliverable.md: the appeal letter, or a short decision memo. State the source document for each factual statement; list anything you could not verify under "Gaps".
- decision.json: {"decision": one of APPEAL | CORRECT_AND_RESUBMIT | DO_NOT_APPEAL | ESCALATE_MISSING_DOCS, "denial_code", "action_deadline" (the deadline that governs your recommended action: the corrected-claim deadline if you recommend a corrected claim, otherwise the appeal deadline), "deadline_ok", "criteria": [{"id" (policy section, e.g. 2.1(a)), "status": met|unmet|unknown, "evidence"}], "enclosures": [], "gaps": []}

SYNTHETIC DATA - NOT REAL PHI
