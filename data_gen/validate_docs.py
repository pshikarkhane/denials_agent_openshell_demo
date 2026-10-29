"""Document-level checks for validate_data: policy library, rendered documents, evidence quotes, leaks, mount safety."""
import hashlib
import re
from pathlib import Path

from data_gen import reference as R
from data_gen.docs_util import SYNTHETIC_FOOTER, locate, needle, source_path
from data_gen.gen_cases import STD_DOCS
from data_gen.note_lint import note_body, spell_issues
from data_gen.schema import Decision, Trap

STD = STD_DOCS  # eob, denial letter, claim history: rendered for every case
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


def _sec_key(s):
    return [(0, int(x)) if x.isdigit() else (1, x) for x in re.findall(r"\d+|[a-z]", s)]


CORRECTED_SENTENCE = ("An appeal does not cure missing or invalid claim data. When a claim is denied for missing or invalid "
                      "required information, the provider should submit a corrected claim.")


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
        pay = dict(R.PAYERS[payer])
        if pid in R.DISTRACTOR_DOCS and R.DISTRACTOR_DOCS[pid]["kind"] == "superseded version":
            from data_gen.gen_policies import perturb
            pay["timely_filing_days"] = int(perturb(str(pay["timely_filing_days"])))  # its own, older limit
        for label, key in (("7.1 Appeal deadline", "appeal_days"), ("7.2 Timely filing limit", "timely_filing_days"),
                           ("7.3 Corrected claims", "corrected_claim_days")):
            m = re.search(rf"^{re.escape(label)}:.*?(\d+) days", t, re.M)
            if not m or int(m.group(1)) != pay[key]:
                rep.error(f"policy_library/{pid}", f"{label} must state {pay[key]} days (reference.py), found {m.group(1) if m else None}")
        if SYNTHETIC_FOOTER not in t:
            rep.error(f"policy_library/{pid}", "missing synthetic footer")
        secs = re.findall(r"^Section (\S+)", t, re.M)
        if secs != sorted(secs, key=_sec_key):
            rep.error(f"policy_library/{pid}", f"sections are not in numeric order: {secs}")
        majors = sorted({int(x.split(".")[0].rstrip("(abc)")) for x in secs if x[0].isdigit() and x != "7"})
        if majors and majors != list(range(majors[0], majors[0] + len(majors))):
            rep.error(f"policy_library/{pid}", f"gaps in section numbering: major sections {majors}")
        subs = {}
        for x in secs:
            m = re.match(r"(\d+)\.(\d+)", x)
            if m:
                subs.setdefault(int(m.group(1)), set()).add(int(m.group(2)))
        for mj, ss in subs.items():
            if sorted(ss) != list(range(1, len(ss) + 1)):
                rep.error(f"policy_library/{pid}", f"gaps in subsection numbering of section {mj}: {sorted(ss)}")
        for bad in ("unless clinically justified", "approved exception"):
            if bad in t.lower():
                rep.error(f"policy_library/{pid}", f"contains removed wording {bad!r}")
        if pid in ("MP-CLM-004", "MP-BND-002") and CORRECTED_SENTENCE not in " ".join(t.split()):
            rep.error(f"policy_library/{pid}", "missing the corrected-claim sentence required for CORRECT_AND_RESUBMIT policies")
        if pid in ("MP-CLM-004", "MP-BND-002") and re.search(r"appeals? (?:is|are) (?:barred|not permitted|prohibited)", t, re.I):
            rep.error(f"policy_library/{pid}", "must not say appeals are barred")
        if pid == "MP-BND-002":
            for c1, c2 in R.BUNDLE_PAIRS:
                if f"CPT {c2}" not in t or f"CPT {c1}" not in t:
                    rep.error(f"policy_library/{pid}", f"bundled pair {c1}/{c2} is not stated explicitly")
        if pid in ("MP-TF-001", "MP-TF-010"):
            sec21 = _section_bodies(t).get("2.1", "")
            lim = re.search(r"^7\.2 .*?(\d+) days", t, re.M)
            if lim and lim.group(1) not in _ints(sec21):
                rep.error(f"policy_library/{pid}", f"section 2.1 and 7.2 disagree on the filing limit (7.2 says {lim.group(1)})")
        if pid == "MP-TF-010" and not re.search(r"SUPERSEDED.*MP-TF-001.*\d{4}-\d{2}-\d{2}", t, re.S):
            rep.error(f"policy_library/{pid}", "must state it is superseded, with the superseding policy and date")
        if pid == "MP-PT-011":
            s23 = _section_bodies(t).get("2.3", "")
            if "21 through 30" not in s23:
                rep.error(f"policy_library/{pid}", "section 2.3 must say visits 21 through 30 may be considered")
        if pid == "MP-APL-001" and "first-level appeal decision" not in t:
            rep.error(f"policy_library/{pid}", "must state when the second-level window starts")
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
        eob, den, hist = (base / "docs" / s for s in STD)
        if not (eob.exists() and den.exists() and hist.exists() and (base / "task.md").exists()):
            rep.error(w, "eob_835.txt, denial_letter.txt, claim_history.txt or task.md is not rendered")
            continue
        e_txt, d_txt, h_txt = eob.read_text(), den.read_text(), hist.read_text()
        # claim_history agrees with truth
        for n in (t.claim.claim_no, t.patient.synthetic_id, t.payer_id, t.claim.dos.isoformat(),
                  f"{f['claim_submitted_date']}  Submitted to clearinghouse (submission 1 of 1)",
                  f"{f['clearinghouse_accepted_date']}  Clearinghouse acceptance (277CA): ACCEPTED",
                  f"{f['payer_received_date']}  Received by payer", f"{t.denial.denial_date.isoformat()}  Adjudicated by payer", f"(CARC {t.denial.carc})"):
            if n not in " ".join(h_txt.split()) and " ".join(n.split()) not in " ".join(h_txt.split()):
                rep.error(w, f"claim_history: expected {n!r} (from truth.json) is missing")
        if t.category == 10:
            exp = f"claim {f['original_claim_no']} paid {f['original_paid_date']} amount {f['original_paid_amount']:.2f}"
            if exp not in h_txt:
                rep.error(w, "claim_history: prior adjudicated claim reference disagrees with truth")
        elif "Prior adjudicated claims for this service: none recorded" not in h_txt:
            rep.error(w, "claim_history: must state that no prior adjudicated claim is recorded")
        if t.category in (3, 4):
            want = (f"Retroactive authorization request: received {f['retro_request_date']}" if "retro_request_date" in f
                    else "Retroactive authorization request: none recorded")
            if want not in h_txt:
                rep.error(w, f"claim_history: expected {want!r}")
        elif "Retroactive authorization" in h_txt:
            rep.error(w, "claim_history mentions retroactive authorization in a case that has no such scenario")
        if f"{t.action_deadline.isoformat()}" not in d_txt:
            rep.error(w, "denial letter does not state the action deadline date")
        if "action_deadline" not in (base / "task.md").read_text():
            rep.error(w, "task.md output format must name action_deadline")
        money = f"{t.claim.billed:.2f}"
        for label, txt, need in (
                ("eob", e_txt, [t.claim.claim_no, money, t.claim.dos.isoformat(), t.claim.cpt, t.denial.carc, t.patient.synthetic_id]),
                ("denial", d_txt, [t.claim.claim_no, money, t.claim.dos.isoformat(), t.denial.carc, t.appeal_deadline.isoformat(),
                                   f"Date of notice: {t.denial.denial_date.isoformat()}", f"by {f['corrected_claim_deadline']}",
                                   f"within {R.PAYERS[t.payer_id]['appeal_days']} days"])):
            for n in need:
                if n not in txt:
                    rep.error(w, f"{label}: expected {n!r} (from truth.json) is missing")
        # EOB realism rules
        if e_txt.splitlines()[0] != "835 REMITTANCE ADVICE":
            rep.error(w, "eob: title must be exactly '835 REMITTANCE ADVICE' (no synthetic marker in the title)")
        ssn = re.search(r"SSN: (\S+)", e_txt)
        if not ssn or not re.fullmatch(r"XXX-XX-\d{4}", ssn.group(1)):
            rep.error(w, "eob: SSN line must be masked to the last four digits (XXX-XX-dddd)")
        rline = re.search(r"Rendering provider: (.*)", e_txt)
        if rline and f.get("missing_field") != "rendering_provider":
            if t.claim.cpt in ("72148", "73721") and "(Radiology)" not in rline.group(1):
                rep.error(w, "eob: rendering provider for an MRI must be radiology")
            if t.claim.cpt.startswith("97") and ", PT" not in rline.group(1):
                rep.error(w, "eob: rendering provider for therapy must be a therapist")
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
                    if ev not in ("eob_835.txt", "denial_letter.txt") and (f"criterion_{c.id}_quote", ev) not in quotes:
                        rep.error(w, f"criterion {c.id} cites {ev} but no verbatim evidence quote is recorded for it")
        elif docs - set(STD):
            rep.error(w, f"non-pilot case has clinical documents already: {sorted(docs - set(STD))}")
        if w in pilots and docs - set(STD) - planned:
            rep.error(w, f"documents that are not in the plan: {sorted(docs - set(STD) - planned)}")
        # criteria that rely on claim_history (all cases) need a recorded quote
        cq = {(x.key, x.source_file) for x in t.facts if x.evidence}
        for c in t.policy_criteria:
            if "claim_history.txt" in c.evidence and (f"criterion_{c.id}_quote", "claim_history.txt") not in cq:
                rep.error(w, f"criterion {c.id} cites claim_history.txt but no verbatim quote is recorded")
        if w in pilots:
            lint = man.get("note_lint", {})
            for d in sorted(docs - set(STD)):
                if d.startswith("notes/") or d == "supporting/pt_progress_note.txt":
                    for sp in spell_issues(note_body((base / "docs" / d).read_text())):
                        rep.error(w, f"{d}: possible misspelling {sp['word']!r} (did you mean {sp['suggestion']!r}?)")
                    rec = lint.get(f"{w}/{d}")
                    if not rec or rec.get("reviewer_issues") != 0 or rec.get("spell") != "pass":
                        rep.error(w, f"{d}: no passing note_lint record (spellcheck + second-pass reviewer) in the manifest")
            if t.category in (1, 2):
                ortho = next((d for d in docs if d.endswith("_ortho.txt")), None)
                if not ortho or "Imaging history:" not in (base / "docs" / ortho).read_text():
                    rep.error(w, "medical-necessity case: the ortho note must contain an 'Imaging history:' statement")
                if not any(x.key == "last_lumbar_imaging_date" and x.evidence and x.evidence.startswith("Imaging history:") for x in t.facts):
                    rep.error(w, "imaging history statement is not recorded as a quote on last_lumbar_imaging_date")
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
        for m in re.finditer(r"SYN-", text):
            if text[max(0, m.start() - 5):m.start()] != "MRN: ":
                rep.error(rel, "SYN- prefix is only allowed on MRNs")
                break
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
    if "git_sha" not in man:
        rep.error("manifest", "git_sha missing (regenerate the manifest inside the git repository)")
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
