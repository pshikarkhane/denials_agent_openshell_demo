"""Re-apply the audit `tag` rules (build_events.classify_audit) to existing runs/<run>/<case>/audit.jsonl and refresh the audit_* counts in summary.json.
  python scripts/hermes/retag_audit.py runs/hermes-p1-r1 runs/hermes-p1-r2"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_events as be  # noqa: E402

for run in sys.argv[1:]:
    for case in sorted(Path(run).glob("C-*")):
        ap, sp = case / "audit.jsonl", case / "summary.json"
        if not ap.exists():
            continue
        ev = [json.loads(x) for x in ap.read_text().splitlines() if x.strip()]
        for e in ev:
            if e["tag"] != "post_run":
                e["tag"] = be.classify_audit(e)
            elif be.classify_audit(e) == "background":
                e["tag"] = "background"
        ap.write_text("".join(json.dumps(e, sort_keys=True, ensure_ascii=False) + "\n" for e in ev))
        s = json.loads(sp.read_text())
        s.update(audit_events=len(ev), audit_background=sum(e["tag"] == "background" for e in ev), audit_post_run=sum(e["tag"] == "post_run" for e in ev),
                 audit_denied_run=sum(e["tag"] == "run" and e["result"] == "denied" for e in ev))
        sp.write_text(json.dumps(s, indent=1, sort_keys=True) + "\n")
        print(case, s["audit_background"], s["audit_denied_run"])
