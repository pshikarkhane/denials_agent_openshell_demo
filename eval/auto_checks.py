"""Code-graded ('auto') rubric criteria: exact-match fields only. Pooled with judge verdicts."""
import re
from datetime import date

from eval.deliverable_schema import normalize_section

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def date_variants(iso):
    d = date.fromisoformat(iso)
    m = MONTHS[d.month - 1]
    return {iso, f"{m} {d.day}, {d.year}", f"{m[:3]} {d.day}, {d.year}", f"{d.month}/{d.day}/{d.year}",
            f"{d.month:02d}/{d.day:02d}/{d.year}", f"{d.day} {m} {d.year}"}


def norm_code(s):
    return re.sub(r"[\s-]", "", str(s)).upper()


def grade_auto(spec, decision, deliverable_text):
    """Returns (passed: bool, detail: str). `decision` is a DecisionJson or None (invalid/missing decision.json)."""
    kind = spec["kind"]
    if kind == "identifiers":
        text = deliverable_text or ""
        miss = [k for k in ("claim_no", "patient_id", "cpt") if spec[k] not in text]
        if not any(v in text for v in date_variants(spec["dos"])):
            miss.append("dos")
        return (not miss, "ok" if not miss else f"missing/incorrect in deliverable.md: {miss}")
    if decision is None:
        return False, "decision.json missing or invalid"
    if kind == "decision_eq":
        return decision.decision == spec["expected"], f"decision={decision.decision} expected={spec['expected']}"
    if kind == "denial_code_eq":
        return norm_code(decision.denial_code) == norm_code(spec["expected"]), f"denial_code={decision.denial_code} expected={spec['expected']}"
    if kind == "policy_id_eq":
        return decision.policy_id == spec["expected"], f"policy_id={decision.policy_id} expected={spec['expected']}"
    if kind == "action_deadline_eq":
        ok = decision.action_deadline.isoformat() == spec["date"] and decision.deadline_ok == spec["deadline_ok"]
        return ok, f"action_deadline={decision.action_deadline} deadline_ok={decision.deadline_ok} expected={spec['date']}/{spec['deadline_ok']}"
    if kind == "criteria_status_eq":
        got = {normalize_section(c.id): c.status for c in decision.criteria}
        bad = {s: (got.get(s), st) for s, st in spec["expected"].items() if got.get(s) != st}
        return (not bad, "ok" if not bad else f"mismatch (got, expected): {bad}")
    raise ValueError(f"unknown auto kind {kind}")
