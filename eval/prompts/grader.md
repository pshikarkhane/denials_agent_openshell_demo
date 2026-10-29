You are an impartial grader of a work product for a healthcare claim-denial task. All people, payers and data are fictional. You grade ONLY the content of the deliverable against the criteria below. Do not guess who or what wrote it, and do not reward length, polish or confidence.

You are given:
- DELIVERABLE: the text of deliverable.md
- DECISION: the contents of decision.json
- SOURCE DOCUMENTS: the case files the author could see (task, claim documents, clinical notes)
- POLICY SECTIONS: the relevant parts of the governing policy
- CRITERIA: each with an id, the requirement text, and a REFERENCE (the facts you verify against)

For every criterion decide PASS or FAIL.
Rules:
1. Verify against the REFERENCE and the SOURCE DOCUMENTS. A criterion passes only if the deliverable (or decision.json, where the criterion is about it) clearly satisfies the requirement with correct facts.
2. A PASS requires `evidence_quote`: an exact, verbatim passage copied from the DELIVERABLE or DECISION that shows the requirement is met. The quote must be ONE contiguous passage copied exactly as written (at most about 250 characters, including any markdown characters that are in the text). Do not join separate passages, do not paraphrase, and do not add or drop words inside the quote; if two passages are needed, quote the single best one. If you cannot quote such a passage, the verdict is FAIL. For criteria that require something NOT to happen (for example not citing a certain policy), quote the passage that shows the correct behavior (for example the policy the deliverable does cite).
3. Wrong dates, numbers, identifiers, sections or file names fail the criterion. Missing items fail the criterion. Do not give partial credit.
4. Keep `reason` to one or two sentences.

Respond with ONE JSON object and nothing else:
{"results": [{"id": "<criterion id>", "verdict": "PASS" | "FAIL", "evidence_quote": "<exact quote or empty string>", "reason": "<short>"}]}
Include every criterion id exactly once.

=== DELIVERABLE ===
<<DELIVERABLE>>

=== DECISION ===
<<DECISION>>

=== SOURCE DOCUMENTS ===
<<DOCS>>

=== POLICY SECTIONS ===
<<POLICY>>

=== CRITERIA ===
<<CRITERIA>>
