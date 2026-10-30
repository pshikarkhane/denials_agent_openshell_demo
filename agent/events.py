"""Run recorder for the demo UI: runs/<run_id>/<case_id>/events.jsonl (stable schema, see docs/EVENTS_SPEC.md) and trace.json (replay steps).
Everything written is passed through key redaction. Only agent-visible content is recorded (model text and tool results)."""
import json
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "phase0"))
from _common import redact  # noqa: E402

KINDS = ("run_start", "model_request", "model_response", "tool_call", "tool_result", "self_check", "revision", "run_end")
EVENT_KEYS = ("seq", "ts", "run_id", "case_id", "variant", "kind", "name", "status", "duration_ms", "data")


def snip(x, n=200):
    s = x if isinstance(x, str) else json.dumps(x, sort_keys=True, default=str)
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n - 1] + "…"


class Recorder:
    def __init__(self, out_dir, run_id, case_id, variant="agent"):
        self.dir, self.run_id, self.case_id, self.variant = Path(out_dir), run_id, case_id, variant
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "events.jsonl"
        self.path.write_text("")
        self.events, self.seq, self._lock = [], 0, threading.Lock()

    def emit(self, kind, name, status="ok", duration_ms=0, data=None):
        assert kind in KINDS, kind
        with self._lock:
            self.seq += 1
            ev = {"seq": self.seq, "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "run_id": self.run_id, "case_id": self.case_id,
                  "variant": self.variant, "kind": kind, "name": name, "status": status, "duration_ms": int(duration_ms), "data": data or {}}
            line = redact(json.dumps(ev, sort_keys=True, default=str))
            ev = json.loads(line)
            self.events.append(ev)
            with self.path.open("a") as f:
                f.write(line + "\n")
        return ev

    def build_trace(self):
        steps, pending = [], {}
        for e in self.events:
            d, k = e["data"], e["kind"]
            if k == "tool_call":
                pending[d.get("tool_call_id")] = d
            if k == "run_start":
                steps.append(("run", "start", f"model {d.get('model')}", "run started", 0, "ok"))
            elif k == "model_response":
                calls = [c["name"] for c in d.get("tool_calls", [])]
                res = ("tool calls: " + ", ".join(calls)) if calls else snip(d.get("content") or d.get("error") or "(empty)")
                steps.append(("model", f"turn {d.get('turn')}", f"attempt {d.get('attempt')}", res, e["duration_ms"], e["status"]))
            elif k == "tool_result":
                call = pending.get(d.get("tool_call_id"), {})
                steps.append(("tool", e["name"], snip(call.get("arguments", {}), 160), snip(d.get("result", ""), 200), e["duration_ms"], e["status"]))
            elif k == "self_check":
                steps.append(("self_check", d.get("phase", ""), "", f"ok={d.get('ok')} errors={d.get('n_errors')} warnings={d.get('n_warnings')}", e["duration_ms"], e["status"]))
            elif k == "revision":
                steps.append(("revision", f"revision {d.get('n')}", "", snip(d.get("reason", "")), 0, e["status"]))
            elif k == "run_end":
                steps.append(("run", "end", "", f"status {d.get('status')}; turns {d.get('turns')}", 0, e["status"]))
        return [{"n": i, "kind": a, "name": b, "args_summary": c, "result_summary": r, "duration_ms": dur, "status": st}
                for i, (a, b, c, r, dur, st) in enumerate(steps, 1)]

    def write_trace(self):
        text = redact(json.dumps(self.build_trace(), indent=1, sort_keys=True))
        (self.dir / "trace.json").write_text(text + "\n")
