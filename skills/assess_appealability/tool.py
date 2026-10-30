"""assess_appealability: DETERMINISTIC FACTS ONLY. Deadlines and day counts, timely-filing arithmetic, claim-history facts and a criteria
skeleton (policy requirement sections + evidence candidates). It never outputs a decision or a criterion status."""
import re

from pydantic import BaseModel

from skills.common.bm25 import BM25
from skills.common.io import SkillError, SkillInput
from skills.common.policies import load_policies
from skills.common.text import add_days, excerpt, iso, numbered, to_date, tokens
from skills.parse_denial_eob.tool import Input as ParseInput, run_tool as parse_run
from skills.retrieve_payer_policy.tool import Input as RetInput, run_tool as ret_run

HIST = re.compile(r"^\s*(\d{4}-\d{2}-\d{2})\s{2,}(.*)$")
NOTE_DATE = re.compile(r"(?:^|/)(\d{4}-\d{2}-\d{2})_")


class Input(SkillInput):
    policy_id: str | None = None       # default: the policy retrieve_payer_policy selects
    evidence_per_section: int = 3


class Output(BaseModel):
    as_of_date: str | None
    dates: dict
    deadlines: dict
    action_deadline_rule: str
    timely_filing: dict
    claim_history: dict
    policy: dict | None
    criteria_skeleton: list[dict]
    documents_dated_after_dos: list[dict]
    notes: list[str]


def _days_view(deadline, as_of):
    d = to_date(deadline)
    return {"date": deadline, "days_remaining": (d - to_date(as_of)).days if as_of else None, "open_on_review_date": (as_of <= deadline) if as_of else None}


def parse_history(text):
    h = {"events": [], "earlier_submissions": None, "retro_authorization_request": None, "prior_claims": None, "status": None}
    for no, ln in numbered(text):
        m = HIST.match(ln)
        if m and "Adjudicated by payer" in m.group(2):
            h["status"] = {"date": m.group(1), "text": m.group(2), "line": no}
        elif m:
            h["events"].append({"date": m.group(1), "event": m.group(2).strip(), "line": no})
        elif ln.strip().startswith("Earlier submissions:"):
            h["earlier_submissions"] = {"text": ln.strip().split(":", 1)[1].strip(), "line": no}
        elif ln.strip().startswith("Retroactive authorization request:"):
            h["retro_authorization_request"] = {"text": ln.strip().split(":", 1)[1].strip(), "line": no}
        elif ln.strip().startswith("Prior adjudicated claims for this service:"):
            h["prior_claims"] = {"text": ln.strip().split(":", 1)[1].strip(), "line": no}
    ev = h["events"]
    pick = lambda kw: next((e["date"] for e in ev if kw in e["event"]), None)  # noqa: E731
    h["submitted_date"], h["clearinghouse_accepted_date"], h["payer_received_date"] = pick("Submitted to clearinghouse"), pick("Clearinghouse acceptance"), pick("Received by payer")
    return h


def requirement_sections(policy):
    """Sections that state requirements: the numbered 2.x sections of the policy."""
    return {k: v for k, v in policy.sections.items() if k.split(".")[0] == "2"}


