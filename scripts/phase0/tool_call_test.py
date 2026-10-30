"""Phase 0, step 5: N tool-call attempts through the port-forwarded Hermes API; failure rate + one trace sample.

Each attempt asks the agent to run a terminal command with a unique expected output. An attempt passes if the run
emits tool.started + tool.completed (no error), ends with run.completed, and the final output contains the expected
string. Failures (with redacted response bodies / events) go to logs/hermes_tool_failures.jsonl.

Usage: python scripts/phase0/tool_call_test.py [N=10] [--sample docs/samples/hermes_trace_sample.json]
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import ROOT, redact  # noqa: E402
import hermes_client as hc  # noqa: E402

FAIL_LOG = ROOT / "logs" / "hermes_tool_failures.jsonl"


def attempt(token, i):
    expect = f"check-{i}-{(i + 3) * 7}"
    prompt = (f"Use your terminal tool to run exactly: echo check-{i}-$(( ({i}+3)*7 )) . "
              f"Then reply with only the exact output of that command.")
    rec = {"attempt": i, "expect": expect, "ok": False, "events": [], "error": None}
    t0 = time.time()
    try:
        rid = hc.start_run(token, prompt)
        rec["run_id"] = rid
        for ev in hc.stream_events(token, rid):
            rec["events"].append(ev)
        names = [e["event"] for e in rec["events"]]
        done = next((e for e in rec["events"] if e["event"] == "run.completed"), None)
        tool_ok = ("tool.started" in names and any(e["event"] == "tool.completed" and not e.get("error")
                                                   for e in rec["events"]))
        rec["ok"] = bool(done and tool_ok and expect in (done.get("output") or ""))
        if not rec["ok"]:
            rec["error"] = f"events={names}; output={(done or {}).get('output')!r}"
    except Exception as e:  # noqa: BLE001 - record and continue
        rec["error"] = redact(f"{type(e).__name__}: {e}", token)
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(args[0]) if args else 10
    sample = sys.argv[sys.argv.index("--sample") + 1] if "--sample" in sys.argv else None
    token = hc.gateway_token()
    results = []
    for i in range(1, n + 1):
        r = attempt(token, i)
        results.append(r)
        print(f"{'PASS' if r['ok'] else 'FAIL'}  attempt {i:2d}  {r['seconds']:5.1f}s  {r['error'] or ''}", flush=True)
        if not r["ok"]:
            FAIL_LOG.parent.mkdir(parents=True, exist_ok=True)
            with FAIL_LOG.open("a") as f:
                f.write(redact(json.dumps(r, default=str), token) + "\n")
    bad = sum(not r["ok"] for r in results)
    print(f"tool-call failure rate: {bad}/{n} = {bad / n:.0%}")
    if sample:
        good = next((r for r in results if r["ok"]), None)
        if good:
            msgs = hc.session_messages(token, good["run_id"])
            out = {"description": "One real Hermes run: SSE events from GET /v1/runs/{id}/events plus the full message "
                                  "history from GET /api/sessions/{id}/messages (tool arguments and results).",
                   "run_id": good["run_id"], "prompt_expectation": good["expect"],
                   "sse_events": good["events"], "session_messages": msgs}
            Path(sample).parent.mkdir(parents=True, exist_ok=True)
            Path(sample).write_text(redact(json.dumps(out, indent=2, default=str), token) + "\n")
            print(f"trace sample written to {sample}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
