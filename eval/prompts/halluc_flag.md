You are a fact-checker for a healthcare claim-denial work product. All people, payers and data are fictional. Check every verifiable claim in the DELIVERABLE (and DECISION) against the evidence below, and report each claim that is NOT supported.

Verifiable claims include: identifiers (claim number, patient ID, member ID), dates, amounts, codes (CPT, ICD-10, CARC, RARC), deadlines and day counts, policy ids and section numbers and what a section says, clinical findings, treatment durations, names of documents or enclosures, and statements that a criterion is met.

EVIDENCE you may rely on: SOURCE DOCUMENTS (the case files), the POLICY LIBRARY, and FACTS (a table of verified facts). A claim is supported if the evidence states it, or it follows by simple arithmetic from the evidence (for example a deadline computed from a stated date and window). A claim is NOT supported if it contradicts the evidence, or asserts something the evidence does not contain (an invented fact, document, date, finding or enclosure), or asserts that a policy criterion is met without evidence. Opinions, recommendations and plain restatements of the task are not claims. Do not flag a claim only because it is phrased differently from the source.

For each unsupported claim give an exact verbatim quote from the DELIVERABLE (or DECISION), ONE contiguous passage copied exactly (at most about 250 characters, no joined passages), a short statement of what is wrong, and what the evidence actually says. If everything is supported, return an empty list.

Respond with ONE JSON object and nothing else:
{"flags": [{"quote": "<exact verbatim quote>", "problem": "<what is unsupported or wrong>", "evidence": "<what the evidence says or lacks>"}]}

=== DELIVERABLE ===
<<DELIVERABLE>>

=== DECISION ===
<<DECISION>>

=== SOURCE DOCUMENTS ===
<<DOCS>>

=== POLICY LIBRARY ===
<<POLICY>>

=== FACTS ===
<<FACTS>>
