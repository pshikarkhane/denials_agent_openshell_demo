"""Run denied-claim cases through the REAL Hermes agent inside the OpenShell sandbox.

  python scripts/hermes/run_case.py --cases pilot --repeats 2 --run-id hermes-p1 [--resume] [--time-limit 900]
  python scripts/hermes/run_case.py --case C-0005 --repeats 1 --run-id hermes-try

Per case and repeat (run id <run-id>-rN, folder runs/<run-id>-rN/<case_id>/):
  1. stage ONE case by allowlisted copy, install it read-only in the sandbox, reinstall the six Hermes adapters;
  2. reset everything Hermes could persist (sessions, memory, self-made skills, work dir, /tmp) and verify against the baseline;
  3. POST /v1/runs {input: task.md + case id, instructions: scripts/hermes/prompts/hermes_system.md}; stream the SSE events (timeout, one retry on a gateway restart);
  4. join with GET /api/sessions/<id>/messages and agent.log; copy ONLY deliverable.md, decision.json and skill_events.jsonl out of the sandbox;
  5. run self_check once more on the final files (harness-run, recorded separately), diff the persisted state, capture the audit window;
  6. write events.jsonl, trace.json, audit.jsonl, summary.json, final_self_check.json, persistence.json and hermes_raw/ (raw SSE, messages, agent.log lines).
Nothing but those outputs and logs is read from the sandbox. The API key is never read here (the Hermes gateway uses its own configuration)."""
import argparse
import hashlib
import json
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import build_events as be  # noqa: E402
import sbx  # noqa: E402
from agent.events import Recorder  # noqa: E402
from _common import redact  # noqa: E402  (scripts/phase0)

PROMPT = HERE / "prompts" / "hermes_system.md"
TERMINAL = {"run.completed", "run.failed", "run.cancelled", "run.stopped"}
OUT_FILES = ("deliverable.md", "decision.json")
RUN = f"{sbx.BASE}/bin/run_skill"


def git_state():
    try:
        sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", ".", ":!runs"], capture_output=True, text=True, check=True).stdout.strip())
        return sha, dirty
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, None


def write_json(path, obj, indent=1):
    Path(path).write_text(redact(json.dumps(obj, indent=indent, sort_keys=True, default=str)) + "\n")


def wait_health(timeout=150):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if sbx.health().get("status") == "ok":
                return True
        except Exception:
            pass
        time.sleep(3)
    return False


def stream_run(tok, hid, deadline_s, sink):
    """Stream SSE into `sink` (list) in a thread; stop the run at the deadline. -> 'completed' | 'failed' | 'timeout' | 'stream_lost'."""
    done = {"state": None}

    def reader():
        try:
            for ev in sbx.hc.stream_events(tok, hid, timeout=60 * 5):
                sink.append(ev)
                if ev.get("event") in TERMINAL:
                    done["state"] = "completed" if ev["event"] == "run.completed" else "failed"
        except Exception as e:  # noqa: BLE001
            done["err"] = type(e).__name__
        done.setdefault("state", None)
        done["ended"] = True

    th = threading.Thread(target=reader, daemon=True)
    th.start()
    t0 = time.time()
    while th.is_alive() and time.time() - t0 < deadline_s:
        th.join(2)
    if th.is_alive():
        try:
            sbx.hc._req(f"/v1/runs/{hid}/stop", tok, {}).close()
        except Exception:  # noqa: BLE001
            pass
        th.join(20)
        return "timeout"
    return done["state"] or "stream_lost"


def agent_log_for(hid):
    return sbx.sbx(f"grep -F '[{hid}]' /sandbox/.hermes/logs/agent.log")[1].splitlines()


def split_log(lines):
    """Hermes forks a background self-review (memory/skill writing) after each run; its model calls are logged under the SAME run id.
    -> (main run lines up to 'Turn ended', review lines after it)."""
    for i, ln in enumerate(lines):
        if "Turn ended:" in ln:
            return lines[:i + 1], lines[i + 1:]
    return lines, []


def wait_for_review(hid, grace=30, timeout=360):
    """Block until the post-run background review has finished (so it cannot write memory/skills after our reset).
    -> {'started', 'complete', 'timed_out', 'waited_s', 'result_line'}"""
    t0 = time.time()
    info = {"started": False, "complete": False, "timed_out": False, "result_line": None}
    while True:
        _, rest = split_log(agent_log_for(hid))
        done = [ln for ln in rest if "Background review complete" in ln]
        info["started"] = bool(rest)
        if done:
            info["complete"], info["result_line"] = True, done[0].split("agent.background_review:")[-1].strip()
            break
        waited = time.time() - t0
        if not rest and waited >= grace:
            break                                           # no review was started
        if waited >= timeout:
            info["timed_out"] = True
            break
        time.sleep(3)
    info["waited_s"] = round(time.time() - t0, 1)
    return info


def sandbox_cat(path):
    rc, out, _ = sbx.sbx(f"[ -f '{path}' ] && cat '{path}'")
    return out if rc == 0 else None


