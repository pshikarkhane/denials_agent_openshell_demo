"""Deterministic documents (no LLM) for all cases: docs/eob_835.txt, docs/denial_letter.txt and task.md.

Codes, dates, amounts, claim numbers and deadlines come only from truth.json. Patient/provider details come from
the seeded Faker profile. Nothing here mentions the decision, category or traps.
Usage: python -m data_gen.render_docs [--data data] [--seed N]
"""
import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path

from data_gen import reference as R
from data_gen.docs_util import SYNTHETIC_FOOTER, case_dir, fill_lines
from data_gen.gen_cases import DEFAULT_SEED, build_manifest, load_truths, write_truth
from data_gen.profiles import profile
from data_gen.schema import Truth

PAYER_ADDR = {"MERIDIAN_COMM": "Appeals Unit, P.O. Box 5100, Meridian City, ST 00001",
              "HALCYON_PLAN": "Appeals Unit, P.O. Box 7200, Halcyon Bay, ST 00002",
              "TERRAVISTA_HEALTH": "Appeals Unit, P.O. Box 3300, Terravista, ST 00003"}


def facts(t):
    d = {}
    for f in t.facts:
        d.setdefault(f.key, f.value)
    return d


def m(x):
    return f"{x:.2f}"


def render_eob(t, p):
    f = facts(t)
    c = t.claim
    cat, fld = t.category, f.get("missing_field")
    received = f.get("payer_received_date", f["claim_submitted_date"] if t.category != 5 else f["payer_received_date"])
    lines = []  # (cpt, modifier, billed, allowed, paid, adjustment)
    carc, rarc = t.denial.carc, t.denial.rarc
    rarc_s = f" RARC {rarc}" if rarc else ""
    if cat == 7:
        allowed, pr1 = f["allowed_amount"], f["pr1_amount"]
        lines.append((c.cpt, "", c.billed, allowed, round(allowed - pr1, 2), f"{carc} {m(pr1)}"))
        status = "PROCESSED - PATIENT RESPONSIBILITY APPLIED"
    else:
        main = (c.cpt, "59" if f.get("modifier_present") else "", c.billed, 0.0, 0.0, f"{carc} {m(c.billed)}{rarc_s}")
        status = "DENIED"
        if cat == 9:
            b1 = f["column1_billed_amount"]
            a1 = round(b1 * 0.62, 2)
            lines += [(f["column1_code"], "", b1, a1, a1, ""), main]
            status = "PARTIALLY DENIED"
        elif fld == "modifier_25":
            b2 = f["same_day_procedure_billed"]
            a2 = round(b2 * 0.62, 2)
            lines += [main, (f["same_day_procedure_cpt"], "", b2, a2, a2, "")]
            status = "PARTIALLY DENIED"
        else:
            lines.append(main)
    tb, ta, tp = (round(sum(x[i] for x in lines), 2) for i in (2, 3, 4))
    pr = m(f["pr1_amount"]) if cat == 7 else "0.00"
    pos = "(not provided)" if fld == "place_of_service" else "11"
    rend = "(not provided)" if fld == "rendering_provider" else f"{p['provider']} (ID SYN-RP-{t.claim.claim_no[-4:]})"
    ref = "(not provided)" if fld == "referring_provider" else p["specialist"]
    out = [
        "835 REMITTANCE ADVICE (SYNTHETIC RENDERING)", "",
        f"Payer: {R.PAYER_NAMES[t.payer_id]}", f"Payer ID: {t.payer_id}", f"Payee: {p['practice']}",
        f"Trace number: {p['trace']}", f"Remittance date: {t.denial.denial_date.isoformat()}", "",
        "PATIENT", f"  Name: {p['name']}", f"  Patient ID: {t.patient.synthetic_id}", f"  MRN: {p['mrn']}",
        f"  Member ID: {p['member_id']}", f"  Date of birth: {p['dob']}", f"  SSN: {p['ssn']}", "",
        "CLAIM", f"  Claim number: {c.claim_no}", f"  Claim status: {status}",
        f"  Date of service: {c.dos.isoformat()}", f"  Date claim received by payer: {received}",
        f"  Diagnosis (ICD-10): {', '.join(c.icd10)}", f"  Place of service: {pos}",
        f"  Rendering provider: {rend}", f"  Referring provider: {ref}", "",
        "SERVICE LINES", "  Line  CPT    Mod  Billed     Allowed    Paid       Adjustment",
    ]
    for i, (cpt, mod, b, a, pd, adj) in enumerate(lines, 1):
        out.append(f"  {i:<5} {cpt:<6} {mod:<4} {m(b):<10} {m(a):<10} {m(pd):<10} {adj}".rstrip())
        out.append(f"        ({R.CPT[cpt]})")
    out += ["", f"TOTALS  Billed {m(tb)}  Allowed {m(ta)}  Paid {m(tp)}  Patient responsibility {pr}"]
    if cat == 7:
        out.append(f"  Amount not allowed (billed minus allowed): {m(round(c.billed - f['allowed_amount'], 2))}")
    out += ["", SYNTHETIC_FOOTER]
    return "\n".join(out) + "\n"


