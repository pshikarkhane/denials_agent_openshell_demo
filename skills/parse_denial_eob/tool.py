"""parse_denial_eob: deterministic extraction of the denial facts from eob_835.txt, denial_letter.txt and task.md.
Fields that cannot be found are null with a reason (never guessed); a required remit field that is absent (shown as '(not provided)') is listed under missing_required."""
import re

from pydantic import BaseModel

from skills.common.io import SkillError, SkillInput
from skills.common.text import add_days, iso, to_date

FILES = ("eob_835.txt", "denial_letter.txt", "claim_history.txt")


class Input(SkillInput):
    pass


class Party(BaseModel):
    id: str | None = None
    name: str | None = None
    member_id: str | None = None


class ServiceLine(BaseModel):
    line: int
    cpt: str
    modifier: str | None
    description: str | None
    billed: float
    allowed: float
    paid: float
    adjustment_code: str | None
    adjustment_amount: float | None
    rarc: str | None


class Output(BaseModel):
    payer: Party
    claim_no: str | None
    patient: Party
    dos: str | None
    cpt: str | None
    service_description: str | None
    icd10: list[str]
    service_lines: list[ServiceLine]
    denied_line: int | None
    amounts: dict
    denial: dict
    appeal: dict
    corrected_claim: dict
    policy_title: str | None
    as_of_date: str | None
    claim_details: dict
    letter_facts: dict
    missing_required: list[dict]
    not_found: dict
    consistency: list[str]


def _kv(text, label):
    m = re.search(rf"^[ \t]*{re.escape(label)}:[ \t]*(.*?)[ \t]*$", text, re.M)
    return m.group(1) if m else None


def _money(s):
    return float(s) if s is not None else None


LINE = re.compile(r"^\s+(\d+)\s+(\d{5})\s+(?:([A-Z0-9]{2})\s+)?(\d+\.\d\d)\s+(\d+\.\d\d)\s+(\d+\.\d\d)\s*(.*)$", re.M)


def parse_eob(text):
    d = {"lines": [], "diag": []}
    d["payer_name"], d["payer_id"] = _kv(text, "Payer"), _kv(text, "Payer ID")
    d["name"], d["patient_id"], d["member_id"] = _kv(text, "Name"), _kv(text, "Patient ID"), _kv(text, "Member ID")
    d["claim_no"], d["status"], d["dos"] = _kv(text, "Claim number"), _kv(text, "Claim status"), _kv(text, "Date of service")
    d["received"], d["pos"] = _kv(text, "Date claim received by payer"), _kv(text, "Place of service")
    d["rendering"], d["referring"] = _kv(text, "Rendering provider"), _kv(text, "Referring provider")
    d["remit_date"] = _kv(text, "Remittance date")
    dx = _kv(text, "Diagnosis (ICD-10)")
    d["diag"] = [x.strip() for x in dx.split(",")] if dx else []
    desc = re.findall(r"^\s+\((.*)\)\s*$", text, re.M)
    for i, m in enumerate(LINE.finditer(text)):
        n, cpt, mod, billed, allowed, paid, adj = m.groups()
        code = re.match(r"((?:CO|PR|OA|PI)-\d+)\s+(\d+\.\d\d)", adj.strip())
        rarc = re.search(r"RARC\s+(\S+)", adj)
        d["lines"].append(ServiceLine(line=int(n), cpt=cpt, modifier=mod, description=desc[i] if i < len(desc) else None, billed=float(billed),
                                      allowed=float(allowed), paid=float(paid), adjustment_code=code.group(1) if code else None,
                                      adjustment_amount=float(code.group(2)) if code else None, rarc=rarc.group(1) if rarc else None))
    t = re.search(r"TOTALS\s+Billed (\S+)\s+Allowed (\S+)\s+Paid (\S+)\s+Patient responsibility (\S+)", text)
    d["totals"] = {"billed": float(t.group(1)), "allowed": float(t.group(2)), "paid": float(t.group(3)), "patient_responsibility": float(t.group(4))} if t else None
    return d


