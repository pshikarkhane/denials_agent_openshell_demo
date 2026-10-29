#!/usr/bin/env python3
"""Generate docs/CODER_CHECKLIST.md from the generated truth files: only the code pairs, RARCs and bundling pairs actually in use.
Usage: .venv/bin/python scripts/make_coder_checklist.py"""
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


def main():
    _, truths = load_truths(ROOT / "data")
    pairs, wrong, rarc, bundles, mods = defaultdict(set), defaultdict(set), defaultdict(set), defaultdict(set), defaultdict(set)
    carc_cat = defaultdict(set)
    for t in truths:
        f = facts(t)
        for i in t.claim.icd10:
            (wrong if t.category == 11 else pairs)[(t.claim.cpt, i)].add(t.category)
        if t.category == 11:
            for i in f["corrected_icd10"]:
                pairs[(t.claim.cpt, i)].add(11)
        rarc[(t.denial.carc, t.denial.rarc)].add(t.category)
        carc_cat[t.denial.carc].add(t.category)
        if "column1_code" in f:
            bundles[(f["column1_code"], t.claim.cpt)].add(t.case_id)
        if "missing_field" in f:
            mods[(f["missing_field"], t.claim.cpt, t.denial.carc)].add(t.case_id)
    box = "[ ] OK  [ ] wrong  Notes: "
    L = ["# Coder checklist", "",
         "For a coding / revenue-cycle professional. **Every item was chosen by an AI assistant from general knowledge and has not been verified.** Code descriptions are paraphrases, not AMA/CMS text. All data is synthetic. Please mark each line OK or wrong and say what the correct code would be.", "",
         "This list contains only what is **in use in the generated cases now**. Generated from `data/` by `scripts/make_coder_checklist.py`.", "",
         "## 1. CPT + ICD-10 pairings meant to be valid", ""]
    for (cpt, icd), cats in sorted(pairs.items()):
        L.append(f"- {cpt} ({R.CPT[cpt]}) + {icd} ({R.ICD10[icd]})  | categories {sorted(cats)}  | {box}")
    L += ["", "Categories 1-2 carry exactly one diagnosis per claim (no Excludes1 pairs). Please confirm that no claim in this dataset reports M54.1x together with M51.1x.", "",
          "## 2. Pairings that are deliberately WRONG (category 11, CO-11); the corrected diagnosis is in section 1", ""]
    for (cpt, icd), cats in sorted(wrong.items()):
        L.append(f"- {cpt} ({R.CPT[cpt]}) billed with {icd} ({R.ICD10[icd]}): is it a clear mismatch that a payer edit would deny?  | {box}")
    L += ["", "## 3. CARC / RARC pairings in use", "",
          "RARCs were **omitted** (none shown on the remit) for CO-197, CO-4, CO-18 and CO-16 until you recommend one. If you give a RARC for these, say whether it appears with the scenario shown.", ""]
    for (carc, rc), cats in sorted(rarc.items(), key=lambda x: (x[0][0], str(x[0][1]))):
        scen = "; ".join(R.CATEGORIES[c]["name"] for c in sorted(cats))
        L.append(f"- {carc} ({R.CARC_TEXT[carc]}) with RARC {rc or 'none'}  | scenario: {scen}  | {box}")
    L += ["", "## 4. Bundling pairs (CO-97 / N20, distinct-service modifier 59 or XS)", "",
          "`97530 + 97140` is new in this round (it replaced `20610 + 76942`, which CPT rules do not allow to be billed together). Please also say whether 97110 + 97140 has an edit at all.", ""]
    for (c1, c2), ids in sorted(bundles.items()):
        L.append(f"- Column 1: {c1} ({R.CPT[c1]}); denied column 2: {c2} ({R.CPT[c2]})  | {len(ids)} case(s)  | edit exists? modifier 59/XS allowed? {box}")
    L += ["", "## 5. Modifier / claim-data scenarios (CO-4, CO-16)", ""]
    desc = {"modifier_25": "modifier 25 on an E/M billed with a same-day procedure (20610)", "laterality_modifier": "RT/LT laterality modifier missing on a knee MRI",
            "modifier_gp": "modifier GP missing on therapy (97110)", "rendering_provider": "rendering provider identifier missing",
            "referring_provider": "referring provider missing on imaging", "place_of_service": "place of service code missing"}
    for (fld, cpt, carc), ids in sorted(mods.items()):
        L.append(f"- {carc}: {desc[fld]} (CPT {cpt})  | {len(ids)} case(s)  | right CARC for this scenario? {box}")
    L += ["", "## 6. Changed this round (flagged: coder to confirm)", "",
          "- 99214 was replaced by 99213 everywhere (simple diagnoses). Confirm 99213 fits each pairing in section 1.",
          "- CBC (85025) is now paired with D64.9 (anemia) or R53.83 (other fatigue) instead of hypertension.",
          "- Categories 1-2: one diagnosis per claim (from M54.16, M54.17, M51.16, M51.17, M51.26) for CPT 72148.",
          "- Bundling pair 20610 + 76942 replaced by 97530 + 97140 (candidates considered: 97530/97140, 97112/97140, 97110/97530).",
          "- RARCs omitted for CO-197, CO-4, CO-18, CO-16.",
          "- Kept as is: category 3 'urgent' scenario uses elective orthopedic procedures (27447, 29881, 63030) with an urgent-evaluation note; tell us if that is too unrealistic.", ""]
    (ROOT / "docs" / "CODER_CHECKLIST.md").write_text("\n".join(L) + "\n")
    print("wrote docs/CODER_CHECKLIST.md")


main()
