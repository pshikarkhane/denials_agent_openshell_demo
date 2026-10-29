"""Part 2 + 3 programmatic checks (no LLM). Independent re-computation from truth.json + reference.py; read-only.
Writes docs/auto_review_raw/programmatic.json and prints a summary."""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW, ROOT, manifest_pilots  # noqa: E402
from data_gen import reference as R  # noqa: E402
from data_gen.gen_cases import load_truths  # noqa: E402
from data_gen.schema import Truth  # noqa: E402

ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
d = date.fromisoformat
flags = []  # (severity, where, message)


def flag(sev, where, msg):
    flags.append({"severity": sev, "where": where, "message": msg})


def facts(t):
    out = {}
    for f in t.facts:
        out.setdefault(f.key, f.value)
    return out


def check_arithmetic(t):
    f, w, pay = facts(t), t.case_id, R.PAYERS[t.payer_id]
    sub, den, dos, asof = d(f["claim_submitted_date"]), t.denial.denial_date, t.claim.dos, d(f["as_of_date"])
    if not dos <= sub <= den < t.appeal_deadline:
        flag("major", w, f"date order broken: DOS {dos}, submitted {sub}, notice {den}, deadline {t.appeal_deadline}")
    if t.appeal_deadline != den + timedelta(days=pay["appeal_days"]):
        flag("major", w, "appeal deadline != notice + appeal window")
    if d(f["corrected_claim_deadline"]) != den + timedelta(days=pay["corrected_claim_days"]):
        flag("major", w, "corrected-claim deadline != notice + window")
    if "timely_filing_deadline" in f and d(f["timely_filing_deadline"]) != dos + timedelta(days=pay["timely_filing_days"]):
        flag("major", w, "filing deadline != DOS + filing window")
    if not asof > den:
        flag("major", w, "as-of date is not after the notice date")


def check_docs(t):
    w, base = t.case_id, ROOT / "data" / "cases" / t.case_id
    f = facts(t)
    den = (base / "docs" / "denial_letter.txt").read_text()
    eob = (base / "docs" / "eob_835.txt").read_text()
    task = (base / "task.md").read_text()
    pairs = [("denial notice date", re.search(r"Date of notice: (\S+)", den), t.denial.denial_date.isoformat()),
             ("denial appeal deadline", re.search(r"must be received by (\S+?)\.", den), t.appeal_deadline.isoformat()),
             ("denial corrected deadline", re.search(r"that is, by (\S+?)\.", den), f["corrected_claim_deadline"]),
             ("denial claim no", re.search(r"Claim number: (\S+)", den), t.claim.claim_no),
             ("denial DOS", re.search(r"Date of service: (\S+)", den), t.claim.dos.isoformat()),
             ("denial billed", re.search(r"Billed amount: (\S+)", den), f"{t.claim.billed:.2f}"),
             ("eob claim no", re.search(r"Claim number: (\S+)", eob), t.claim.claim_no),
             ("eob DOS", re.search(r"Date of service: (\S+)", eob), t.claim.dos.isoformat()),
             ("eob patient id", re.search(r"Patient ID: (\S+)", eob), t.patient.synthetic_id),
             ("task as-of", re.search(r"review is (\S+?)\.", task), f["as_of_date"]),
             ("task claim", re.search(r"(\d{7})", task), t.claim.claim_no)]
    for label, m, want in pairs:
        if not m or m.group(1) != want:
            flag("major", w, f"{label}: document says {m.group(1) if m else None}, truth says {want}")
    if t.policy_id and R.POLICY_TITLES[t.policy_id] not in den and t.category != 7 and t.category != 10:
        flag("minor", w, "denial letter does not cite the policy title")
    # identity consistency across eob + notes
    name = re.search(r"Name: (.+)", eob).group(1).strip()
    dob, mrn = re.search(r"Date of birth: (\S+)", eob).group(1), re.search(r"MRN: (\S+)", eob).group(1)
    for p in sorted((base / "docs").rglob("*.txt")):
        txt = p.read_text()
        m = re.search(r"Patient: (.+?)\s+(?:DOB: (\S+)\s+)?MRN: (\S+)", txt)
        if m and (m.group(1).strip() != name or m.group(3) != mrn or (m.group(2) and m.group(2) != dob)):
            flag("major", w, f"{p.name}: patient identity differs from EOB ({m.groups()} vs {name}, {dob}, {mrn})")
        enc = re.search(r"Date of encounter: (\S+)", txt)
        fd = ISO.search(p.name)
        if enc and fd and enc.group(1) != fd.group(0):
            flag("major", w, f"{p.name}: encounter date {enc.group(1)} != filename date")
        if enc:
            age = re.search(r"(\d+)-year-old", txt)
            if age:
                b, e = d(dob), d(enc.group(1))
                true_age = e.year - b.year - ((e.month, e.day) < (b.month, b.day))
                if int(age.group(1)) != true_age:
                    flag("minor", w, f"{p.name}: says {age.group(1)}-year-old but DOB {dob} gives {true_age} on {enc.group(1)}")
            body = txt.split("-" * 60)[1] if "-" * 60 in txt else txt
            for ds in set(ISO.findall(body)):
                if d(ds) > d(enc.group(1)) and d(ds) != t.claim.dos:
                    flag("minor", w, f"{p.name}: body mentions future date {ds} (encounter {enc.group(1)})")
                elif d(ds) > d(enc.group(1)):
                    flag("minor", w, f"{p.name}: body mentions the date of service {ds} as a future date (encounter {enc.group(1)})")
        for ds in set(ISO.findall(txt)):
            if p.name != "denial_letter.txt" and d(ds) > d(f["as_of_date"]):  # the letter legitimately states future deadlines
                flag("major", w, f"{p.name}: mentions {ds}, after the as-of date")
    # evidence quotes verbatim + line numbers
    for fa in t.facts:
        if fa.evidence:
            p = base / "docs" / fa.source_file
            if not p.exists():
                flag("major", w, f"evidence file {fa.source_file} is missing")
                continue
            lines = p.read_text().splitlines()
            norm = " ".join(fa.evidence.split())
            hit = [i + 1 for i in range(len(lines)) if norm in " ".join(lines[i].split())]
            if not hit:
                flag("major", w, f"evidence for {fa.key} not verbatim in {fa.source_file}: {fa.evidence!r}")
            elif fa.line not in hit:
                flag("minor", w, f"evidence line number for {fa.key} is {fa.line}, found on {hit}")
    # criteria evidence: unmet/unknown criteria must not have a quiet quote-supporting fact in a different file
    # solvability by title: policies whose title equals the letter's title
    m = re.search(r"\(Medical Policy: (.+?)\)\.", den)
    if m:
        title = m.group(1)
        cands = [pid for pid, tt in {**R.POLICY_TITLES, **{k: v["title"] for k, v in R.DISTRACTOR_DOCS.items()}}.items() if tt == title]
        pay = {**R.POLICIES, **{k: v["payer"] for k, v in R.DISTRACTOR_DOCS.items()}}
        by_payer = [c for c in cands if pay[c] == t.payer_id]
        flag("info", w, f"title {title!r} matches {cands}; after payer filter: {by_payer}"
             + ("  <-- TIE" if len(by_payer) > 1 else ""))


