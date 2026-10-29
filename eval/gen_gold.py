"""Gold deliverables for the pilot cases (HOST-ONLY: data/cases/<id>/gold/). Written by the `datagen` model (never the agent model),
then checked with the deliverable schema and the 'auto' rubric criteria, which must pass 100%.
Usage: python -m eval.gen_gold [--data data] [--cases C-0005 ...] [--force]
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

from data_gen import reference as R
from data_gen.gen_cases import build_manifest, load_truths
from data_gen.llm import chat_with_retry, datagen_model, load_models
from data_gen.render_docs import PAYER_ADDR
from eval.auto_checks import grade_auto
from eval.deliverable_schema import validate_decision_text
from eval.gen_rubrics import facts
from eval.rubric_schema import Rubric

PROMPT_FILE = Path(__file__).parent / "prompts" / "gold_writer.md"
MAX_TRIES = 3
KIND = {
    "APPEAL": ("Write an APPEAL LETTER (deliverable.md) addressed to the payer's appeals unit at the address given in the denial letter. It must: identify the claim "
               "(claim number, patient ID, date of service, CPT); state the denial reason; request a clear remedy (overturn the denial and reprocess the claim); "
               "cite the governing policy by ID and by the section number for each criterion; support each criterion with specific, dated evidence from the "
               "named files; state the action deadline and its relation to the review date; list the enclosures; and include a Gaps section."),
    "DO_NOT_APPEAL": ("Write a short DECISION MEMO (deliverable.md), NOT an appeal letter. It must: identify the claim (claim number, patient ID, date of service, CPT); "
                      "state the denial reason; explain why an appeal should not be filed, citing the governing policy by ID and section and the evidence files, with "
                      "any date arithmetic shown; state the deadline facts; and give the recommended next action."),
    "CORRECT_AND_RESUBMIT": ("Write a short DECISION MEMO (deliverable.md), NOT an appeal letter. It must: identify the claim (claim number, patient ID, date of service, "
                             "CPT); name the missing or invalid item and the correction; cite the governing policy by ID and section; state that a corrected claim, not "
                             "an appeal, is the right route and give the corrected-claim deadline with how it follows from the notice date; and give the next action."),
    "ESCALATE_MISSING_DOCS": ("Write a short DECISION MEMO (deliverable.md), NOT an appeal letter. It must: identify the claim (claim number, patient ID, date of service, "
                              "CPT); explain which policy criterion cannot be established; name the specific missing document and where the record refers to it; say what "
                              "is needed and from whom; give the deadline facts; and state that the decision is to escalate until the document is received."),
}


def situations(t, f):
    tr = {x.value for x in t.traps}
    out = []
    asof, ad = date.fromisoformat(f["as_of_date"]), t.action_deadline
    out.append(f"- The review date is {asof}. The action deadline is {ad} ({(ad - asof).days} days {'remaining' if ad >= asof else 'ago, i.e. already passed'}).")
    if t.correct_decision.value == "CORRECT_AND_RESUBMIT":
        out.append(f"- The denial letter also shows an appeal deadline of {t.appeal_deadline}; it is not the governing deadline for this action.")
    if "deadline_within_7_days" in tr:
        out.append("- Very little time remains before the action deadline: say so and say what must happen before it "
                   "(act immediately if filing; if not filing, confirm the decision before the window closes; if escalating, obtain the documents before it).")
    if "deadline_passed" in tr:
        out.append("- The action deadline has passed before the review date: say so.")
    if "note_after_dos" in tr:
        out.append(f"- The note {f['post_dos_note']} was written after the date of service. Do not use it as evidence for the service; you may mention it is post-service.")
    if "notes_disagree_therapy_duration" in tr:
        p = next(x.source_file for x in t.facts if x.key == "conflicting_therapy_duration_days")
        out.append(f"- {p} gives a different therapy duration from the PT log. Point out the conflict and rely on the PT log (supporting/pt_log.txt).")
    if "policy_effective_after_dos" in tr:
        out.append(f"- The date of service {t.claim.dos} is before the policy's effective date {f['policy_effective_date']}. State this and that the policy says its requirements carry forward.")
    if t.category == 6:
        lim = R.PAYERS[t.payer_id]["timely_filing_days"]
        out.append(f"- Show the filing arithmetic: date of service {t.claim.dos} plus {lim} days is {f['timely_filing_deadline']}; the payer received the claim {f['payer_received_date']}; claim_history.txt records no earlier submission.")
    if t.category == 7:
        out.append("- The amount is patient responsibility (deductible); the next action is to bill the patient, with the amount from the documents.")
    if t.category == 10:
        out.append("- The claim duplicates an earlier adjudicated claim; refer to it using the documents.")
    if any(c.basis == "documented_absence" for c in t.policy_criteria):
        out.append("- Where a document explicitly states something does not exist (for example 'No prior lumbar imaging on file' or 'Earlier submissions: none recorded'), report exactly what the document says and cite it.")
    return "\n".join(out)


def build_prompt(t, root):
    root, f = Path(root), facts(t)
    base = root / "cases" / t.case_id
    docs = "\n".join(f"===== FILE: {p.relative_to(base / 'docs').as_posix()} =====\n{p.read_text()}" for p in sorted((base / "docs").rglob("*")) if p.is_file())
    pol = (root / "policy_library" / f"{t.policy_id}.txt").read_text()
    crit = "\n".join(f"- {c.section.lstrip('§')} | {c.status} | {c.evidence[0] if c.evidence else 'null'}" for c in t.policy_criteria)
    fields = (f'"case_id": "{t.case_id}", "decision": "{t.correct_decision.value}", "denial_code": "{t.denial.carc}", "policy_id": "{t.policy_id}", '
              f'"action_deadline": "{t.action_deadline}", "deadline_ok": {str(date.fromisoformat(f["as_of_date"]) <= t.action_deadline).lower()}')
    encl = json.dumps(t.required_enclosures) if t.required_enclosures else "[] (none required)"
    tpl = PROMPT_FILE.read_text()
    for k, v in {"KIND_INSTRUCTIONS": KIND[t.correct_decision.value], "DECISION_FIELDS": fields, "CRITERIA_LIST": crit, "ENCLOSURES": encl,
                 "SITUATIONS": situations(t, f), "TASK": (base / "task.md").read_text(), "DOCS": docs, "POLICY": pol}.items():
        tpl = tpl.replace(f"<<{k}>>", v)
    return tpl


def parse_output(text):
    m = re.search(r"<<<DELIVERABLE>>>\s*(.*?)\s*<<<DECISION>>>\s*(.*?)\s*(?:<<<END>>>|\Z)", text, re.S)
    if not m:
        return None, None
    dec = re.sub(r"^```(?:json)?\s*|\s*```$", "", m.group(2).strip())
    return m.group(1).strip() + "\n", dec + "\n"


def check_gold(t, rubric, deliverable, decision_text):
    """Schema + auto criteria. Returns (problems, decision_obj)."""
    dec, errs = validate_decision_text(decision_text, t.case_id)
    problems = list(errs)
    for c in rubric.criteria:
        if c.check == "auto":
            ok, detail = grade_auto(c.auto, dec, deliverable)
            if not ok:
                problems.append(f"{c.id}: {detail}")
    return problems, dec


def write_gold(cfg, t, root, force=False):
    root = Path(root)
    gdir = root / "cases" / t.case_id / "gold"
    if (gdir / "deliverable.md").exists() and not force:
        return "kept"
    rubric = Rubric.model_validate_json((root / "cases" / t.case_id / "rubric.json").read_text())
    model, temp = datagen_model(cfg), float(cfg["datagen"]["temperature"])
    prompt, feedback = build_prompt(t, root), ""
    for attempt in range(1, MAX_TRIES + 1):
        text, usage, secs = chat_with_retry(cfg, model, prompt + feedback, max_tokens=8000, temperature=temp, timeout=300, attempts=5, backoff=4.0)
        deliverable, decision = parse_output(text)
        problems = ["could not parse the <<<DELIVERABLE>>> / <<<DECISION>>> blocks"] if deliverable is None else check_gold(t, rubric, deliverable, decision)[0]
        if not problems:
            gdir.mkdir(parents=True, exist_ok=True)
            (gdir / "deliverable.md").write_text(deliverable)
            (gdir / "decision.json").write_text(json.dumps(json.loads(decision), indent=2) + "\n")
            (gdir / "meta.json").write_text(json.dumps({
                "model_id": model, "temperature": temp, "max_tokens": 8000, "attempts": attempt, "usage": usage,
                "prompt_template_sha256": hashlib.sha256(PROMPT_FILE.read_bytes()).hexdigest(),
                "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "note": "written by the datagen model; schema and auto rubric criteria pass 100%"}, indent=2) + "\n")
            return f"written (attempt {attempt})"
        feedback = "\n\nYour previous answer was rejected: " + "; ".join(problems) + ". Fix these and answer again in the same format."
    raise SystemExit(f"{t.case_id}: gold failed validation after {MAX_TRIES} tries: {problems}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--cases", nargs="*")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    cfg = load_models()
    man, truths = load_truths(a.data)
    for t in truths:
        if t.case_id in (a.cases or man["pilot_cases"]):
            print(t.case_id, write_gold(cfg, t, a.data, a.force), flush=True)
    build_manifest(a.data, truths, man["seed"])


if __name__ == "__main__":
    main()
