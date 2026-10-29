You are adjudicating possible errors flagged in a healthcare claim-denial work product. All people, payers and data are fictional. For EACH flag below decide independently:
- upheld: true if the flagged claim is really unsupported or wrong given the evidence, false if it is actually supported (by the evidence or by simple arithmetic from it).
- severity (only meaningful if upheld): "material" if the error would mislead a reader on a substantive point: a wrong claim number, code, amount, date or deadline; a policy section that does not exist or says something else; a clinical finding or therapy duration not in the record; an invented document or enclosure; or asserting that a policy criterion is met without evidence. "minor" if it is a real error unlikely to affect the appeal (formatting, trivial misstatement).

EVIDENCE: SOURCE DOCUMENTS, POLICY LIBRARY and FACTS below.

Respond with ONE JSON object and nothing else:
{"adjudications": [{"flag_id": "<id>", "upheld": true | false, "severity": "material" | "minor", "reason": "<short>"}]}
Include every flag id exactly once.

=== DELIVERABLE ===
<<DELIVERABLE>>

=== DECISION ===
<<DECISION>>

=== FLAGS ===
<<FLAGS>>

=== SOURCE DOCUMENTS ===
<<DOCS>>

=== POLICY LIBRARY ===
<<POLICY>>

=== FACTS ===
<<FACTS>>
