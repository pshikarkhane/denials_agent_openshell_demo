"""Policy library: 8 primary + 3 distractor policy documents (LLM-assisted, then frozen).

The LLM writes only the prose of each numbered section. Everything else is injected deterministically: titles, ids, payers,
effective dates, version history, the Key Parameters block (appeal / timely-filing / corrected-claim windows and
policy-specific numbers), the code pairs of MP-BND-002, fixed sentences, and the corrected-claim sentence of the policies
behind CORRECT_AND_RESUBMIT cases. Section numbers and requirements come from the criteria in truth.json, so every
`policy_criteria[].section` exists; sections are rendered in numeric order. Fictional payers, original wording.
Frozen: existing files are never overwritten without --force. Usage: python -m data_gen.gen_policies [--data data] [--force]
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from data_gen import reference as R
from data_gen.docs_util import SYNTHETIC_FOOTER
from data_gen.gen_cases import build_manifest, load_truths
from data_gen.llm import datagen_record, generate, load_models
from data_gen.render_docs import PAYER_ADDR

MAX_TRIES = 3
BANNED = re.compile(r"aetna|cigna|united ?health|humana|anthem|blue cross|kaiser|cms|\d{4}-\d{2}-\d{2}|MP-[A-Z]+-\d+|"
                    r"\bunless\b|clinically justified|\bexcept(?:ion|ions)?\b", re.I)
_PERTURB = {6: 4, 12: 6, 14: 7, 30: 45, 20: 12, 21: 13, 90: 60}
SYSTEM = ("You write sections of FICTIONAL health plan medical policies for a software demo. Use original wording; never copy "
          "real payer or CMS text. Plain prose only, no markdown, no bullet lists. State exactly the requirement given: add no "
          "exceptions, caveats, or conditions of your own.")

# Sections that exist only for APL-001 (no truth criteria reference this policy).
APL_SECTIONS = {"2.1": "A provider may request a first-level appeal of an adverse claim determination within the appeal window in Section 7.",
                "2.2": "A provider who disagrees with the first-level outcome may request a second-level review within the second-level window in Section 7."}
CORRECTED_SENTENCE = ("An appeal does not cure missing or invalid claim data. When a claim is denied for missing or invalid "
                      "required information, the provider should submit a corrected claim.")
CORRECTED_POLICIES = {"MP-CLM-004": "3", "MP-BND-002": "4"}  # policies behind CORRECT_AND_RESUBMIT categories (8, 11, 9-correct)
FIXED_SENTENCES = {("MP-PT-011", "2.3"): "Visits 21 through 30 may be considered when functional improvement is documented and the "
                                          "plan of care is recertified. Visits beyond 30 are not covered."}


def sec_key(s):
    """Numeric sort key: '2.1(a)' -> [(0,2),(0,1),(1,'a')]."""
    return [(0, int(x)) if x.isdigit() else (1, x) for x in re.findall(r"\d+|[a-z]", s)]


def collect_sections(root):
    """(policy_id -> {section -> requirement text}) from every truth.json; conflicting texts are an error."""
    _, truths = load_truths(root)
    out = {}
    for t in truths:
        for c in t.policy_criteria:
            sec = c.section.lstrip("§")
            prev = out.setdefault(t.policy_id, {}).setdefault(sec, c.text)
            if prev != c.text:
                raise SystemExit(f"{t.policy_id} section {sec}: conflicting requirement texts {prev!r} vs {c.text!r}")
    out["MP-APL-001"] = dict(APL_SECTIONS)
    return out


def perturb(text):
    return re.sub(r"\d+", lambda m: str(_PERTURB.get(int(m.group()), int(m.group()) + 5)), text)


def _ints(text):
    return {int(x) for x in re.findall(r"(?<![\d.])\d+(?![\d.])", re.sub(r"\b\d+(\.\d+)?(\([a-z]\))?\b(?= *[:])", "", text))}


def _prompt(pid, title, payer, sections, extra=""):
    lines = "\n".join(f"### {s}\nRequirement to state: {r}" for s, r in sections.items())
    return (f"Policy: {title} ({pid}), issued by the fictional plan {R.PAYER_NAMES[payer]}.{extra}\n"
            "Write: first a section headed '### 1' (Purpose and scope, 2 sentences, no numbers), then each numbered section below. "
            "For each section write 2-3 sentences of policy language that states its requirement. Keep every number in the "
            "requirement exactly as given and add NO other numbers, dates, policy ids or code lists. Output each section as a line "
            "'### <number>' followed by its paragraph.\n\n### 1\n(purpose)\n" + lines)


def _parse(text):
    parts = re.split(r"^###\s*(\S+)\s*$", text, flags=re.M)
    return {parts[i]: " ".join(parts[i + 1].split()) for i in range(1, len(parts) - 1, 2)}


def write_sections(cfg, pid, title, payer, sections, extra=""):
    feedback = ""
    for attempt in range(MAX_TRIES):
        got = _parse(generate(cfg, _prompt(pid, title, payer, sections, extra) + feedback, SYSTEM))
        problems = [f"missing section {s}" for s in ["1", *sections] if not got.get(s)]
        for s, req in sections.items():
            body = got.get(s, "")
            extra_nums = _ints(body) - _ints(req)
            if extra_nums:
                problems.append(f"section {s} contains numbers not in its requirement: {sorted(extra_nums)}")
            if _ints(req) - _ints(body):
                problems.append(f"section {s} must contain the number(s) {sorted(_ints(req) - _ints(body))}")
        for s, body in got.items():
            if BANNED.search(body):
                problems.append(f"section {s} contains a banned pattern (date, policy id, real payer name, 'unless'/'exception' wording)")
        if not problems:
            return got
        feedback = "\n\nYour previous answer was rejected: " + "; ".join(problems) + ". Fix these and answer again."
    raise SystemExit(f"{pid}: could not get valid sections after {MAX_TRIES} tries: {problems}")


def params_block(pid, payer, parent=None, superseded=False):
    """Key parameters. A distractor states ITS OWN values: perturbed policy-specific numbers, and for a superseded
    timely-filing version its own (older) filing limit, so the document never contradicts itself."""
    pay = dict(R.PAYERS[payer])
    if superseded:
        pay["timely_filing_days"] = int(perturb(str(pay["timely_filing_days"])))
    rows = [f"7.1 Appeal deadline: {pay['appeal_days']} days from the date of the claim determination notice.",
            f"7.2 Timely filing limit: {pay['timely_filing_days']} days from the date of service.",
            f"7.3 Corrected claims: must be received within {pay['corrected_claim_days']} days of the date of the notice.",
            f"7.4 Appeals address: {PAYER_ADDR[payer]}"]
    base = parent or pid
    specific = {"MP-PA-003": [f"7.5 Retroactive authorization window: {R.RETRO_AUTH_WINDOW_DAYS} days from the date of service."],
                "MP-PT-011": [f"7.5 Outpatient therapy visit limit: {R.PT_VISIT_LIMIT} visits per calendar year.",
                              f"7.6 Maximum visits with documented functional improvement and a recertified plan of care: {R.PT_VISIT_CAP} visits per calendar year."],
                "MP-BND-002": ["7.5 Distinct procedural service modifier: 59 (or XS) on the denied line."],
                "MP-APL-001": [f"7.5 Second-level review: must be requested within {pay['appeal_days']} days of the date of the first-level appeal decision notice."]}
    extra = specific.get(base, [])
    if parent:  # perturb the numbers in the text, never the row label (7.5)
        extra = [x.split(" ", 1)[0] + " " + perturb(x.split(" ", 1)[1]) for x in extra]
    return rows + extra


def injected_sections(pid):
    """Deterministic sections: {number: (heading suffix, body)}."""
    out = {}
    if pid == "MP-BND-002":
        pairs = "; ".join(f"CPT {c2} ({R.CPT[c2]}) is bundled into CPT {c1} ({R.CPT[c1]}) when both are billed for the same session"
                          for c1, c2 in R.BUNDLE_PAIRS)
        out["3"] = ("Code pairs subject to this edit", pairs + ". A distinct-procedural-service modifier on the denied line is required to request separate payment.")
    if pid in CORRECTED_POLICIES:
        out[CORRECTED_POLICIES[pid]] = ("Corrections and resubmission", CORRECTED_SENTENCE + " The corrected-claim deadline is stated in Section 7.3.")
    return out


def render_policy(pid, title, payer, effective, bodies, sections, status_lines, parent=None, superseded=False):
    entries = {s: (f"Section {s}", bodies[s] + (" " + FIXED_SENTENCES[(pid, s)] if (pid, s) in FIXED_SENTENCES else "")) for s in sections}
    for s, (suffix, body) in ({} if parent else injected_sections(pid)).items():
        entries[s] = (f"Section {s}  {suffix}", body)
    out = [title.upper(), f"Policy ID: {pid}", f"Payer: {R.PAYER_NAMES[payer]}", f"Payer ID: {payer}",
           f"Effective date: {effective}", *status_lines, "", "Section 1  Purpose and scope", bodies["1"], ""]
    for s in sorted(entries, key=sec_key):
        out += [entries[s][0], entries[s][1], ""]
    out += ["Section 7  Key parameters and general provisions", *params_block(pid, payer, parent, superseded), "", SYNTHETIC_FOOTER]
    return "\n".join(out) + "\n"


def build_all(cfg, root, force=False):
    root = Path(root)
    lib = root / "policy_library"
    lib.mkdir(exist_ok=True)
    secs = collect_sections(root)
    jobs = []
    for pid, payer in R.POLICIES.items():
        status = [f"Version history: Version 3.0, effective {R.POLICY_EFFECTIVE[pid]}. The requirements below carry forward "
                  "unchanged from Version 2.0 (effective 2025-01-01) and apply to dates of service on or after 2025-01-01."]
        jobs.append((pid, R.POLICY_TITLES[pid], payer, R.POLICY_EFFECTIVE[pid].isoformat(), secs[pid], status, "", None, False))
    eff = {"MP-IMG-012": "2026-02-01", "MP-PA-030": "2026-04-01", "MP-TF-010": "2024-01-01"}
    for did, d in R.DISTRACTOR_DOCS.items():
        sup = d["kind"] == "superseded version"
        status = [f"Status: SUPERSEDED. Replaced by {d['parent']} (current version effective {R.POLICY_EFFECTIVE[d['parent']]}). "
                  "Version 1.0, effective 2024-01-01; this version last applied to dates of service on or before 2024-12-31."
                  ] if sup else ["Version history: Version 1.0, current."]
        sections = {s: perturb(r) for s, r in secs[d["parent"]].items()}
        jobs.append((did, d["title"], d["payer"], eff[did], sections, status,
                     " This policy is a near-duplicate of a sibling policy; its thresholds differ.", d["parent"], sup))
    written = {}
    for pid, title, payer, effective, sections, status, extra, parent, sup in jobs:
        path = lib / f"{pid}.txt"
        if path.exists() and not force:
            written[pid] = "kept (frozen)"
            continue
        bodies = write_sections(cfg, pid, title, payer, sections, extra)
        path.write_text(render_policy(pid, title, payer, effective, bodies, list(sections), status, parent, sup))
        written[pid] = "written"
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(lib.glob("*.txt"))}
    man, truths = load_truths(root)
    build_manifest(root, truths, man["seed"], {"datagen": datagen_record(cfg, "data_gen/gen_policies.py", man.get("datagen")),
                                               "policy_library": {"frozen": True, "files": files}})
    return written


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--force", action="store_true", help="regenerate even though the library is frozen")
    a = ap.parse_args()
    print(json.dumps(build_all(load_models(), a.data, a.force), indent=1))
