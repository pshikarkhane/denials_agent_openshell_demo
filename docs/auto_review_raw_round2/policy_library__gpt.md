<!-- reviewer=gpt model=azure/openai/gpt-5.5 time=2026-10-29T18:23:47.637490+00:00 secs=44 usage={"completion_tokens": 4379, "prompt_tokens": 5634, "total_tokens": 10013, "completion_tokens_details": {"reasoning_tokens": 2588}, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "cache_creation_tokens": 0}} -->
{
  "findings": [
    {
      "area": "ordering",
      "severity": "major",
      "policy": "MP-PA-030",
      "quote": "7.4 Appeals address: Appeals Unit, P.O. Box 5100, Meridian City, ST 00001\n12.10 Retroactive authorization window: 7 days from the date of service.",
      "problem": "The numbering jumps from Section 7.4 to 12.10 inside the Section 7 key-parameters block. This is out of numeric order and could confuse section-based citation or retrieval.",
      "suggested_fix": "Renumber 12.10 as 7.5, or move it to a properly labeled Section 12 if that section exists."
    },
    {
      "area": "corrected_claim_gap",
      "severity": "major",
      "policy": "MP-CLM-004",
      "quote": "Section 2.3\nA denied claim must not be a duplicate of a claim that has already been adjudicated. Terravista Health will verify that the claim under review does not match an already-adjudicated claim before further handling. Claims identified as duplicates of adjudicated claims will be addressed under the duplicate provisions of this policy.",
      "problem": "The policy says duplicate claims will be addressed under duplicate provisions, but no separate duplicate provisions appear. For cases where the correct action is CORRECT_AND_RESUBMIT, the text does not clearly tell the reader what correction is expected for a duplicate-claim denial.",
      "suggested_fix": "Add explicit duplicate-claim handling language, e.g. whether the provider should not resubmit, should submit a corrected replacement claim with the original claim reference, or should correct the data element that caused an erroneous duplicate match. State that the corrected-claim deadline in Section 7.3 applies when resubmission is appropriate."
    },
    {
      "area": "corrected_claim_gap",
      "severity": "major",
      "policy": "MP-CLM-004",
      "quote": "Section 2.4\nThe diagnosis billed on a claim must support the billed procedure according to the applicable payer edit. Terravista Health will apply its edit rules to confirm that the billed diagnosis aligns with the billed procedure. Claims that fail this edit may be subject to additional review under this policy.",
      "problem": "For diagnosis-edit denials, the policy describes the edit but does not explicitly say that an invalid or unsupported billed diagnosis should be corrected and resubmitted rather than appealed. Section 3 covers missing or invalid required information generally, but the diagnosis-edit section itself only says the claim may be subject to additional review.",
      "suggested_fix": "Add a sentence stating that when the billed diagnosis code is incorrect or incomplete, the provider should submit a corrected claim, and that the corrected-claim deadline in Section 7.3 applies."
    },
    {
      "area": "corrected_claim_gap",
      "severity": "minor",
      "policy": "MP-BND-002",
      "quote": "Section 2.2\nA distinct-procedural-service modifier must be appended to the line that was denied under the bundling edit. The modifier indicates that the provider is asserting the service is distinct and warrants separate consideration. Without the modifier appended to the denied line, the service will not be evaluated as a distinct procedural service.",
      "problem": "The policy requires the modifier on the denied line, and Section 4 says missing or invalid claim data should be corrected rather than appealed. However, it would be clearer if the bundling section explicitly stated that a missing distinct-procedural-service modifier is fixed by corrected claim, not by appeal.",
      "suggested_fix": "Add a sentence to Section 2.2 or Section 3: \"If the modifier was omitted from the denied line, the provider must submit a corrected claim within the corrected-claim deadline in Section 7.3; an appeal will not cure the missing modifier.\""
    },
    {
      "area": "distractor",
      "severity": "minor",
      "policy": "MP-PA-030",
      "quote": "PRIOR AUTHORIZATION AND RETROACTIVE AUTHORIZATION",
      "problem": "This distractor has the exact same title as MP-PA-003. It is distinguishable by payer, but because denial letters cite policies by title only, a title-only retrieval step could tie MP-PA-030 with the correct Halcyon policy.",
      "suggested_fix": "Keep the payer filtering requirement explicit in the test harness, or make the distractor title slightly more distinguishable, e.g. \"PRIOR AUTHORIZATION AND RETROACTIVE AUTHORIZATION - MERIDIAN\"."
    },
    {
      "area": "distractor",
      "severity": "minor",
      "policy": "MP-TF-010",
      "quote": "Status: SUPERSEDED. Replaced by MP-TF-001 (current version effective 2026-03-15). Version 1.0, effective 2024-01-01; this version last applied to dates of service on or before 2024-12-31.",
      "problem": "This distractor has the same title and payer as MP-TF-001, so a title-only lookup could retrieve both. It is distinguishable by status, replacement note, and applicable dates of service, so this is not a contradiction.",
      "suggested_fix": "No substantive policy change is required, but ensure the retrieval logic considers status and date-of-service applicability when titles match."
    },
    {
      "area": "realism",
      "severity": "minor",
      "policy": "ALL",
      "quote": "SYNTHETIC DATA - NOT REAL PHI",
      "problem": "This footer clearly signals that the documents are part of a synthetic test set, which is unrealistic for payer policy language and could leak the nature of the evaluation.",
      "suggested_fix": "Remove this footer from the policy text shown to agents, or keep it only in metadata outside the retrievable policy body."
    },
    {
      "area": "realism",
      "severity": "minor",
      "policy": "MP-APL-001",
      "quote": "Appeals Unit, P.O. Box 5100, Meridian City, ST 00001",
      "problem": "The placeholder state and ZIP format are obviously fictional. Similar placeholder addresses appear across the library and may hint that the policies are synthetic.",
      "suggested_fix": "Use less conspicuous fictional addresses, or omit mailing addresses if they are not needed for the denial-appeal task."
    }
  ],
  "clean_areas": [
    "The primary policy payer IDs and effective dates match the intended parameters.",
    "Appeal, timely filing, and corrected-claim windows match the intended parameters for Meridian, Halcyon, and Terravista.",
    "The retroactive authorization window in MP-PA-003 is 14 days from date of service, matching the intended parameter.",
    "The outpatient therapy limits in MP-PT-011 match the intended 20-visit base limit and consideration of visits 21 through 30 with documented improvement and a recertified plan of care.",
    "MP-BND-002 contains the intended code pairs: CPT 97140 into CPT 97110 and CPT 97140 into CPT 97530.",
    "The Version 3.0 carry-forward wording in the primary policies is not internally contradictory; it allows dates of service before the current effective date to be handled under unchanged prior-version requirements.",
    "No primary policy contains an appeal, timely-filing, corrected-claim, retro-authorization, or therapy-limit contradiction against the intended parameters.",
    "The imaging distractor MP-IMG-012 is plausibly similar to MP-IMG-007 but distinguishable by service type, CT versus MRI.",
    "The superseded timely-filing distractor MP-TF-010 is distinguishable from MP-TF-001 by status and date-of-service applicability.",
    "The repeated jump to Section 7 for key parameters in the primary policies creates numbering gaps, but it is consistent across the library and does not create an out-of-order citation problem except in MP-PA-030."
  ],
  "overall": "The library mostly matches the intended parameters, with the main issues being MP-PA-030's bad section number, incomplete corrected-claim guidance in MP-CLM-004, a minor clarity gap in MP-BND-002, and synthetic/test-signaling language."
}