def _reason(t, f, p):
    cat, title = t.category, R.POLICY_TITLES[t.policy_id]
    lim = R.PAYERS[t.payer_id]["timely_filing_days"]
    return {
        1: f"The clinical information submitted did not demonstrate that this service met the plan's medical necessity criteria (Medical Policy: {title}).",
        2: f"The clinical information submitted did not demonstrate that this service met the plan's medical necessity criteria (Medical Policy: {title}).",
        3: f"No prior authorization was on file for this service, which requires authorization (Medical Policy: {title}).",
        4: f"No prior authorization was on file for this service, which requires authorization (Medical Policy: {title}).",
        5: f"Our records show the claim was received on {f.get('payer_received_date')}, after the {lim}-day filing limit. "
           f"The filing deadline for this date of service was {f.get('timely_filing_deadline')} (Medical Policy: {title}).",
        6: f"Our records show the claim was received on {f.get('payer_received_date')}, after the {lim}-day filing limit. "
           f"The filing deadline for this date of service was {f.get('timely_filing_deadline')} (Medical Policy: {title}).",
        7: "The billed amount was applied to the member's deductible. This amount is the member's responsibility.",
        8: f"The claim is missing required information: {f.get('missing_item')} (Medical Policy: {title}).",
        9: f"This service is considered included in the payment for procedure {f.get('column1_code')} billed on the same claim (Medical Policy: {title}).",
        10: f"This claim duplicates claim {f.get('original_claim_no')}, which was paid on {f.get('original_paid_date')} "
            f"in the amount of {m(f.get('original_paid_amount', 0.0))}.",
        11: f"The diagnosis code(s) {', '.join(t.claim.icd10)} are not consistent with procedure {t.claim.cpt} (Medical Policy: {title}).",
        12: f"The number of visits for this benefit period exceeds the plan's outpatient therapy visit limit (Medical Policy: {title}).",
    }[cat]


def render_denial(t, p):
    f, c = facts(t), t.claim
    pay = R.PAYERS[t.payer_id]
    rarc = f"Remark code (RARC): {t.denial.rarc}" if t.denial.rarc else "Remark code (RARC): none"
    out = [
        R.PAYER_NAMES[t.payer_id].upper(), f"Payer ID: {t.payer_id}", "NOTICE OF CLAIM DETERMINATION", "",
        f"Date of notice: {t.denial.denial_date.isoformat()}", f"To: {p['practice']}",
        f"Member: {p['name']}   Patient ID: {t.patient.synthetic_id}   Member ID: {p['member_id']}", "",
        f"Claim number: {c.claim_no}", f"Date of service: {c.dos.isoformat()}",
        f"Service: {c.cpt} - {R.CPT[c.cpt]}", f"Billed amount: {m(c.billed)}", "",
        "DETERMINATION", f"Reason code (CARC): {t.denial.carc}  {R.CARC_TEXT[t.denial.carc]}", rarc,
        _reason(t, f, p), "",
        "Appeal Rights",
        f"You may request an appeal within {pay['appeal_days']} days of the date of this notice. "
        f"The appeal must be received by {t.appeal_deadline.isoformat()}.",
        f"Send appeals to: {PAYER_ADDR[t.payer_id]}", "",
        "Corrected Claims",
        f"A corrected claim must be received within {pay['corrected_claim_days']} days of the date of this notice, "
        f"that is, by {f['corrected_claim_deadline']}.", "",
        SYNTHETIC_FOOTER,
    ]
    return "\n".join(out) + "\n"


