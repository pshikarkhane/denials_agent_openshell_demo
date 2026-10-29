"""Document-level checks for validate_data: policy library, rendered documents, evidence quotes, leaks, mount safety."""
import hashlib
import re
from pathlib import Path

from data_gen import reference as R
from data_gen.docs_util import SYNTHETIC_FOOTER, locate, needle, source_path
from data_gen.schema import Decision, Trap

STD = ("eob_835.txt", "denial_letter.txt")
ENUM_TOKENS = [d.value for d in Decision]
DECISION_TOKEN = re.compile(r"\b(?:DO_NOT_APPEAL|CORRECT_AND_RESUBMIT|ESCALATE_MISSING_DOCS|APPEAL)\b")
LEAK = re.compile(r"truth\.json|rubric|\bgold\b|correct_decision|ground[- ]truth|" + "|".join(x.value for x in Trap), re.I)
CATEGORY_NAMES = [c["name"] for c in R.CATEGORIES.values()]
SSN = re.compile(r"\b(\d{3})-(\d{2})-(\d{4})\b")
PHONE = re.compile(r"\b(\d{3})-(\d{4})\b")
MRN = re.compile(r"MRN:\s*(\S+)")
FORBIDDEN_NAMES = {"truth.json", "rubric.json"}


def agent_visible_files(root):
    """Everything that is mounted into the sandbox (cases/*/docs/**, policy_library/**) plus each task.md."""
    root = Path(root)
    files = []
    for d in sorted((root / "cases").glob("C-*")):
        files += [p for p in sorted((d / "docs").rglob("*")) if p.is_file()] if (d / "docs").exists() else []
        if (d / "task.md").exists():
            files.append(d / "task.md")
    if (root / "policy_library").exists():
        files += [p for p in sorted((root / "policy_library").rglob("*")) if p.is_file()]
    return files


