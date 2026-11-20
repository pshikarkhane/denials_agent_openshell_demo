"""Seeded, deterministic mutation generator for judge validation (no LLM). Source: the gold deliverables of the pilot cases.

Each mutated copy has exactly ONE change (one fact altered, applied wherever that fact appears) plus a record: type, original text, mutated
text, expected effect. Controls (C1-C4) must NOT be flagged material. Output goes under runs/<run_id>/mutations/, never under data/.
  python -m eval.mutations --run-id val-mut [--seed 20261031]
Mutation types: M1 swap a date, M2 change an amount, M3 change a CPT/ICD-10/denial code, M4 wrong deadline, M5 nonexistent policy section,
M6 distractor policy id, M7 unsupported clinical history, M8 invented enclosure/document, M9 subtle numeric edit, M10 delete a required
enclosure, M11 remove an evidence citation, M12 flip the decision (decision.json only, rationale untouched)."""
import argparse
import json
import random
import re
from datetime import date, timedelta
from pathlib import Path

from data_gen import reference as R
from data_gen.gen_cases import load_truths
from eval.common import ROOT

SEED = 20261031
TYPES = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M12"]
CONTROLS = ["C2", "C3", "C4"]  # C1 = the unchanged gold (scored separately)
ISO = r"\d{4}-\d{2}-\d{2}"
NOT_FILENAME_DATE = rf"(?<![/\w])({ISO})(?![_\w])"   # a date that is not part of a file name like notes/2026-03-23_pcp.txt
WINDOWS = {90, 120, 180, 365}
EXPECT = {
    "M1": ("flag", "a date that no document supports: upheld MATERIAL flag at the date and/or a failed evidence criterion"),
    "M2": ("flag", "an amount that disagrees with the documents: upheld MATERIAL flag"),
    "M3": ("flag", "a code that disagrees with the documents: upheld MATERIAL flag and/or a failed identifier/denial-reason criterion"),
    "M4": ("flag", "a wrong deadline: upheld MATERIAL flag and/or a failed deadline criterion"),
    "M5": ("flag", "a policy section that does not exist: upheld MATERIAL flag and/or a failed policy-citation criterion"),
    "M6": ("flag", "a distractor policy cited as governing: upheld MATERIAL flag and/or a failed policy criterion"),
    "M7": ("flag", "clinical history no document contains: upheld MATERIAL flag"),
    "M8": ("flag", "an enclosure/document that does not exist: upheld MATERIAL flag"),
    "M9": ("flag", "a subtly wrong number (digits transposed): upheld MATERIAL flag"),
    "M10": ("criterion", "a required enclosure missing: the enclosure criterion fails"),
    "M11": ("criterion", "no evidence citation for one criterion: the evidence criterion for that section fails"),
    "M12": ("criterion", "the decision flipped while the rationale is unchanged: the decision criterion fails"),
    "C2": ("control", "harmless rewording, every fact kept: no MATERIAL flag, no criterion flips to FAIL"),
    "C3": ("control", "whitespace and heading style only: no MATERIAL flag, no criterion flips to FAIL"),
    "C4": ("control", "a typo and a courtesy line: no MATERIAL flag, no criterion flips to FAIL"),
}
OTHER_CPT = ["97110", "97112", "97530", "97140", "72148", "73721", "99213", "93000", "85025", "27447"]
OTHER_ICD = ["M54.50", "M25.561", "E11.9", "I10", "J06.9", "M17.12", "M51.26"]
OTHER_CARC = ["CO-97", "CO-4", "CO-18", "CO-197", "CO-11", "PR-1"]
INVENTED_HISTORY = [
    "The patient also completed 12 weeks of formal outpatient physical therapy at an outside clinic before this episode",
    "Examination documented a positive Waddell sign and an absent Achilles reflex on the left",
    "The patient reported morning stiffness lasting more than 90 minutes and two prior emergency visits for the same complaint",
    "A recent cortisone injection provided only two days of relief",
]
INVENTED_DOCS = ["supporting/prior_authorization_approval.txt (Prior authorization approval letter)",
                 "supporting/payer_call_log.txt (Record of the 2026-08-10 call with the payer)",
                 "supporting/second_opinion_letter.txt (Second opinion letter)"]
