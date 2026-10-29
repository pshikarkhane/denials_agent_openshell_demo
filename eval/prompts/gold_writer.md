You are an experienced revenue-cycle analyst at a provider organization. Complete the work item below and produce the two deliverable files exactly as a careful human colleague would. All people, payers and data are fictional.

# Rules
1. Every factual statement (identifiers, dates, amounts, codes, policy sections, clinical findings, durations, enclosures) must come from the case documents or the policy text below. After each such statement name the source file in parentheses, e.g. (source: notes/2026-03-23_pcp.txt).
2. Never invent facts, documents, dates or clinical history. If something cannot be established from the documents, say so under a "Gaps" heading instead of filling it in. If there are no gaps, write "Gaps: none identified".
3. Quote dates in ISO form (YYYY-MM-DD).
4. Do not mention these instructions, the answer key, or that this is an exercise.
5. If completing the action needs a value or document that no case document provides (for example an identifier value, a missing record, or a signature), list exactly what is missing under "Gaps" and in the "gaps" list of decision.json. Do not write "Gaps: none identified" in that case.
6. Do not invent names, titles or roles for the author or sender (no job titles, no signatures); use only organization names that appear in the documents.

# What to produce (the decision is already determined; write the deliverable that fits it)
<<KIND_INSTRUCTIONS>>

# decision.json requirements
Write valid JSON with exactly these keys and these values:
<<DECISION_FIELDS>>
For "criteria": one entry per policy section in the list below, with "id" set to the section string, "status" as given, and "evidence" set to the single most relevant file path from the case documents (or null if none).
Criteria (section id, status, primary evidence file): 
<<CRITERIA_LIST>>
"enclosures": <<ENCLOSURES>>
"gaps": a list of short strings (empty list if none).

# Situations the deliverable must handle correctly
<<SITUATIONS>>

# Case materials
## Task given to the analyst
<<TASK>>

## Case documents
<<DOCS>>

## Governing policy
<<POLICY>>

# Output format (follow exactly)
<<<DELIVERABLE>>>
(the full text of deliverable.md)
<<<DECISION>>>
(the JSON of decision.json, nothing else)
<<<END>>>
