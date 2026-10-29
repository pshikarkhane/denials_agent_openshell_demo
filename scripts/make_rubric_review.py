#!/usr/bin/env python3
"""Generate docs/RUBRIC_REVIEW.md (HOST-ONLY: shows rubrics and gold deliverables). Usage: python scripts/make_rubric_review.py"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = {
    "C-0005": [
        "Evidence criteria (EVD*, HON1) name the exact sentences in the notes. Do they leave room for another valid way to cite the same facts, or are they too tied to one phrasing?",
        "HON1 (imaging history): the gold also cites claim_history lines ('none recorded') in support. Those lines are about claim submissions, not imaging. Is that acceptable support, or should the rubric/gold rely only on the ortho note's 'Imaging history' sentence?",
        "TRP1 requires resolving the conflicting therapy-duration note by relying on the PT log. Is 'rely on the PT log' the resolution you want, or should flagging the conflict be enough?",
    ],
    "C-0030": [
        "REM1 expects 'does not appeal ... closes the claim'. For a CO-29 denial is closing/write-off the right business next step, or should the memo say something else (e.g. check whether a clearinghouse record exists elsewhere)?",
        "TRP1 (less than 8 days to the deadline) is vague for a DO_NOT_APPEAL case: 'says what must happen before it'. Does it test anything useful here?",
        "DLN2 checks the filing arithmetic (DOS + 90 days vs payer received date). Should it also require pointing out that claim_history records the 277CA acceptance on 2026-07-14, which is also late?",
    ],
}


def main():
    out = ["# Rubric review (host-only)", "",
           "Two of the five pilot rubrics in full, with the gold deliverable, so you can judge whether the criteria are fair and checkable. "
           "`auto` = graded in code (exact match); `judge` = graded by the three-judge panel against the reference. Full results and costs are in `docs/STATUS.md`.", ""]
    for cid in ("C-0005", "C-0030"):
        base = ROOT / "data" / "cases" / cid
        r = json.loads((base / "rubric.json").read_text())
        out += [f"## {cid}: {r['decision']}", "", "| id | family | check | criterion | reference |", "|---|---|---|---|---|"]
        for c in r["criteria"]:
            out.append(f"| {c['id']} | {c['family']} | {c['check']} | {c['text']} | {c['reference'].replace('|', '/')} |")
        out += ["", f"Skipped/trimmed: {r['skipped'] or 'none'}", "", "**Three things to check:**", ""]
        out += [f"{i}. {t}" for i, t in enumerate(CHECKS[cid], 1)]
        out += ["", f"### Gold deliverable.md ({cid})", "", "```markdown", (base / "gold" / "deliverable.md").read_text().rstrip(), "```", "",
                f"### Gold decision.json ({cid})", "", "```json", (base / "gold" / "decision.json").read_text().rstrip(), "```", ""]
    (ROOT / "docs" / "RUBRIC_REVIEW.md").write_text("\n".join(out) + "\n")
    print("wrote docs/RUBRIC_REVIEW.md")


main()
