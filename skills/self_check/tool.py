"""self_check: deterministic checks of a candidate deliverable.md + decision.json against the case documents and the policy library.
No model calls. Returns a checklist with severity and a short revision hint per failure. `ok` is true when no ERROR check failed."""
import json
import re

from pydantic import BaseModel

from skills.common.deliverable_schema import normalize_section, validate_decision_text
from skills.assess_appealability.tool import Input as AssessInput, requirement_sections, run_tool as assess_run
from skills.common.citations import Corpus, verify_citations
from skills.common.io import SkillError, SkillInput
from skills.common.text import mentions_date
from skills.draft_deliverable.tool import read_output_text
from skills.parse_denial_eob.tool import Input as ParseInput, run_tool as parse_run
from skills.retrieve_payer_policy.tool import Input as RetInput, run_tool as ret_run


class Input(SkillInput):
    deliverable_path: str | None = None
    deliverable_text: str | None = None
    decision_path: str | None = None
    decision_text: str | None = None


class Output(BaseModel):
    ok: bool
    n_errors: int
    n_warnings: int
    checks: list[dict]
    citations_failed: list[dict]


# Identifiers and the deadline are checked by their own content checks (identifier_*, deadline_in_text), so no heading is required for them.
LETTER_SECTIONS = {"remedy": r"remed|request", "enclosures": r"enclos", "gaps": r"\bgaps?\b"}
MEMO_SECTIONS = {"next action": r"next action|next step|recommend", "gaps": r"\bgaps?\b"}
LETTER_SIGNS = (r"^#\s*appeal letter", r"respectfully request[^.]*overturn", r"^\*\*to:\*\*[^\n]*appeals unit", r"^to:[^\n]*appeals unit")


LABEL = re.compile(r"^\s*(?:[-*]\s*)?\**([A-Za-z][A-Za-z /&\-]{2,40}?)\**\s*:")


def headings(text):
    """Section headings: markdown headings, whole-line bold, ALL-CAPS lines, and plain-text `Label:` lines (a plain-text memo is a legitimate format)."""
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("#") or re.fullmatch(r"\*\*[^*]+\*\*:?", s):
            out.append(s.lstrip("#").strip("* :").lower())
        elif s and len(s) <= 60 and s.upper() == s and re.search(r"[A-Z]{3}", s):
            out.append(s.lower())
        else:
            m = LABEL.match(ln)
            if m:
                out.append(m.group(1).strip().lower())
    return out


