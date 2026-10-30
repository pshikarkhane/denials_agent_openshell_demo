"""JSON I/O for skills: pydantic input/output models, JSON-schema export, a traced `execute` wrapper and the CLI.

CLI:  python -m skills.<name> '<json args>'  -> prints ONE JSON object with sorted keys. On failure prints
      {"error": {"code": ..., "message": ...}} and exits 1. Configuration (also accepted as JSON args): CASE_ROOT, POLICY_ROOT,
      OUTPUT_ROOT, SKILL_EVENTS_FILE, RUN_ID, CASE_ID environment variables."""
import json
import sys
import time

from pydantic import BaseModel, ConfigDict, ValidationError

from skills.common.events import EventLog
from skills.common.paths import AccessDenied, PathGuard


class SkillError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_root: str | None = None
    policy_root: str | None = None
    output_root: str | None = None
    events_file: str | None = None
    run_id: str | None = None
    case_id: str | None = None
    step: int | None = None


class Ctx:
    def __init__(self, inp, events=None):
        self.events = events or EventLog(inp.events_file, inp.run_id, inp.case_id, inp.step)
        self.guard = PathGuard(inp.case_root, inp.policy_root, inp.output_root, self.events)
        self.tool = "skill"

    def read(self, kind, rel):
        """Guarded read that logs one access event per file."""
        t0 = time.time()
        text = self.guard.read_text(kind, rel)
        self.events.log(f"{self.tool}.read", {"root": kind, "path": str(rel)}, f"{len(text)} chars", (time.time() - t0) * 1000)
        return text


def summarize(obj, n=240):
    s = json.dumps(obj, sort_keys=True, default=str)
    return s if len(s) <= n else s[:n - 1] + "…"


def execute(tool, inp, func, summary=None):
    """Run func(inp, ctx) with timing and an event; returns the output model. Errors are logged and re-raised as SkillError."""
    events = EventLog(inp.events_file, inp.run_id, inp.case_id, inp.step)
    args = {k: v for k, v in inp.model_dump(mode="json").items() if v is not None and k not in ("events_file",) and "text" not in k}
    t0 = time.time()
    try:
        ctx = Ctx(inp, events)             # the guard refuses a contaminated root here
        ctx.tool = tool
        out = func(inp, ctx)
    except AccessDenied as e:
        events.log(tool, args, str(e), (time.time() - t0) * 1000, status="denied", error=str(e))
        raise SkillError("access_denied", str(e)) from None
    except SkillError as e:
        events.log(tool, args, e.message, (time.time() - t0) * 1000, status="error", error=f"{e.code}: {e.message}")
        raise
    except FileNotFoundError as e:
        events.log(tool, args, str(e), (time.time() - t0) * 1000, status="error", error=f"not_found: {e}")
        raise SkillError("not_found", str(e)) from None
    events.log(tool, args, (summary(out) if summary else summarize(out.model_dump(mode="json"))), (time.time() - t0) * 1000)
    return out


def json_schema(model):
    return model.model_json_schema()


def cli(tool, input_model, func, argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        raw = json.loads(argv[0]) if argv else {}
        inp = input_model.model_validate(raw)
        out = execute(tool, inp, func)
        print(json.dumps(out.model_dump(mode="json"), sort_keys=True, indent=1))
        return 0
    except (ValidationError, ValueError) as e:
        print(json.dumps({"error": {"code": "bad_input", "message": str(e)[:500]}}, sort_keys=True))
    except SkillError as e:
        print(json.dumps({"error": {"code": e.code, "message": e.message}}, sort_keys=True))
    return 1
