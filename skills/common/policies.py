"""Parse the policy library (plain text) into structured policies. Shared by retrieve_payer_policy, assess_appealability and self_check."""
import re
from dataclasses import dataclass, field

from skills.common.text import to_date

SECTION = re.compile(r"(?m)^Section (\S+)(?:[ \t]+(.*))?$")


@dataclass
class Policy:
    file: str
    policy_id: str
    title: str
    payer_name: str | None
    payer_id: str | None
    effective: str | None
    status_lines: list = field(default_factory=list)
    applies_from: str | None = None
    applies_until: str | None = None
    superseded: bool = False
    superseded_by: str | None = None
    sections: dict = field(default_factory=dict)      # id -> {"heading": str|None, "text": str, "line": int}
    params: list = field(default_factory=list)        # [(label, text)]
    windows: dict = field(default_factory=dict)
    address: str | None = None
    text: str = ""


def _hdr(text, label):
    m = re.search(rf"^{re.escape(label)}:[ \t]*(.*)$", text, re.M)
    return m.group(1).strip() if m else None


def parse_policy(file, text):
    lines = text.splitlines()
    p = Policy(file=file, policy_id=_hdr(text, "Policy ID") or file.rsplit("/", 1)[-1][:-4], title=(lines[0].strip() if lines else ""),
               payer_name=_hdr(text, "Payer"), payer_id=_hdr(text, "Payer ID"), effective=_hdr(text, "Effective date"), text=text)
    first = SECTION.search(text)
    head = text[:first.start()] if first else text
    p.status_lines = [ln.strip() for ln in head.splitlines()[5:] if ln.strip()]
    status = " ".join(p.status_lines)
    m = re.search(r"apply to dates of service on or after (\d{4}-\d{2}-\d{2})", status)
    p.applies_from = m.group(1) if m else p.effective
    m = re.search(r"dates of service on or before (\d{4}-\d{2}-\d{2})", status)
    p.applies_until = m.group(1) if m else None
    p.superseded = "SUPERSEDED" in status.upper()
    m = re.search(r"Replaced by (MP-[A-Z]+-\d+)", status)
    p.superseded_by = m.group(1) if m else None
    matches = list(SECTION.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end]
        body = body.split("SYNTHETIC DATA")[0]
        sid = m.group(1)
        line = text[:m.start()].count("\n") + 1
        if sid == "7":
            for row in body.strip().splitlines():
                rm = re.match(r"(7\.\d+) (.*)", row.strip())
                if rm:
                    p.params.append((rm.group(1), rm.group(2)))
        else:
            p.sections[sid] = {"heading": (m.group(2) or "").strip() or None, "text": " ".join(body.split()), "line": line}
    for label, text_ in p.params:
        n = re.search(r"(\d+) days", text_)
        if label == "7.1" and n:
            p.windows["appeal_days"] = int(n.group(1))
        elif label == "7.2" and n:
            p.windows["timely_filing_days"] = int(n.group(1))
        elif label == "7.3" and n:
            p.windows["corrected_claim_days"] = int(n.group(1))
        elif label == "7.4":
            p.address = text_.replace("Appeals address:", "").strip()
    return p


def load_policies(ctx):
    out = []
    for f in ctx.guard.list_files("policy"):
        if f.endswith(".txt"):
            out.append(parse_policy(f, ctx.read("policy", f)))
    return out


def applicable(p, dos):
    """(bool, reason). A policy applies to a date of service within [applies_from, applies_until]."""
    d = to_date(dos)
    if p.applies_from and d < to_date(p.applies_from):
        return False, f"date of service {dos} is before {p.applies_from}, when this policy starts to apply"
    if p.applies_until and d > to_date(p.applies_until):
        return False, f"superseded: this version last applied to dates of service on or before {p.applies_until}" + (f"; replaced by {p.superseded_by}" if p.superseded_by else "")
    return True, ""
