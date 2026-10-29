#!/usr/bin/env python3
"""Merge the two reviewer verdicts with the author's own (Claude) flags for coding tables A-E and substitute the result for the
<<CODING_TABLE>> placeholder in docs/AUTO_REVIEW.md. Nobody here is an authoritative coding source: verdicts are only
'suspect' / 'no concern'."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW, ROOT  # noqa: E402

# Own (Claude) flags, from general knowledge and NOT authoritative. id -> (confidence, reason)
OWN = {
    "A17": ("medium", "CBC for plain hypertension has a weak medical-necessity story."),
    "A32": ("low", "E/M level (99214) is set by decision-making, not diagnosis; fit with stable diabetes is arguable."),
    "A33": ("low", "99214 with hypertension alone is arguable; level not diagnosis-driven."),
    "A34": ("medium", "99214 for uncomplicated pharyngitis looks upcoded."),
    "A35": ("medium", "99214 for uncomplicated URI looks upcoded."),
    "A36": ("low", "99214 for non-specific low back pain is arguable."),
    "D1": ("high", "20610 + 76942: CPT directs ultrasound-guided major-joint injection to 20611; 76942 is not reported with 20610, so a modifier-59 appeal is unrealistic."),
    "D2": ("low", "The NCCI pair I recall is 97530/97140, not 97110/97140; verify the edit exists and allows modifier 59."),
    "C3": ("medium", "MA130 normally marks an unprocessable claim with no appeal rights, yet the denial letter gives appeal rights."),
    "C4": ("medium", "N522 is, as I recall, specific to duplicates of crossover claims; weak fit for a plain duplicate."),
    "C5": ("medium", "N54 suggests the claim is inconsistent with an existing authorization; CO-197 here means none on file."),
    "C7": ("medium", "M51 is about an invalid procedure code; a missing modifier would use a modifier-specific remark."),
}
COMBOS = [("M54.16 + M51.16, M54.17 + M51.17 (claims for categories 1-2, e.g. C-0007 carries M54.17 + M51.17)", "high",
           "Excludes1: radiculopathy M54.1- is not reported with disc disorder with radiculopathy M51.1-. Both reviewers and the author agree."),
          ("M54.16/M54.17 + M51.17/M51.16 (cross-region), M51.26 + M51.1x", "medium", "Overlapping or redundant disc/radiculopathy coding on one claim; the generator picks any 2 of 5 codes."),
          ("Scenario realism, category 3 ('urgent' 27447/29881/63030 with an urgent-evaluation note)", "medium",
           "Elective orthopedic surgery described as urgent is unusual; retro-authorization fits true emergencies better (author only).")]


def main():
    lines = {}
    for ln in (RAW / "coding_table_ids.txt").read_text().splitlines():
        m = re.match(r"([A-E]\d+)\. (.*)", ln)
        if m:
            lines[m.group(1)] = m.group(2).split("  |")[0][:110]
    par = json.loads((RAW / "coding_parsed.json").read_text())
    rank = {"high": 3, "medium": 2, "low": 1}
    rows = ["| ID | Line | Gemini | GPT-5.5 | Author (Claude) | Combined | Reason (strongest) |", "|---|---|---|---|---|---|---|"]
    for lid, text in lines.items():
        cells, best = [], (0, "")
        votes = {}
        for rk in ("gemini", "gpt"):
            e = next((x for x in (par.get(rk) or {}).get("lines", []) if x.get("id") == lid), None)
            votes[rk] = e
            cells.append("n/a" if not e else ("no concern" if e["verdict"] != "suspect" else f"suspect ({e.get('confidence')})"))
            if e and e["verdict"] == "suspect" and rank.get(e.get("confidence"), 0) >= best[0]:
                best = (rank.get(e.get("confidence"), 0), e.get("reason", ""))
        own = OWN.get(lid)
        cells.append(f"suspect ({own[0]})" if own else "no concern")
        if own and rank[own[0]] > best[0]:
            best = (rank[own[0]], own[1])
        sus = [c for c in cells if c.startswith("suspect")]
        comb = "no concern" if not sus else ("suspect" + (" (flagged by %d of 3)" % len(sus)))
        if lid.startswith("B"):
            comb = "mismatch is INTENDED" + (" (reviewers agree it is a poor fit)" if sus else "")
        rows.append(f"| {lid} | {text} | {cells[0]} | {cells[1]} | {cells[2]} | {comb} | {best[1][:230].replace('|', '/')} |")
    rows += ["", "**Combination-level flags** (several diagnosis codes on one claim):", ""]
    rows += [f"- {c} | {conf} | {why}" for c, conf, why in COMBOS]
    return "\n".join(rows)


if __name__ == "__main__":
    p = ROOT / "docs" / "AUTO_REVIEW.md"
    text = p.read_text()
    if "<<CODING_TABLE>>" not in text:
        print(main())
    else:
        p.write_text(text.replace("<<CODING_TABLE>>", main()))
        print("table substituted")