def check_case_specific(t):
    f, w = facts(t), t.case_id
    base = ROOT / "data" / "cases" / w / "docs"
    if t.category in (1, 2) and "therapy_duration_days" in f:
        log = (base / "supporting" / "pt_log.txt").read_text()
        m = re.search(r"Treatment period: (\S+) to (\S+) \((\d+) days\)", log)
        if m and (d(m.group(2)) - d(m.group(1))).days != int(m.group(3)):
            flag("major", w, "PT log day count != its own dates")
        visits = re.findall(r"Visit (\d+) \| (\S+)", log)
        if m and visits and d(visits[-1][1]) > d(m.group(2)):
            flag("minor", w, "PT log has a visit after the end of the stated treatment period")
    if t.category == 12:
        log = (base / "supporting" / "pt_log.txt").read_text()
        visits = re.findall(r"Visit (\d+) \| (\S+)", log)
        if [int(v[0]) for v in visits] != list(range(1, len(visits) + 1)):
            flag("major", w, "PT log visit numbers are not sequential")
        if visits[-1][1] != t.claim.dos.isoformat() or int(visits[-1][0]) != f["denied_visit_number"]:
            flag("major", w, "last PT visit is not the denied visit on the DOS")
        ds = [d(v[1]) for v in visits]
        if ds != sorted(set(ds)):
            flag("major", w, "PT visit dates not strictly increasing")
        gaps = [(b - a).days for a, b in zip(ds, ds[1:])]
        flag("info", w, f"PT visits {len(visits)} over {(ds[-1]-ds[0]).days} days; gap min/max {min(gaps)}/{max(gaps)} days")
    if t.category == 6:
        for p in (base / "notes").glob("*.txt"):
            if re.search(r"claim|billing|submitted|clearinghouse", p.read_text(), re.I):
                flag("major", w, f"{p.name} mentions claim/billing despite 'no proof of filing' design")