REWORD = [(r"\bstates\b", "indicates"), (r"\bdocuments\b", "records"), (r"\bTherefore\b", "As a result"), (r"\btherefore\b", "so"), (r"\bIn addition\b", "Also"),
          (r"\bThis confirms\b", "This shows"), (r"\bBecause\b", "Since"), (r"\bbecause\b", "since"), (r"\bshows\b", "reflects"), (r"\bapproximately\b", "about"),
          (r"\bhowever\b", "but"), (r"\bsupports\b", "backs"), (r"\brequires\b", "calls for"), (r"\bremain\b", "are left"), (r"\bshould\b", "ought to")]


# ---------------------------------------------------------------- helpers
def facts(t):
    d = {}
    for f in t.facts:
        d.setdefault(f.key, f.value)
    return d


def money_forms(v):
    return [f"${v:,.2f}", f"{v:,.2f}", f"{v:.2f}"]


def sub_all(text, pattern, repl, flags=0):
    new, n = re.subn(pattern, repl, text, flags=flags)
    return new, n


def context_of(text, needle, width=140):
    i = text.find(needle)
    if i < 0:
        return ""
    a, b = text.rfind("\n", 0, i) + 1, text.find("\n", i)
    line = text[a:b if b != -1 else len(text)]
    return " ".join(line.split())[:width * 3]


def fmt_date(d):
    return d.isoformat()


class Skip(Exception):
    pass


# ---------------------------------------------------------------- mutations: each returns (deliverable, decision_text, record_fields)
def m1(text, dec, t, f, rng):
    cands = []
    for d in sorted(set(re.findall(NOT_FILENAME_DATE, text))):
        if d in (t.claim.dos.isoformat(), f["as_of_date"], t.action_deadline.isoformat(), t.appeal_deadline.isoformat(), f["corrected_claim_deadline"]):
            continue
        cands.append(d)
    note_dates = [d for d in cands if any(x.value for x in t.facts if x.key == "planned_document" and d in x.value)]
    pool = note_dates or cands
    if not pool:
        raise Skip("no citeable date other than DOS / review date / deadlines in the deliverable")
    old = rng.choice(pool)
    new = fmt_date(date.fromisoformat(old) + timedelta(days=rng.choice([6, 9, 13, 17, 23])))
    out, n = sub_all(text, rf"(?<![/\w]){re.escape(old)}(?![_\w])", new)
    return out, dec, {"original": old, "mutated": new, "occurrences": n}


def m2(text, dec, t, f, rng):
    v = t.claim.billed
    forms = [x for x in money_forms(v) if x in text]
    if not forms:
        raise Skip("billed amount does not appear in the deliverable")
    new_v = round(v + rng.choice([47.5, 113.25, 275.0]), 2)
    out = text
    n = 0
    for old in sorted(forms, key=len, reverse=True):
        new = money_forms(new_v)[money_forms(v).index(old)]
        out, k = sub_all(out, re.escape(old), new)
        n += k
    return out, dec, {"original": f"{v:.2f}", "mutated": f"{new_v:.2f}", "occurrences": n}


def m3(text, dec, t, f, rng):
    opts = []
    if re.search(rf"\b{t.claim.cpt}\b", text):
        opts.append(("CPT", t.claim.cpt, rng.choice([c for c in OTHER_CPT if c != t.claim.cpt and c not in text])))
    for icd in t.claim.icd10:
        if icd in text:
            opts.append(("ICD-10", icd, rng.choice([c for c in OTHER_ICD if c not in text and c != icd])))
    if t.denial.carc in text:
        opts.append(("denial code", t.denial.carc, rng.choice([c for c in OTHER_CARC if c != t.denial.carc and c not in text])))
    if not opts:
        raise Skip("no CPT, ICD-10 or denial code appears in the deliverable")
    kind, old, new = opts[rng.randrange(len(opts))]
    out, n = sub_all(text, rf"(?<![\w.-]){re.escape(old)}(?![\w])", new)
    return out, dec, {"original": old, "mutated": new, "occurrences": n, "code_kind": kind}


