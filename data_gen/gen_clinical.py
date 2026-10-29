"""PILOT clinical documents: LLM-written notes + templated supporting docs for a few cases only.

Each note must contain deterministic `required` sentences verbatim (they become the evidence quotes stored in
truth.facts with line numbers). The LLM output is rejected and retried if it omits a required sentence, uses a date, code
or treatment duration it was not given, or mentions claims/billing. Frozen: existing files are kept unless --force.
Usage: python -m data_gen.gen_clinical [--data data] [--force]
"""
import argparse
import json
import random
import re
from datetime import date, timedelta
from pathlib import Path

from data_gen import reference as R
from data_gen.docs_util import SYNTHETIC_FOOTER, case_dir, fill_lines, set_fact
from data_gen.gen_cases import DEFAULT_SEED, build_manifest, load_truths, write_truth
from data_gen.llm import datagen_record, generate, load_models, reviewer_model
from data_gen.note_lint import note_body, reviewer_issues, spell_issues
from data_gen.profiles import profile

PILOT_CATEGORIES = (1, 2, 6, 8, 12)
MAX_TRIES = 3
NOTE_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
FORBIDDEN = re.compile(r"\b(claims?|denial|denied|appeals?|billing|billed|payer|insurance|authorization|reimburse\w*)\b", re.I)
DURATION = re.compile(r"\b\d+\s*(?:-\s*)?(?:weeks?|days?|months?|wks?)\b", re.I)
MONTHS = re.compile(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? \d{1,2}\b", re.I)
SYSTEM = "You write realistic but entirely FICTIONAL outpatient clinical notes for a software demo. Plain text only."
DEFICITS = ["{side} L5 distribution weakness (extensor hallucis longus 4/5) with decreased sensation over the dorsal foot",
            "{side} S1 radiculopathy with diminished ankle reflex and decreased plantar sensation",
            "{side} leg paresthesias with a positive straight leg raise at 40 degrees"]


def side_of(t):
    """Symptom side for the case, fixed so every note agrees."""
    return "left" if int(t.case_id[-2:]) % 2 else "right"
KIND_TITLE = {"pcp": "PRIMARY CARE VISIT NOTE", "ortho": "ORTHOPEDIC CONSULTATION NOTE", "visit": "OFFICE VISIT NOTE",
              "followup": "FOLLOW-UP VISIT NOTE", "pcp_followup": "PRIMARY CARE FOLLOW-UP NOTE",
              "initial_eval": "PHYSICAL THERAPY INITIAL EVALUATION", "referral": "PHYSICIAN PLAN-OF-CARE RECERTIFICATION",
              "pt_progress_note": "PHYSICAL THERAPY PROGRESS NOTE"}


NUM_GRADE = r"\b\d\s*[+-]?\s*/\s*5\b"  # numeric strength grades invite cross-note inconsistencies
IMG_WORDS = r"MRI|imaging|x-?rays?|radiograph\w*|CT scan|scan"
EXAM_WORDS = r"sensation|sensory|reflexes?|strength|neurolog\w*\s+(?:exam|examination|findings?)"
PRIOR_IMG = re.compile(rf"\b(?:prior|previous|previously|recent|recently|earlier|last|negative)\b[^.]{{0,40}}\b(?:{IMG_WORDS})\b|"
                       rf"\b(?:{IMG_WORDS})\b[^.]{{0,40}}\b(?:reviewed|previously|last year|on file|showed|reveal\w*)\b", re.I)


class Doc:
    """allow_dos: the date of service may be written in the body (post-service notes only). forbid: extra regexes."""
    def __init__(self, path, kind, when, author, required=(), context="", extra_dates=(), template=None, allow_dos=False, forbid=()):
        self.path, self.kind, self.when, self.author = path, kind, when, author
        self.required, self.context, self.extra_dates, self.template = list(required), context, list(extra_dates), template
        self.allow_dos, self.forbid = allow_dos, [re.compile(x, re.I) for x in forbid]


def _d(s):
    return date.fromisoformat(s)


def _file_date(path):
    m = NOTE_DATE.search(path)
    return _d(m.group(1)) if m else None


def _dx(t):
    return "; ".join(f"{c} ({R.ICD10[c]})" for c in t.claim.icd10)


def _weekdays(a, b):
    out, d = [], a
    while d <= b:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def pt_log_text(prof, t, start, end, n_visits=None, last_visit_on=None):
    """Templated PT attendance log on weekdays. With n_visits the last visit lands on last_visit_on (a weekday)."""
    if n_visits:
        days = _weekdays(start, last_visit_on)
        dates = [days[round(i * (len(days) - 1) / (n_visits - 1))] for i in range(n_visits)]
    else:
        dates, d = [], start
        while d <= end:
            while d.weekday() >= 5:
                d += timedelta(days=1)
            if d <= end:
                dates.append(d)
            d += timedelta(days=3 + len(dates) % 2)
    acts = ["therapeutic exercise", "neuromuscular re-education", "therapeutic activities", "manual therapy"]
    rows = [f"Visit {i} | {x.isoformat()} | {acts[i % 4]}" for i, x in enumerate(dates, 1)]
    return dates, rows


def plan_imaging(t, f, prof, rng):
    docs, quotes = [], []
    start, ortho_p = _d(f["therapy_start_date"]), next(p for p in f_docs(t) if p.endswith("_ortho.txt"))
    ortho = _file_date(ortho_p)
    c1 = next(c for c in t.policy_criteria if c.id == "C1").status
    deficit = next(c for c in t.policy_criteria if c.id == "C2").status == "met"
    pcp_p = next(p for p in f_docs(t) if p.endswith("_pcp.txt"))
    q_start = ("Started NSAIDs, a home exercise program and a physical therapy referral at this visit." if c1 != "unknown"
               else "Physical therapy referral placed at this visit; attendance records have not been received.")
    q_date = f"Date of encounter: {start}"  # header line of the PCP note: carries the therapy start date
    side = side_of(t)
    q_neuro = "Neurological exam: " + (rng.choice(DEFICITS).format(side=side) if deficit else "no focal motor or sensory deficit and no red-flag signs or symptoms.")
    last_img = f["last_lumbar_imaging_date"]
    q_img = ("Imaging history: No prior lumbar imaging on file." if last_img == "none"
             else f"Imaging history: Lumbar radiographs {last_img}; no other lumbar imaging since.")
    docs.append(Doc(pcp_p, "pcp", start, prof["provider"], [q_start],
                    f"Visit for low back pain with {side} leg symptoms (all symptoms are on the {side} side). Plan: begin conservative management; reassess later. The exam is limited "
                    "to tenderness and range of motion. Do not mention imaging or any follow-up date.",
                    [start], forbid=[rf"\b(?:{IMG_WORDS}|{EXAM_WORDS})\b"]))
    docs.append(Doc(ortho_p, "ortho", ortho, prof["specialist"], [q_neuro, q_img],
                    f"Specialist evaluation of persistent low back and {side} leg symptoms (all symptoms are on the {side} side; diagnosis: {_dx(t)}). Plan: lumbar spine MRI ordered. "
                    "Do not state how long conservative treatment has lasted. Apart from the required imaging-history sentence, do not mention "
                    "earlier or prior imaging, and give no follow-up date.", [start], forbid=[PRIOR_IMG.pattern]))
    quotes += [("therapy_start_date", pcp_p, q_date), ("criterion_C1_quote", pcp_p, q_start),
               ("ortho_exam_has_neuro_deficit", ortho_p, q_neuro), ("criterion_C2_quote", ortho_p, q_neuro),
               ("last_lumbar_imaging_date", ortho_p, q_img), ("criterion_C3_quote", ortho_p, q_img)]
    if "supporting/pt_log.txt" in f_docs(t):
        dates, rows = pt_log_text(prof, t, start, ortho)
        n_days = (ortho - start).days
        q_period = f"Treatment period: {start} to {ortho} ({n_days} days)"
        text = "\n".join([f"{prof['practice']} - PHYSICAL THERAPY ATTENDANCE LOG", f"Patient: {prof['name']}  MRN: {prof['mrn']}",
                          f"Start of care: {start}", f"Therapist: {prof['therapist']}", "", *rows, "", q_period,
                          f"Visits completed to date: {len(dates)}", "", SYNTHETIC_FOOTER]) + "\n"
        docs.append(Doc("supporting/pt_log.txt", "pt_log", start, prof["therapist"], template=text))
        quotes += [("therapy_duration_days", "supporting/pt_log.txt", q_period), ("criterion_C1_quote", "supporting/pt_log.txt", q_period)]
    if "supporting/prior_imaging.txt" in f_docs(t):
        q_study = f"Study date: {last_img}"
        text = "\n".join([f"{prof['practice']} - RADIOLOGY REPORT (LUMBAR SPINE RADIOGRAPHS)", f"Patient: {prof['name']}  MRN: {prof['mrn']}",
                          q_study, "Impression: mild degenerative changes; no acute osseous abnormality.", "", SYNTHETIC_FOOTER]) + "\n"
        docs.append(Doc("supporting/prior_imaging.txt", "prior_imaging", _d(last_img), "", template=text))
        quotes += [("criterion_C3_quote", "supporting/prior_imaging.txt", q_study)]
    return docs, quotes


def f_docs(t):
    return [x.value for x in t.facts if x.key == "planned_document"]


def plan_visits(t, f, prof, rng):
    """Categories 6 and 8: a pre-service PCP note and a visit note on the date of service (no billing-style sentences)."""
    dos = t.claim.dos
    pcp_p = next(p for p in f_docs(t) if p.endswith("_pcp.txt"))
    visit_p = next(p for p in f_docs(t) if p.endswith("_visit.txt"))
    side = "left" if t.claim.icd10[0][-1] == "2" else "right"
    by_cpt = {"99213": "Routine follow-up office visit.", "73721": f"MRI of the {side} knee was obtained at the imaging appointment.",
              "93000": "A 12-lead ECG was obtained and reviewed at this visit.", "97110": "Therapeutic exercise was provided in clinic.",
              "85025": "Blood was drawn for a complete blood count."}
    ctx = {"modifier_25": "A significant, separately identifiable evaluation and management service was provided in addition to a major joint injection performed the same day.",
           "laterality_modifier": f"Imaging was ordered and performed for the {side} knee.",
           "modifier_gp": "Therapy was delivered under a physical therapy plan of care.",
           "rendering_provider": f"The note is signed by the treating clinician, {prof['provider']}.",
           "referring_provider": f"The patient was referred for this service by {prof['provider']}.",
           "place_of_service": "This was an in-office visit."}.get(f.get("missing_field"), by_cpt.get(t.claim.cpt, "Routine office service."))
    docs = [Doc(pcp_p, "pcp", _file_date(pcp_p), prof["provider"], [],
                f"Evaluation of {_dx(t)}; plan for {R.CPT[t.claim.cpt].lower()} at a subsequent visit. Do not mention dates of other visits.", []),
            Doc(visit_p, "visit", dos, prof["provider"], [], f"Visit for {_dx(t)}. {ctx}", [], allow_dos=True)]
    return docs, [("dos_documented", visit_p, f"Date of encounter: {dos}")]


FN_SIDE = {"1": "right", "2": "left"}


def functional_sentence(t, rng):
    """Functional-improvement measure chosen by diagnosis / body region (no lumbar flexion for a knee)."""
    dx = t.claim.icd10[0]
    a, c_ = rng.randint(95, 110), rng.randint(4, 8)
    if dx in ("M25.561", "M25.562"):
        return (f"Functional improvement: {FN_SIDE[dx[-1]]} knee flexion improved from {a} to {a + rng.randint(15, 25)} degrees and "
                f"stair-climbing tolerance improved from {c_} to {c_ + rng.randint(4, 7)} steps.")
    if dx == "M25.511":
        return (f"Functional improvement: right shoulder abduction improved from {a + 20} to {a + 55} degrees and overhead reach "
                f"tolerance improved from {c_} to {c_ + rng.randint(4, 8)} minutes.")
    if dx == "M62.81":
        return (f"Functional improvement: five-times sit-to-stand time improved from {c_ + 16} to {c_ + 8} seconds and grip strength "
                f"improved from {c_ + 40} to {c_ + 52} pounds.")
    return (f"Functional improvement: lumbar flexion improved from {a - 65} to {a - 40} degrees and sit-to-stand time improved from "
            f"{c_ + 14} to {c_ + 6} seconds.")


def plan_pt(t, f, prof, rng):
    dos = t.claim.dos
    start = _d(f["therapy_start_date"])
    visit_no = f["denied_visit_number"]
    init_p = next(p for p in f_docs(t) if p.endswith("_initial_eval.txt"))
    ref_p = next(p for p in f_docs(t) if p.endswith("_referral.txt"))
    ref_d = _file_date(ref_p)
    q_init = "Initial evaluation completed today and plan of care established."
    q_ref = "I have reviewed the plan of care and recertify continued physical therapy."
    q_fn = functional_sentence(t, rng)
    dates, rows = pt_log_text(prof, t, start, dos, n_visits=visit_no, last_visit_on=dos)
    prog_d = dates[-4]  # the progress note is written at one of the logged visits
    q_visit = f"Visit {visit_no} | {dos}"
    q_total = f"Visits completed in calendar year {dos.year}: {visit_no} (no other outpatient therapy visits recorded)"
    q_dur = f"Treatment period: {start} to {dos}"
    log = "\n".join([f"{prof['practice']} - PHYSICAL THERAPY ATTENDANCE LOG", f"Patient: {prof['name']}  MRN: {prof['mrn']}",
                     f"Start of care: {start}", f"Therapist: {prof['therapist']}", "", *rows, "", q_dur, q_total, "", SYNTHETIC_FOOTER]) + "\n"
    docs = [Doc(init_p, "initial_eval", start, prof["therapist"], [q_init], f"PT initial evaluation for {_dx(t)}; goals: reduce pain and improve functional mobility.", [], forbid=[NUM_GRADE]),
            Doc(ref_p, "referral", ref_d, prof["specialist"], [q_ref], f"Physician review of the PT plan of care for {_dx(t)}; continued therapy is recommended.", [start], forbid=[NUM_GRADE]),
            Doc("supporting/pt_progress_note.txt", "pt_progress_note", prog_d, prof["therapist"], [q_fn],
                f"PT progress note for {_dx(t)}; therapy began {start}. Describe continued gains and the plan to continue.", [start], forbid=[NUM_GRADE]),
            Doc("supporting/pt_log.txt", "pt_log", start, prof["therapist"], template=log)]
    quotes = [("therapy_start_date", "supporting/pt_log.txt", f"Start of care: {start}"), ("therapy_duration_days", "supporting/pt_log.txt", q_dur),
              ("denied_visit_number", "supporting/pt_log.txt", q_visit), ("criterion_C1_quote", "supporting/pt_progress_note.txt", q_fn),
              ("criterion_C2_quote", ref_p, q_ref), ("criterion_C3_quote", "supporting/pt_log.txt", q_visit)]
    return docs, quotes


def plan_traps(t, f, prof, rng, docs, quotes):
    start = f.get("therapy_start_date")
    for p in f_docs(t):
        if p.endswith("_pcp_followup.txt"):
            q = f"Patient reports about {f['conflicting_therapy_duration_days']} days of physical therapy so far."
            docs.append(Doc(p, "pcp_followup", _file_date(p), prof["provider"], [q],
                            f"Follow-up visit for persistent symptoms{(' on the ' + side_of(t) + ' side') if t.category in (1, 2) else ''}; plan to continue therapy. The exam is limited to tenderness and range of "
                            "motion. Do not mention imaging or any future visit date.", [_d(start)] if start else [],
                            forbid=[rf"\b(?:{IMG_WORDS}|{EXAM_WORDS})\b"] if t.category in (1, 2) else []))
            quotes.append(("conflicting_therapy_duration_days", p, q))
        elif p.endswith("_followup.txt"):
            docs.append(Doc(p, "followup", _file_date(p), prof["provider"], [],
                            "Routine follow-up after the earlier service; symptoms are unchanged; discuss ongoing care. "
                            "Do not describe the pre-service treatment course. Do not mention imaging or exam findings other than tenderness.",
                            [], allow_dos=True, forbid=[rf"\b(?:{IMG_WORDS}|{EXAM_WORDS})\b"] if t.category in (1, 2, 12) else []))


def plan_case(t, prof, seed):
    rng = random.Random(f"{seed}:clin:{t.case_id}")
    f = {x.key: x.value for x in t.facts}
    if t.category in (1, 2):
        docs, q = plan_imaging(t, f, prof, rng)
    elif t.category in (6, 8):
        docs, q = plan_visits(t, f, prof, rng)
    elif t.category == 12:
        docs, q = plan_pt(t, f, prof, rng)
    else:
        raise SystemExit(f"category {t.category} is not part of the pilot")
    plan_traps(t, f, prof, rng, docs, q)
    planned = set(f_docs(t))
    missing = planned - {d.path for d in docs}
    if missing:
        raise SystemExit(f"{t.case_id}: planned documents with no clinical plan: {sorted(missing)}")
    return docs, q


def _age(prof, when):
    b = _d(prof["dob"])
    return when.year - b.year - ((when.month, when.day) < (b.month, b.day))


def prompt_for(doc, t, prof, allowed_dates, codes):
    req = "\n".join(f'- "{r}"' for r in doc.required) or "- (none)"
    return (f"Write the BODY of a {KIND_TITLE[doc.kind].lower()} for a {_age(prof, doc.when)}-year-old {'woman' if prof['sex'] == 'F' else 'man'}.\n"
            f"Author: {doc.author}. Encounter date: {doc.when}.\nClinical context: {doc.context}\n\n"
            f"The body MUST contain each of these sentences exactly as written (character for character):\n{req}\n\n"
            f"Rules: 130-220 words; short labelled sections (Reason for visit, History, Exam, Assessment, Plan); plain text, no markdown. "
            f"The only dates you may write are {sorted(map(str, allowed_dates))}, in YYYY-MM-DD form. Do not state any treatment durations "
            f"(no 'weeks', 'days' or 'months' counts) other than inside the required sentences. The only diagnosis/procedure codes you may "
            f"use are {sorted(codes)} (using none is fine). Do not mention claims, billing, insurance, authorization, or appeals, and do not write today's date or the phrase 'established patient' in the body. Do not "
            f"write a header, patient name or signature; they are added separately.")


def check_body(body, doc, allowed_dates, codes):
    norm = " ".join(body.split())
    problems = [f"missing required sentence: {r!r}" for r in doc.required if " ".join(r.split()) not in norm]
    scrub = norm
    for r in doc.required:
        scrub = scrub.replace(" ".join(r.split()), "")
    bad_dates = set(NOTE_DATE.findall(scrub)) - {str(d) for d in allowed_dates}
    if bad_dates:
        problems.append(f"dates not allowed: {sorted(bad_dates)}")
    if MONTHS.search(scrub):
        problems.append("dates must be YYYY-MM-DD")
    if DURATION.search(scrub):
        problems.append(f"treatment durations not allowed: {DURATION.search(scrub).group()!r}")
    bad_codes = (set(re.findall(r"\b\d{5}\b", scrub)) | set(re.findall(r"\b[A-Z]\d{2}(?:\.\d+)?\b", scrub))) - set(codes)
    if bad_codes:
        problems.append(f"codes not allowed: {sorted(bad_codes)}")
    if FORBIDDEN.search(scrub):
        problems.append(f"forbidden word: {FORBIDDEN.search(scrub).group()!r}")
    for rx in doc.forbid:
        if rx.search(scrub):
            problems.append(f"not allowed in this document: {rx.search(scrub).group()!r}")
    return problems


def wrap_note(doc, t, prof, body):
    return "\n".join([prof["practice"], KIND_TITLE[doc.kind], f"Patient: {prof['name']}   DOB: {prof['dob']}   MRN: {prof['mrn']}   "
                      f"Patient ID: {t.patient.synthetic_id}", f"Date of encounter: {doc.when}", f"Provider: {doc.author}", "-" * 60,
                      body.strip(), "-" * 60, f"Electronically signed: {doc.author}", "", SYNTHETIC_FOOTER]) + "\n"


def render_doc(cfg, doc, t, prof, force):
    """Returns (status, lint_record). LLM notes pass rule checks, the clinical spellcheck and a second-pass reviewer (non-datagen)."""
    path = case_dir(cfg["_root"], t.case_id) / "docs" / doc.path
    path.parent.mkdir(parents=True, exist_ok=True)
    if doc.template is not None:
        path.write_text(doc.template)
        return "template", None
    if path.exists() and not force:
        return "kept (frozen)", None
    allowed = {*doc.extra_dates} | {_d(x) for r in doc.required for x in NOTE_DATE.findall(r)}  # the encounter date is in the header, not the body
    if doc.allow_dos:
        allowed.add(t.claim.dos)
    codes = set(t.claim.icd10) | ({t.claim.cpt} if doc.allow_dos else set())
    feedback = ""
    for attempt in range(1, MAX_TRIES + 1):
        body = generate(cfg, prompt_for(doc, t, prof, allowed, codes) + feedback, SYSTEM)
        problems = check_body(body, doc, allowed, codes)
        spell = [] if problems else spell_issues(body)
        if spell:
            problems.append("possible misspellings: " + ", ".join(f"{x['word']} (did you mean {x['suggestion']}?)" for x in spell))
        issues = [] if problems else reviewer_issues(cfg, KIND_TITLE[doc.kind].lower(), body)
        if issues:
            problems.append("a reviewer flagged nonsense phrasing: " + "; ".join(f"'{x.get('quote')}': {x.get('problem')}" for x in issues))
        if not problems:
            path.write_text(wrap_note(doc, t, prof, body))
            return "written", {"spell": "pass", "reviewer_model": reviewer_model(cfg), "reviewer_issues": 0, "attempts": attempt}
        feedback = "\n\nYour previous answer was rejected: " + "; ".join(problems) + ". Rewrite the body fixing this."
    raise SystemExit(f"{t.case_id}/{doc.path}: invalid after {MAX_TRIES} tries: {problems}")


def pilot_ids(man):
    return [e["case_id"] for e in man["cases"] if e["split"] == "dev" and e["category"] in PILOT_CATEGORIES]


def run(cfg, root, seed, force=False):
    cfg["_root"] = root
    man, truths = load_truths(root)
    by = {t.case_id: t for t in truths}
    old_lint = man.get("note_lint", {})
    report, lint = {}, {}  # records are rebuilt from the current plan, so stale entries disappear
    for cid in pilot_ids(man):
        t = by[cid]
        prof = profile(seed, cid)
        docs, quotes = plan_case(t, prof, seed)
        base = case_dir(root, cid) / "docs"
        planned = {d.path for d in docs}
        for sub in ("notes", "supporting"):  # stale clinical files from an earlier plan are removed
            for p in (base / sub).glob("*.txt") if (base / sub).exists() else []:
                if f"{sub}/{p.name}" not in planned:
                    p.unlink()
        # keep the deterministic claim_history quotes; clinical quote facts are rebuilt below
        t.facts = [f for f in t.facts if not (f.key.startswith("criterion_") and f.source_file != "claim_history.txt")]
        res = {}
        for d in docs:
            status, rec = render_doc(cfg, d, t, prof, force)
            res[d.path] = status
            key = f"{cid}/{d.path}"
            if rec:
                lint[key] = rec
            elif status.startswith("kept") and key in old_lint:
                lint[key] = old_lint[key]
        for key, src, q in quotes:
            set_fact(t, key, src, q)
        n, missing = fill_lines(root, t)
        write_truth(root, t)
        report[cid] = {"files": res, "lines_filled": n, "unlocated_facts": missing}
    man["pilot_cases"] = pilot_ids(man)
    build_manifest(root, truths, man["seed"], {"pilot_cases": man["pilot_cases"], "note_lint": lint,
                                               "datagen": datagen_record(cfg, "data_gen/gen_clinical.py", man.get("datagen"))})
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    print(json.dumps(run(load_models(), a.data, a.seed, a.force), indent=1))
