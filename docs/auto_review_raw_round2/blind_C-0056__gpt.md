<!-- reviewer=gpt model=azure/openai/gpt-5.5 time=2026-10-29T18:11:55.704238+00:00 secs=34 usage={"completion_tokens": 3654, "prompt_tokens": 7899, "total_tokens": 11553, "completion_tokens_details": {"reasoning_tokens": 2588}, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "cache_creation_tokens": 0}} -->
{
  "decision": "APPEAL",
  "decision_rationale": "The line is visit 21, exceeding the base 20-visit limit but within visits 21-30. MP-PT-011 permits visits 21-30 when measurable functional improvement and physician recertification are documented. The progress note documents objective functional gains, and the physician recertified continued PT. Corrected claim is not appropriate because the denial was not for missing or invalid claim data. Appeal deadline remains open.",
  "policy_relied_on": [
    "MP-PT-011 - Outpatient Therapy Visit Limits"
  ],
  "governing_deadline": {
    "date": "2026-10-28",
    "governs": "First-level appeal must be received by Halcyon Health Plan",
    "how_computed": "MP-PT-011 Section 7.1 and the denial letter allow 120 days from the claim determination notice dated 2026-06-30; 2026-06-30 plus 120 days is 2026-10-28. The denial letter also states the appeal must be received by 2026-10-28."
  },
  "criteria": [
    {
      "policy_id": "MP-PT-011",
      "section": "2.1",
      "requirement": "Coverage requires the medical record to demonstrate measurable functional improvement resulting from therapy, with objective changes in functional status attributable to treatment.",
      "status": "met",
      "evidence_file": "/sandbox/data/cases/C-0056/docs/supporting/pt_progress_note.txt",
      "evidence_quote": "Functional improvement: lumbar flexion improved from 41 to 66 degrees and sit-to-stand time improved from 20 to 12 seconds."
    },
    {
      "policy_id": "MP-PT-011",
      "section": "2.2",
      "requirement": "The treating physician must have recertified the plan of care for continued therapy services.",
      "status": "met",
      "evidence_file": "/sandbox/data/cases/C-0056/docs/notes/2026-03-26_referral.txt",
      "evidence_quote": "I have reviewed the plan of care and recertify continued physical therapy."
    },
    {
      "policy_id": "MP-PT-011",
      "section": "2.3",
      "requirement": "The provision applies when the denied visit falls within visits 21 through 30 of the calendar year; such visits may be considered when functional improvement is documented and the plan of care is recertified.",
      "status": "met",
      "evidence_file": "/sandbox/data/cases/C-0056/docs/supporting/pt_log.txt",
      "evidence_quote": "Visit 21 | 2026-05-21 | neuromuscular re-education"
    },
    {
      "policy_id": "MP-PT-011",
      "section": "7.5",
      "requirement": "Base outpatient therapy visit limit is 20 visits per calendar year.",
      "status": "unmet",
      "evidence_file": "/sandbox/data/cases/C-0056/docs/supporting/pt_log.txt",
      "evidence_quote": "Visits completed to date: 21"
    },
    {
      "policy_id": "MP-PT-011",
      "section": "7.6",
      "requirement": "Maximum visits with documented functional improvement and a recertified plan of care is 30 visits per calendar year.",
      "status": "met",
      "evidence_file": "/sandbox/data/cases/C-0056/docs/supporting/pt_log.txt",
      "evidence_quote": "Visits completed to date: 21"
    },
    {
      "policy_id": "MP-PT-011",
      "section": "7.1",
      "requirement": "Appeal deadline is 120 days from the claim determination notice.",
      "status": "met",
      "evidence_file": "/sandbox/data/cases/C-0056/docs/denial_letter.txt",
      "evidence_quote": "The appeal must be received by 2026-10-28."
    }
  ],
  "gaps": [
    "No payer benefit accumulator was provided to confirm the member's total calendar-year outpatient therapy visits across all providers; the recommendation relies on King Medical Group's attendance log showing visit 21.",
    "No daily treatment note for the 2026-05-21 visit was provided beyond the claim/EOB and attendance log.",
    "The initial evaluation and progress note are inconsistent on baseline strength: initial evaluation says strength was 4/5, while the progress note says strength is now 4/5, up from 3/5."
  ],
  "test_suspicion": "The denial letter directly identifies the intended policy: \"Medical Policy: Outpatient Therapy Visit Limits\"; the policy library contains the matching title \"OUTPATIENT THERAPY VISIT LIMITS\"."
}