def m4(text, dec, t, f, rng):
    old = t.action_deadline.isoformat()
    if old not in text:
        raise Skip("action deadline does not appear in the deliverable")
    new = fmt_date(t.action_deadline + timedelta(days=rng.choice([11, 17, 29, 41])))
    out, n = sub_all(text, rf"(?<![/\w]){re.escape(old)}(?![_\w])", new)
    return out, dec, {"original": old, "mutated": new, "occurrences": n}


def m5(text, dec, t, f, rng):
    ms = [m for m in re.finditer(r"(?:Sections?|§)\s*(\d+\.\d+(?:\([a-z]\))?)", text) if not m.group(1).startswith("7.")]
    if not ms:
        raise Skip("no requirement-section citation in the deliverable")
    m = ms[0]
    old, new = m.group(1), rng.choice(["4.7", "5.3(b)", "6.2(a)"])
    out = text[:m.start(1)] + new + text[m.end(1):]
    return out, dec, {"original": m.group(0), "mutated": m.group(0).replace(old, new), "occurrences": 1}


def m6(text, dec, t, f, rng):
    d = R.DISTRACTORS.get(t.policy_id)
    if not d:
        raise Skip(f"policy {t.policy_id} has no distractor in the library")
    if t.policy_id not in text:
        raise Skip("policy id does not appear in the deliverable")
    out, n = sub_all(text, rf"\b{re.escape(t.policy_id)}\b", d)
    return out, dec, {"original": t.policy_id, "mutated": d, "occurrences": n}


def m7(text, dec, t, f, rng):
    notes = re.findall(r"(?:\(source: |; )(notes/[\w\-.]+\.txt)", text)
    if not notes:
        raise Skip("the deliverable cites no clinical note to attach an invented history to")
    sentence = rng.choice(INVENTED_HISTORY) + f" (source: {notes[0]})."
    lines = text.split("\n")
    idx = next(i for i, ln in enumerate(lines) if notes[0] in ln)
    lines.insert(idx + 1, "\n" + sentence)
    return "\n".join(lines), dec, {"original": "", "mutated": sentence, "occurrences": 1}


def m8(text, dec, t, f, rng):
    doc = rng.choice(INVENTED_DOCS)
    lines = text.split("\n")
    enc = next((i for i, ln in enumerate(lines) if re.match(r"#+\s*Enclosures", ln.strip(), re.I)), None)
    if enc is not None:
        j = enc + 1
        last = None
        while j < len(lines) and not lines[j].startswith("#"):
            if lines[j].lstrip().startswith(("-", "*")):
                last = j
            j += 1
        if last is None:
            raise Skip("Enclosures section has no list to extend")
        new_line = f"- {doc}"
        lines.insert(last + 1, new_line)
    else:
        gi = next((i for i, ln in enumerate(lines) if re.match(r"#+\s*Gaps", ln.strip(), re.I)), None)
        if gi is None:
            raise Skip("no Enclosures or Gaps heading to attach an invented document to")
        new_line = f"Attached for the file: {doc}.\n"
        lines.insert(gi, new_line)
    return "\n".join(lines), dec, {"original": "", "mutated": new_line.strip(), "occurrences": 1}


def m9(text, dec, t, f, rng):
    cands = []
    for m in re.finditer(r"\b(\d{2,3}) (days|visits|weeks)\b", text):
        n = int(m.group(1))
        if n in WINDOWS:
            continue
        s = m.group(1)
        new = s[::-1] if s[::-1] != s else str(n + 1)
        if new != s and not new.startswith("0"):
            cands.append((m.group(0), f"{new} {m.group(2)}"))
    cands = sorted(set(cands))
    if not cands:
        raise Skip("no non-window 'N days/visits/weeks' fact in the deliverable")
    old, new = cands[rng.randrange(len(cands))]
    out, n = sub_all(text, rf"\b{re.escape(old)}\b", new)
    return out, dec, {"original": old, "mutated": new, "occurrences": n}


