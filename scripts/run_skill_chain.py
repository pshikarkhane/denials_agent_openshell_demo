#!/usr/bin/env python3
"""Run the four read-only skills in order on a STAGED copy of a case (task.md + docs/** + the policy library; never truth/rubric/gold/attacks)
and print the JSON each step would give the model. Offline: no model calls, no keys.

  python scripts/run_skill_chain.py --case C-0005 [--data data] [--events docs/samples/skill_events_sample.jsonl] [--out docs/samples/skill_chain_C-0005.json]
"""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skills.assess_appealability import call as assess  # noqa: E402
from skills.parse_denial_eob import call as parse  # noqa: E402
from skills.pull_clinical_notes import call as pull  # noqa: E402
from skills.retrieve_payer_policy import call as retrieve  # noqa: E402


def stage(data, case, dest):
    src = Path(data) / "cases" / case
    (dest / "case").mkdir(parents=True)
    shutil.copy2(src / "task.md", dest / "case" / "task.md")
    shutil.copytree(src / "docs", dest / "case" / "docs")
    shutil.copytree(Path(data) / "policy_library", dest / "policy_library")
    return dest / "case", dest / "policy_library"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--events", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    tmp = Path(tempfile.mkdtemp(prefix="skillchain_"))
    case_root, policy_root = stage(a.data, a.case, tmp)
    events = Path(a.events) if a.events else tmp / "events.jsonl"
    if events.exists():
        events.unlink()
    base = {"case_root": str(case_root), "policy_root": str(policy_root), "case_id": a.case, "run_id": f"chain-{a.case}", "events_file": str(events)}
    steps = []
    p = parse({**base, "step": 1})
    steps.append({"step": 1, "tool": "parse_denial_eob", "output": p})
    r = retrieve({**base, "step": 2, "payer": p["payer"]["id"], "dos": p["dos"], "cpt": p["cpt"], "service_description": p["service_description"], "icd10": p["icd10"],
                  "denial_code": p["denial"]["carc"], "denial_text": p["denial"]["carc_text"], "reason_text": p["denial"]["reason_text"], "policy_title": p["policy_title"]})
    steps.append({"step": 2, "tool": "retrieve_payer_policy", "output": r})
    n = pull({**base, "step": 3})
    steps.append({"step": 3, "tool": "pull_clinical_notes", "output": n})
    s = assess({**base, "step": 4, "policy_id": r["policy"]["policy_id"] if r["status"] == "selected" else None})
    steps.append({"step": 4, "tool": "assess_appealability", "output": s})
    text = json.dumps({"case": a.case, "steps": steps}, sort_keys=True, indent=1)
    ev_text = events.read_text()
    for real, token in ((str(case_root), "<CASE_ROOT>"), (str(policy_root), "<POLICY_ROOT>")):
        text, ev_text = text.replace(real, token), ev_text.replace(real, token)
    events.write_text(ev_text)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text + "\n")
    if not a.quiet:
        for st in steps:
            print(f"--- step {st['step']}: {st['tool']} ---")
            print(json.dumps(st["output"], sort_keys=True, indent=1)[:3000])
    print(f"events: {events} ({len(ev_text.splitlines())} lines)" + (f"; chain: {a.out}" if a.out else ""))
    shutil.rmtree(tmp, ignore_errors=True) if not a.events else None


if __name__ == "__main__":
    main()