def parse_letter(text):
    d = {}
    d["payer_name"] = text.splitlines()[0].title() if text.strip() else None
    d["payer_id"], d["notice_date"] = _kv(text, "Payer ID"), _kv(text, "Date of notice")
    m = re.search(r"Member:\s*(.*?)\s{2,}Patient ID:\s*(\S+)\s+Member ID:\s*(\S+)", text)
    d["name"], d["patient_id"], d["member_id"] = (m.groups() if m else (None, None, None))
    d["claim_no"], d["dos"], d["billed"] = _kv(text, "Claim number"), _kv(text, "Date of service"), _kv(text, "Billed amount")
    s = re.match(r"(\d{5}) - (.*)", _kv(text, "Service") or "")
    d["cpt"], d["service_description"] = (s.group(1), s.group(2)) if s else (None, None)
    c = re.match(r"Reason code \(CARC\):\s*((?:CO|PR|OA|PI)-\d+)\s+(.*)", _kv_line(text, "Reason code (CARC)"))
    d["carc"], d["carc_text"] = (c.group(1), c.group(2)) if c else (None, None)
    r = _kv(text, "Remark code (RARC)")
    d["rarc"] = None if r in (None, "none") else r
    d["rarc_stated"] = r is not None
    lines = text.splitlines()
    i = next((k for k, ln in enumerate(lines) if ln.startswith("Remark code (RARC)")), None)
    d["reason_text"] = lines[i + 1].strip() if i is not None and i + 1 < len(lines) else None
    ti = re.search(r"\(Medical Policy:\s*(.+)\)\.?\s*$", d["reason_text"] or "")
    d["policy_title"] = ti.group(1).strip() if ti else None
    a = re.search(r"appeal within (\d+) days of the date of this notice\. The appeal must be received by (\d{4}-\d{2}-\d{2})", text)
    d["appeal_days"], d["appeal_by"] = (int(a.group(1)), a.group(2)) if a else (None, None)
    d["appeal_address"] = _kv(text, "Send appeals to")
    cc = re.search(r"corrected claim must be received within (\d+) days of the date of this notice,\s*that is, by (\d{4}-\d{2}-\d{2})", text)
    d["corrected_days"], d["corrected_by"] = (int(cc.group(1)), cc.group(2)) if cc else (None, None)
    rt = d["reason_text"] or ""
    f = {}
    m = re.search(r"received on (\d{4}-\d{2}-\d{2}), after the (\d+)-day filing limit\. The filing deadline for this date of service was (\d{4}-\d{2}-\d{2})", rt)
    if m:
        f.update(payer_received_date=m.group(1), filing_limit_days=int(m.group(2)), filing_deadline=m.group(3))
    m = re.search(r"missing required information: (.*?) \(Medical Policy", rt)
    if m:
        f["missing_item"] = m.group(1)
    m = re.search(r"duplicates claim (\d+), which was paid on (\d{4}-\d{2}-\d{2}) in the amount of (\d+\.\d\d)", rt)
    if m:
        f["duplicate_of"] = {"claim_no": m.group(1), "paid_date": m.group(2), "paid_amount": float(m.group(3))}
    m = re.search(r"included in the payment for procedure (\d{5})", rt)
    if m:
        f["bundled_with_cpt"] = m.group(1)
    d["facts"] = f
    return d


def _kv_line(text, label):
    m = re.search(rf"^{re.escape(label)}:.*$", text, re.M)
    return m.group(0) if m else ""


def parse_task(text):
    d = {}
    m = re.search(r"review is (\d{4}-\d{2}-\d{2})\.", text)
    d["as_of"] = m.group(1) if m else None
    m = re.search(r"\b(\d{7})\b", text.split("Case files:")[0])
    d["claim_no"] = m.group(1) if m else None
    m = re.search(r"\b(P-\d{4})\b", text)
    d["patient_id"] = m.group(1) if m else None
    m = re.search(r"/sandbox/work/output/(C-\d{4})/", text)
    d["case_id"] = m.group(1) if m else None
    return d


