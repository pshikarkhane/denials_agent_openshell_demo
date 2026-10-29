<!-- reviewer=gpt model=azure/openai/gpt-5.5 time=2026-10-28T22:46:37.824959+00:00 secs=33 usage={"completion_tokens": 3065, "prompt_tokens": 8452, "total_tokens": 11517, "completion_tokens_details": {"reasoning_tokens": 2070}, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "cache_creation_tokens": 0}} -->
{
  "decision": "APPEAL",
  "decision_rationale": "The denial is for exceeding the 20-visit outpatient therapy limit, but Halcyon policy allows coverage up to 30 visits with documented exception criteria. The denied DOS was visit 28, with measurable functional improvement and physician recertification documented. This is not a coding or corrected-claim issue. Appeal is timely as of 2026-07-08.",
  "policy_relied_on": "MP-PT-011 - OUTPATIENT THERAPY VISIT LIMITS",
  "governing_deadline": {
    "date": "2026-10-19",
    "governs": "First-level appeal receipt deadline for claim denial",
    "how_computed": "Denial notice dated 2026-06-21 states appeals must be requested within 120 days and received by 2026-10-19; MP-PT-011 Section 7.1 also states appeal deadline is 120 days from the claim determination notice."
  },
  "criteria": [
    {
      "policy_id": "MP-PT-011",
      "section": "7.5",
      "requirement": "Outpatient therapy visit limit is 20 visits per calendar year.",
      "status": "unmet",
      "evidence_file": "docs/supporting/pt_log.txt",
      "evidence_quote": "Visit 28 | 2026-05-21 | therapeutic exercise"
    },
    {
      "policy_id": "MP-PT-011",
      "section": "4.2",
      "requirement": "Clinical record must document measurable functional improvement attributable to the services provided, with objective and comparable findings showing meaningful progress.",
      "status": "met",
      "evidence_file": "docs/supporting/pt_progress_note.txt",
      "evidence_quote": "Patient demonstrates meaningful progress toward established goals with improved range, strength, and functional mobility."
    },
    {
      "policy_id": "MP-PT-011",
      "section": "4.3",
      "requirement": "Supervising physician must recertify the plan of care at plan-specified intervals and confirm ongoing therapy remains appropriate.",
      "status": "met",
      "evidence_file": "docs/notes/2026-04-03_referral.txt",
      "evidence_quote": "I recertify the physical therapy plan of care as of 2026-04-03."
    },
    {
      "policy_id": "MP-PT-011",
      "section": "4.4",
      "requirement": "Additional therapy under an approved exception is available only when the cumulative visit count remains within the exception cap of 30.",
      "status": "met",
      "evidence_file": "docs/supporting/pt_log.txt",
      "evidence_quote": "Visits completed to date: 28"
    },
    {
      "policy_id": "MP-PT-011",
      "section": "7.6",
      "requirement": "Visit cap with documented exception is 30 visits per calendar year.",
      "status": "met",
      "evidence_file": "docs/supporting/pt_log.txt",
      "evidence_quote": "Treatment period: 2026-03-06 to 2026-05-21"
    },
    {
      "policy_id": "MP-PT-011",
      "section": "7.1",
      "requirement": "Appeal deadline is 120 days from the date of the claim determination notice.",
      "status": "met",
      "evidence_file": "docs/denial_letter.txt",
      "evidence_quote": "The appeal must be received by 2026-10-19."
    }
  ],
  "gaps": [
    "No separate document explicitly showing Halcyon pre-approved or formally granted an outpatient therapy exception; available records support requesting/applying the documented exception.",
    "No detailed PT treatment note for the exact denied DOS 2026-05-21 beyond the attendance log entry.",
    "Progress note includes lumbar stiffness and lumbar flexion metrics, while the claim diagnosis and main therapy records identify left knee pain M25.562.",
    "EOB lists rendering provider as Dr. Daniel Sanders, while PT attendance/progress documentation lists David Fisher, PT as therapist."
  ],
  "test_suspicion": "The denial points directly to the matching policy: \"Medical Policy: Outpatient Therapy Visit Limits\" and the library contains \"OUTPATIENT THERAPY VISIT LIMITS.\" The follow-up note also flags relevance artificially: \"This visit took place after the date of service 2026-05-21.\""
}
