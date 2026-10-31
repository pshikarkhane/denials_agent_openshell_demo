"""Re-derive events.jsonl, trace.json and the trace-derived summary.json fields of existing Hermes runs from their saved raw files
(hermes_raw/sse_events.jsonl, session_messages.json, session.json, agent_log.txt). No sandbox or network access. Use after a change to build_events.py.
  python scripts/hermes/rebuild_events.py runs/hermes-p1-r1 runs/hermes-p1-r2"""
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import build_events as be  # noqa: E402
from agent.events import Recorder  # noqa: E402
from _common import redact  # noqa: E402  (scripts/phase0; found through hermes' sbx import path)

sys.path.insert(0, str(HERE.parents[1] / "scripts" / "phase0"))


def rebuild(case_dir):
    case_dir = Path(case_dir)
    sp = case_dir / "summary.json"
    s = json.loads(sp.read_text())
    raw = case_dir / "hermes_raw"
    sse = [json.loads(x) for x in (raw / "sse_events.jsonl").read_text().splitlines() if x.strip()]
    msgs = json.loads((raw / "session_messages.json").read_text())
    log = (raw / "agent_log.txt").read_text().splitlines()
    t0 = datetime.fromisoformat(s["started"]).timestamp()
    meta = {"run_id": s["run_id"], "case_id": s["case_id"], "hermes_run_id": s["hermes_run_id"], "model": s["model_id"], "prompt_sha256": s["prompt_sha256"], "git_sha": s["git_sha"],
            "max_turns": s["max_turns"], "time_limit_s": s.get("time_limit_s", 900), "start": t0, "end": t0 + s["seconds"], "status": s["status"],
            "usage": next((e.get("usage") for e in sse if e.get("event") == "run.completed"), None) or {}, "hermes_version": s["hermes_version"]}
    events, S = be.build(meta, sse, msgs, log)
    rec = Recorder(case_dir, s["run_id"], s["case_id"], "hermes")
    rec.events = events
    (case_dir / "events.jsonl").write_text("".join(redact(json.dumps(e, sort_keys=True, default=str)) + "\n" for e in events))
    rec.write_trace()
    s.update(be.derived_fields(S))
    sp.write_text(redact(json.dumps(s, indent=1, sort_keys=True, default=str)) + "\n")
    return S


if __name__ == "__main__":
    for run in sys.argv[1:]:
        for case in sorted(Path(run).glob("C-*")):
            S = rebuild(case)
            print(case, "malformed", S["malformed_calls"], "tool_errors", S["tool_errors"], "args_via_expansion", S["args_via_shell_expansion"])
