"""Generate truth.json for 60 synthetic cases (12 categories x 5) plus data/manifest.json.

Pure Python, seeded RNG. No documents are rendered and no LLM is called. All codes, dates, amounts and
deadlines are computed here. Usage: python -m data_gen.gen_cases [--seed N] [--out data] [--force]

SAFETY: truth.json files that already hold clinical facts (evidence quotes) are never overwritten without --force.
"""
import argparse
import hashlib
import json
import random
import subprocess
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from data_gen import reference as R
from data_gen.schema import Claim, Decision, Denial, Fact, Patient, PolicyCriterion, Trap, Truth

DEFAULT_SEED = 20261028
PROJECT_VERSION = "phase1-v2"
STD_DOCS = ("eob_835.txt", "denial_letter.txt", "claim_history.txt")
# At most one "hard" problem per case. policy_effective_after_dos and distractor_policy_similar_name are retrieval-level
# (soft) traps and may accompany one hard trap, up to 2 traps in total.
HARD_TRAPS = {Trap.DEADLINE_WITHIN_7_DAYS, Trap.DEADLINE_PASSED, Trap.NOTE_AFTER_DOS,
              Trap.NOTES_DISAGREE_THERAPY_DURATION, Trap.CRITERION_NO_SUPPORTING_DOC}


def iso(d):
    return d.isoformat()


@dataclass
class Ctx:
    rng: random.Random
    case_id: str
    cat: int
    decision: Decision
    policy_id: str
    payer: str
    taken_patients: set
    taken_claims: set
    dos: date = None
    submitted: date = None   # practice submission = clearinghouse acceptance
    received: date | None = None  # payer received date
    denial: date | None = None
    as_of: date = None
    cpt: str = ""
    icd10: list = field(default_factory=list)
    billed: float = 0.0
    carc: str = ""
    rarc: str | None = None
    therapy_start: date | None = None
    criteria: list = field(default_factory=list)
    facts: list = field(default_factory=list)
    docs: list = field(default_factory=list)
    enclosures: list = field(default_factory=list)

    def fact(self, key, value, source):
        self.facts.append(Fact(key=key, value=value, source_file=source))

    def add_doc(self, path):
        self.docs.append(path)
        self.fact("planned_document", path, path)

    def crit(self, cid, section, text, status, evidence, basis="evidence"):
        if isinstance(status, bool):
            status = "met" if status else "unmet"
        self.criteria.append(PolicyCriterion(id=cid, section=section, text=text, status=status, basis=basis,
                                             evidence=list(evidence)))

    def days(self, lo, hi):
        return timedelta(days=self.rng.randint(lo, hi))

    @staticmethod
    def wd(d):
        """Move a weekend date forward to Monday: outpatient visits and notes are dated on weekdays."""
        while d.weekday() >= 5:
            d += timedelta(days=1)
        return d

    def money(self, lo, hi):
        return round(self.rng.uniform(lo, hi), 2)


# ---------------------------------------------------------------- category builders
# Section numbers are consecutive within each policy (2.1, 2.2, ...); gen_policies reads them from truth.

