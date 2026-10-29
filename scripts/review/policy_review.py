"""Part 3 (policy library) review by the reviewer models: contradictions, ordering, version-history wording, windows,
and gaps in the policies that back CORRECT_AND_RESUBMIT categories. Gets the library plus the intended windows from reference.py."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW, ROOT, ask, load_models, parse_json, reviewers, run_parallel  # noqa: E402

PROMPT = """You are reviewing the payer policy library of a SYNTHETIC denial-appeal test (fictional payers). Review all 11 policies (8 primary, 3 near-duplicate distractors) critically and do not invent problems.

Intended parameters (must match the policy text exactly):
{windows}

Policy structure notes: sections are cited by number in an answer key; denial letters cite policies by TITLE only. Policies MP-CLM-004 (claim data / duplicates / diagnosis edits) and MP-BND-002 (bundling; its code pairs are CPT 97140 into 97110 and 97140 into 97530) back cases whose correct action is CORRECT_AND_RESUBMIT rather than appeal.

Check:
1. Section ordering and numbering (are sections out of numeric order? gaps?).
2. Internal contradictions, or contradictions with the intended parameters above.
3. Version-history wording (effective date, 'carry forward', 'applies to dates of service on or after'): confusing or contradictory? Does it allow a date of service before the effective date to be handled sensibly?
4. For policies backing CORRECT_AND_RESUBMIT cases: does the text tell a reader that missing/invalid claim data should be fixed by a corrected claim rather than an appeal, and which deadline applies? What is missing?
5. Distractors: are they plausibly similar but distinguishable by payer, service or version? Could an agent tie between a distractor and the right policy?
6. Anything unrealistic for payer policy language, or that hints this is a test.

Respond with ONE JSON object: {{"findings": [{{"area": "ordering|contradiction|windows|version|corrected_claim_gap|distractor|realism", "severity": "blocker|major|minor", "policy": "MP-...", "quote": "exact quote", "problem": "...", "suggested_fix": "..."}}], "clean_areas": [...], "overall": "one sentence"}}

POLICY LIBRARY:
{lib}
"""


def windows():
    from data_gen import reference as R
    rows = [f"{p} ({R.PAYER_NAMES[p]}): appeal {w['appeal_days']} days from notice; timely filing {w['timely_filing_days']} days from DOS; corrected claim {w['corrected_claim_days']} days from notice"
            for p, w in R.PAYERS.items()]
    rows += [f"{pid}: payer {payer}, effective {R.POLICY_EFFECTIVE[pid]}" for pid, payer in R.POLICIES.items()]
    rows += [f"retro-auth window {R.RETRO_AUTH_WINDOW_DAYS} days; PT visit limit {R.PT_VISIT_LIMIT}, visits {R.PT_VISIT_LIMIT + 1} through {R.PT_VISIT_CAP} may be considered with documented improvement and a recertified plan of care"]
    return "\n".join(rows)


def run(cfg):
    lib = "\n".join(f"===== FILE: policy_library/{p.name} =====\n{p.read_text()}" for p in sorted((ROOT / "data" / "policy_library").glob("*.txt")))
    prompt = PROMPT.format(windows=windows(), lib=lib)
    outs = run_parallel([lambda rk=rk, m=m: (rk, ask(cfg, rk, m, "policy_library", prompt)) for rk, m in reviewers(cfg).items()])
    (RAW / "policy_parsed.json").write_text(json.dumps({k: parse_json(v) for k, v in outs.items()}, indent=2) + "\n")
    return outs


if __name__ == "__main__":
    for k, v in run(load_models()).items():
        p = parse_json(v)
        print(k, "unparseable" if p is None else f"{len(p.get('findings', []))} findings")
