<!-- reviewer=gemini model=gcp/google/gemini-3.1-pro-preview time=2026-10-28T22:45:42.640310+00:00 secs=48 usage={"completion_tokens": 5354, "prompt_tokens": 7857, "total_tokens": 13211, "completion_tokens_details": {"reasoning_tokens": 4768, "text_tokens": 586}, "prompt_tokens_details": {"text_tokens": 7857}} -->
```json
{
  "decision": "ESCALATE_MISSING_DOCS",
  "decision_rationale": "The claim was denied for timely filing because it was received on 2026-07-24, exceeding the 90-day limit from the 2026-04-01 date of service. To appeal successfully, Terravista Health policy MP-TF-001 Section 2.3 requires documentation demonstrating timely submission, such as a clearinghouse acceptance report. Because this proof is missing from the provided files, we must escalate to obtain it. Without proof of timely submission, the claim cannot be appealed.",
  "policy_relied_on": [
    "MP-TF-001 Timely Filing of Claims"
  ],
  "governing_deadline": {
    "date": "2026-11-05",
    "governs": "appeal",
    "how_computed": "90 days from the notice date of 2026-08-07"
  },
  "criteria": [
    {
      "policy_id": "MP-TF-001",
      "section": "2.1",
      "requirement": "Providers must submit each claim to Terravista Health within 90 days of the date of service",
      "status": "unmet",
      "evidence_file": "docs/denial_letter.txt",
      "evidence_quote": "received on 2026-07-24, after the 90-day filing limit"
    },
    {
      "policy_id": "MP-TF-001",
      "section": "2.3",
      "requirement": "Providers are responsible for retaining documentation that demonstrates a claim was submitted within the required filing window... Acceptable proof of timely filing includes a clearinghouse acceptance report",
      "status": "unknown",
      "evidence_file": null,
      "evidence_quote": null
    }
  ],
  "gaps": [
    "Clearinghouse acceptance report or other proof of initial claim submission to confirm if the claim was originally filed within the 90-day window."
  ],
  "test_suspicion": "The EOB explicitly states '835 REMITTANCE ADVICE (SYNTHETIC RENDERING)' and uses identifiers prefixed with 'SYN-', such as MRN 'SYN-926375', provider ID 'SYN-RP-8115', and trace number 'SYN-EFT-83231976'."
}
```