def _imaging(c, c1, c2):
    """Lumbar MRI necessity (MP-IMG-007). c1: met|short|missing (conservative therapy); c2: neuro deficit documented."""
    c.cpt, c.carc, c.rarc = "72148", "CO-50", c.rng.choice(["N115", "N386"])
    c.icd10, c.billed = c.rng.sample(R.VALID_PAIRS["72148"], 1), c.money(1400, 2100)  # one diagnosis: no Excludes1 pairs
    ortho = c.wd(c.dos - c.days(3, 14))
    start = c.wd((c.dos - c.days(60, 100)) if c1 == "met" else (ortho - c.days(10, 30)))
    c.therapy_start = start
    pcp, ortho_f = f"notes/{iso(start)}_pcp.txt", f"notes/{iso(ortho)}_ortho.txt"
    c.add_doc(pcp)
    c.add_doc(ortho_f)
    c.fact("therapy_start_date", iso(start), pcp)
    if c1 != "missing":
        c.add_doc("supporting/pt_log.txt")
        c1_ev = [pcp, "supporting/pt_log.txt"]
        c.fact("therapy_duration_days", (ortho - start).days, "supporting/pt_log.txt")
    else:  # MISSING EVIDENCE: the PCP note refers to PT records that were never received
        c.fact("missing_docs", ["supporting/pt_log.txt"], pcp)
        c1_ev = [pcp]
    c.fact("ortho_exam_has_neuro_deficit", c2, ortho_f)
    has_prior = c.rng.random() < 0.5  # DOCUMENTED ABSENCE either way: the ortho note states the imaging history
    c3_ev = [ortho_f]
    if has_prior:
        c.add_doc("supporting/prior_imaging.txt")
        c3_ev.append("supporting/prior_imaging.txt")
        c.fact("last_lumbar_imaging_date", iso(c.dos - c.days(500, 900)), ortho_f)
    else:
        c.fact("last_lumbar_imaging_date", "none", ortho_f)
    c.crit("C1", "§2.1(a)", ">=6 weeks conservative therapy", {"met": "met", "short": "unmet", "missing": "unknown"}[c1], c1_ev,
           "missing_evidence" if c1 == "missing" else "evidence")
    c.crit("C2", "§2.1(b)", "Neuro deficit or red flag documented", c2, [ortho_f])
    c.crit("C3", "§2.1(c)", "No imaging of the same region within 12 months", True, c3_ev, "documented_absence")
    if c.decision == Decision.APPEAL:
        c.enclosures = ["supporting/pt_log.txt", ortho_f]


def build_1(c):
    _imaging(c, "met", True)


def build_2(c):
    if c.decision == Decision.ESCALATE_MISSING_DOCS:
        _imaging(c, "missing", True)
    else:
        _imaging(c, *c.rng.choice([("short", True), ("met", False), ("short", False)]))


def _auth_service(c):
    c.cpt = c.rng.choice(["27447", "29881", "63030"])
    c.icd10 = c.rng.sample(R.VALID_PAIRS[c.cpt], 1)
    c.billed = c.money(2800, 5200)
    c.carc, c.rarc = "CO-197", None  # RARC omitted until a coder verifies a pairing
    c.fact("auth_required", True, "denial_letter.txt")
    c.fact("auth_on_file", False, "denial_letter.txt")
    c.fact("retro_auth_window_days", R.RETRO_AUTH_WINDOW_DAYS, "policy_library")


def build_3(c):
    _auth_service(c)
    urgent = f"notes/{iso(c.dos - timedelta(days=1))}_urgent_eval.txt"
    req = c.dos + c.days(1, 10)
    c.add_doc(urgent)
    c.add_doc("supporting/retro_auth_request.txt")
    c.fact("service_type", "urgent", urgent)
    c.fact("retro_request_date", iso(req), "claim_history.txt")
    c.crit("C1", "§2.1", "Service requires prior authorization", True, ["denial_letter.txt"])
    c.crit("C2", "§2.2", "Service was urgent/emergent so auth could not be obtained beforehand", True, [urgent])
    c.crit("C3", "§2.3", f"Retro-auth requested within {R.RETRO_AUTH_WINDOW_DAYS} days of DOS", True,
           ["claim_history.txt", "supporting/retro_auth_request.txt"])
    c.enclosures = [urgent, "supporting/retro_auth_request.txt"]