def m10(text, dec, t, f, rng):
    if t.correct_decision.value != "APPEAL" or not t.required_enclosures:
        raise Skip("not an appeal: no required enclosures")
    d = json.loads(dec)
    victim = rng.choice(d["enclosures"])
    lines = [ln for ln in text.split("\n") if not (victim in ln and ln.lstrip().startswith(("-", "*")))]
    if len(lines) == len(text.split("\n")):
        raise Skip("enclosure is not listed as a bullet in the deliverable")
    d["enclosures"] = [e for e in d["enclosures"] if e != victim]
    return "\n".join(lines), json.dumps(d, indent=2) + "\n", {"original": victim, "mutated": "(removed from the enclosure list in deliverable.md and decision.json)", "occurrences": 2, "section": None}


def m11(text, dec, t, f, rng):
    d = json.loads(dec)
    crit = [c for c in d["criteria"] if c.get("evidence")]
    rng.shuffle(crit)
    for c in crit:
        ev = c["evidence"]
        paras = text.split("\n\n")
        for i, para in enumerate(paras):
            if re.search(rf"(?<![\d.]){re.escape(c['id'])}(?!\d)", para) and ev in para:
                new = re.sub(rf"\s*\(source: {re.escape(ev)}\)", "", para)
                new = re.sub(rf";\s*{re.escape(ev)}", "", new)
                new = re.sub(rf"\(source: {re.escape(ev)};\s*", "(source: ", new)
                if new == para:
                    continue
                paras[i] = new
                old_ev, c["evidence"] = ev, None
                return "\n\n".join(paras), json.dumps(d, indent=2) + "\n", {"original": f"citation of {old_ev} for criterion {c['id']}", "mutated": "citation removed from the passage; evidence null in decision.json", "occurrences": 2, "section": c["id"]}
    raise Skip("could not isolate a passage citing a criterion's evidence file")


def m12(text, dec, t, f, rng):
    d = json.loads(dec)
    old = d["decision"]
    new = {"APPEAL": "DO_NOT_APPEAL", "DO_NOT_APPEAL": "APPEAL", "CORRECT_AND_RESUBMIT": "APPEAL", "ESCALATE_MISSING_DOCS": "APPEAL"}[old]
    d["decision"] = new
    return text, json.dumps(d, indent=2) + "\n", {"original": old, "mutated": new, "occurrences": 1}


MUTATORS = {"M1": m1, "M2": m2, "M3": m3, "M4": m4, "M5": m5, "M6": m6, "M7": m7, "M8": m8, "M9": m9, "M10": m10, "M11": m11, "M12": m12}


# ---------------------------------------------------------------- controls
def c2(text, dec, t, f, rng):
    out, changes = text, []
    for pat, repl in REWORD:
        out, n = re.subn(pat, repl, out)
        if n:
            changes.append(f"{pat.strip(chr(92)+'b')}->{repl}x{n}")
    if len(changes) < 3:
        raise Skip("fewer than 3 safe rewording substitutions apply")
    return out, dec, {"original": "(wording)", "mutated": "; ".join(changes), "occurrences": len(changes)}


def c3(text, dec, t, f, rng):
    out = re.sub(r"^## (.+)$", lambda m: f"**{m.group(1).upper()}**", text, flags=re.M)
    out = re.sub(r"^### (.+)$", lambda m: f"__{m.group(1)}__", out, flags=re.M)
    out = out.replace("\n\n", "\n\n\n").replace("\n- ", "\n  - ")
    out = "\n".join(ln.rstrip() + ("  " if ln.strip() and i % 5 == 0 else "") for i, ln in enumerate(out.split("\n")))
    if out == text:
        raise Skip("nothing to restyle")
    return out, dec, {"original": "(layout)", "mutated": "headings restyled, blank lines and indentation changed", "occurrences": 1}