def check_policies():
    lib = ROOT / "data" / "policy_library"
    for p in sorted(lib.glob("*.txt")):
        txt = p.read_text()
        secs = re.findall(r"^Section (\S+)", txt, re.M)
        def key(s):
            return [int(x) if x.isdigit() else x for x in re.findall(r"\d+|[a-z]", s)]
        if secs != sorted(secs, key=key):
            flag("minor", p.name, f"sections out of numeric order: {secs}")
        pid = p.stem
        payer = R.POLICIES.get(pid) or R.DISTRACTOR_DOCS[pid]["payer"]
        for label, key_ in (("7.1", "appeal_days"), ("7.2", "timely_filing_days"), ("7.3", "corrected_claim_days")):
            m = re.search(rf"^{re.escape(label)} .*?(\d+) days", txt, re.M)
            want = R.PAYERS[payer][key_]
            if pid == "MP-TF-010" and key_ == "timely_filing_days":
                want = 60  # the superseded version states its own (older) limit, consistent with its section 2.1
            if not m or int(m.group(1)) != want:
                flag("major", p.name, f"{label} window {m.group(1) if m else None} != expected {want}")
        body = txt.split("Section 7")[0]
        mentions_corrected = len(re.findall(r"corrected claim", body, re.I))
        mentions_appeal = len(re.findall(r"\bappeal", body, re.I))
        flag("info", p.name, f"sections 1-6 mention 'corrected claim' {mentions_corrected}x, 'appeal' {mentions_appeal}x")
    # CORRECT_AND_RESUBMIT gap (programmatic version): does the policy say a missing-data denial is cured by a corrected claim, not appeal?
    for pid in ("MP-CLM-004", "MP-BND-002"):
        txt = (lib / f"{pid}.txt").read_text()
        body = txt.split("Section 7")[0]
        cured = re.search(r"appeal[^.]*(?:does not|will not|cannot|not cure|not a substitute)|(?:instead of|rather than)[^.]*appeal", body, re.I)
        flag("major" if not cured else "info", pid, "no sentence says an appeal does not cure missing/invalid claim data; corrected claim vs appeal is not distinguished"
             if not cured else "policy distinguishes appeal from corrected claim")
        flag("info" if "corrected claim" in body.lower() else "major", pid,
             "section text mentions corrected claims" if "corrected claim" in body.lower() else "no section mentions corrected claims (only the 7.3 parameter)")


def check_schema_and_traps(truths):
    fields = list(Truth.model_fields)
    flag("info", "schema", f"Truth top-level fields: {fields}; action_deadline present: {'action_deadline' in fields}")
    car = [t for t in truths if t.correct_decision.value == "CORRECT_AND_RESUBMIT"]
    bad = 0
    for t in truths:
        f = facts(t)
        left = (t.action_deadline - d(f["as_of_date"])).days
        tr = [x.value for x in t.traps]
        if "deadline_within_7_days" in tr and not 1 <= left <= 7:
            flag("major", t.case_id, f"deadline_within_7_days but {left} days remain to the ACTION deadline")
            bad += 1
        if "deadline_passed" in tr and left >= 0:
            flag("major", t.case_id, "deadline_passed but the action deadline has not passed")
            bad += 1
    flag("info", "traps", f"deadline traps measured on action_deadline in all {len(truths)} cases: {'yes' if not bad else 'NO'}")
    lure = [t.case_id for t in car if d(facts(t)["as_of_date"]) > t.appeal_deadline]
    flag("info", "traps", f"{len(lure)} of {len(car)} CORRECT_AND_RESUBMIT cases have an appeal deadline that is already past at the as-of date (intentional lure): {lure}")
    flag("info", "traps", f"cases with more than one hard trap: {[t.case_id for t in truths if len([x for x in t.traps if x.value in ('deadline_within_7_days','deadline_passed','note_after_dos','notes_disagree_therapy_duration','criterion_no_supporting_doc')]) > 1]}")


def check_c0005(by):
    t = by["C-0005"]
    f = facts(t)
    flag("info", "C-0005", f"notice {t.denial.denial_date}, as-of {f['as_of_date']} ({(d(f['as_of_date']) - t.denial.denial_date).days} days after notice), appeal deadline {t.appeal_deadline} "
         f"({(t.appeal_deadline - d(f['as_of_date'])).days} days after as-of); DOS {t.claim.dos}; evidence docs dated {[x.value for x in t.facts if x.key == 'planned_document']}")
    flag("info", "C-0005", "as-of date is more than 5 months after the denial notice while all documents are dated 2026-04..2026-07: the agent is told it is 2027-01-03")


def main():
    _, truths = load_truths(ROOT / "data")
    by = {t.case_id: t for t in truths}
    for t in truths:
        check_arithmetic(t)
    for cid in manifest_pilots():
        check_docs(by[cid])
        check_case_specific(by[cid])
    check_policies()
    check_schema_and_traps(truths)
    check_c0005(by)
    (RAW / "programmatic.json").write_text(json.dumps(flags, indent=1) + "\n")
    from collections import Counter
    print(Counter(f["severity"] for f in flags))
    for f in flags:
        if f["severity"] != "info":
            print(f"[{f['severity']}] {f['where']}: {f['message']}")


if __name__ == "__main__":
    main()