def build_4(c):
    _auth_service(c)
    sched = f"notes/{iso(c.dos - c.days(20, 60))}_ortho.txt"
    c.add_doc(sched)
    c.fact("service_type", "elective", sched)
    late = c.rng.random() < 0.5
    if late:
        c.add_doc("supporting/late_retro_request.txt")
        c.fact("retro_request_date", iso(c.dos + c.days(R.RETRO_AUTH_WINDOW_DAYS + 6, 45)), "claim_history.txt")
    else:
        c.fact("retro_request_filed", False, "claim_history.txt")
    c.crit("C1", "§2.1", "Service requires prior authorization", True, ["denial_letter.txt"])
    c.crit("C2", "§2.2", "Service was urgent/emergent so auth could not be obtained beforehand", False, [sched])
    c.crit("C3", "§2.3", f"Retro-auth requested within {R.RETRO_AUTH_WINDOW_DAYS} days of DOS", False,
           ["claim_history.txt"] + (["supporting/late_retro_request.txt"] if late else []),
           "evidence" if late else "documented_absence")


def _tf_service(c):
    c.cpt = c.rng.choice(["99213", "73721", "93000"])
    c.icd10 = c.rng.sample(R.VALID_PAIRS[c.cpt], 1)
    c.billed = {"99213": c.money(120, 260), "73721": c.money(950, 1600), "93000": c.money(90, 180)}[c.cpt]
    c.carc, c.rarc = "CO-29", None
    c.fact("timely_filing_limit_days", R.PAYERS[c.payer]["timely_filing_days"], "policy_library")
    c.fact("timely_filing_deadline", iso(c.dos + timedelta(days=R.PAYERS[c.payer]["timely_filing_days"])), "denial_letter.txt")


def build_5(c):
    """Proof exists: claim_history shows an early accepted submission; the payer's own received date is late."""
    _tf_service(c)
    lim = R.PAYERS[c.payer]["timely_filing_days"]
    c.submitted = c.dos + c.days(10, 60)
    c.received = c.dos + timedelta(days=lim) + c.days(5, 40)
    c.denial = c.received + c.days(14, 21)
    c.crit("C1", "§2.1", f"Claim submitted within {lim} days of DOS", True, ["claim_history.txt"])
    c.crit("C2", "§2.2", "Proof of clearinghouse acceptance within the filing limit is available", True, ["claim_history.txt"])
    c.enclosures = ["claim_history.txt"]


def build_6(c):
    """Expired: claim_history shows a single, late submission and states that no earlier one is recorded (documented absence)."""
    _tf_service(c)
    lim = R.PAYERS[c.payer]["timely_filing_days"]
    c.submitted = c.dos + timedelta(days=lim) + c.days(5, 60)
    c.received = c.submitted + c.days(1, 2)
    c.denial = c.received + c.days(14, 21)
    c.add_doc(f"notes/{iso(c.wd(c.dos - c.days(14, 45)))}_pcp.txt")
    c.add_doc(f"notes/{iso(c.dos)}_visit.txt")
    c.crit("C1", "§2.1", f"Claim submitted within {lim} days of DOS", False, ["claim_history.txt"])
    c.crit("C2", "§2.2", "Proof of clearinghouse acceptance within the filing limit is available", False, ["claim_history.txt"],
           "documented_absence")


def build_7(c):
    c.cpt = c.rng.choice(["99213", "85025"])
    c.icd10 = c.rng.sample(R.VALID_PAIRS[c.cpt], 1)
    c.billed = c.money(120, 420)
    allowed = round(c.billed * c.rng.uniform(0.5, 0.7), 2)
    total = c.rng.choice([500, 1000, 1500, 2500])
    met_before = c.rng.randrange(0, total - 40, 10)
    pr1 = round(min(allowed, total - met_before), 2)
    c.carc, c.rarc = "PR-1", None
    c.add_doc("supporting/benefit_summary.txt")
    src = "supporting/benefit_summary.txt"
    c.fact("allowed_amount", allowed, "eob_835.txt")
    c.fact("deductible_total", total, src)
    c.fact("deductible_met_before_dos", met_before, src)
    c.fact("pr1_amount", pr1, "eob_835.txt")
    c.crit("C1", "§2.1", "Member deductible was already satisfied before DOS", False, [src])
    c.crit("C2", "§2.2", "Payer applied the deductible in error", False, [src])


