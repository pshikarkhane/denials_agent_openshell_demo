"""Reference data: fictional payers, policy registry, category table, and the local CPT/ICD-10 table.

Everything is fictional or paraphrased; no real payer text. RARC/CARC pairings are plausible but have NOT been
confirmed by an RCM/coding reviewer (see docs/STATUS.md).
"""
from data_gen.schema import Decision

A, CAR, DNA, ESC = (Decision.APPEAL, Decision.CORRECT_AND_RESUBMIT,
                    Decision.DO_NOT_APPEAL, Decision.ESCALATE_MISSING_DOCS)

# Fictional payers. Day counts are fixed per payer so deadline math is reproducible.
PAYERS = {
    "MERIDIAN_COMM":    {"appeal_days": 180, "timely_filing_days": 180, "corrected_claim_days": 365},
    "HALCYON_PLAN":     {"appeal_days": 120, "timely_filing_days": 365, "corrected_claim_days": 180},
    "TERRAVISTA_HEALTH": {"appeal_days": 90,  "timely_filing_days": 90,  "corrected_claim_days": 180},
}
RETRO_AUTH_WINDOW_DAYS = 14   # HALCYON_PLAN, MP-PA-003
PT_VISIT_LIMIT = 20           # HALCYON_PLAN, MP-PT-011
PT_VISIT_CAP_WITH_EXCEPTION = 30

# 8 primary policy documents (spec 3.4) plus 3 near-duplicate distractors.
POLICIES = {
    "MP-IMG-007": "MERIDIAN_COMM",    # lumbar MRI medical necessity
    "MP-BND-002": "MERIDIAN_COMM",    # bundling / distinct-procedure modifiers
    "MP-BEN-002": "MERIDIAN_COMM",    # member cost sharing
    "MP-APL-001": "MERIDIAN_COMM",    # appeal levels and deadlines
    "MP-PA-003":  "HALCYON_PLAN",     # prior auth / retro-auth
    "MP-PT-011":  "HALCYON_PLAN",     # outpatient therapy visit limits
    "MP-TF-001":  "TERRAVISTA_HEALTH",  # timely filing
    "MP-CLM-004": "TERRAVISTA_HEALTH",  # claim submission, duplicates, edits
}
DISTRACTORS = {"MP-IMG-007": "MP-IMG-012", "MP-PA-003": "MP-PA-030", "MP-TF-001": "MP-TF-010"}

CATEGORIES = {
    1:  {"name": "Medical necessity, record supports", "carc": "CO-50", "policy": "MP-IMG-007", "decisions": [A] * 5},
    2:  {"name": "Medical necessity, record does not support", "carc": "CO-50", "policy": "MP-IMG-007",
         "decisions": [DNA] * 3 + [ESC] * 2},
    3:  {"name": "No prior auth, retro-auth available", "carc": "CO-197", "policy": "MP-PA-003", "decisions": [A] * 5},
    4:  {"name": "No prior auth, not retro-eligible", "carc": "CO-197", "policy": "MP-PA-003", "decisions": [DNA] * 5},
    5:  {"name": "Timely filing, proof exists", "carc": "CO-29", "policy": "MP-TF-001", "decisions": [A] * 5},
    6:  {"name": "Timely filing, expired, no proof", "carc": "CO-29", "policy": "MP-TF-001", "decisions": [DNA] * 5},
    7:  {"name": "Patient responsibility (deductible)", "carc": "PR-1", "policy": "MP-BEN-002", "decisions": [DNA] * 5},
    8:  {"name": "Missing/invalid information or modifier", "carc": "CO-4/CO-16", "policy": "MP-CLM-004",
         "decisions": [CAR] * 5},
    9:  {"name": "Bundling / NCCI-style", "carc": "CO-97", "policy": "MP-BND-002", "decisions": [A] * 2 + [CAR] * 3},
    10: {"name": "Duplicate claim", "carc": "CO-18", "policy": "MP-CLM-004", "decisions": [DNA] * 5},
    11: {"name": "Diagnosis inconsistent with procedure", "carc": "CO-11", "policy": "MP-CLM-004",
         "decisions": [CAR] * 5},
    12: {"name": "Frequency / visit-limit exceeded", "carc": "CO-151", "policy": "MP-PT-011", "decisions": [A] * 5},
}
CASES_PER_CATEGORY = 5
DEV_PER_CATEGORY = 1

