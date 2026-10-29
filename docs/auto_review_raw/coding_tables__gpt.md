<!-- reviewer=gpt model=azure/openai/gpt-5.5 time=2026-10-29T20:25:06.916668+00:00 secs=61 usage={"completion_tokens": 6462, "prompt_tokens": 2474, "total_tokens": 8936, "completion_tokens_details": {"reasoning_tokens": 4142}, "prompt_tokens_details": {"cached_tokens": 2304, "cache_write_tokens": 0, "cache_creation_tokens": 0}} -->
{
  "lines": [
    {"id":"S1.1","verdict":"no concern","confidence":"high","reason":"Total knee arthroplasty has an obvious diagnosis fit with right-knee primary osteoarthritis."},
    {"id":"S1.2","verdict":"no concern","confidence":"high","reason":"Knee arthroscopy with meniscectomy fits an old medial meniscus tear diagnosis."},
    {"id":"S1.3","verdict":"no concern","confidence":"high","reason":"Knee arthroscopy with meniscectomy fits a left medial meniscus tear diagnosis; CPT is not laterality-specific."},
    {"id":"S1.4","verdict":"no concern","confidence":"high","reason":"Lumbar laminotomy/discectomy fits lumbar disc displacement."},
    {"id":"S1.5","verdict":"no concern","confidence":"high","reason":"Lumbar spine MRI fits lumbar disc disorder with radiculopathy."},
    {"id":"S1.6","verdict":"no concern","confidence":"medium","reason":"Lumbosacral disc disorder with radiculopathy can plausibly support lumbar/lumbosacral MRI despite the category-11 tag."},
    {"id":"S1.7","verdict":"no concern","confidence":"high","reason":"Lumbar spine MRI fits lumbar disc displacement."},
    {"id":"S1.8","verdict":"no concern","confidence":"high","reason":"Lumbar radiculopathy is a typical diagnosis fit for lumbar spine MRI."},
    {"id":"S1.9","verdict":"no concern","confidence":"medium","reason":"Lumbosacral radiculopathy can plausibly support lumbar/lumbosacral spine MRI."},
    {"id":"S1.10","verdict":"no concern","confidence":"high","reason":"Lower-extremity joint MRI fits suspected/internal knee meniscus derangement if the imaged joint is the knee."},
    {"id":"S1.11","verdict":"no concern","confidence":"high","reason":"Knee pain is a common diagnosis fit for lower-extremity joint MRI when the knee is imaged."},
    {"id":"S1.12","verdict":"no concern","confidence":"high","reason":"Left knee pain is a common diagnosis fit for lower-extremity joint MRI when the knee is imaged."},
    {"id":"S1.13","verdict":"no concern","confidence":"high","reason":"CBC with differential fits anemia evaluation."},
    {"id":"S1.14","verdict":"no concern","confidence":"medium","reason":"Hypertension can support ECG in some evaluation/monitoring contexts, though payer medical-necessity policy may vary."},
    {"id":"S1.15","verdict":"no concern","confidence":"high","reason":"Chest pain is a typical diagnosis fit for ECG."},
    {"id":"S1.16","verdict":"no concern","confidence":"high","reason":"Therapeutic exercise fits shoulder pain in a therapy plan of care."},
    {"id":"S1.17","verdict":"no concern","confidence":"high","reason":"Therapeutic exercise fits knee pain in a therapy plan of care."},
    {"id":"S1.18","verdict":"no concern","confidence":"high","reason":"Therapeutic exercise fits left knee pain in a therapy plan of care."},
    {"id":"S1.19","verdict":"no concern","confidence":"high","reason":"Therapeutic exercise fits low back pain in a therapy plan of care."},
    {"id":"S1.20","verdict":"no concern","confidence":"medium","reason":"Neuromuscular re-education can fit lumbar radiculopathy when neuromuscular deficits are documented."},
    {"id":"S1.21","verdict":"no concern","confidence":"low","reason":"Neuromuscular re-education may fit low back pain if functional neuromuscular deficits are documented, though pain alone is nonspecific."},
    {"id":"S1.22","verdict":"no concern","confidence":"high","reason":"Manual therapy fits knee pain in a therapy plan of care."},
    {"id":"S1.23","verdict":"no concern","confidence":"high","reason":"Manual therapy fits lumbar disc disorder with radiculopathy in a therapy plan of care."},
    {"id":"S1.24","verdict":"no concern","confidence":"high","reason":"Manual therapy fits low back pain in a therapy plan of care."},
    {"id":"S1.25","verdict":"no concern","confidence":"high","reason":"Therapeutic activities fit knee pain when functional limitations are treated."},
    {"id":"S1.26","verdict":"no concern","confidence":"high","reason":"Therapeutic activities fit muscle weakness when functional limitations are treated."},
    {"id":"S1.27","verdict":"no concern","confidence":"high","reason":"Established patient E/M fits management of type 2 diabetes."},
    {"id":"S1.28","verdict":"no concern","confidence":"high","reason":"Established patient E/M fits management of hyperlipidemia."},
    {"id":"S1.29","verdict":"no concern","confidence":"high","reason":"Established patient E/M fits management of hypertension."},
    {"id":"S1.30","verdict":"no concern","confidence":"high","reason":"Established patient E/M fits evaluation of acute pharyngitis."},
    {"id":"S1.31","verdict":"no concern","confidence":"high","reason":"Established patient E/M fits evaluation of acute upper respiratory infection."},
    {"id":"S1.32","verdict":"no concern","confidence":"high","reason":"Established patient E/M fits evaluation or follow-up of low back pain."},

    {"id":"S2.1","verdict":"no concern","confidence":"high","reason":"This is a clear intended mismatch: pharyngitis does not explain total knee arthroplasty."},
    {"id":"S2.2","verdict":"no concern","confidence":"high","reason":"This is a clear intended mismatch: URI does not explain total knee arthroplasty."},
    {"id":"S2.3","verdict":"no concern","confidence":"high","reason":"This is a clear intended mismatch: anemia does not explain lumbar spine MRI."},
    {"id":"S2.4","verdict":"suspect","confidence":"medium","reason":"Anemia is weak for ECG by itself, but not as clean a diagnosis/procedure inconsistency as the other deliberate mismatches."},
    {"id":"S2.5","verdict":"no concern","confidence":"medium","reason":"Hyperlipidemia alone is a plausible intended medical-necessity mismatch for ECG screening/risk assessment."},

    {"id":"S3.1","verdict":"no concern","confidence":"medium","reason":"CO-11 fits diagnosis/procedure inconsistency and M76 broadly supports missing/incomplete/invalid diagnosis information."},
    {"id":"S3.2","verdict":"no concern","confidence":"high","reason":"CO-151 with N640 fits frequency or visit-limit exceeded."},
    {"id":"S3.3","verdict":"suspect","confidence":"high","reason":"CO-16 fits missing information, but CO-16 generally requires at least one remark code to identify what is missing."},
    {"id":"S3.4","verdict":"no concern","confidence":"high","reason":"CO-18 fits exact duplicate claim/service and no RARC is not inherently concerning."},
    {"id":"S3.5","verdict":"no concern","confidence":"high","reason":"CO-197 fits absent precertification/authorization/notification scenarios."},
    {"id":"S3.6","verdict":"no concern","confidence":"high","reason":"CO-29 fits timely-filing denial scenarios, including appeals with proof or no proof."},
    {"id":"S3.7","verdict":"no concern","confidence":"high","reason":"CO-4 fits an inconsistent or missing modifier scenario."},
    {"id":"S3.8","verdict":"no concern","confidence":"high","reason":"CO-50 with N115 fits a medical-necessity denial tied to coverage policy."},
    {"id":"S3.9","verdict":"no concern","confidence":"high","reason":"CO-50 with N386 fits a medical-necessity denial tied to coverage policy."},
    {"id":"S3.10","verdict":"no concern","confidence":"high","reason":"CO-97 with N20 fits a bundled/included service denial."},
    {"id":"S3.11","verdict":"no concern","confidence":"high","reason":"PR-1 fits patient deductible responsibility."},

    {"id":"S4.1","verdict":"no concern","confidence":"high","reason":"97140 is commonly bundled against 97110 under NCCI-style edits, and modifier 59/XS may be plausible for a distinct site/session."},
    {"id":"S4.2","verdict":"no concern","confidence":"high","reason":"97140 is commonly bundled against 97530 under NCCI-style edits, and modifier 59/XS may be plausible for a distinct site/session."},

    {"id":"S5.1","verdict":"no concern","confidence":"high","reason":"CO-4 fits a missing required therapy modifier such as GP on 97110."},
    {"id":"S5.2","verdict":"no concern","confidence":"high","reason":"CO-16 fits missing claim information such as place of service, though a clarifying RARC is often expected."},
    {"id":"S5.3","verdict":"no concern","confidence":"high","reason":"CO-16 fits missing claim information such as a rendering provider identifier, though a clarifying RARC is often expected."}
  ],
  "combination_flags": [
    {
      "codes":"M51.16 + M54.16",
      "confidence":"high",
      "reason":"If placed together on one claim for the same condition, lumbar radiculopathy is generally not reported separately with lumbar disc disorder with radiculopathy; M54.1 has Excludes1-style conflict with disc-disorder radiculopathy codes."
    },
    {
      "codes":"M51.17 + M54.17",
      "confidence":"high",
      "reason":"If combined, lumbosacral radiculopathy is generally not separately coded with lumbosacral disc disorder with radiculopathy due to an Excludes1-style conflict."
    },
    {
      "codes":"M51.26 + M54.50",
      "confidence":"medium",
      "reason":"If combined for the same back-pain condition, low back pain may conflict with or be redundant to lumbar disc displacement because M54.5 has Excludes1-style guidance for lumbago due to intervertebral disc displacement."
    }
  ]
}