_CAT8 = [  # RARCs omitted for CO-4 / CO-16 until a coder verifies them
    ("CO-4", "99213", "modifier 25 missing on visit billed same day as a procedure", "append modifier 25", "modifier_25"),
    ("CO-4", "73721", "laterality modifier (RT/LT) missing", "append RT or LT per the order", "laterality_modifier"),
    ("CO-4", "97110", "therapy modifier GP missing", "append modifier GP", "modifier_gp"),
    ("CO-16", "99213", "rendering provider identifier missing on claim", "add rendering provider identifier", "rendering_provider"),
    ("CO-16", "73721", "referring provider information missing", "add referring provider information", "referring_provider"),
    ("CO-16", "99213", "place of service code missing", "add place of service code", "place_of_service"),
]


def build_8(c):
    c.carc, c.cpt, missing, fix, field_code = c.rng.choice(_CAT8)
    c.rarc = None
    c.icd10 = c.rng.sample(R.VALID_PAIRS[c.cpt], 1)
    c.billed = {"99213": c.money(120, 260), "73721": c.money(950, 1600), "97110": c.money(95, 160)}[c.cpt]
    note = f"notes/{iso(c.dos)}_visit.txt"
    c.add_doc(f"notes/{iso(c.wd(c.dos - c.days(14, 45)))}_pcp.txt")
    c.add_doc(note)
    c.fact("missing_item", missing, "denial_letter.txt")
    c.fact("missing_field", field_code, "eob_835.txt")
    c.fact("correct_fix", fix, "policy_library")
    if field_code == "modifier_25":
        c.fact("same_day_procedure_cpt", "20610", "eob_835.txt")
        c.fact("same_day_procedure_billed", c.money(150, 400), "eob_835.txt")
    c.crit("C1", "§2.1", "Claim as submitted contained all required data elements and modifiers", False, ["eob_835.txt"])
    c.crit("C2", "§2.2", "Corrected claim can be filed within the payer corrected-claim window", True, ["denial_letter.txt"])


def build_9(c):
    col1, col2 = c.rng.choice(R.BUNDLE_PAIRS)
    c.cpt = col2
    shared = [x for x in R.VALID_PAIRS[col2] if x in R.VALID_PAIRS[col1]]
    c.icd10, c.billed = c.rng.sample(shared, 1), c.money(80, 240)
    c.carc, c.rarc = "CO-97", "N20"
    note = f"notes/{iso(c.dos)}_procedure.txt"
    c.add_doc(note)
    has_mod = c.decision == Decision.APPEAL
    c.fact("column1_code", col1, "eob_835.txt")
    c.fact("column1_billed_amount", c.money(150, 400), "eob_835.txt")
    c.fact("modifier_required", "59", "policy_library")
    c.fact("modifier_present", has_mod, "eob_835.txt")
    c.crit("C1", "§2.1", "Services documented as distinct (separate session/site)", True, [note])
    c.crit("C2", "§2.2", "Distinct-procedural-service modifier appended to the denied line", has_mod, ["eob_835.txt"])
    if has_mod:
        c.enclosures = [note]


def build_10(c):
    c.cpt = c.rng.choice(["99213", "73721", "97110"])
    c.icd10 = c.rng.sample(R.VALID_PAIRS[c.cpt], 1)
    c.billed = {"99213": c.money(120, 260), "73721": c.money(950, 1600), "97110": c.money(95, 160)}[c.cpt]
    orig_sub = c.dos + c.days(3, 10)
    orig_paid = orig_sub + c.days(10, 20)
    c.submitted = orig_paid + c.days(5, 25)
    c.received = c.submitted + c.days(1, 2)
    c.denial = c.received + c.days(14, 21)
    c.carc, c.rarc = "CO-18", None
    c.add_doc("supporting/original_remit.txt")
    c.fact("original_claim_no", _claim_no(c), "denial_letter.txt")
    c.fact("original_paid_date", iso(orig_paid), "denial_letter.txt")
    c.fact("original_paid_amount", round(c.billed * 0.6, 2), "denial_letter.txt")
    c.crit("C1", "§2.3", "Denied claim is not a duplicate of an already-adjudicated claim", False,
           ["claim_history.txt", "supporting/original_remit.txt"])


