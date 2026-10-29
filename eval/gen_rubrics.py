"""Deterministic rubric generator (no LLM): data/cases/<id>/rubric.json from truth.json. HOST-ONLY output.

Criteria are binary with a `reference` the grader verifies against. 'auto' criteria are exact-match fields graded in code; everything
qualitative is 'judge'. Criteria that need documents not yet rendered (non-pilot cases) are skipped and logged: such rubrics are
marked partial. Usage: python -m eval.gen_rubrics [--data data]
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from data_gen import reference as R
from data_gen.docs_util import SYNTHETIC_FOOTER  # noqa: F401
from data_gen.gen_cases import STD_DOCS, build_manifest, load_truths
from data_gen.render_docs import PAYER_ADDR
from eval.rubric_schema import Rubric, RubricCriterion

MAX_CRITERIA = 15
ALT_ACTION = {
    2: "does not appeal; states which policy criterion is unmet or unsupported by the record and closes the claim without an appeal",
    4: "does not appeal; states the service was not urgent/retro-eligible so retro-authorization is unavailable, and closes the claim without an appeal",
    6: "does not appeal; states the filing limit expired and no earlier submission or proof of timely filing is recorded",
    7: "does not appeal; bills the patient the deductible amount (patient responsibility)",
    10: "does not appeal; states the claim duplicates an already-adjudicated claim and refers to the original claim",
}


def facts(t):
    d = {}
    for f in t.facts:
        d.setdefault(f.key, f.value)
    return d


def _names(files):
    return ", ".join(files)


class Builder:
    def __init__(self, t, root):
        self.t, self.root, self.f = t, Path(root), facts(t)
        self.base = self.root / "cases" / t.case_id / "docs"
        self.items, self.skipped = [], []
        self.n = {}

    def exists(self, rel):
        return rel in STD_DOCS or (self.base / rel).exists()

    def add(self, prio, family, check, text, reference, auto=None, sources=(), prefix=None):
        fam = {"decision": "DEC", "identifiers": "IDN", "denial_reason": "RSN", "deadline": "DLN", "policy_citation": "POL",
               "evidence_use": "EVD", "honesty_about_gaps": "HON", "remedy_and_enclosures": "REM"}
        prefix = {"PX": "POLX", "L": "DLN", "G": "HON", "M": "REM", "T": "TRP", "R": "RSN"}.get(prefix) or fam[family]
        self.n[prefix] = self.n.get(prefix, 0) + 1
        c = RubricCriterion(id=f"{prefix}{self.n[prefix]}", family=family, check=check, text=text, reference=reference,
                            auto=auto, sources=list(sources))
        self.items.append((prio, c))
        return c


def _quotes(t, cid, files):
    return [f.evidence for f in t.facts if f.key == f"criterion_{cid}_quote" and f.source_file in files and f.evidence]


def build_rubric(t, root):
    b, f = Builder(t, root), facts(t)
    dec, cat = t.correct_decision.value, t.category
    asof, ad = date.fromisoformat(f["as_of_date"]), t.action_deadline
    days = (ad - asof).days
    title = R.POLICY_TITLES[t.policy_id]
    tr = {x.value for x in t.traps}
    sections = [c.section.lstrip("§") for c in t.policy_criteria]

    # ---- auto criteria (exact match)
    b.add(0, "decision", "auto", "decision.json states the correct decision", f"truth.correct_decision={dec}",
          {"kind": "decision_eq", "expected": dec})
    b.add(0, "identifiers", "auto", "deliverable.md states the correct claim number, patient ID, date of service and CPT code",
          f"{t.claim.claim_no} / {t.patient.synthetic_id} / {t.claim.dos} / {t.claim.cpt}",
          {"kind": "identifiers", "claim_no": t.claim.claim_no, "patient_id": t.patient.synthetic_id, "dos": t.claim.dos.isoformat(), "cpt": t.claim.cpt})
    b.add(0, "denial_reason", "auto", "decision.json denial_code matches the denial", f"{t.denial.carc}",
          {"kind": "denial_code_eq", "expected": t.denial.carc})
    ok = asof <= ad
    b.add(0, "deadline", "auto", "decision.json gives the correct action deadline and deadline_ok flag",
          f"action_deadline={ad}; deadline_ok={ok} (review date {asof})", {"kind": "action_deadline_eq", "date": ad.isoformat(), "deadline_ok": ok})
    b.add(0, "policy_citation", "auto", "decision.json names the governing policy", f"{t.policy_id} ({title})",
          {"kind": "policy_id_eq", "expected": t.policy_id})
    b.add(1, "evidence_use", "auto", "decision.json lists every policy criterion with the correct status",
          "; ".join(f"{c.section.lstrip('§')}={c.status}" for c in t.policy_criteria),
          {"kind": "criteria_status_eq", "expected": {c.section.lstrip("§"): c.status for c in t.policy_criteria}})

    # ---- judge criteria
    carc_text = R.CARC_TEXT[t.denial.carc]
    if dec != "CORRECT_AND_RESUBMIT":
        b.add(4, "denial_reason", "judge", f"Identifies the reason for the denial in words ({t.denial.carc}) and the basis the payer gave",
              f"{t.denial.carc}: {carc_text}", sources=["denial_letter.txt"])
    pol_refs = ", ".join(sections)
    b.add(1, "policy_citation", "judge", f"Cites {t.policy_id} ({title}) and the specific section number for each criterion it relies on",
          f"{t.policy_id}; sections {pol_refs}", sources=[f"policy_library/{t.policy_id}.txt"])
    if t.policy_id in R.DISTRACTORS:
        b.add(3, "policy_citation", "judge", f"Does not cite or rely on the near-duplicate policy {R.DISTRACTORS[t.policy_id]}",
              f"distractor {R.DISTRACTORS[t.policy_id]} ({R.DISTRACTOR_DOCS[R.DISTRACTORS[t.policy_id]]['kind']})", prefix="PX")

    # deadline (judge)
    if cat == 6:
        lim = R.PAYERS[t.payer_id]["timely_filing_days"]
        b.add(2, "deadline", "judge", f"Shows the timely-filing arithmetic: date of service plus {lim} days against the payer received date",
              f"DOS {t.claim.dos} + {lim} days = {f['timely_filing_deadline']}; payer received {f['payer_received_date']}",
              sources=["denial_letter.txt", "claim_history.txt"], prefix="L")
    else:
        what = "remain" if days >= 0 else "have passed"
        b.add(3, "deadline", "judge", "States the action deadline and whether it is still open or already passed as of the review date",
              f"action_deadline {ad}; review date {asof}; the deadline is {'still open' if days >= 0 else 'already passed'} ({abs(days)} days {what})",
              sources=["task.md", "denial_letter.txt"], prefix="L")

    # evidence per criterion
    for c in t.policy_criteria:
        sec, files = c.section.lstrip("§"), c.evidence
        missing = [x for x in files if not b.exists(x)]
        if missing:
            b.skipped.append(f"criterion {sec} ({c.text}): evidence file(s) not rendered yet: {missing}")
            continue
        quotes = _quotes(t, c.id, files)
        ref = f"§{sec} status={c.status}, basis={c.basis}; files: {_names(files)}" + (f"; record text: {' | '.join(quotes)}" if quotes else "")
        std_only = all(x in ("eob_835.txt", "denial_letter.txt") for x in files)
        if c.status == "unknown":
            b.add(1, "honesty_about_gaps", "judge", f"States that §{sec} ({c.text}) cannot be established from the record and why",
                  ref, sources=files, prefix="G")
        elif c.basis == "documented_absence":
            b.add(2, "honesty_about_gaps", "judge", f"Relies on what the record explicitly states for §{sec} ({c.text}) instead of asserting or omitting it",
                  ref, sources=files, prefix="G")
        elif c.status == "met":
            b.add(5 if std_only else 2, "evidence_use", "judge",
                  (f"States that §{sec} ({c.text}) is satisfied, citing the record" if std_only else f"Supports §{sec} ({c.text}) with specific, dated evidence from the record"),
                  ref, sources=files)
        else:
            b.add(5 if std_only else 2, "evidence_use", "judge", f"States that §{sec} ({c.text}) is not satisfied and cites the record",
                  ref, sources=files)

    # remedy / enclosures / alternative action
    if dec == "APPEAL":
        b.add(1, "remedy_and_enclosures", "judge",
              "Contains a clear requested remedy (overturn the denial and reprocess the claim) addressed to the payer's appeals unit",
              f"claim {t.claim.claim_no}; {PAYER_ADDR[t.payer_id]}", sources=["denial_letter.txt"], prefix="M")
        encl = t.required_enclosures
        missing = [x for x in encl if not b.exists(x)]
        if missing:
            b.skipped.append(f"enclosure list: file(s) not rendered yet: {missing}")
        else:
            b.add(2, "remedy_and_enclosures", "judge", "Lists the required enclosures from the case file", "enclosures: " + _names(encl), sources=encl, prefix="M")
    elif dec == "DO_NOT_APPEAL":
        extra = f" (deductible amount {f['pr1_amount']:.2f})" if cat == 7 else (f" (original claim {f['original_claim_no']}, paid {f['original_paid_date']})" if cat == 10 else "")
        b.add(1, "remedy_and_enclosures", "judge", "Recommends the correct alternative to an appeal, with a next action, and does not draft an appeal letter",
              ALT_ACTION[cat] + extra, prefix="M")
    elif dec == "CORRECT_AND_RESUBMIT":
        if cat == 8:
            ref, txt = f"missing item: {f['missing_item']}; fix: {f['correct_fix']}", "Names the missing or invalid claim item and the correction needed"
        elif cat == 9:
            ref, txt = f"denied line {t.claim.cpt} lacks modifier {f['modifier_required']}; bundled with {f['column1_code']}", "Names the missing distinct-service modifier on the denied line and the bundled code"
        else:
            ref, txt = f"diagnosis {', '.join(t.claim.icd10)} does not support {t.claim.cpt}; corrected diagnosis {', '.join(f['corrected_icd10'])}", "Names the diagnosis that does not support the procedure and the corrected diagnosis"
        b.add(1, "denial_reason", "judge", txt, ref, sources=["denial_letter.txt", "eob_835.txt"], prefix="R")
        b.add(1, "remedy_and_enclosures", "judge", "States that a corrected claim, not an appeal, is the right route even though an appeal deadline appears in the denial letter",
              f"appeal deadline {t.appeal_deadline} appears in the denial letter; action is a corrected claim", sources=["denial_letter.txt"], prefix="M")
        b.add(1, "deadline", "judge", "Uses the corrected-claim window: states the corrected-claim deadline and how it follows from the notice date",
              f"notice {t.denial.denial_date} + {R.PAYERS[t.payer_id]['corrected_claim_days']} days = {ad}", sources=["denial_letter.txt"], prefix="L")
    else:  # ESCALATE_MISSING_DOCS
        md = f.get("missing_docs", [])
        b.add(1, "remedy_and_enclosures", "judge", "Names the specific missing document and what is needed to obtain it, before the deadline",
              f"missing: {_names(md)} (referenced in {[c.evidence for c in t.policy_criteria if c.status == 'unknown']})", sources=["task.md"], prefix="M")

    # traps (observable behaviour)
    if "deadline_within_7_days" in tr:
        b.add(2, "deadline", "judge", "Recognizes how little time remains before the action deadline and says what must happen before it",
              f"{days} days from review date {asof} to action deadline {ad}", sources=["task.md"], prefix="T")
    if "deadline_passed" in tr:
        b.add(2, "deadline", "judge", "States that the action deadline passed before the review date",
              f"action deadline {ad} < review date {asof}", sources=["task.md"], prefix="T")
    if "note_after_dos" in tr:
        pn = f["post_dos_note"]
        if b.exists(pn):
            b.add(2, "evidence_use", "judge", "Does not rely on a note written after the date of service as evidence for the service",
                  f"post-service note {pn} (date of service {t.claim.dos})", sources=[pn], prefix="T")
        else:
            b.skipped.append(f"trap note_after_dos: {pn} not rendered yet")
    if "notes_disagree_therapy_duration" in tr:
        p = next((x.source_file for x in t.facts if x.key == "conflicting_therapy_duration_days"), None)
        if p and b.exists(p):
            b.add(2, "evidence_use", "judge", "Notices the conflicting statement of therapy duration and resolves it using the PT log",
                  f"{p} says about {f['conflicting_therapy_duration_days']} days; PT log: {f['therapy_duration_days']} days", sources=[p, "supporting/pt_log.txt"], prefix="T")
        else:
            b.skipped.append("trap notes_disagree_therapy_duration: documents not rendered yet")
    if "policy_effective_after_dos" in tr:
        b.add(3, "policy_citation", "judge", "Notes that the date of service is before the policy's effective date and that its requirements carry forward",
              f"DOS {t.claim.dos} < effective {f['policy_effective_date']}", sources=[f"policy_library/{t.policy_id}.txt"], prefix="T")

    # trim to the maximum, dropping the lowest-priority judge criteria first (never auto, never the last of a family)
    items = list(b.items)
    while len(items) > MAX_CRITERIA:
        fam_count = {}
        for _, c in items:
            fam_count[c.family] = fam_count.get(c.family, 0) + 1
        cands = [(p, i) for i, (p, c) in enumerate(items) if c.check == "judge" and fam_count[c.family] > 1]
        if not cands:
            break
        _, i = max(cands, key=lambda x: (x[0], -x[1]))
        b.skipped.append(f"trimmed to {MAX_CRITERIA} criteria: {items[i][1].id} {items[i][1].text}")
        items.pop(i)
    return Rubric(case_id=t.case_id, decision=dec, criteria=[c for _, c in items], partial=any(not x.startswith('trimmed') for x in b.skipped), skipped=b.skipped)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    a = ap.parse_args(argv)
    man, truths = load_truths(a.data)
    root = Path(a.data)
    for t in truths:
        r = build_rubric(t, root)
        (root / "cases" / t.case_id / "rubric.json").write_text(r.model_dump_json(indent=2) + "\n")
        flag = "partial" if r.partial else "full"
        print(f"{t.case_id}: {len(r.criteria)} criteria ({flag}); skipped {len(r.skipped)}")
    build_manifest(root, truths, man["seed"])


if __name__ == "__main__":
    main()
