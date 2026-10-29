#!/usr/bin/env python3
"""Recompute a run's gold sanity numbers WITHOUT the Claude judge (it is the same model as the datagen/gold writer, so it should not
grade its own writing). Reads runs/<run_id>/cases/*.json; no model calls. Usage: python scripts/gold_without_claude.py <run_id>"""
import json
import sys
from pathlib import Path

run = Path(__file__).resolve().parents[1] / "runs" / sys.argv[1]
for f in sorted((run / "cases").glob("C-*.json")):
    d = json.loads(f.read_text())
    p, h = d["panel"], d["hallucination"]
    keep = [j for j in p["judges"] if j != "claude"]
    n = p["criteria_total"]
    panel_pass = 0
    for cid, a in p["auto"].items():
        panel_pass += a["pass"]
    judge_ids = [c for c in p["panel"] if c not in p["auto"]]
    for cid in judge_ids:
        votes = [p["judges"][j]["verdicts"].get(cid, {}).get("verdict") for j in keep if not p["judges"][j]["failed"]]
        panel_pass += bool(votes) and votes.count("PASS") > len(votes) / 2
    mat = minor = 0
    for fl in h["flags"]:
        up = [v for j, v in fl["votes"].items() if j in keep and v["upheld"]]
        if len(up) >= 2:
            if sum(v["severity"] == "material" for v in up) >= len(up) - sum(v["severity"] == "material" for v in up):
                mat += 1
            else:
                minor += 1
    print(f"{d['panel']['case_id']}: panel pass {panel_pass}/{n} ({panel_pass / n:.0%}); upheld material {mat}, minor {minor} (judges: {', '.join(keep)})")
