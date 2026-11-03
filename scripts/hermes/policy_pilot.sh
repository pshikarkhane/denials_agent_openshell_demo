#!/bin/sh
# One pilot case (C-0005) end to end after a policy change, then list every ALLOWED network event of the run window by host.
# usage: scripts/hermes/policy_pilot.sh <run-id>
set -e
cd "$(dirname "$0")/../.."
export PATH=$HOME/.local/bin:$PATH
.venv/bin/python scripts/hermes/run_case.py --case C-0005 --repeats 1 --run-id "$1" 2>&1 | grep -v -i warning
.venv/bin/python - "$1" <<'PY'
import json, sys, collections, re
a = f"runs/{sys.argv[1]}-r1/C-0005/audit.jsonl"
c = collections.Counter()
for l in open(a):
    e = json.loads(l)
    if e["event_class"] in ("NET:OPEN", "HTTP:GET", "HTTP:POST", "HTTP:PUT") and e["result"]:
        c[(e["tag"], e["result"], re.sub(r"^\w+ https?://", "", (e["target"] or "")).split("/")[0][:60] if e["event_class"] != "NET:OPEN" else e["target"])] += 1
for k, v in sorted(c.items()): print(v, k)
PY
