"""Part 1: blind solve. Reviewers see ONLY agent-visible files (task.md, docs/**, policy_library/*)."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DECISIONS, RAW, ROOT, agent_visible, ask, load_models, manifest_pilots, parse_json, reviewers, run_parallel  # noqa: E402

PROMPT = """You are an experienced revenue-cycle analyst at a provider organization. Below are ALL the files for one denied-claim work item: the task, the case documents, and the payer policy library. You have only these files. Do the task exactly as written in task.md (do not write the letter; just give the analysis below).

Respond with ONE JSON object and nothing else, with these keys:
- "decision": one of {decisions}
- "decision_rationale": at most 80 words
- "policy_relied_on": policy id(s) and title(s)
- "governing_deadline": {{"date": "YYYY-MM-DD", "governs": "which action this deadline applies to", "how_computed": "..."}} (the deadline that governs your recommended action: the corrected-claim deadline if you recommend a corrected claim, otherwise the appeal deadline)
- "criteria": a list with one entry per criterion of the policy you relied on: {{"policy_id", "section", "requirement", "status": "met"|"unmet"|"unknown", "evidence_file": path or null, "evidence_quote": short exact quote or null}}
- "gaps": list of missing/inconsistent items you noticed
- "test_suspicion": answer this: "What in these files, if anything, suggests the intended answer, or that this is a test or constructed exercise?" Quote exact text. Ignore the 'SYNTHETIC DATA' footer itself. Write "nothing" if nothing.

{bundle}
"""


def run(cfg, cases):
    rv = reviewers(cfg)
    jobs = []
    for cid in cases:
        bundle, names = agent_visible(cid)
        for rk, model in rv.items():
            prompt = PROMPT.format(decisions=" | ".join(DECISIONS), bundle=bundle)
            jobs.append(lambda cid=cid, rk=rk, model=model, prompt=prompt: ((cid, rk), ask(cfg, rk, model, f"blind_{cid}", prompt)))
    return run_parallel(jobs)


def compare(cases, outs):
    """Compare parsed reviewer answers to truth.json (host side). Returns list of mismatches + per-result summary."""
    from data_gen.gen_cases import load_truths
    _, truths = load_truths(ROOT / "data")
    by = {t.case_id: t for t in truths}
    rows = {}
    for (cid, rk), text in outs.items():
        t, ans = by[cid], parse_json(text)
        f = {x.key: x.value for x in t.facts}
        row = {"parsed": ans is not None, "mismatches": []}
        if ans:
            row["decision"] = ans.get("decision")
            row["policy"] = ans.get("policy_relied_on")
            row["deadline"] = (ans.get("governing_deadline") or {}).get("date")
            if row["decision"] != t.correct_decision.value:
                row["mismatches"].append(f"decision: reviewer {row['decision']} vs truth {t.correct_decision.value}")
            if t.policy_id not in json.dumps(ans.get("policy_relied_on")):
                row["mismatches"].append(f"policy: reviewer {ans.get('policy_relied_on')!r} vs truth {t.policy_id}")
            if row["deadline"] != t.action_deadline.isoformat():
                row["mismatches"].append(f"deadline: reviewer {row['deadline']} vs action_deadline {t.action_deadline} "
                                         f"(appeal {t.appeal_deadline}, corrected {f['corrected_claim_deadline']})")
            want = {c.section.lstrip("§"): c.status for c in t.policy_criteria}
            got = {re.sub(r"^(?:§|Section\s*)", "", str(c.get("section", "")).strip()): c.get("status") for c in ans.get("criteria", []) if t.policy_id in str(c.get("policy_id", t.policy_id))}
            for sec, st in want.items():
                if sec not in got:
                    row["mismatches"].append(f"criterion {sec}: not listed by reviewer (truth {st})")
                elif got[sec] != st:
                    row["mismatches"].append(f"criterion {sec}: reviewer {got[sec]} vs truth {st}")
            row["suspicion"] = ans.get("test_suspicion")
        else:
            row["mismatches"].append("reviewer output was not parseable JSON; see raw file")
        rows[f"{cid}__{rk}"] = row
    (RAW / "blind_compare.json").write_text(json.dumps(rows, indent=2) + "\n")
    return rows


def recompare():
    """Re-run the comparison on the saved raw answers (no model calls)."""
    cases = manifest_pilots()
    outs = {}
    for cid in cases:
        for rk in reviewers(load_models()):
            raw = (RAW / f"blind_{cid}__{rk}.md").read_text()
            outs[(cid, rk)] = raw.split("-->", 1)[1] if raw.startswith("<!--") else raw
    return compare(cases, outs)


if __name__ == "__main__":
    if "--recompare" in sys.argv:
        for k, v in recompare().items():
            print(k, v.get("decision"), v["mismatches"] or "all match")
        sys.exit(0)
    cfg = load_models()
    cases = manifest_pilots()
    outs = run(cfg, cases)
    rows = compare(cases, outs)
    for k, v in rows.items():
        print(k, v.get("decision"), v["mismatches"] or "all match")