def run_tool(inp, ctx):
    texts, nf = {}, {}
    for f in ("eob_835.txt", "denial_letter.txt"):
        try:
            texts[f] = ctx.read("case", f"docs/{f}")
        except FileNotFoundError:
            texts[f] = None
            nf[f] = "file not present in the case"
    try:
        task = ctx.read("case", "task.md")
    except FileNotFoundError:
        task = None
        nf["task.md"] = "file not present in the case"
    if texts["eob_835.txt"] is None and texts["denial_letter.txt"] is None:
        raise SkillError("no_documents", "neither eob_835.txt nor denial_letter.txt exists in the case root")
    e = parse_eob(texts["eob_835.txt"]) if texts["eob_835.txt"] else {"lines": [], "diag": [], "totals": None}
    L = parse_letter(texts["denial_letter.txt"]) if texts["denial_letter.txt"] else {"facts": {}}
    T = parse_task(task) if task else {}

    def pick(key, *vals, field=None, reason=None):
        for v in vals:
            if v not in (None, ""):
                return v
        nf[field or key] = reason or f"'{key}' not found in the documents"
        return None

    consistency = []
    for label, a, b in (("claim number", e.get("claim_no"), L.get("claim_no")), ("date of service", e.get("dos"), L.get("dos")),
                        ("patient id", e.get("patient_id"), L.get("patient_id")), ("payer id", e.get("payer_id"), L.get("payer_id")),
                        ("claim number (task)", L.get("claim_no") or e.get("claim_no"), T.get("claim_no")),
                        ("patient id (task)", L.get("patient_id") or e.get("patient_id"), T.get("patient_id"))):
        if a and b and a != b:
            consistency.append(f"{label} differs between documents: {a} vs {b}")
    lines = e["lines"]
    denied = next((x for x in lines if x.adjustment_code), None)
    cpt = pick("cpt", denied.cpt if denied else None, L.get("cpt"))
    amounts = {"billed": denied.billed if denied else None, "allowed": denied.allowed if denied else None, "paid": denied.paid if denied else None,
               "denied_amount": denied.adjustment_amount if denied else None,
               "patient_responsibility": e["totals"]["patient_responsibility"] if e.get("totals") else None, "claim_totals": e.get("totals")}
    if amounts["billed"] is None and L.get("billed"):
        amounts["billed"] = float(L["billed"])
    if denied is None:
        nf["denied_line"] = "no service line carries an adjustment code on the remit"
    carc = pick("carc", denied.adjustment_code if denied else None, L.get("carc"), field="carc")
    rarc = (denied.rarc if denied else None) or L.get("rarc")
    notice = pick("notice_date", L.get("notice_date"), e.get("remit_date"), field="notice_date")
    appeal = {"window_days": L.get("appeal_days"), "by_date": L.get("appeal_by"), "address": L.get("appeal_address")}
    cc = {"window_days": L.get("corrected_days"), "by_date": L.get("corrected_by")}
    for k, v in (("appeal.window_days", appeal["window_days"]), ("appeal.by_date", appeal["by_date"]), ("corrected_claim.window_days", cc["window_days"]), ("corrected_claim.by_date", cc["by_date"])):
        if v is None:
            nf[k] = "appeal / corrected-claim paragraph not found in the denial letter"
    if appeal["window_days"] and appeal["by_date"] and notice and iso(add_days(to_date(notice), appeal["window_days"])) != appeal["by_date"]:
        consistency.append("appeal-by date in the letter does not equal notice date + stated window")
    if cc["window_days"] and cc["by_date"] and notice and iso(add_days(to_date(notice), cc["window_days"])) != cc["by_date"]:
        consistency.append("corrected-claim date in the letter does not equal notice date + stated window")
    # only REQUIRED remit fields that are absent are reported; empty optional columns (for example the modifier column) are not information
    missing = [{"field": field, "reason": f"required remit field is absent: the remit shows '(not provided)' for {field.replace('_', ' ')}"}
               for field, key in (("place_of_service", "pos"), ("rendering_provider", "rendering"), ("referring_provider", "referring")) if e.get(key) == "(not provided)"]
    policy_title = L.get("policy_title")
    if policy_title is None:
        nf["policy_title"] = "the denial letter does not name a policy title"
    if not e["diag"]:
        nf["icd10"] = "diagnosis line not found on the remit"
    if T.get("as_of") is None:
        nf["as_of_date"] = "task.md does not state a review date"
    return Output(
        payer=Party(id=pick("payer_id", e.get("payer_id"), L.get("payer_id"), field="payer.id"), name=e.get("payer_name") or L.get("payer_name")),
        claim_no=pick("claim_no", e.get("claim_no"), L.get("claim_no"), T.get("claim_no")),
        patient=Party(id=pick("patient_id", e.get("patient_id"), L.get("patient_id"), T.get("patient_id"), field="patient.id"),
                      name=e.get("name") or L.get("name"), member_id=e.get("member_id") or L.get("member_id")),
        dos=pick("dos", e.get("dos"), L.get("dos")), cpt=cpt,
        service_description=(denied.description if denied and denied.description else None) or L.get("service_description"),
        icd10=e["diag"], service_lines=lines, denied_line=denied.line if denied else None, amounts=amounts,
        denial={"carc": carc, "carc_text": L.get("carc_text"), "rarc": rarc, "reason_text": L.get("reason_text"), "notice_date": notice},
        appeal=appeal, corrected_claim=cc, policy_title=policy_title, as_of_date=T.get("as_of"),
        claim_details={"payer_received_date": e.get("received"), "claim_status": e.get("status"), "place_of_service": e.get("pos"),
                       "rendering_provider": e.get("rendering"), "referring_provider": e.get("referring"), "case_id_in_task": T.get("case_id")},
        letter_facts=L.get("facts", {}), missing_required=missing, not_found=nf, consistency=consistency)
