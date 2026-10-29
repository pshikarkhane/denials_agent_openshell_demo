#!/usr/bin/env python3
"""Run the automated review: python scripts/review/run_review.py [programmatic blind realism policy coding]  (default: all)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blind_solve  # noqa: E402
import coding_review  # noqa: E402
import policy_review  # noqa: E402
import programmatic_checks  # noqa: E402
import realism_review  # noqa: E402
from common import load_models, manifest_pilots  # noqa: E402

steps = sys.argv[1:] or ["programmatic", "blind", "realism", "policy", "coding"]
cfg = load_models()
if "programmatic" in steps:
    programmatic_checks.main()
if "blind" in steps:
    cases = manifest_pilots()
    for k, v in blind_solve.compare(cases, blind_solve.run(cfg, cases)).items():
        print("blind", k, v.get("decision"), v["mismatches"] or "all match", flush=True)
if "realism" in steps:
    for k, v in realism_review.run(cfg, manifest_pilots()).items():
        print("realism", k, "unparseable" if v is None else f"{len(v.get('findings', []))} findings", flush=True)
if "policy" in steps:
    for k, v in policy_review.run(cfg).items():
        print("policy", k, len(v), flush=True)
if "coding" in steps:
    for k, v in coding_review.run(cfg).items():
        print("coding", k, len(v), flush=True)
