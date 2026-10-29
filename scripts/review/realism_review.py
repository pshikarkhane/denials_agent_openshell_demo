"""Part 2: realism / leak / evidence / consistency / solvability review. Reviewers get agent-visible files PLUS the host-only
truth (criteria, facts, traps, decision) of the case. Reviewer output is host-side only; nothing here is mounted."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW, ROOT, agent_visible, ask, load_models, manifest_pilots, parse_json, reviewers, run_parallel  # noqa: E402

PROMPT = """You are reviewing a SYNTHETIC test case for a denial-appeal AI agent. You are given (A) the host-only answer key for one case and (B) every file the agent will see (task, documents, payer policy library). Be a skeptical reviewer. Do not invent problems: if a check is clean, say so.

Review these five areas:
1. REALISM: would a billing/RCM professional find the denial letter, EOB or clinical notes odd (voice too polished, copied phrasing, implausible clinical details, wrong payer tone, unrealistic fields)?
2. LEAKS: any word or phrasing in the agent-visible files that reveals the decision, the category, the trap, or that criteria are met/unmet. (The 'SYNTHETIC DATA' footer is expected. The task.md lists the four possible decision values by design.)
3. EVIDENCE MATCH: for each criterion marked met, is the evidence actually in the cited file; for each unmet/unknown, is the evidence truly absent or contradicted, with NO quiet support elsewhere; is each trap present and visible but not obvious?
4. CROSS-FILE CONSISTENCY: claim number, patient ID, name, DOB, MRN, DOS, CPT/ICD-10, billed amount, deadlines, payer name and policy title across eob, denial letter, task.md, notes and policy.
5. SOLVABILITY: can the correct policy be uniquely identified from payer, title, service and effective date without tying with a distractor? Is the intended decision defensible from the documents alone?

Respond with ONE JSON object: {{"findings": [{{"area": "realism|leak|evidence|consistency|solvability", "severity": "blocker|major|minor", "file": "...", "quote": "exact quote", "problem": "...", "suggested_fix": "..."}}], "clean_areas": ["areas with no findings"], "overall": "one sentence"}}. Severity: blocker = makes the case unsolvable/wrong or leaks the answer; major = likely to distort scoring or obviously unrealistic; minor = polish.

(A) ANSWER KEY (host-only truth.json):
{truth}

(B) AGENT-VISIBLE FILES:
{bundle}
"""


def run(cfg, cases):
    rv = reviewers(cfg)
    jobs = []
    for cid in cases:
        bundle, _ = agent_visible(cid)
        truth = (ROOT / "data" / "cases" / cid / "truth.json").read_text()
        for rk, model in rv.items():
            prompt = PROMPT.format(truth=truth, bundle=bundle)
            jobs.append(lambda cid=cid, rk=rk, model=model, prompt=prompt: ((cid, rk), ask(cfg, rk, model, f"realism_{cid}", prompt)))
    outs = run_parallel(jobs)
    parsed = {f"{k[0]}__{k[1]}": parse_json(v) for k, v in outs.items()}
    (RAW / "realism_parsed.json").write_text(json.dumps(parsed, indent=2) + "\n")
    return parsed


if __name__ == "__main__":
    parsed = run(load_models(), manifest_pilots())
    for k, v in parsed.items():
        print(k, "unparseable" if v is None else f"{len(v.get('findings', []))} findings")