# Small local code table (own paraphrased descriptions). Anything not here is flagged for human review.
CPT = {
    "72148": "MRI lumbar spine without contrast", "27447": "Total knee arthroplasty",
    "29881": "Knee arthroscopy with meniscectomy", "63030": "Lumbar laminotomy/discectomy",
    "99213": "Established patient visit, low", "99214": "Established patient visit, moderate",
    "73721": "MRI lower-extremity joint without contrast", "93000": "ECG with interpretation",
    "85025": "Complete blood count with differential", "97110": "Therapeutic exercise",
    "97112": "Neuromuscular re-education", "97140": "Manual therapy", "97530": "Therapeutic activities",
    "20610": "Major joint injection/aspiration", "76942": "Ultrasound guidance for needle placement",
    "36415": "Venipuncture",
}
ICD10 = {
    "M54.16": "Radiculopathy, lumbar", "M54.17": "Radiculopathy, lumbosacral", "M51.16": "Disc disorder w/ radiculopathy, lumbar",
    "M51.17": "Disc disorder w/ radiculopathy, lumbosacral", "M51.26": "Other disc displacement, lumbar",
    "M17.11": "Primary OA, right knee", "M17.12": "Primary OA, left knee",
    "M23.221": "Old meniscus tear, post horn medial, right knee", "M23.222": "Old meniscus tear, post horn medial, left knee",
    "E11.9": "Type 2 diabetes without complications", "I10": "Essential hypertension", "J06.9": "Acute upper respiratory infection",
    "J02.9": "Acute pharyngitis", "E78.5": "Hyperlipidemia", "M25.561": "Pain in right knee", "M25.562": "Pain in left knee",
    "M25.511": "Pain in right shoulder", "M54.50": "Low back pain, unspecified", "M62.81": "Muscle weakness",
    "R07.9": "Chest pain, unspecified", "D64.9": "Anemia, unspecified",
}
_PT_DX = ["M54.16", "M54.50", "M25.511", "M25.561", "M25.562", "M62.81", "M51.16"]
VALID_PAIRS = {
    "72148": ["M54.16", "M51.16", "M54.17", "M51.17", "M51.26"],
    "27447": ["M17.11", "M17.12"], "29881": ["M23.221", "M23.222"],
    "63030": ["M51.16", "M51.17", "M51.26"],
    "99213": ["E11.9", "I10", "J06.9", "J02.9", "E78.5", "M54.50"],
    "99214": ["E11.9", "I10", "J06.9", "J02.9", "E78.5", "M54.50"],
    "73721": ["M25.561", "M25.562", "M23.221", "M23.222"],
    "93000": ["R07.9", "I10"], "85025": ["D64.9", "E11.9", "I10"],
    "97110": _PT_DX, "97112": _PT_DX, "97530": _PT_DX, "97140": _PT_DX,
    "20610": ["M17.11", "M17.12", "M25.561", "M25.562", "M25.511"],
    "76942": ["M17.11", "M17.12", "M25.561", "M25.562"],
    "36415": ["E11.9", "D64.9", "I10", "E78.5"],
}

# Fixed per-policy effective dates (host-side truth for the policy library). A case whose DOS falls before its
# policy's effective date carries the `policy_effective_after_dos` trap; all other cases have DOS >= effective date.
from datetime import date  # noqa: E402

POLICY_EFFECTIVE = {
    "MP-IMG-007": date(2026, 4, 15), "MP-PA-003": date(2026, 4, 1), "MP-TF-001": date(2026, 3, 15),
    "MP-BND-002": date(2026, 4, 10), "MP-PT-011": date(2026, 4, 20), "MP-BEN-002": date(2026, 3, 1),
    "MP-CLM-004": date(2026, 4, 5), "MP-APL-001": date(2026, 3, 1),
}
DOS_RANGE = (date(2026, 2, 1), date(2026, 7, 31))
PAYER_NAMES = {"MERIDIAN_COMM": "Meridian Community Health Plan", "HALCYON_PLAN": "Halcyon Health Plan",
               "TERRAVISTA_HEALTH": "Terravista Health"}

POLICY_TITLES = {
    "MP-IMG-007": "Advanced Imaging: Lumbar Spine MRI Medical Necessity",
    "MP-BND-002": "Claim Bundling and Distinct Procedural Service Modifiers",
    "MP-BEN-002": "Member Cost Sharing and Deductibles",
    "MP-APL-001": "Appeals Levels and Deadlines",
    "MP-PA-003": "Prior Authorization and Retroactive Authorization",
    "MP-PT-011": "Outpatient Therapy Visit Limits",
    "MP-TF-001": "Timely Filing of Claims",
    "MP-CLM-004": "Claim Submission Requirements, Duplicate Claims and Edit Rules",
}
# Near-duplicate distractors: id -> (payer, title, kind). `parent` is the primary policy each one imitates.
DISTRACTOR_DOCS = {
    "MP-IMG-012": {"parent": "MP-IMG-007", "payer": "MERIDIAN_COMM", "kind": "wrong service",
                   "title": "Advanced Imaging: Lumbar Spine CT Medical Necessity"},
    "MP-PA-030":  {"parent": "MP-PA-003", "payer": "MERIDIAN_COMM", "kind": "wrong payer",
                   "title": "Prior Authorization and Retroactive Authorization"},
    "MP-TF-010":  {"parent": "MP-TF-001", "payer": "TERRAVISTA_HEALTH", "kind": "superseded version",
                   "title": "Timely Filing of Claims"},
}
# CARC wording: short paraphrases of the public code meanings.
CARC_TEXT = {
    "CO-50": "The service was not deemed medically necessary by the plan.",
    "CO-197": "Precertification/authorization/notification was absent.",
    "CO-29": "The time limit for filing has expired.",
    "PR-1": "Amount applied to the patient's deductible.",
    "CO-4": "The procedure code is inconsistent with the modifier used, or a required modifier is missing.",
    "CO-16": "The claim lacks information needed for adjudication.",
    "CO-97": "The benefit for this service is included in the payment for another service already adjudicated.",
    "CO-18": "Exact duplicate of a claim/service already adjudicated.",
    "CO-11": "The diagnosis is inconsistent with the procedure.",
    "CO-151": "Payment adjusted because the information submitted does not support this many services or this frequency.",
}