def build_11(c):
    c.cpt = c.rng.choice(["72148", "27447", "93000", "73721", "63030"])
    wrong = [x for x in ("J06.9", "J02.9", "E78.5", "D64.9") if x not in R.VALID_PAIRS[c.cpt]]
    c.icd10 = [c.rng.choice(wrong)]
    fixed = c.rng.sample(R.VALID_PAIRS[c.cpt], 1)
    c.billed = {"72148": c.money(1400, 2100), "27447": c.money(2800, 5200), "93000": c.money(90, 180),
                "73721": c.money(950, 1600), "63030": c.money(2800, 5200)}[c.cpt]
    c.carc, c.rarc = "CO-11", "M76"
    note = f"notes/{iso(c.dos)}_visit.txt"
    c.add_doc(note)
    c.fact("corrected_icd10", fixed, note)
    c.crit("C1", "§2.4", "Billed diagnosis supports the billed procedure per payer edit", False, ["denial_letter.txt"])
    c.crit("C2", "§2.5", "Clinical note documents a diagnosis that supports the procedure", True, [note])


def build_12(c):
    c.cpt = c.rng.choice(["97110", "97112", "97530"])
    c.icd10, c.billed = c.rng.sample(R.VALID_PAIRS[c.cpt], 1), c.money(95, 160)
    c.carc, c.rarc = "CO-151", "N640"
    start = c.wd(max(c.dos - c.days(70, 120), date(2026, 1, 5)))  # all 21 visits fall in calendar year 2026
    c.therapy_start = start
    referral = f"notes/{iso(c.wd(start + c.days(20, 35)))}_referral.txt"
    for d in (f"notes/{iso(start)}_initial_eval.txt", "supporting/pt_log.txt", "supporting/pt_progress_note.txt", referral):
        c.add_doc(d)
    visit_no = R.PT_VISIT_LIMIT + 1  # the denied visit is the FIRST visit over the limit
    c.fact("therapy_start_date", iso(start), "supporting/pt_log.txt")
    c.fact("therapy_duration_days", (c.dos - start).days, "supporting/pt_log.txt")
    c.fact("visit_limit", R.PT_VISIT_LIMIT, "policy_library")
    c.fact("visit_cap", R.PT_VISIT_CAP, "policy_library")
    c.fact("denied_visit_number", visit_no, "supporting/pt_log.txt")
    c.crit("C1", "§2.1", "Measurable functional improvement documented", True, ["supporting/pt_progress_note.txt"])
    c.crit("C2", "§2.2", "Physician recertified the plan of care", True, [referral])
    c.crit("C3", "§2.3", f"Denied visit is within visits {R.PT_VISIT_LIMIT + 1} through {R.PT_VISIT_CAP} of the calendar year",
           True, ["supporting/pt_log.txt"])
    c.enclosures = ["supporting/pt_progress_note.txt", referral, "supporting/pt_log.txt"]


BUILDERS = {1: build_1, 2: build_2, 3: build_3, 4: build_4, 5: build_5, 6: build_6,
            7: build_7, 8: build_8, 9: build_9, 10: build_10, 11: build_11, 12: build_12}

# ---------------------------------------------------------------- traps (spec 3.5)
_DOS_NOTE_CATS = {1, 2, 3, 4, 9, 12}
_POLICY_DATE_CATS = {1, 2, 3, 4, 5, 6, 9, 12}