def run_tool(inp, ctx):
    parsed = parse_run(ParseInput(case_root=inp.case_root, policy_root=inp.policy_root, events_file=inp.events_file, run_id=inp.run_id, case_id=inp.case_id), ctx)
    notes = []
    as_of, notice, dos = parsed.as_of_date, parsed.denial["notice_date"], parsed.dos
    if not (notice and dos):
        raise SkillError("missing_facts", "notice date or date of service could not be parsed; run parse_denial_eob and inspect not_found")
    pols = {p.policy_id: p for p in load_policies(ctx)}
    ret = None
    if inp.policy_id:
        if inp.policy_id not in pols:
            raise SkillError("not_found", f"policy {inp.policy_id} is not in the policy library")
        policy = pols[inp.policy_id]
    else:
        ret = ret_run(RetInput(case_root=inp.case_root, policy_root=inp.policy_root, payer=parsed.payer.id or "", dos=dos, cpt=parsed.cpt,
                               service_description=parsed.service_description, icd10=parsed.icd10, denial_code=parsed.denial["carc"],
                               denial_text=parsed.denial["carc_text"], reason_text=parsed.denial["reason_text"], policy_title=parsed.policy_title), ctx)
        policy = pols[ret.policy["policy_id"]] if ret.status == "selected" else None
        if policy is None:
            notes.append(f"policy retrieval returned {ret.status!r}: {ret.reason}; filing-limit facts that need a policy are null")
    ap_days, cc_days = parsed.appeal["window_days"], parsed.corrected_claim["window_days"]
    appeal_by = iso(add_days(to_date(notice), ap_days)) if ap_days else None
    corrected_by = iso(add_days(to_date(notice), cc_days)) if cc_days else None
    for label, calc, stated in (("appeal", appeal_by, parsed.appeal["by_date"]), ("corrected-claim", corrected_by, parsed.corrected_claim["by_date"])):
        if calc and stated and calc != stated:
            notes.append(f"{label} date computed from the notice ({calc}) differs from the date stated in the letter ({stated})")
    deadlines = {"appeal": {**_days_view(appeal_by, as_of), "window_days": ap_days, "basis": f"notice date {notice} + {ap_days} days", "stated_in_letter": parsed.appeal["by_date"]} if appeal_by else None,
                 "corrected_claim": {**_days_view(corrected_by, as_of), "window_days": cc_days, "basis": f"notice date {notice} + {cc_days} days", "stated_in_letter": parsed.corrected_claim["by_date"]} if corrected_by else None}
    rule = ("action_deadline = the corrected-claim deadline if you recommend submitting a corrected claim; otherwise the appeal deadline (this also covers "
            "a recommendation not to appeal, or to escalate because documents are missing). deadline_ok = review date <= action_deadline.")
    try:
        hist = parse_history(ctx.read("case", "docs/claim_history.txt"))
    except FileNotFoundError:
        hist = parse_history("")
        notes.append("claim_history.txt is not present in the case")
    limit = policy.windows.get("timely_filing_days") if policy else None
    tf = {"limit_days": limit, "limit_source": f"{policy.policy_id} 7.2" if policy and limit else None, "filing_deadline": iso(add_days(to_date(dos), limit)) if limit else None,
          "stated_in_letter": parsed.letter_facts.get("filing_deadline"), "first_accepted_date": hist["clearinghouse_accepted_date"] or hist["submitted_date"],
          "payer_received_date": hist["payer_received_date"] or parsed.claim_details["payer_received_date"], "status": None, "status_reason": None}
    if limit and tf["first_accepted_date"] and tf["payer_received_date"]:
        fd = tf["filing_deadline"]
        acc_ok, rec_ok = tf["first_accepted_date"] <= fd, tf["payer_received_date"] <= fd
        tf["status"] = "within_limit" if acc_ok and rec_ok else ("accepted_within_limit_received_after" if acc_ok else "after_limit")
        tf["status_reason"] = f"first accepted {tf['first_accepted_date']} and payer received {tf['payer_received_date']} compared with filing deadline {fd}"
    else:
        tf["status_reason"] = "needs the policy filing limit and the claim_history dates"
    skeleton = []
    if policy:
        doc_lines = []
        for f in ctx.guard.list_files("case", "docs"):
            for no, ln in numbered(ctx.guard.read_text("case", f)):
                if ln.strip() and "SYNTHETIC DATA" not in ln:
                    doc_lines.append((f[len("docs/"):], no, ln))
        bm = BM25([x[2] for x in doc_lines])
        payer_words = set(tokens(f"{parsed.payer.name} {parsed.payer.id}"))
        for sid, sec in requirement_sections(policy).items():
            cands = []
            query = " ".join(w for w in tokens(sec["text"]) if w not in payer_words)  # the payer's own name is not evidence
            for i, sc in bm.rank(query)[:inp.evidence_per_section]:
                if sc > 0:
                    cands.append({"file": doc_lines[i][0], "line": doc_lines[i][1], "excerpt": excerpt(doc_lines[i][2]), "score": round(sc, 3)})
            skeleton.append({"section": sid, "policy_id": policy.policy_id, "requirement_text": sec["text"], "status": None, "evidence_candidates": cands})
        if policy.effective and dos < policy.effective:
            notes.append(f"date of service {dos} is before the policy effective date {policy.effective}; the policy states it applies to dates of service on or after {policy.applies_from}")
    after = []
    for f in ctx.guard.list_files("case", "docs"):
        m = NOTE_DATE.search(f)
        if m and f.startswith("docs/notes/") and m.group(1) > dos:
            after.append({"path": f[len("docs/"):], "date": m.group(1), "days_after_dos": (to_date(m.group(1)) - to_date(dos)).days})
    return Output(
        as_of_date=as_of, dates={"dos": dos, "notice_date": notice, "claim_submitted_date": hist["submitted_date"], "payer_received_date": tf["payer_received_date"]},
        deadlines=deadlines, action_deadline_rule=rule, timely_filing=tf,
        claim_history={k: hist[k] for k in ("events", "earlier_submissions", "retro_authorization_request", "prior_claims", "status")},
        policy={"policy_id": policy.policy_id, "effective_date": policy.effective, "applies_from": policy.applies_from} if policy else None,
        criteria_skeleton=skeleton, documents_dated_after_dos=after, notes=notes)
