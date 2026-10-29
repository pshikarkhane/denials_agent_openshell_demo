<!-- reviewer=gemini model=gcp/google/gemini-3.1-pro-preview time=2026-10-29T20:25:32.404929+00:00 secs=86 usage={"completion_tokens": 10193, "prompt_tokens": 2786, "total_tokens": 12979, "completion_tokens_details": {"reasoning_tokens": 7675, "text_tokens": 2518}, "prompt_tokens_details": {"text_tokens": 2786}} -->
```json
{
  "lines": [
    {"id": "S1.1", "verdict": "no concern", "confidence": "high", "reason": "Standard CPT/ICD-10 pairing for total knee replacement."},
    {"id": "S1.2", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: knee arthroscopy for meniscus tear."},
    {"id": "S1.3", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: knee arthroscopy for meniscus tear."},
    {"id": "S1.4", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: lumbar discectomy for disc displacement."},
    {"id": "S1.5", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: MRI lumbar for disc disorder with radiculopathy."},
    {"id": "S1.6", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: MRI lumbar for lumbosacral disc disorder."},
    {"id": "S1.7", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: MRI lumbar for disc displacement."},
    {"id": "S1.8", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: MRI lumbar for radiculopathy."},
    {"id": "S1.9", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: MRI lumbar for lumbosacral radiculopathy."},
    {"id": "S1.10", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: Lower extremity MRI for meniscus tear."},
    {"id": "S1.11", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: Lower extremity MRI for knee pain."},
    {"id": "S1.12", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: Lower extremity MRI for knee pain."},
    {"id": "S1.13", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: CBC for anemia."},
    {"id": "S1.14", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: ECG for hypertension is typically valid."},
    {"id": "S1.15", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: ECG for chest pain."},
    {"id": "S1.16", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: PT exercise for shoulder pain."},
    {"id": "S1.17", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: PT exercise for knee pain."},
    {"id": "S1.18", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: PT exercise for knee pain."},
    {"id": "S1.19", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: PT exercise for low back pain."},
    {"id": "S1.20", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: Neuromuscular re-ed for radiculopathy."},
    {"id": "S1.21", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: Neuromuscular re-ed for low back pain."},
    {"id": "S1.22", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: Manual therapy for knee pain."},
    {"id": "S1.23", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: Manual therapy for disc disorder."},
    {"id": "S1.24", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: Manual therapy for low back pain."},
    {"id": "S1.25", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: Therapeutic activities for knee pain."},
    {"id": "S1.26", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: Therapeutic activities for muscle weakness."},
    {"id": "S1.27", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: E&M for diabetes."},
    {"id": "S1.28", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: E&M for hyperlipidemia."},
    {"id": "S1.29", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: E&M for hypertension."},
    {"id": "S1.30", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: E&M for acute pharyngitis."},
    {"id": "S1.31", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: E&M for URI."},
    {"id": "S1.32", "verdict": "no concern", "confidence": "high", "reason": "Standard pairing: E&M for low back pain."},
    {"id": "S2.1", "verdict": "no concern", "confidence": "high", "reason": "Clear deliberate mismatch for testing CO-11 (ortho procedure with respiratory dx)."},
    {"id": "S2.2", "verdict": "no concern", "confidence": "high", "reason": "Clear deliberate mismatch for testing CO-11."},
    {"id": "S2.3", "verdict": "no concern", "confidence": "high", "reason": "Clear deliberate mismatch (spine MRI for anemia)."},
    {"id": "S2.4", "verdict": "no concern", "confidence": "high", "reason": "Clear deliberate mismatch (ECG for anemia)."},
    {"id": "S2.5", "verdict": "no concern", "confidence": "medium", "reason": "Plausible mismatch (ECG typically not medically necessary for uncomplicated hyperlipidemia)."},
    {"id": "S3.1", "verdict": "suspect", "confidence": "medium", "reason": "M76 means missing/invalid diagnosis, which better fits CO-16 than CO-11 (diagnosis inconsistent with procedure)."},
    {"id": "S3.2", "verdict": "no concern", "confidence": "high", "reason": "CO-151 and N640 both perfectly match frequency/limit exceeded scenarios."},
    {"id": "S3.3", "verdict": "no concern", "confidence": "high", "reason": "CO-16 fits missing info scenario; RARC deliberately omitted per instructions."},
    {"id": "S3.4", "verdict": "no concern", "confidence": "high", "reason": "CO-18 fits duplicate claim scenario; RARC deliberately omitted."},
    {"id": "S3.5", "verdict": "no concern", "confidence": "high", "reason": "CO-197 fits prior auth scenario; RARC deliberately omitted."},
    {"id": "S3.6", "verdict": "no concern", "confidence": "high", "reason": "CO-29 perfectly fits timely filing scenario."},
    {"id": "S3.7", "verdict": "no concern", "confidence": "high", "reason": "CO-4 fits modifier issue scenario; RARC deliberately omitted."},
    {"id": "S3.8", "verdict": "no concern", "confidence": "high", "reason": "CO-50 and N115 match medical necessity and LMRP/LCD rules."},
    {"id": "S3.9", "verdict": "no concern", "confidence": "high", "reason": "CO-50 and N386 match medical necessity and NCD rules."},
    {"id": "S3.10", "verdict": "no concern", "confidence": "high", "reason": "CO-97 and N20 perfectly match bundling/NCCI scenarios."},
    {"id": "S3.11", "verdict": "no concern", "confidence": "high", "reason": "PR-1 perfectly fits deductible scenario."},
    {"id": "S4.1", "verdict": "no concern", "confidence": "high", "reason": "97140 is an NCCI column 2 code to 97110, and modifier 59/XS is allowed if distinct."},
    {"id": "S4.2", "verdict": "no concern", "confidence": "high", "reason": "97140 is an NCCI column 2 code to 97530, and modifier 59/XS is allowed if distinct."},
    {"id": "S5.1", "verdict": "no concern", "confidence": "high", "reason": "CO-4 correctly applies to missing modifiers like GP on PT codes."},
    {"id": "S5.2", "verdict": "no concern", "confidence": "high", "reason": "CO-16 correctly applies to missing place of service (claim info)."},
    {"id": "S5.3", "verdict": "no concern", "confidence": "high", "reason": "CO-16 correctly applies to missing rendering provider ID."}
  ],
  "combination_flags": [
    {
      "codes": "M54.50 combined with M51.26",
      "confidence": "high",
      "reason": "ICD-10 Excludes1 conflict: M54.50 (low back pain) explicitly excludes lumbago due to intervertebral disc displacement (M51.2-)."
    },
    {
      "codes": "M54.50 combined with M54.16 or M51.16",
      "confidence": "medium",
      "reason": "Coding a symptom (low back pain) alongside the definitive diagnosis (lumbar radiculopathy/disc disorder) can trigger Excludes1 or inclusive coding denials."
    },
    {
      "codes": "M25.561/M25.562 combined with M23.221/M23.222",
      "confidence": "medium",
      "reason": "Coding a symptom (knee pain) alongside a definitive diagnosis (meniscus tear) for the same joint violates general coding guidelines."
    }
  ]
}
```
