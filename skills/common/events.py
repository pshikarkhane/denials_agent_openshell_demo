"""Event log. Every skill call appends ONE JSON line to the events file (stable schema, feeds the replay UI):

  {"ts": ISO-8601 UTC, "run_id": str|null, "case_id": str|null, "step": int|null, "tool": str, "args": object,
   "result_summary": str, "duration_ms": int, "status": "ok" | "error" | "denied", "error": str|null}

`tool` is the skill name, `<skill>.read` for each file a skill reads (one event per file access) or `path_guard` for a refused access
(status "denied"). Keys are always sorted, one event per line. With no events file configured events are kept in memory only."""
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

KEYS = ("ts", "run_id", "case_id", "step", "tool", "args", "result_summary", "duration_ms", "status", "error")


class EventLog:
    def __init__(self, path=None, run_id=None, case_id=None, step=None):
        self.path = Path(path or os.environ.get("SKILL_EVENTS_FILE") or "") if (path or os.environ.get("SKILL_EVENTS_FILE")) else None
        self.run_id = run_id or os.environ.get("RUN_ID")
        self.case_id = case_id or os.environ.get("CASE_ID")
        self.step = step
        self.events = []
        self._lock = threading.Lock()

    def log(self, tool, args, result_summary, duration_ms, status="ok", error=None):
        ev = {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "run_id": self.run_id, "case_id": self.case_id,
              "step": self.step, "tool": tool, "args": args, "result_summary": str(result_summary)[:300], "duration_ms": int(duration_ms),
              "status": status, "error": error}
        assert tuple(sorted(ev)) == tuple(sorted(KEYS))
        with self._lock:
            self.events.append(ev)
            if self.path is not None:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a") as f:
                    f.write(json.dumps(ev, sort_keys=True) + "\n")
        return ev