def _section_bodies(text):
    parts = re.split(r"^Section (\S+)", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def _ints(s):
    return set(re.findall(r"(?<![\d.])\d+(?![\d.])", s))


def check_policy_library(root, truths, rep):
    lib = Path(root) / "policy_library"
    texts = {}
    expected = {**{p: R.POLICIES[p] for p in R.POLICIES}, **{d: v["payer"] for d, v in R.DISTRACTOR_DOCS.items()}}
    for pid, payer in expected.items():
        p = lib / f"{pid}.txt"
        if not p.exists():
            rep.error("policy_library", f"{pid}.txt is missing")
            continue
        t = p.read_text()
        texts[pid] = t
        if f"Policy ID: {pid}" not in t or f"Payer ID: {payer}" not in t:
            rep.error(f"policy_library/{pid}", "policy id or payer id line is missing/wrong")
        if pid in R.POLICY_EFFECTIVE and f"Effective date: {R.POLICY_EFFECTIVE[pid].isoformat()}" not in t:
            rep.error(f"policy_library/{pid}", "effective date disagrees with reference.py")
        pay = R.PAYERS[payer]
        for label, key in (("7.1 Appeal deadline", "appeal_days"), ("7.2 Timely filing limit", "timely_filing_days"),
                           ("7.3 Corrected claims", "corrected_claim_days")):
            m = re.search(rf"^{re.escape(label)}:.*?(\d+) days", t, re.M)
            if not m or int(m.group(1)) != pay[key]:
                rep.error(f"policy_library/{pid}", f"{label} must state {pay[key]} days (reference.py), found {m.group(1) if m else None}")
        if SYNTHETIC_FOOTER not in t:
            rep.error(f"policy_library/{pid}", "missing synthetic footer")
    seen = set()
    for t in truths:
        body = _section_bodies(texts.get(t.policy_id, ""))
        for c in t.policy_criteria:
            sec = c.section.lstrip("§")
            if sec not in body:
                rep.error(t.case_id, f"criterion {c.id} section {sec} does not exist in {t.policy_id}")
            elif _ints(c.text) - _ints(body[sec]):
                rep.error(t.case_id, f"section {sec} of {t.policy_id} lacks the number(s) in criterion text {c.text!r}")
            seen.add((t.policy_id, sec))
        for f in t.facts:  # facts sourced from the policy library must appear in the cited policy (or its distractor)
            if f.source_file == "policy_library" and needle(f) is not None:
                hay = texts.get(t.policy_id, "") + texts.get(R.DISTRACTORS.get(t.policy_id, ""), "")
                if needle(f) not in hay:
                    rep.error(t.case_id, f"fact '{f.key}'={needle(f)!r} not found in policy library text for {t.policy_id}")
    return texts


def check_documents(root, truths, man, rep):
    root = Path(root)
    pilots = set(man.get("pilot_cases", []))
    for t in truths:
        w, base = t.case_id, root / "cases" / t.case_id
        f = {x.key: x.value for x in t.facts}
        eob, den = (base / "docs" / s for s in STD)
        if not (eob.exists() and den.exists() and (base / "task.md").exists()):
            rep.error(w, "eob_835.txt, denial_letter.txt or task.md is not rendered")
            continue
        e_txt, d_txt = eob.read_text(), den.read_text()
        money = f"{t.claim.billed:.2f}"
        for label, txt, need in (
                ("eob", e_txt, [t.claim.claim_no, money, t.claim.dos.isoformat(), t.claim.cpt, t.denial.carc, t.patient.synthetic_id]),
                ("denial", d_txt, [t.claim.claim_no, money, t.claim.dos.isoformat(), t.denial.carc, t.appeal_deadline.isoformat(),
                                   f"Date of notice: {t.denial.denial_date.isoformat()}", f"by {f['corrected_claim_deadline']}",
                                   f"within {R.PAYERS[t.payer_id]['appeal_days']} days"])):
            for n in need:
                if n not in txt:
                    rep.error(w, f"{label}: expected {n!r} (from truth.json) is missing")
        if t.category == 7 and (f"{f['pr1_amount']:.2f}" not in e_txt or f"{f['allowed_amount']:.2f}" not in e_txt):
            rep.error(w, "eob: PR-1 or allowed amount disagrees with truth.json")
        if f["as_of_date"] not in (base / "task.md").read_text():
            rep.error(w, "task.md must state the as-of date from truth facts")
        # fact quotes / literals appear in their (rendered) source docs; stored line numbers are correct
        for fa in t.facts:
            n, p = needle(fa), source_path(root, w, fa.source_file)
            if n is None or p is None:
                continue
            if not p.exists():
                if w in pilots and fa.evidence:
                    rep.error(w, f"fact '{fa.key}' cites {fa.source_file}, which does not exist")
                continue
            ln = locate(p.read_text(), fa)
            if ln is None:
                rep.error(w, f"fact '{fa.key}': {n!r} does not appear in {fa.source_file}")
            elif fa.line != ln:
                rep.error(w, f"fact '{fa.key}': stored line {fa.line} but text is on line {ln} of {fa.source_file}")
        docs = {p.relative_to(base / "docs").as_posix() for p in (base / "docs").rglob("*") if p.is_file()}
        planned = {x.value for x in t.facts if x.key == "planned_document"}
        if w in pilots:
            if planned - docs:
                rep.error(w, f"pilot case: planned documents not rendered: {sorted(planned - docs)}")
            quotes = {(x.key, x.source_file) for x in t.facts if x.evidence}
            for c in t.policy_criteria:
                for ev in c.evidence:
                    if ev not in STD and (f"criterion_{c.id}_quote", ev) not in quotes:
                        rep.error(w, f"criterion {c.id} cites {ev} but no verbatim evidence quote is recorded for it")
        elif docs - set(STD):
            rep.error(w, f"non-pilot case has clinical documents already: {sorted(docs - set(STD))}")
    return pilots


def check_agent_visible(root, truths, rep):
    case_decisions = {t.case_id: t.correct_decision for t in truths}
    for p in agent_visible_files(root):
        rel = p.relative_to(root).as_posix()
        text = p.read_text()
        if SYNTHETIC_FOOTER not in text.rstrip().splitlines()[-1]:
            rep.error(rel, f"does not end with '{SYNTHETIC_FOOTER}'")
        if LEAK.search(text):
            rep.error(rel, f"leaks answer-key vocabulary: {LEAK.search(text).group()!r}")
        for name in CATEGORY_NAMES:
            if re.search(rf"\b{re.escape(name)}\b(?!s)", text):  # exact, case-sensitive: policy titles may share words
                rep.error(rel, f"contains a category name: {name!r}")
        toks = set(DECISION_TOKEN.findall(text))
        if p.name == "task.md":
            if toks != set(ENUM_TOKENS):
                rep.error(rel, "task.md must list all four decision values (format spec) and nothing else")
        elif toks:
            rep.error(rel, f"mentions decision value(s) {sorted(toks)}")
        for m in SSN.finditer(text):
            if not m.group(1).startswith("9"):
                rep.error(rel, f"SSN-like string {m.group(0)} is not in the invalid 9xx range")
        for m in PHONE.finditer(text):
            if not (m.group(1) == "555" and m.group(2).startswith("01")):
                rep.error(rel, f"phone-like string {m.group(0)} is not 555-01xx")
        for m in MRN.finditer(text):
            if not m.group(1).startswith("SYN-"):
                rep.error(rel, f"MRN {m.group(1)} does not start with SYN-")


def check_mount_safety(root, rep):
    """Nothing answer-key-like may sit in a mountable location (docs/, policy_library/, sandbox/)."""
    root = Path(root)
    spots = [d / "docs" for d in (root / "cases").glob("C-*")] + [root / "policy_library", root.parent / "sandbox"]
    for spot in spots:
        if not spot.exists():
            continue
        for p in spot.rglob("*"):
            parts = {x.lower() for x in p.relative_to(spot).parts}
            if p.is_symlink():
                rep.error(str(p), "symlink inside a mountable directory")
            if p.name.lower() in FORBIDDEN_NAMES or "gold" in parts or "rubric" in p.name.lower():
                rep.error(str(p), "answer-key file/dir under a path that will be mounted into the sandbox")
            if spot.name == "docs" and p.is_file() and p.suffix != ".txt":
                rep.error(str(p), "only .txt documents are allowed under docs/")
    for df in (root.parent / "sandbox").rglob("Dockerfile*") if (root.parent / "sandbox").exists() else []:
        if re.search(r"(truth|rubric|gold)", df.read_text(), re.I):
            rep.error(str(df), "Dockerfile references truth/rubric/gold")


def check_manifest_datagen(root, man, rep):
    dg = man.get("datagen")
    if not dg:
        rep.error("manifest", "datagen record (model id, prompts hash) is missing")
        return
    if len(dg.get("prompts_sha256_by_file", {})) < 2:
        rep.error("manifest", "datagen.prompts_sha256_by_file must cover both gen_policies.py and gen_clinical.py")
    for k in ("model_id", "agent_model_id", "prompts_sha256"):
        if not dg.get(k):
            rep.error("manifest", f"datagen.{k} is missing")
    if dg.get("model_id") == dg.get("agent_model_id") or "nemotron" in str(dg.get("model_id", "")).lower():
        rep.error("manifest", "datagen model must not be the agent model")
    lib = man.get("policy_library", {}).get("files", {})
    for name, h in lib.items():
        p = Path(root) / "policy_library" / name
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != h:
            rep.error("manifest", f"frozen policy file {name} changed or is missing")