_OUTPUT = (
    "\nOutput format. Write two files to /sandbox/work/output/{cid}/ :\n"
    "- deliverable.md: the appeal letter, or a short decision memo. State the source document for each factual statement; "
    "list anything you could not verify under \"Gaps\".\n"
    "- decision.json: {{\"decision\": one of APPEAL | CORRECT_AND_RESUBMIT | DO_NOT_APPEAL | ESCALATE_MISSING_DOCS, "
    "\"denial_code\", \"appeal_deadline\", \"deadline_ok\", \"criteria\": [{{\"id\" (policy section, e.g. 3.2(a)), \"status\": met|unmet|unknown, \"evidence\"}}], "
    "\"enclosures\": [], \"gaps\": []}}\n"
    "\n" + SYNTHETIC_FOOTER + "\n"
)
_T = [
    "Claim {claim} for patient {pid} was denied (see attached). Review the denial, the payer's policy, and the clinical record. "
    "Decide whether we should appeal, correct and resubmit, or not pursue. Prepare the deliverable: an appeal letter if appealing, "
    "otherwise a short decision memo. Flag anything missing.",
    "Please look at the denial on claim {claim} ({pid}). Pull the relevant payer policy and the chart, tell me what we should do "
    "about it, and write it up. If we appeal, I need the letter ready to send; if not, a brief memo explaining why.",
    "Denial work item: claim {claim}, patient {pid}, payer {payer}. The remit, denial notice and chart documents are in the case folder. "
    "Work out what the denial is about, check it against the payer's policy library, and recommend a course of action with the "
    "supporting paper. Call out missing documentation rather than assuming it exists.",
    "Claim {claim} / {pid} came back denied. Can you review it end to end? I want your recommendation (appeal, fix and resubmit, "
    "or let it go), the reasoning tied to the policy and the record, and the appropriate letter or memo.",
    "Review claim {claim} for {pid}. Read the denial and remit, find the governing payer policy, check the clinical documentation "
    "against it, and check the deadlines. Produce whatever deliverable the situation calls for (appeal letter or decision memo). "
    "List anything missing or inconsistent.",
    "New denial in the queue: {claim} ({pid}, {payer}). Please figure out whether this is worth pursuing, and if so how. "
    "Cite the policy sections and the record for every point, and note where documentation is lacking.",
    "Handle the denial on claim {claim}, patient {pid}. Summarize why it was denied, whether the payer's own policy supports "
    "overturning it, and what we should do next. Draft the letter or memo that goes with your recommendation.",
    "Claim {claim} for patient {pid} was denied. Use the attached documents and the payer's policy library to decide our next "
    "step. Be explicit about deadlines and about anything that is missing from the file.",
]


def render_task(t, seed):
    rng = random.Random(f"{seed}:task:{t.case_id}")
    f = facts(t)
    body = rng.choice(_T).format(claim=t.claim.claim_no, pid=t.patient.synthetic_id, payer=R.PAYER_NAMES[t.payer_id])
    return (f"# Task\n\n{body}\n\nToday's date for this review is {f['as_of_date']}.\n\n"
            f"Case files: /sandbox/data/cases/{t.case_id}/docs/ . Payer policy library: /sandbox/data/policy_library/ .\n"
            + _OUTPUT.format(cid=t.case_id))


def render_all(root, seed):
    man, truths = load_truths(root)
    for t in truths:
        p = profile(seed, t.case_id)
        base = case_dir(root, t.case_id)
        (base / "docs").mkdir(parents=True, exist_ok=True)
        (base / "docs" / "eob_835.txt").write_text(render_eob(t, p))
        (base / "docs" / "denial_letter.txt").write_text(render_denial(t, p))
        (base / "task.md").write_text(render_task(t, seed))
        fill_lines(root, t)
        write_truth(root, t)
    build_manifest(root, truths, man["seed"])
    return len(truths)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    a = ap.parse_args()
    print(f"rendered eob_835.txt, denial_letter.txt, task.md for {render_all(a.data, a.seed)} cases")
