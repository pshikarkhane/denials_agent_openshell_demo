"""draft_deliverable: VALIDATION HELPERS for the model's drafting. It does not write the deliverable. Actions:
  validate_decision  validate decision.json against skills/common/deliverable_schema.py
  render_skeleton    deliverable.md skeleton (identifiers + computed facts + <<FILL: ...>> placeholders) for a letter or a memo
  verify_citations   every cited file / line / quote / policy id / section id must exist in the case documents or policy library"""
import json
from typing import Literal

from pydantic import BaseModel

from skills.common.deliverable_schema import validate_decision_text
from skills.assess_appealability.tool import Input as AssessInput, run_tool as assess_run
from skills.common.citations import Corpus, verify_citations
from skills.common.io import SkillError, SkillInput
from skills.parse_denial_eob.tool import Input as ParseInput, run_tool as parse_run


class Input(SkillInput):
    action: Literal["validate_decision", "render_skeleton", "verify_citations"]
    kind: Literal["letter", "memo"] | None = None          # render_skeleton: choose after you decide
    decision_path: str | None = None                       # relative to OUTPUT_ROOT
    decision_text: str | None = None
    deliverable_path: str | None = None                    # relative to OUTPUT_ROOT
    deliverable_text: str | None = None
    policy_id: str | None = None


class Output(BaseModel):
    action: str
    valid: bool | None = None
    errors: list[str] = []
    skeleton: str | None = None
    citations: list[dict] = []
    summary: dict = {}


def read_output_text(ctx, path, text, label):
    if text is not None:
        return text
    if path is None:
        raise SkillError("bad_input", f"{label}: give {label}_text or {label}_path")
    return ctx.read("output", path)


def run_tool(inp, ctx):
    if inp.action == "validate_decision":
        text = read_output_text(ctx, inp.decision_path, inp.decision_text, "decision")
        _, errs = validate_decision_text(text, inp.case_id)
        return Output(action=inp.action, valid=not errs, errors=errs)
    if inp.action == "verify_citations":
        text = read_output_text(ctx, inp.deliverable_path, inp.deliverable_text, "deliverable")
        pid = inp.policy_id
        if pid is None and (inp.decision_text or inp.decision_path):
            try:
                d = json.loads(read_output_text(ctx, inp.decision_path, inp.decision_text, "decision"))
                pid = d.get("policy_id")
            except ValueError:
                pass
        res = verify_citations(text, Corpus(ctx), pid)
        bad = [r for r in res if not r["pass"]]
        return Output(action=inp.action, valid=not bad, citations=res, summary={"total": len(res), "failed": len(bad)})
    if inp.kind is None:
        raise SkillError("bad_input", "render_skeleton needs kind='letter' or 'memo'")
    return Output(action=inp.action, skeleton=render_skeleton(inp, ctx))


FILL = "<<FILL: {}>>"


def render_skeleton(inp, ctx):
    base = dict(case_root=inp.case_root, policy_root=inp.policy_root, events_file=inp.events_file, run_id=inp.run_id, case_id=inp.case_id)
    P = parse_run(ParseInput(**base), ctx)
    A = assess_run(AssessInput(**base, policy_id=inp.policy_id), ctx)
    letter = inp.kind == "letter"
    d = A.deadlines
    L = [f"# {'Appeal Letter' if letter else 'Decision Memo'}: Claim {P.claim_no}", ""]
    if letter:
        L += [f"**To:** {P.appeal['address'] or FILL.format('appeals unit name and address from the denial letter')}",
              f"**From:** {FILL.format('provider organization named in the documents')}"]
    L += [f"**Review date:** {A.as_of_date}", "", "## Claim identification",
          f"- Claim number: {P.claim_no} (source: denial_letter.txt)", f"- Patient ID: {P.patient.id} (source: denial_letter.txt)",
          f"- Date of service: {P.dos} (source: eob_835.txt)", f"- Service: CPT {P.cpt} {P.service_description or ''} (source: denial_letter.txt)",
          f"- Payer: {P.payer.name} ({P.payer.id}) (source: eob_835.txt)", f"- Denial code: {P.denial['carc']}" + (f" / RARC {P.denial['rarc']}" if P.denial["rarc"] else "") + " (source: denial_letter.txt)", "",
          "## Denial reason", f"{P.denial['reason_text'] or FILL.format('state the denial reason')} (source: denial_letter.txt)", "",
          "## Decision", FILL.format("your decision and one sentence of why"), "", "## Reasoning", FILL.format("how the policy criteria and the record lead to your decision"), ""]
    if letter:
        L += ["## Remedy requested", FILL.format("the specific remedy you ask the payer for, addressed to the appeals unit"), ""]
    L += ["## Policy criteria and evidence", f"Policy: {A.policy['policy_id'] if A.policy else FILL.format('governing policy id')}", ""]
    for s in A.criteria_skeleton:
        cands = "; ".join(f"{c['file']}:{c['line']}" for c in s["evidence_candidates"]) or "none found"
        L += [f"### Section {s['section']}", f"Requirement: {s['requirement_text']}", FILL.format(f"status of Section {s['section']} and the dated evidence (candidates: {cands})"), ""]
    ap, cc = d["appeal"], d["corrected_claim"]
    L += ["## Deadline", f"- Review date: {A.as_of_date}; notice date: {A.dates['notice_date']}",
          f"- Appeal deadline: {ap['date'] if ap else None} ({ap['days_remaining'] if ap else None} days from the review date)",
          f"- Corrected-claim deadline: {cc['date'] if cc else None} ({cc['days_remaining'] if cc else None} days from the review date)",
          FILL.format("which deadline governs your recommended action, and whether it is still open"), ""]
    if letter:
        L += ["## Enclosures", FILL.format("each enclosed document, by file name"), ""]
    else:
        L += ["## Next action", FILL.format("the recommended next step and owner"), ""]
    L += ["## Gaps", FILL.format("anything the documents do not establish (or: Gaps: none identified)"), ""]
    return "\n".join(L)
