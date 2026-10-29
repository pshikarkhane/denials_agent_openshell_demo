#!/usr/bin/env python3
"""Generate docs/PILOT_REVIEW.md from data/ (host-only: it states the correct decisions). Usage: python scripts/make_pilot_review.py"""
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_gen import reference as R  # noqa: E402
from data_gen.gen_cases import load_truths  # noqa: E402


def facts(t):
    d = {}
    for f in t.facts:
        d.setdefault(f.key, f.value)
    return d


def checks(t, f, files):
    cat, out = t.category, []
    quote = lambda key: next((x for x in t.facts if x.key == key and x.evidence), None)  # noqa: E731
    if cat in (1, 2):
        d = f.get("therapy_duration_days")
        out.append(f"Conservative therapy: does the PCP note cite a start date of {f['therapy_start_date']} and does `supporting/pt_log.txt` show a "
                   f"treatment period of {d} days (policy §3.2(a) needs 42+)? Expected status for C1: **{t.policy_criteria[0].status}**."
                   if d else f"Conservative therapy: PT attendance records are absent. Is it clear that C1 can't be established? Expected C1: **{t.policy_criteria[0].status}**.")
        c2 = t.policy_criteria[1].status
        out.append(f"Neuro finding (C2 = **{c2}**): does the ortho note's `Neurological exam:` line {'record a real deficit' if c2 == 'met' else 'record no deficit'}, "
                   "and do the PCP/follow-up notes avoid contradicting it?")
    if cat == 12:
        out.append(f"Visit limit: `supporting/pt_log.txt` shows visit {f['denied_visit_number']} on the date of service. Is that over the limit of {f['visit_limit']} "
                   f"and not above the cap of {f['visit_cap']}?")
        out.append("Exception criteria: does the progress note show measurable functional improvement and does the referral note recertify the plan of care? "
                   "Is the note content plausible for PT?")
    if cat == 6:
        out.append(f"Filing math: DOS {t.claim.dos}, limit {f['timely_filing_limit_days']} days, so the deadline is {f['timely_filing_deadline']}; the payer received the claim "
                   f"{f['payer_received_date']}. Is the denial letter consistent?")
        out.append("No proof of timely submission: do the notes avoid any mention of claim submission, billing or a clearinghouse?")
    if cat == 8:
        out.append(f"Missing item: the denial says \"{f['missing_item']}\". Does the EOB show that item blank/absent (field `{f['missing_field']}`)?")
        out.append("Visit note: does it document the same service as the claim without adding facts that would change the fix?")
    tr = {x.value for x in t.traps}
    if "notes_disagree_therapy_duration" in tr:
        out.append(f"Conflict trap: the `pcp_followup` note says about {f['conflicting_therapy_duration_days']} days of PT, the PT log says otherwise. "
                   "Is the disagreement visible and realistic rather than absurd?")
    if "note_after_dos" in tr:
        out.append(f"Post-DOS note ({f['post_dos_note']}): does it avoid supplying evidence that would only exist after the service?")
    if "criterion_no_supporting_doc" in tr:
        out.append("No prior-imaging document exists. Do none of the notes or letters assert or imply a prior study?")
    if "deadline_within_7_days" in tr:
        out.append(f"Deadline trap: task.md says today is {f['as_of_date']}; the appeal deadline is {t.appeal_deadline}. Is the remaining time clear and is the "
                   "correct decision still sensible?")
    if "deadline_passed" in tr:
        out.append(f"Deadline trap: as-of {f['as_of_date']} is after the deadline {t.appeal_deadline}. Is this clear from task.md and the denial letter?")
    if "policy_effective_after_dos" in tr:
        out.append(f"Policy-date trap: DOS {t.claim.dos} is before the policy's effective date {f['policy_effective_date']}. The policy states its requirements carry forward. "
                   "Is that wording acceptable, or should the case be redesigned?")
    if "distractor_policy_similar_name" in tr:
        out.append(f"Distractor: `{f['distractor_policy_id']}` has the same/similar title. Does it differ enough to be a real trap and not confusable on the facts alone?")
    out.append("Anything in the agent-visible files that hints at the answer, or reads unrealistically for a payer/provider document?")
    return out[:3] if len(out) >= 3 else out