def _hard_pool(c):
    """Hard traps that can apply to this case. criterion_no_supporting_doc is reserved for ESCALATE_MISSING_DOCS cases."""
    t = [Trap.DEADLINE_WITHIN_7_DAYS]
    if c.decision == Decision.DO_NOT_APPEAL:
        t.append(Trap.DEADLINE_PASSED)
    if c.cat in _DOS_NOTE_CATS:
        t.append(Trap.NOTE_AFTER_DOS)
    if c.therapy_start and "supporting/pt_log.txt" in c.docs:
        t.append(Trap.NOTES_DISAGREE_THERAPY_DURATION)
    return sorted(t, key=lambda x: x.value)


def _apply(c, trap, action_deadline):
    if trap == Trap.DEADLINE_WITHIN_7_DAYS:
        c.as_of = action_deadline - c.days(1, 7)
    elif trap == Trap.DEADLINE_PASSED:
        c.as_of = action_deadline + c.days(1, 30)
    elif trap == Trap.NOTE_AFTER_DOS:
        d = min(c.dos + c.days(8, 40), c.as_of - timedelta(days=1))
        path = f"notes/{iso(d)}_followup.txt"
        c.add_doc(path)
        c.fact("post_dos_note", path, path)
    elif trap == Trap.NOTES_DISAGREE_THERAPY_DURATION:
        note_date = c.wd(c.therapy_start + c.days(14, 28))
        path = f"notes/{iso(note_date)}_pcp_followup.txt"
        c.add_doc(path)
        # the patient under-reports: fewer days than have actually elapsed at the note date, so the conflict is plausible
        # and points the opposite way from a >=6-week PT log
        c.fact("conflicting_therapy_duration_days", max(5, (note_date - c.therapy_start).days - c.rng.randint(7, 12)), path)
        c.fact("authoritative_duration_source", "supporting/pt_log.txt", "supporting/pt_log.txt")
    elif trap == Trap.CRITERION_NO_SUPPORTING_DOC:
        pass  # structural: the case's MISSING EVIDENCE (see _imaging); the trap only labels it
    elif trap == Trap.POLICY_EFFECTIVE_AFTER_DOS:
        pass  # structural: DOS was drawn before the policy's effective date (see generate_case)
    elif trap == Trap.DISTRACTOR_POLICY_SIMILAR_NAME:
        c.fact("distractor_policy_id", R.DISTRACTORS[c.policy_id], "policy_library")


_FIRST = [Trap.DEADLINE_WITHIN_7_DAYS, Trap.DEADLINE_PASSED]  # applied first: they set as_of


def _weekday_in(d, lo, hi):
    """Nearest weekday within [lo, hi]: dates of service are weekdays."""
    for delta in (0, 1, 2, -1, -2):
        x = d + timedelta(days=delta)
        if lo <= x <= hi and x.weekday() < 5:
            return x
    return d


def _claim_no(c):
    """Original-claim number for duplicate cases: derived deterministically, distinct from claim_no."""
    return str(int(c.facts[0].value) - 11 * (c.rng.randint(1, 9)))


# ---------------------------------------------------------------- assembly