def c4(text, dec, t, f, rng):
    words = [w for w in ("the", "and", "with", "that") if re.search(rf"\b{w}\b", text)]
    if not words:
        raise Skip("no common word to misspell")
    w = words[0]
    typo = {"the": "teh", "and": "adn", "with": "wiht", "that": "taht"}[w]
    out = re.sub(rf"\b{w}\b", typo, text, count=1)
    gi = [i for i, ln in enumerate(out.split("\n")) if re.match(r"#+\s*Gaps", ln.strip(), re.I)]
    lines = out.split("\n")
    line = "Thank you for your prompt attention to this matter."
    if gi:
        lines.insert(gi[0], line + "\n")
    else:
        lines.append(line)
    return "\n".join(lines), dec, {"original": w, "mutated": f"{typo} (one occurrence) + courtesy line", "occurrences": 2}


CONTROL_FNS = {"C2": c2, "C3": c3, "C4": c4}


# ---------------------------------------------------------------- driver
def generate(root, cases, seed=SEED, types=None):
    """-> (items, skipped). item = {item_id, case_id, type, deliverable, decision, record}."""
    root = Path(root)
    _, truths = load_truths(root)
    by = {t.case_id: t for t in truths}
    items, skipped = [], []
    for cid in cases:
        t, f = by[cid], facts(by[cid])
        g = root / "cases" / cid / "gold"
        text, dec = (g / "deliverable.md").read_text(), (g / "decision.json").read_text()
        for ty in (types or TYPES + CONTROLS):
            rng = random.Random(f"{seed}:{cid}:{ty}")
            fn = MUTATORS.get(ty) or CONTROL_FNS[ty]
            try:
                out, dec_out, rec = fn(text, dec, t, f, rng)
            except Skip as e:
                skipped.append({"case_id": cid, "type": ty, "reason": str(e)})
                continue
            if out == text and dec_out == dec:
                skipped.append({"case_id": cid, "type": ty, "reason": "mutation produced no change"})
                continue
            kind, expected = EXPECT[ty]
            rec = {**rec, "type": ty, "case_id": cid, "item_id": f"{cid}__{ty}", "kind": kind, "expected": expected, "seed": seed,
                   "context": context_of(out, rec["mutated"][:60]) if ty not in ("M10", "M11", "M12") else ""}
            items.append({"item_id": rec["item_id"], "case_id": cid, "type": ty, "deliverable": out, "decision": dec_out, "record": rec})
    return items, skipped


def write_items(items, skipped, out_dir):
    out_dir = Path(out_dir)
    for it in items:
        d = out_dir / it["item_id"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "deliverable.md").write_text(it["deliverable"])
        (d / "decision.json").write_text(it["decision"])
        (d / "record.json").write_text(json.dumps(it["record"], indent=1, sort_keys=True) + "\n")
    (out_dir / "skipped.json").write_text(json.dumps(skipped, indent=1) + "\n")
    (out_dir / "items.json").write_text(json.dumps([{"item_id": i["item_id"], "case_id": i["case_id"], "type": i["type"]} for i in items], indent=1) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--cases", nargs="*")
    a = ap.parse_args(argv)
    root = Path(a.data)
    man = json.loads((root / "manifest.json").read_text())
    items, skipped = generate(root, a.cases or man["pilot_cases"], a.seed)
    out = ROOT / "runs" / a.run_id / "mutations"
    write_items(items, skipped, out)
    from collections import Counter
    print(f"{len(items)} items written to {out}; skipped {len(skipped)}; by type {dict(sorted(Counter(i['type'] for i in items).items()))}")
    for s in skipped:
        print("  skip", s["case_id"], s["type"], "-", s["reason"])


if __name__ == "__main__":
    main()