def main():
    man, truths = load_truths(ROOT / "data")
    by = {t.case_id: t for t in truths}
    L = ["# Pilot review pack", "",
         "Host-only: this page states the correct decisions. Do not mount it. Review the 5 pilot cases and the coding tables below, then tell me what to change before I generate clinical documents for the other 55 cases.", "",
         "How to read a case: open `data/cases/<id>/task.md` first (that is all the agent is told), then the files listed. `truth.json` is the answer key.", ""]
    for cid in man["pilot_cases"]:
        t, f = by[cid], facts(by[cid])
        base = f"data/cases/{cid}"
        files = [f"{base}/task.md", f"{base}/docs/eob_835.txt", f"{base}/docs/denial_letter.txt"] + sorted(f"{base}/docs/{x.value}" for x in t.facts if x.key == "planned_document")
        L += [f"## {cid}: category {t.category}, {R.CATEGORIES[t.category]['name']}", "",
              f"- **Correct decision:** {t.correct_decision.value}   |   **Split:** {t.split}   |   **Traps:** {', '.join(x.value for x in t.traps) or 'none'}",
              f"- **Denial:** {t.denial.carc}{' / ' + t.denial.rarc if t.denial.rarc else ''}   |   **Policy:** {t.policy_id} ({t.payer_id}, effective {f['policy_effective_date']})   |   **Appeal deadline:** {t.appeal_deadline}   |   **As-of:** {f['as_of_date']}",
              "- **Criteria:** " + "; ".join(f"{c.id} {c.section} = {c.status}" for c in t.policy_criteria),
              f"- **Policy file:** `data/policy_library/{t.policy_id}.txt`", "- **Files to read:**"]
        L += [f"  - `{x}`" for x in files]
        L += ["", "**Check these:**"] + [f"{i}. {c}" for i, c in enumerate(checks(t, f, files), 1)] + [""]
    # coding tables over ALL 60 cases (what has been generated so far)
    pairs, cr, bundles, wrong = defaultdict(set), defaultdict(set), defaultdict(set), defaultdict(set)
    for t in truths:
        f = facts(t)
        for i in t.claim.icd10:
            (wrong if t.category == 11 else pairs)[(t.claim.cpt, i)].add(t.category)
        if t.category == 11:
            for i in f["corrected_icd10"]:
                pairs[(t.claim.cpt, i)].add(11)
        cr[(t.denial.carc, t.denial.rarc or "none")].add(t.category)
        if "column1_code" in f:
            bundles[(f["column1_code"], t.claim.cpt)].add(t.case_id)
    mark = "[ ] correct  [ ] incorrect  Notes: "
    L += ["## Coding review (all 60 cases; mark each line)", "",
          "Descriptions are my own paraphrases, not AMA/CMS text. **Nothing here has been checked by a coding professional.**", "",
          "### A. CPT + ICD-10 pairings that are supposed to be valid", ""]
    for (cpt, icd), cats in sorted(pairs.items()):
        L.append(f"- {cpt} ({R.CPT[cpt]}) + {icd} ({R.ICD10[icd]})  | categories {sorted(cats)}  | {mark}")
    L += ["", "### B. Pairings that are deliberately INVALID (category 11: the diagnosis is inconsistent with the procedure)", ""]
    for (cpt, icd), cats in sorted(wrong.items()):
        L.append(f"- {cpt} ({R.CPT[cpt]}) + {icd} ({R.ICD10[icd]})  | {mark}")
    L += ["", "### C. CARC / RARC pairings by scenario", ""]
    for (carc, rarc), cats in sorted(cr.items()):
        L.append(f"- {carc} ({R.CARC_TEXT[carc]}) with RARC {rarc}  | scenario(s): {'; '.join(R.CATEGORIES[c]['name'] for c in sorted(cats))}  | {mark}")
    L += ["", "### D. Bundling pairs (column 1 code / denied column 2 code, distinct-service modifier 59)", ""]
    for (c1, c2), ids in sorted(bundles.items()):
        L.append(f"- {c1} ({R.CPT[c1]}) bundled with denied {c2} ({R.CPT[c2]})  | {len(ids)} case(s)  | {mark}")
    L += ["", "### E. Category / CARC scenario pairings from the spec", ""]
    for k, v in R.CATEGORIES.items():
        L.append(f"- {k}. {v['name']}: {v['carc']}  | {mark}")
    Path(ROOT / "docs" / "PILOT_REVIEW.md").write_text("\n".join(L) + "\n")
    print("wrote docs/PILOT_REVIEW.md")


main()