def generate_case(seed, case_id, cat, decision, split, taken_patients, taken_claims):
    rng = random.Random(f"{seed}:{case_id}")
    meta = R.CATEGORIES[cat]
    policy = meta["policy"]
    c = Ctx(rng, case_id, cat, decision, policy, R.POLICIES[policy], taken_patients, taken_claims)
    eff = R.POLICY_EFFECTIVE[policy]
    want_eff = cat in _POLICY_DATE_CATS and rng.random() < 0.2
    lo, hi = (R.DOS_RANGE[0], eff - timedelta(days=1)) if want_eff else (eff, R.DOS_RANGE[1])
    c.dos = _weekday_in(lo + timedelta(days=rng.randint(0, (hi - lo).days)), lo, hi)
    c.submitted = c.dos + c.days(3, 14)

    pid = rng.randint(1000, 9999)
    while pid in taken_patients:
        pid = rng.randint(1000, 9999)
    taken_patients.add(pid)
    claim_no = rng.randint(1000100, 9999999)
    while claim_no in taken_claims:
        claim_no = rng.randint(1000100, 9999999)
    taken_claims.add(claim_no)
    c.fact("claim_no", str(claim_no), "denial_letter.txt")  # facts[0]: used by _claim_no

    BUILDERS[cat](c)
    if c.received is None:
        c.received = c.submitted + c.days(1, 3)
    if c.denial is None:
        c.denial = c.received + c.days(14, 30)

    pay = R.PAYERS[c.payer]
    appeal_deadline = c.denial + timedelta(days=pay["appeal_days"])
    corrected_deadline = c.denial + timedelta(days=pay["corrected_claim_days"])
    action_deadline = corrected_deadline if decision == Decision.CORRECT_AND_RESUBMIT else appeal_deadline
    c.as_of = min(c.denial + c.days(5, 40), action_deadline - timedelta(days=8))

    picked = [Trap.POLICY_EFFECTIVE_AFTER_DOS] if want_eff else []
    if decision == Decision.ESCALATE_MISSING_DOCS:
        picked.append(Trap.CRITERION_NO_SUPPORTING_DOC)  # the one hard problem of an ESCALATE case
    else:
        pool = _hard_pool(c)
        if pool and rng.random() < 0.6:
            picked.append(rng.choice(pool))
    if len(picked) < 2 and c.policy_id in R.DISTRACTORS and rng.random() < 0.3:
        picked.append(Trap.DISTRACTOR_POLICY_SIMILAR_NAME)
    picked.sort(key=lambda t: (t not in _FIRST, t.value))
    for t in picked:
        _apply(c, t, action_deadline)

    cc_deadline = Fact(key="corrected_claim_deadline", value=iso(corrected_deadline), source_file="denial_letter.txt")
    ids = [
        ("patient_id", f"P-{pid}", "eob_835.txt"), ("cpt", c.cpt, "eob_835.txt"), ("icd10", c.icd10, "eob_835.txt"),
        ("dos", iso(c.dos), "eob_835.txt"), ("billed", c.billed, "eob_835.txt"), ("payer_id", c.payer, "denial_letter.txt"),
        ("policy_id", policy, "policy_library"), ("carc", c.carc, "denial_letter.txt"),
        ("denial_date", iso(c.denial), "denial_letter.txt"),
        ("claim_submitted_date", iso(c.submitted), "claim_history.txt"),
        ("clearinghouse_accepted_date", iso(c.submitted), "claim_history.txt"),
        ("payer_received_date", iso(c.received), "claim_history.txt"),
        ("appeal_window_days", pay["appeal_days"], "denial_letter.txt"), ("appeal_deadline", iso(appeal_deadline), "denial_letter.txt"),
        ("action_deadline", iso(action_deadline), "denial_letter.txt"),
        ("as_of_date", iso(c.as_of), "task.md"), ("policy_effective_date", iso(eff), "policy_library"),
    ]
    if c.rarc:
        ids.append(("rarc", c.rarc, "denial_letter.txt"))
    c.facts[1:1] = [Fact(key=k, value=v, source_file=s) for k, v, s in ids] + [cc_deadline]

    return Truth(
        case_id=case_id, category=cat, split=split, payer_id=c.payer, policy_id=policy,
        patient=Patient(synthetic_id=f"P-{pid}"),
        claim=Claim(claim_no=str(claim_no), cpt=c.cpt, icd10=c.icd10, dos=c.dos, billed=c.billed),
        denial=Denial(carc=c.carc, rarc=c.rarc, denial_date=c.denial),
        appeal_deadline=appeal_deadline, action_deadline=action_deadline, policy_criteria=c.criteria,
        correct_decision=decision, traps=picked, required_enclosures=c.enclosures, facts=c.facts,
    )