def copy_outputs(case_id, out_dir):
    """Copy ONLY the named output files and the skills' own event log. Everything else in the output dir is listed, not copied."""
    base = f"/sandbox/work/output/{case_id}"
    rc, listing, _ = sbx.sbx(f"ls -la --time-style=+%s {base}")
    got = {}
    for name, dest in (("deliverable.md", "deliverable.md"), ("decision.json", "decision.json"), ("skill_events.jsonl", "skills_events.jsonl")):
        txt = sandbox_cat(f"{base}/{name}")
        if txt is not None:
            (out_dir / dest).write_text(redact(txt))
            got[name] = len(txt)
    return got, listing


def run_once(run_id, case_id, a, tok, out):
    """One attempt. Returns (state, data dict). Raises only on harness failure."""
    sbx.install_case(case_id)
    reset = sbx.reset_state(case_id, tok)
    task = (ROOT / "data" / "cases" / case_id / "task.md").read_text()
    text = task.rstrip() + f"\n\nCase ID: {case_id}. Use it as <CASE_ID> in the skill commands.\n"
    instructions = PROMPT.read_text()
    t0 = time.time()
    hid = sbx.hc.start_run(tok, text, instructions=instructions)
    sse = []
    state = stream_run(tok, hid, a.time_limit, sse)
    t1 = time.time()
    return state, {"hid": hid, "sse": sse, "t0": t0, "t1": t1, "reset": reset, "task_input": text}


