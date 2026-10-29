"""Validate generated truth.json files and the manifest (DEMO_SPEC section 3.7, checks that apply pre-rendering).

Findings are ERRORs (exit 1) or REVIEWs (need a human; exit 0 unless --strict). Unknown codes are never
silently passed: they become REVIEW findings. STRICTLY READ-ONLY: nothing is written under the data directory;
the report goes to stdout (and to --report PATH, which must be outside the data directory, e.g. under docs/).
Usage: python -m data_gen.validate_data [--data data] [--strict] [--truth-only] [--report docs/validation_report.json]
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from pydantic import ValidationError

from data_gen import reference as R
from data_gen.gen_cases import HARD_TRAPS, STD_DOCS, dataset_hash
from data_gen.schema import Decision, Trap, Truth
from data_gen.validate_docs import (check_agent_visible, check_documents, check_manifest_datagen, check_mount_safety,
                                    check_policy_library)

SSN = re.compile(r"\b(\d{3})-(\d{2})-(\d{4})\b")
NOTE_DATE = re.compile(r"^notes/(\d{4}-\d{2}-\d{2})_")
EXCLUDES1 = (re.compile(r"^M54\.1"), re.compile(r"^M51\.1"))  # radiculopathy vs disc disorder with radiculopathy (at least this pair)
REQUIRED_FACTS = ["action_deadline", "clearinghouse_accepted_date", "payer_received_date", "corrected_claim_deadline", "policy_effective_date", "claim_no", "patient_id", "cpt", "icd10", "dos", "billed", "payer_id", "policy_id", "carc",
                  "denial_date", "claim_submitted_date", "appeal_window_days", "appeal_deadline", "as_of_date"]


class Report:
    def __init__(self):
        self.errors, self.reviews = [], []

    def error(self, where, msg):
        self.errors.append({"where": where, "message": msg})

    def review(self, where, msg):
        self.reviews.append({"where": where, "message": msg})


def _facts(t):
    d = {}
    for f in t.facts:
        d.setdefault(f.key, f.value)
    return d


def _d(s):
    return date.fromisoformat(s)


def check_case(t, rep, raw_text=""):
    w = t.case_id
    f = _facts(t)
    payer = R.PAYERS.get(t.payer_id)
    meta = R.CATEGORIES[t.category]

    # required fields / fact table agree with the structured fields
    missing = [k for k in REQUIRED_FACTS if k not in f]
    for k in missing:
        rep.error(w, f"missing required fact '{k}'")
    if missing:
        return
    same = {"claim_no": t.claim.claim_no, "patient_id": t.patient.synthetic_id, "cpt": t.claim.cpt,
            "icd10": t.claim.icd10, "dos": t.claim.dos.isoformat(), "billed": t.claim.billed,
            "payer_id": t.payer_id, "policy_id": t.policy_id, "carc": t.denial.carc,
            "denial_date": t.denial.denial_date.isoformat(), "appeal_deadline": t.appeal_deadline.isoformat(),
            "action_deadline": t.action_deadline.isoformat()}
    for k, v in same.items():
        if f[k] != v:
            rep.error(w, f"fact '{k}'={f[k]!r} disagrees with structured field {v!r}")

    # payers fictional; policy/payer/category consistent
    if payer is None:
        rep.error(w, f"payer {t.payer_id} is not in the fictional payer table")
        return
    if R.POLICIES.get(t.policy_id) != t.payer_id:
        rep.error(w, f"policy {t.policy_id} does not belong to payer {t.payer_id}")
    if t.policy_id != meta["policy"]:
        rep.error(w, f"policy {t.policy_id} != category {t.category} policy {meta['policy']}")

    # category / decision consistency
    if t.correct_decision not in meta["decisions"]:
        rep.error(w, f"decision {t.correct_decision.value} not allowed for category {t.category}")
    if t.category == 8:
        if t.denial.carc not in ("CO-4", "CO-16"):
            rep.error(w, f"category 8 CARC {t.denial.carc} not CO-4/CO-16")
    elif t.denial.carc != meta["carc"]:
        rep.error(w, f"CARC {t.denial.carc} != category {t.category} CARC {meta['carc']}")
    status = [c.status for c in t.policy_criteria]
    if t.correct_decision == Decision.APPEAL:
        if any(x != "met" for x in status):
            rep.error(w, "APPEAL case has a criterion that is not 'met'")
        if not t.required_enclosures:
            rep.error(w, "APPEAL case has no required_enclosures")
    else:
        if all(x == "met" for x in status):
            rep.error(w, f"{t.correct_decision.value} case has every criterion met")
        if t.required_enclosures:
            rep.error(w, "non-APPEAL case lists required_enclosures")
    if t.correct_decision == Decision.ESCALATE_MISSING_DOCS:
        if "missing_docs" not in f:
            rep.error(w, "ESCALATE_MISSING_DOCS case has no 'missing_docs' fact")
        if "unknown" not in status:
            rep.error(w, "ESCALATE_MISSING_DOCS case has no 'unknown' criterion")
    elif "unknown" in status:
        rep.error(w, "'unknown' criterion on a case that is not ESCALATE_MISSING_DOCS")
    # absence model: unknown <=> missing_evidence; documented_absence is met/unmet and must be backed by a quote
    for c in t.policy_criteria:
        if (c.status == "unknown") != (c.basis == "missing_evidence"):
            rep.error(w, f"criterion {c.id}: status {c.status!r} and basis {c.basis!r} disagree (unknown <=> missing_evidence)")
    # dates ordered + deadline math
    dos, sub, den = t.claim.dos, _d(f["claim_submitted_date"]), t.denial.denial_date
    rcv = _d(f["payer_received_date"])
    as_of, dl = _d(f["as_of_date"]), t.action_deadline
    if not dos <= sub <= rcv <= den:
        rep.error(w, f"expected DOS <= submitted <= payer received <= denial, got {dos}, {sub}, {rcv}, {den}")
    if f["clearinghouse_accepted_date"] != f["claim_submitted_date"]:
        rep.error(w, "clearinghouse acceptance must be on the submission date")
    want_action = _d(f["corrected_claim_deadline"]) if t.correct_decision == Decision.CORRECT_AND_RESUBMIT else t.appeal_deadline
    if t.action_deadline != want_action:
        rep.error(w, f"action_deadline {t.action_deadline} must be the {'corrected-claim' if t.correct_decision == Decision.CORRECT_AND_RESUBMIT else 'appeal'} deadline {want_action}")
    if not den < as_of:
        rep.error(w, f"as_of {as_of} must be after denial {den}")
    if f["appeal_window_days"] != payer["appeal_days"]:
        rep.error(w, f"appeal window {f['appeal_window_days']} != payer window {payer['appeal_days']}")
    if t.appeal_deadline != den + timedelta(days=payer["appeal_days"]):
        rep.error(w, f"appeal_deadline {t.appeal_deadline} != denial {den} + {payer['appeal_days']}d")
    if _d(f["corrected_claim_deadline"]) != den + timedelta(days=payer["corrected_claim_days"]):
        rep.error(w, "corrected_claim_deadline math is wrong")
    if "timely_filing_deadline" in f and _d(f["timely_filing_deadline"]) != dos + timedelta(days=payer["timely_filing_days"]):
        rep.error(w, "timely_filing_deadline math is wrong")

    # documents referenced exist in the plan; note dates
    planned = {x.value for x in t.facts if x.key == "planned_document"}
    known = planned | set(STD_DOCS)
    for c in t.policy_criteria:
        for e in c.evidence:
            if e not in known:
                rep.error(w, f"criterion {c.id} evidence '{e}' is not a planned document")
            m = NOTE_DATE.match(e)
            if m and _d(m.group(1)) > dos:
                rep.error(w, f"criterion {c.id} cites note {e} dated after DOS {dos}")
    for e in t.required_enclosures:
        if e not in known:
            rep.error(w, f"enclosure '{e}' is not a planned document")
    for x in t.facts:
        if x.source_file not in known | {"task.md", "policy_library"}:
            rep.error(w, f"fact '{x.key}' cites unknown source '{x.source_file}'")
    for p in planned:
        m = NOTE_DATE.match(p)
        if m and _d(m.group(1)) > as_of:
            rep.error(w, f"note {p} is dated after the as-of date {as_of}")

    # traps
    if len(set(t.traps)) != len(t.traps) or len(t.traps) > 2:
        rep.error(w, f"traps must be unique and at most 2: {[x.value for x in t.traps]}")
    hard = [x for x in t.traps if x in HARD_TRAPS]
    if len(hard) > 1:
        rep.error(w, f"stacked hard traps (at most one allowed): {[x.value for x in hard]}")
    if (Trap.CRITERION_NO_SUPPORTING_DOC in t.traps) != (t.correct_decision == Decision.ESCALATE_MISSING_DOCS):
        rep.error(w, "criterion_no_supporting_doc must be present exactly on ESCALATE_MISSING_DOCS cases")
    left = (dl - as_of).days
    if Trap.DEADLINE_WITHIN_7_DAYS in t.traps and not 1 <= left <= 7:
        rep.error(w, f"deadline_within_7_days but {left} days remain")
    if Trap.DEADLINE_PASSED in t.traps:
        if left >= 0:
            rep.error(w, "deadline_passed but deadline not passed at as_of")
        if t.correct_decision != Decision.DO_NOT_APPEAL:
            rep.error(w, "deadline_passed only allowed on DO_NOT_APPEAL cases")
    if not ({Trap.DEADLINE_WITHIN_7_DAYS, Trap.DEADLINE_PASSED} & set(t.traps)) and left < 8:
        rep.error(w, f"only {left} days to deadline without a deadline trap")
    if Trap.NOTE_AFTER_DOS in t.traps:
        pn = f.get("post_dos_note", "")
        m = NOTE_DATE.match(pn)
        if not m or _d(m.group(1)) <= dos:
            rep.error(w, "note_after_dos trap without a post-DOS note")
    if Trap.DISTRACTOR_POLICY_SIMILAR_NAME in t.traps and f.get("distractor_policy_id") != R.DISTRACTORS.get(t.policy_id):
        rep.error(w, "distractor trap fact does not match registry")
    eff = R.POLICY_EFFECTIVE.get(t.policy_id)
    if eff is None or f["policy_effective_date"] != eff.isoformat():
        rep.error(w, "policy_effective_date missing or disagrees with reference.py")
    elif (dos < eff) != (Trap.POLICY_EFFECTIVE_AFTER_DOS in t.traps):
        rep.error(w, f"DOS {dos} vs policy effective {eff} disagrees with the policy_effective_after_dos trap flag")

    # category-specific semantics
    crit = {c.id: c for c in t.policy_criteria}
    if "therapy_duration_days" in f and t.category in (1, 2) and "C1" in crit:
        if (crit["C1"].status == "met") != (f["therapy_duration_days"] >= 42):
            rep.error(w, "C1 status disagrees with therapy_duration_days >= 42")
    if t.category == 5 and _d(f["clearinghouse_accepted_date"]) > dos + timedelta(days=payer["timely_filing_days"]):
        rep.error(w, "cat 5 proof of filing is after the filing limit")
    if t.category == 6 and sub <= dos + timedelta(days=payer["timely_filing_days"]):
        rep.error(w, "cat 6 submission is within the filing limit, so the claim would not be expired")
    if t.category == 12 and f["denied_visit_number"] != R.PT_VISIT_LIMIT + 1:
        rep.error(w, f"cat 12 denied visit must be the first over the limit ({R.PT_VISIT_LIMIT + 1}), got {f['denied_visit_number']}")
    if t.category in (5, 6) and not _d(f["payer_received_date"]) > dos + timedelta(days=payer["timely_filing_days"]):
        rep.error(w, "payer received date is within the filing limit, so CO-29 would be wrong")
    if t.category == 3 and (_d(f["retro_request_date"]) - dos).days > R.RETRO_AUTH_WINDOW_DAYS:
        rep.error(w, "cat 3 retro request is outside the retro-auth window")
    if t.category == 4 and "retro_request_date" in f and (_d(f["retro_request_date"]) - dos).days <= R.RETRO_AUTH_WINDOW_DAYS:
        rep.error(w, "cat 4 retro request is inside the window, so it would be retro-eligible")
    if t.category == 7:
        want = round(min(f["allowed_amount"], f["deductible_total"] - f["deductible_met_before_dos"]), 2)
        if f["pr1_amount"] != want or want <= 0:
            rep.error(w, f"pr1_amount {f['pr1_amount']} != min(allowed, remaining deductible) {want}")
    if t.category == 9 and f["modifier_present"] != (t.correct_decision == Decision.APPEAL):
        rep.error(w, "cat 9 modifier_present disagrees with decision")
    if t.category == 10 and not _d(f["original_paid_date"]) <= sub:
        rep.error(w, "cat 10 duplicate submitted before the original was paid")
    if t.category == 10 and f["original_claim_no"] == t.claim.claim_no:
        rep.error(w, "cat 10 original claim number equals the denied claim number")

    # code table: unknown -> REVIEW, known-but-invalid pairing -> ERROR (inverted for category 11)
    def check_pair(cpt, icds, expect_valid, label):
        unknown = [c for c in [cpt] if c not in R.CPT] + [i for i in icds if i not in R.ICD10]
        if unknown:
            rep.review(w, f"{label}: code(s) {unknown} not in local code table; needs human review")
            return
        for i in icds:
            ok = i in R.VALID_PAIRS.get(cpt, [])
            if ok != expect_valid:
                rep.error(w, f"{label}: CPT {cpt} / ICD-10 {i} is {'valid' if ok else 'not valid'} in the table, expected "
                             f"{'valid' if expect_valid else 'invalid'}")
    check_pair(t.claim.cpt, t.claim.icd10, t.category != 11, "claim pairing")
    if t.category == 11:
        check_pair(t.claim.cpt, f["corrected_icd10"], True, "corrected pairing")
    if "column1_code" in f:
        check_pair(f["column1_code"], t.claim.icd10, True, "bundling column-1 pairing")

    # ICD-10 Excludes1 (at least M54.1x with M51.1x) on any diagnosis list
    for label, codes in (("claim", t.claim.icd10), ("corrected", f.get("corrected_icd10", []) if t.category == 11 else [])):
        if any(EXCLUDES1[0].match(c) for c in codes) and any(EXCLUDES1[1].match(c) for c in codes):
            rep.error(w, f"{label} diagnoses {codes} violate ICD-10 Excludes1 (M54.1x with M51.1x)")
    if t.category in (1, 2) and len(t.claim.icd10) != 1:
        rep.error(w, "categories 1-2 must carry exactly one diagnosis")

    # SSN-looking strings: anything in a non-9xx range is an error; 9xx is allowed but surfaced
    for m in SSN.finditer(raw_text):
        (rep.error if not m.group(1).startswith("9") else rep.review)(w, f"SSN-like string '{m.group(0)}' found")


def validate(data_dir, check_docs=True):
    rep, root = Report(), Path(data_dir)
    mpath = root / "manifest.json"
    if not mpath.exists():
        rep.error("manifest", f"{mpath} not found")
        return rep, []
    try:
        man = json.loads(mpath.read_text())
        man["cases"]
    except (ValueError, KeyError, TypeError):
        rep.error("manifest", f"{mpath} is not a valid manifest (unparseable or no 'cases')")
        return rep, []
    truths = []
    for e in man["cases"]:
        p = root / e["path"]
        try:
            raw = p.read_text()
            t = Truth.model_validate_json(raw)
        except (OSError, ValidationError) as ex:
            rep.error(e["case_id"], f"cannot load {p}: {str(ex)[:300]}")
            continue
        if t.case_id != e["case_id"] or t.category != e["category"] or t.split != e["split"]:
            rep.error(e["case_id"], "manifest entry disagrees with truth.json (id/category/split)")
        truths.append((t, raw))
    ts = [t for t, _ in truths]

    # global checks
    on_disk = {p.name for p in (root / "cases").glob("C-*")} if (root / "cases").exists() else set()
    if on_disk != {e["case_id"] for e in man["cases"]}:
        rep.error("manifest", "case directories on disk differ from the manifest")
    for key, label in (("case_id", "case id"), ):
        dup = [k for k, n in Counter(getattr(t, key) for t in ts).items() if n > 1]
        if dup:
            rep.error("dataset", f"duplicate {label}: {dup}")
    for label, vals in (("claim_no", [t.claim.claim_no for t in ts]), ("patient id", [t.patient.synthetic_id for t in ts])):
        dup = [k for k, n in Counter(vals).items() if n > 1]
        if dup:
            rep.error("dataset", f"duplicate {label}: {dup}")
    n_cat, per = len(R.CATEGORIES) * R.CASES_PER_CATEGORY, Counter((t.category, t.split) for t in ts)
    if len(ts) != n_cat:
        rep.error("dataset", f"expected {n_cat} cases, found {len(ts)}")
    n_dev, n_test = sum(t.split == "dev" for t in ts), sum(t.split == "test" for t in ts)
    if (n_dev, n_test) != (12, 48):
        rep.error("dataset", f"split counts must be 12 dev / 48 test, got {n_dev} / {n_test}")
    for cat in R.CATEGORIES:
        if (per[(cat, "dev")], per[(cat, "test")]) != (R.DEV_PER_CATEGORY, R.CASES_PER_CATEGORY - R.DEV_PER_CATEGORY):
            rep.error("dataset", f"category {cat} split is {per[(cat, 'dev')]} dev / {per[(cat, 'test')]} test, expected 1 / 4")
        got = sorted(t.correct_decision.value for t in ts if t.category == cat)
        want = sorted(d.value for d in R.CATEGORIES[cat]["decisions"])
        if got != want:
            rep.error("dataset", f"category {cat} decision mix {got} != expected {want}")
    if man.get("counts") != {"cases": len(ts), "dev": n_dev, "test": n_test}:
        rep.error("manifest", "manifest counts disagree with truth files")
    if ts and man.get("dataset_hash") != dataset_hash(root):
        rep.error("manifest", "dataset_hash does not match truth.json contents (data changed after generation?)")

    for t, raw in truths:
        check_case(t, rep, raw)
    if check_docs and ts:
        check_policy_library(root, ts, rep)
        check_documents(root, ts, man, rep)
        check_agent_visible(root, ts, rep)
        check_mount_safety(root, rep)
        check_manifest_datagen(root, man, rep)
    return rep, ts


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--strict", action="store_true", help="treat REVIEW findings as failures")
    ap.add_argument("--truth-only", action="store_true", help="skip document/policy-library checks")
    ap.add_argument("--report", help="also write a JSON report here (must be outside the data directory)")
    a = ap.parse_args(argv)
    rep, ts = validate(a.data, check_docs=not a.truth_only)
    if a.report:
        rp, dp = Path(a.report).resolve(), Path(a.data).resolve()
        if dp in rp.parents or rp == dp:
            raise SystemExit("--report must not be inside the data directory (validate_data is read-only there)")
        rp.write_text(json.dumps({"cases": len(ts), "errors": rep.errors, "reviews": rep.reviews}, indent=2) + "\n")
    for e in rep.errors:
        print(f"ERROR   {e['where']}: {e['message']}")
    for r in rep.reviews:
        print(f"REVIEW  {r['where']}: {r['message']}")
    print(f"{len(ts)} cases checked: {len(rep.errors)} error(s), {len(rep.reviews)} item(s) for human review")
    return 1 if rep.errors or (a.strict and rep.reviews) else 0


if __name__ == "__main__":
    sys.exit(main())
