<!-- reviewer=gemini model=gcp/google/gemini-3.1-pro-preview time=2026-10-29T18:11:21.200370+00:00 secs=40 usage={"completion_tokens": 4153, "prompt_tokens": 7784, "total_tokens": 11937, "completion_tokens_details": {"reasoning_tokens": 3668, "text_tokens": 485}, "prompt_tokens_details": {"text_tokens": 7784}} -->
{
  "decision": "DO_NOT_APPEAL",
  "decision_rationale": "The claim was initially submitted to the clearinghouse on 2026-07-14, which is 104 days after the 2026-04-01 date of service. This exceeds Terravista Health's 90-day timely filing limit. Because the billing system indicates no earlier submissions, there is no proof of timely filing available to support an appeal.",
  "policy_relied_on": "MP-TF-001 TIMELY FILING OF CLAIMS",
  "governing_deadline": {
    "date": "2026-11-01",
    "governs": "appeal",
    "how_computed": "90 days from the date of the claim determination notice (2026-08-03), as explicitly stated in the denial letter and in Policy MP-TF-001 Section 7.1."
  },
  "criteria": [
    {
      "policy_id": "MP-TF-001",
      "section": "2.1",
      "requirement": "Providers must submit each claim within 90 days of the date of service.",
      "status": "unmet",
      "evidence_file": "docs/claim_history.txt",
      "evidence_quote": "2026-07-14  Submitted to clearinghouse (submission 1 of 1)"
    },
    {
      "policy_id": "MP-TF-001",
      "section": "2.2",
      "requirement": "Providers must maintain proof of timely filing in the form of clearinghouse acceptance documentation.",
      "status": "unmet",
      "evidence_file": "docs/claim_history.txt",
      "evidence_quote": "Earlier submissions: none recorded"
    }
  ],
  "gaps": [],
  "test_suspicion": "The Medical Record Number prefix explicitly suggests the data is constructed for an exercise: \"MRN: SYN-926375\"."
}