def run_tool(inp, ctx):
    deliverable = read_output_text(ctx, inp.deliverable_path, inp.deliverable_text, "deliverable")
    dtext = read_output_text(ctx, inp.decision_path, inp.decision_text, "decision")
    base = dict(case_root=inp.case_root, policy_root=inp.policy_root, events_file=inp.events_file, run_id=inp.run_id, case_id=inp.case_id)
    P = parse_run(ParseInput(**base), ctx)
    A = assess_run(AssessInput(**base), ctx)
    corpus = Corpus(ctx)
    R = ret_run(RetInput(**base, payer=P.payer.id or "", dos=P.dos or "", cpt=P.cpt, service_description=P.service_description, icd10=P.icd10,
                         denial_code=P.denial["carc"], denial_text=P.denial["carc_text"], reason_text=P.denial["reason_text"], policy_title=P.policy_title), ctx)
    checks = []

    def chk(cid, name, ok, detail="", hint="", sev="error"):
        checks.append({"id": cid, "check": name, "pass": bool(ok), "severity": sev, "detail": detail, "hint": hint if not ok else ""})

    dec, errs = validate_decision_text(dtext)
    chk("decision_json_valid", "decision.json matches the schema", dec is not None, "; ".join(errs[:4]), "fix the fields named in the detail (see eval/deliverable_schema.py)")
    for key, label, val in (("claim_no", "claim number", P.claim_no), ("patient_id", "patient ID", P.patient.id), ("cpt", "CPT code", P.cpt)):
        chk(f"identifier_{key}", f"deliverable states the correct {label}", bool(val) and val in deliverable, f"expected {val}", f"state the {label} exactly as in the denial letter ({val})")
    chk("identifier_dos", "deliverable states the correct date of service", bool(P.dos) and mentions_date(deliverable, P.dos), f"expected {P.dos}", f"state the date of service ({P.dos})")
    unfilled = re.findall(r"<<FILL[^>]*>>", deliverable)
    chk("no_placeholders", "no unfilled <<FILL>> placeholders remain", not unfilled, f"{len(unfilled)} placeholder(s) left", "replace every <<FILL: ...>> with content or remove the section")
    hs = headings(deliverable)
    appeal_like = any(re.search(p, deliverable, re.I | re.M) for p in LETTER_SIGNS)
    if dec is not None:
        task_case = P.claim_details.get("case_id_in_task")
        chk("case_id", "decision.json case_id matches the case", task_case is None or dec.case_id == task_case, f"decision.json says {dec.case_id}, task says {task_case}", "use the case id from task.md")
        chk("denial_code", "decision.json denial_code matches the denial letter", re.sub(r"[\s-]", "", dec.denial_code).upper() == re.sub(r"[\s-]", "", P.denial["carc"] or "").upper(),
            f"expected {P.denial['carc']}", f"set denial_code to {P.denial['carc']}")
        corrected = dec.decision == "CORRECT_AND_RESUBMIT"
        key = "corrected_claim" if corrected else "appeal"
        want = A.deadlines[key]["date"] if A.deadlines.get(key) else None
        chk("action_deadline", "action_deadline equals the computed deadline for this decision", want is not None and dec.action_deadline.isoformat() == want,
            f"decision.json {dec.action_deadline}; computed {want} ({A.deadlines[key]['basis'] if want else 'unavailable'})",
            f"use the {'corrected-claim' if corrected else 'appeal'} deadline {want} (from assess_appealability)")
        ok_flag = bool(A.as_of_date and want and A.as_of_date <= dec.action_deadline.isoformat())
        chk("deadline_ok", "deadline_ok is correct for the review date", dec.deadline_ok == ok_flag, f"review date {A.as_of_date} vs action_deadline {dec.action_deadline}; expected {ok_flag}", f"set deadline_ok to {str(ok_flag).lower()}")
        chk("deadline_in_text", "deliverable states the action deadline date", bool(want) and mentions_date(deliverable, want), f"expected {want}", f"state the deadline {want} and its relation to the review date")
        pol_ok = dec.policy_id in corpus.policies
        chk("policy_exists", "policy_id exists in the policy library", pol_ok, dec.policy_id, "use a policy id from retrieve_payer_policy")
        if R.status == "selected":
            chk("policy_matches_retrieval", "policy_id is the policy retrieved for this denial", dec.policy_id == R.policy["policy_id"], f"retrieved {R.policy['policy_id']}", f"use {R.policy['policy_id']} or explain the difference in Gaps")
        else:
            chk("policy_matches_retrieval", "policy retrieval was unambiguous", False, f"retrieval status {R.status}: {R.reason}", "state which policy you chose and why", sev="warn")
        pol = corpus.policies.get(dec.policy_id)
        for c in dec.criteria:
            exists = bool(pol) and (c.id in pol.sections or any(k.startswith(c.id + "(") for k in pol.sections) or c.id in {a for a, _ in pol.params})
            chk(f"criterion_section_{c.id}", f"criterion {c.id} is a section of {dec.policy_id}", exists, "", "use section ids that exist in the policy (retrieve_payer_policy returns them)")
            if c.evidence:
                chk(f"evidence_file_{c.id}", f"evidence file for {c.id} exists", corpus.has_file(c.evidence), c.evidence, "cite a file in the case documents or null")
        if pol:
            missing = [s for s in requirement_sections(pol) if s not in {c.id for c in dec.criteria}]
            chk("criteria_cover_requirements", "decision.json lists every requirement section of the policy", not missing, f"not listed: {missing}", "add the sections or state in Gaps why they do not apply", sev="warn")
        for e in dec.enclosures:
            chk(f"enclosure_{e}", f"enclosure {e} exists", corpus.has_file(e), e, "list only files that exist in the case documents")
            chk(f"enclosure_named_{e}", f"enclosure {e} is named in the deliverable", e in deliverable, e, "name each enclosure in the deliverable", sev="warn")
        if dec.decision == "APPEAL":
            chk("appeal_has_enclosures", "an appeal lists its enclosures", bool(dec.enclosures), "", "list the supporting documents you enclose")
        statuses = {c.status for c in dec.criteria}
        blank = [b["field"] for b in P.blank_fields if b["field"] in ("rendering_provider", "referring_provider", "place_of_service")]
        need_gap = dec.decision == "ESCALATE_MISSING_DOCS" or "unknown" in statuses or (corrected and bool(blank))
        why = "decision is ESCALATE_MISSING_DOCS" if dec.decision == "ESCALATE_MISSING_DOCS" else ("a criterion is unknown" if "unknown" in statuses else f"the remit shows blank field(s) {blank}")
        chk("gaps_listed", "gaps are listed where a required value or document is absent", (not need_gap) or bool(dec.gaps), why if need_gap else "no absent required value detected", "list what is missing and what is needed to obtain it in decision.json gaps and in the Gaps section")
        required = LETTER_SECTIONS if dec.decision == "APPEAL" else MEMO_SECTIONS
        for name, rx in required.items():
            chk(f"section_{name.replace(' ', '_')}", f"deliverable has a '{name}' section", any(re.search(rx, h) for h in hs), "", f"add a heading for {name}")
        if dec.decision == "APPEAL":
            pass
        else:
            chk("no_appeal_letter", "an appeal letter exists only when the decision is APPEAL", not appeal_like, "the deliverable reads as an appeal letter", "write a decision memo instead of an appeal letter, or change the decision")
    cites = verify_citations(deliverable, corpus, dec.policy_id if dec else None)
    failed = [c for c in cites if not c["pass"]]
    chk("citations", "every citation (file, quote, policy id, section id) resolves", not failed,
        "; ".join(f"{c['kind']}: {c['text'][:60]} ({c['reason']})" for c in failed[:5]), "remove or correct the citations listed; quote only text that appears in the documents")
    n_err = sum(1 for c in checks if not c["pass"] and c["severity"] == "error")
    n_warn = sum(1 for c in checks if not c["pass"] and c["severity"] == "warn")
    return Output(ok=n_err == 0, n_errors=n_err, n_warnings=n_warn, checks=checks, citations_failed=failed)