def generate_all(seed=DEFAULT_SEED):
    rng = random.Random(f"{seed}:layout")
    taken_p, taken_c, truths, n = set(), set(), [], 0
    for cat, meta in R.CATEGORIES.items():
        decisions = list(meta["decisions"])
        rng.shuffle(decisions)
        dev_idx = rng.randrange(R.CASES_PER_CATEGORY)
        for i, dec in enumerate(decisions):
            n += 1
            truths.append(generate_case(seed, f"C-{n:04d}", cat, dec, "dev" if i == dev_idx else "test", taken_p, taken_c))
    return truths


def dataset_hash(root):
    """SHA-256 over every agent-visible file and truth.json under cases/ plus policy_library/ (not the manifest)."""
    root = Path(root)
    h = hashlib.sha256()
    files = sorted(p for d in ("cases", "policy_library") if (root / d).exists()
                   for p in (root / d).rglob("*") if p.is_file())
    for p in files:
        h.update(str(p.relative_to(root)).encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def git_state():
    """HEAD sha of the repository containing this code and whether the working tree is dirty (None if not a git repo)."""
    here = Path(__file__).resolve().parents[1]
    try:
        sha = subprocess.run(["git", "-C", str(here), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "-C", str(here), "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip())
        return {"git_sha": sha, "git_dirty": dirty}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"git_sha": None, "git_dirty": None}


def build_manifest(root, truths, seed, extra=None):
    root = Path(root)
    old = json.loads((root / "manifest.json").read_text()) if (root / "manifest.json").exists() else {}
    manifest = {
        "version": PROJECT_VERSION, "seed": seed, "dataset_hash": dataset_hash(root), **git_state(),
        "hash_scope": "cases/** (truth.json, task.md, docs/**) and policy_library/**",
        "counts": {"cases": len(truths), "dev": sum(t.split == "dev" for t in truths),
                   "test": sum(t.split == "test" for t in truths)},
        "cases": [{"case_id": t.case_id, "category": t.category, "category_name": R.CATEGORIES[t.category]["name"],
                   "split": t.split, "path": f"cases/{t.case_id}/truth.json"} for t in truths],
    }
    for k in ("datagen", "pilot_cases", "policy_library", "note_lint"):  # written by later pipeline steps; preserved here
        if k in old:
            manifest[k] = old[k]
    manifest.update(extra or {})
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def load_truths(root):
    man = json.loads((Path(root) / "manifest.json").read_text())
    return man, [Truth.model_validate_json((Path(root) / e["path"]).read_text()) for e in man["cases"]]


def write_truth(root, t):
    (Path(root) / "cases" / t.case_id / "truth.json").write_text(t.model_dump_json(indent=2) + "\n")


def clinical_truth_files(out):
    """Existing truth.json files that already hold clinical facts (evidence quotes) and would be lost on regeneration."""
    hits = []
    for p in sorted((Path(out) / "cases").glob("C-*/truth.json")):
        try:
            if any(f.get("evidence") for f in json.loads(p.read_text()).get("facts", [])):
                hits.append(p.parent.name)
        except ValueError:
            continue
    return hits


def write_dataset(truths, out, seed, force=False):
    out = Path(out)
    guarded = clinical_truth_files(out)
    if guarded and not force:
        raise SystemExit(f"refusing to overwrite truth.json files that hold clinical facts ({', '.join(guarded[:5])}"
                         f"{'...' if len(guarded) > 5 else ''}); pass --force to regenerate (then re-run the later stages)")
    for t in truths:
        p = out / "cases" / t.case_id / "truth.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(t.model_dump_json(indent=2) + "\n")
    return build_manifest(out, truths, seed)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", default="data")
    ap.add_argument("--force", action="store_true", help="overwrite truth files that already hold clinical facts")
    a = ap.parse_args()
    m = write_dataset(generate_all(a.seed), a.out, a.seed, a.force)
    print(f"wrote {m['counts']['cases']} cases ({m['counts']['dev']} dev / {m['counts']['test']} test) "
          f"to {a.out}; hash {m['dataset_hash'][:12]}")