def finish_run(run_id, case_id, a, tok, out, state, d, retries):
    hid, sse, t0, t1 = d["hid"], d["sse"], d["t0"], d["t1"]
    raw = out / "hermes_raw"
    raw.mkdir(exist_ok=True)
    msgs, sess = [], {}
    try:                                                    # fetch the transcript first, before anything else happens to the session
        msgs = sbx.hc.session_messages(tok, hid).get("data", [])
        sess = sbx.hc.get_json(f"/api/sessions/{hid}", tok)
    except Exception as e:  # noqa: BLE001
        sess = {"error": type(e).__name__}
    got, listing = copy_outputs(case_id, out)
    review = wait_for_review(hid, grace=a.review_grace)    # must finish before we inspect or reset anything
    t_review_end = time.time()
    all_lines = agent_log_for(hid)
    log_lines, review_lines = split_log(all_lines)
    rapi = be.parse_api_calls(review_lines)
    review["calls"], review["prompt_tokens"], review["completion_tokens"] = len(rapi), sum(x["in"] for x in rapi), sum(x["out"] for x in rapi)
    review["tool_errors_logged"] = sum(1 for ln in review_lines if "Tool " in ln and "returned error" in ln)
    # harness-run self_check on the FINAL files (recorded separately from the agent's own calls); after skill_events.jsonl was copied
    fsc = None
    if set(OUT_FILES) <= set(got):
        rc, o, _ = sbx.sbx(f"{RUN} {case_id} self_check '{{\"deliverable_path\":\"deliverable.md\",\"decision_path\":\"decision.json\"}}'")
        try:
            fsc = json.loads(o)
        except ValueError:
            fsc = {"error": {"code": "unparsed", "message": o[:200]}}
        write_json(out / "final_self_check.json", {**fsc, "source": "harness_after_run"})
    persisted = sbx.diff_state(sbx.inspect(), sbx.baseline_load())
    # audit window
    mins = int((time.time() - t0) / 60) + 3
    ap = subprocess.run([sys.executable, str(ROOT / "scripts" / "phase0" / "export_audit.py"), "--sandbox", sbx.SANDBOX, "--since", f"{mins}m", "-n", "20000"],
                        capture_output=True, text=True, stdin=subprocess.DEVNULL, env=sbx._env())
    raw_audit = [json.loads(x) for x in ap.stdout.splitlines() if x.strip()]
    audit = be.audit_window(raw_audit, t0, t1, t_review_end)
    (out / "audit.jsonl").write_text("".join(redact(json.dumps(x, sort_keys=True, ensure_ascii=False)) + "\n" for x in audit))
    # status
    if set(OUT_FILES) <= set(got) and state == "completed":
        status = "submitted"
    elif set(OUT_FILES) <= set(got):
        status = f"{state}_with_files"
    elif state == "completed":
        status = "no_files"
    else:
        status = state
    sha, dirty = git_state()
    usage = next((e.get("usage") for e in sse if e.get("event") == "run.completed"), None) or {}
    prompt_sha = hashlib.sha256(PROMPT.read_bytes()).hexdigest()
    meta = {"run_id": run_id, "case_id": case_id, "hermes_run_id": hid, "model": sess.get("model"), "prompt_sha256": prompt_sha, "git_sha": sha,
            "max_turns": 60, "time_limit_s": a.time_limit, "start": t0, "end": t1, "status": status, "usage": usage, "hermes_version": sbx.health().get("version")}
    events, S = be.build(meta, sse, msgs, log_lines)
    rec = Recorder(out, run_id, case_id, "hermes")
    rec.events = events
    (out / "events.jsonl").write_text("".join(redact(json.dumps(e, sort_keys=True, default=str)) + "\n" for e in events))
    rec.write_trace()
    write_json(raw / "session_messages.json", msgs)
    write_json(raw / "session.json", sess)
    (raw / "sse_events.jsonl").write_text("".join(redact(json.dumps(e, sort_keys=True)) + "\n" for e in sse))
    (raw / "agent_log.txt").write_text(redact("\n".join(log_lines)) + "\n")
    (raw / "background_review_log.txt").write_text(redact("\n".join(review_lines)) + "\n")
    (raw / "output_listing.txt").write_text(listing)
    (raw / "task_input.txt").write_text(d["task_input"])
    api = be.parse_api_calls(log_lines)
    fsc_ok = None if fsc is None else bool(fsc.get("ok"))
    summary = {"run_id": run_id, "case_id": case_id, "variant": "hermes", "runtime": "hermes", "hermes_run_id": hid, "hermes_version": meta["hermes_version"],
               "model_id": api[0]["model"] if api else sess.get("model"), "temperature": None, "prompt_sha256": prompt_sha, "git_sha": sha, "git_dirty": dirty,
               "started": datetime.fromtimestamp(t0, timezone.utc).isoformat(), "max_turns": 60, **be.derived_fields(S),
               "retries": retries, "status": status, "hermes_stream_state": state,
               "files_copied": sorted(got), "final_self_check": (None if fsc is None else {
                   "ok": fsc_ok, "n_errors": fsc.get("n_errors"), "n_warnings": fsc.get("n_warnings"),
                   "failed": [c["id"] for c in fsc.get("checks", []) if not c["pass"] and c["severity"] == "error"],
                   "warnings": [c["id"] for c in fsc.get("checks", []) if not c["pass"] and c["severity"] == "warn"], "source": "harness_after_run"}),
               "agent_last_self_check_ok": (S["self_checks"][-1]["ok"] if S["self_checks"] else None),
               "reset_before_run": d["reset"], "persisted_after_run": persisted, "session_message_count": sess.get("message_count"),
               "background_review": review, "audit_events": len(audit), "audit_background": sum(1 for x in audit if x["tag"] == "background"), "audit_post_run": sum(1 for x in audit if x["tag"] == "post_run"),
               "audit_denied_run": sum(1 for x in audit if x["tag"] == "run" and x["result"] == "denied"),
               "seconds": round(t1 - t0, 1)}
    write_json(out / "summary.json", summary)
    write_json(out / "persistence.json", {"reset_before_run": d["reset"], "differs_from_baseline_after_run": persisted,
                                           "note": "baseline = sandbox/state_baseline.json; reset_state() wipes all of this before the next run"})
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case")
    ap.add_argument("--cases", help="'pilot' or a comma list")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--time-limit", type=int, default=900, help="seconds per run before the run is stopped")
    ap.add_argument("--review-grace", type=float, default=30.0, help="seconds to wait for a post-run background review to start before assuming there is none")
    a = ap.parse_args(argv)
    man = json.loads((ROOT / "data" / "manifest.json").read_text())
    cases = [a.case] if a.case else (man["pilot_cases"] if a.cases in (None, "pilot") else a.cases.split(","))
    base = a.run_id or "hermes-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    if not wait_health(20):
        sys.exit("Hermes API on 8642 does not answer (is the sandbox running and the forward started?)")
    tok = sbx.token()
    for r in range(1, a.repeats + 1):
        run_id = f"{base}-r{r}"
        for cid in cases:
            out = ROOT / "runs" / run_id / cid
            if a.resume and (out / "summary.json").exists():
                print(run_id, cid, "skipped (finished)", flush=True)
                continue
            out.mkdir(parents=True, exist_ok=True)
            retries = 0
            while True:
                state, d = run_once(run_id, cid, a, tok, out)
                if state in ("stream_lost", "failed") and retries == 0 and not d["sse"][-1:] == [] and not any(e.get("event") == "run.completed" for e in d["sse"]):
                    retries += 1                           # gateway restart / dropped stream: wait for the API, then retry once from a clean state
                    write_json(out / f"attempt1_{state}_sse.json", d["sse"])
                    print(run_id, cid, f"attempt 1 {state}; waiting for the gateway and retrying once", flush=True)
                    if not wait_health(150):
                        break
                    tok = sbx.token()
                    continue
                break
            s = finish_run(run_id, cid, a, tok, out, state, d, retries)
            fs = s["final_self_check"]
            print(run_id, cid, s["status"], f"turns={s['turns']} tools={s['tool_calls_total']} rev={s['revisions']} errs={s['tool_errors']} "
                  f"tok={s['usage']['total_tokens']} final_self_check={None if fs is None else fs['ok']} persisted={bool(s['persisted_after_run'])} {s['seconds']}s", flush=True)
    sbx.reset_state(cases[-1], tok)                          # leave the sandbox clean
    print("sandbox reset to baseline")


if __name__ == "__main__":
    main()
