"""Pre-sandbox agent runner: a plain tool-calling loop that drives the six skills with the agent model (hosted endpoint) on staged cases.
NOT the Hermes integration. The tool interface is the skills' own JSON schema, so the later port is a mapping.

  python -m agent.run_case --cases pilot --repeats 2 [--run-id NAME] [--temperature T] [--resume] [--dry-run]
  python -m agent.run_case --case C-0005 --repeats 1

Each repeat is its own run id (<run-id>-r1, <run-id>-r2): runs/<run-id>-rN/<case_id>/{deliverable.md, decision.json, events.jsonl, trace.json,
summary.json, skills_events.jsonl, final_self_check.json, staged/}. The agent sees only runs/.../staged/ (task.md, docs/**, policy library)
through the skills' path guard; truth.json, rubric.json, gold/ and attacks/ are never read."""
import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from agent.events import Recorder, snip
from agent.fake_model import DryRunModel
from agent.final import parse_final
from agent.model_client import HostedModel, ModelFailure, load_models
from agent.staging import stage_case
from agent.tools import ToolRunner, tool_specs

ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / "agent" / "prompts" / "system.md"
FORMAT_NUDGE = ("Your reply was not a tool call and not in the required final format. Either call a tool, or send the final answer exactly as "
                "<<<DELIVERABLE>>> ... <<<DECISION>>> ... <<<END>>> with the full deliverable.md and the decision.json JSON.")
RETRY_NUDGE = "Your previous response was empty or malformed. Reply with a valid tool call or with the final answer in the required format."


def git_state():
    try:
        sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip())
        return sha, dirty
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, None


def prompt_hash(*files):
    h = hashlib.sha256()
    for f in files:
        h.update(Path(f).read_bytes())
    return h.hexdigest()


def add_usage(total, u):
    for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
        total[k] = total.get(k, 0) + int((u or {}).get(k, 0) or 0)
    det = (u or {}).get("completion_tokens_details") or {}
    total["reasoning_tokens"] = total.get("reasoning_tokens", 0) + int(det.get("reasoning_tokens", 0) or 0)


def run_self_check(runner, rec, deliverable, decision, phase):
    t0 = time.time()
    text, status, _ = runner.execute("self_check", {"deliverable_text": deliverable, "decision_text": decision})
    try:
        r = json.loads(text)
    except ValueError:
        r = {"error": {"message": text[:200]}}
    failed = [c for c in r.get("checks", []) if not c["pass"] and c["severity"] == "error"]
    info = {"phase": phase, "ok": bool(r.get("ok")), "n_errors": r.get("n_errors"), "n_warnings": r.get("n_warnings"),
            "failed": [{"id": c["id"], "detail": c["detail"], "hint": c["hint"]} for c in failed[:12]],
            "warnings": [c["id"] for c in r.get("checks", []) if not c["pass"] and c["severity"] == "warn"]}
    rec.emit("self_check", "self_check", "ok" if r.get("ok") else "error", (time.time() - t0) * 1000, info)
    return info, r


def run_case(model, case_id, data_root, run_dir, run_id, max_turns=14, time_limit=900, max_revisions=2, variant="agent", system_prompt=None):
    """Run one case. Returns the summary dict (also written to summary.json)."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    case_root, policy_root = stage_case(data_root, case_id, run_dir / "staged")
    rec = Recorder(run_dir, run_id, case_id, variant)
    sk_events = run_dir / "skills_events.jsonl"
    if sk_events.exists():
        sk_events.unlink()
    runner = ToolRunner(case_root, policy_root, sk_events, run_id, case_id)
    sysmsg = system_prompt or PROMPT.read_text()
    sha, dirty = git_state()
    summary = {"run_id": run_id, "case_id": case_id, "variant": variant, "model_id": model.model, "temperature": model.temperature, "max_tokens": model.max_tokens,
               "prompt_sha256": prompt_hash(PROMPT) if system_prompt is None else hashlib.sha256(sysmsg.encode()).hexdigest(), "git_sha": sha, "git_dirty": dirty,
               "started": datetime.now(timezone.utc).isoformat(), "max_turns": max_turns, "turns": 0, "tool_calls_by_name": {}, "tool_calls_total": 0, "tool_errors": 0,
               "malformed_calls": 0, "malformed_final": 0, "model_failures": [], "revisions": 0, "usage": {}, "latency_s": [], "path_guard_denials": 0,
               "proposal_self_checks": [], "final_self_check": None, "status": None, "files_written": []}
    rec.emit("run_start", "run_start", data={"model": model.model, "temperature": model.temperature, "prompt_sha256": summary["prompt_sha256"], "git_sha": sha,
                                             "max_turns": max_turns, "time_limit_s": time_limit, "tools": [t["function"]["name"] for t in tool_specs()]})
    task = (case_root / "task.md").read_text()
    messages = [{"role": "system", "content": sysmsg}, {"role": "user", "content": task}]
    tools = tool_specs()
    proposal, status = None, None
    while status is None:
        if summary["turns"] >= max_turns:
            status = "max_turns"
            break
        if time.time() - started > time_limit:
            status = "time_limit"
            break
        summary["turns"] += 1
        turn, resp = summary["turns"], None
        for attempt in range(1, 4):
            req = messages if attempt == 1 else messages + [{"role": "user", "content": RETRY_NUDGE}]
            rec.emit("model_request", "model_request", data={"turn": turn, "attempt": attempt, "n_messages": len(req), "n_tools": len(tools), "approx_chars": sum(len(str(m.get("content") or "")) for m in req)})
            try:
                resp = model.chat(req, tools)
            except ModelFailure as e:
                summary["model_failures"].append({"turn": turn, "attempt": attempt, "kind": e.kind})
                rec.emit("model_response", "model_response", "error", 0, {"turn": turn, "attempt": attempt, "ok": False, "error": f"{e.kind}: {e}"[:200]})
                time.sleep(0 if getattr(model, "model", "").endswith("fake") or model.model in ("scripted-fake", "dry-run-fake") else 1.5 * attempt)
                continue
            m = resp.message
            empty = not m.get("tool_calls") and not (m.get("content") or "").strip()
            add_usage(summary["usage"], resp.usage)
            summary["latency_s"].append(round(resp.secs, 2))
            rec.emit("model_response", "model_response", "error" if empty else "ok", resp.secs * 1000,
                     {"turn": turn, "attempt": attempt, "ok": not empty, "content": m.get("content"), "finish_reason": resp.finish_reason, "usage": resp.usage,
                      "tool_calls": [{"id": c["id"], "name": c["function"]["name"], "arguments": c["function"]["arguments"]} for c in m.get("tool_calls", []) or []]})
            if empty:
                summary["model_failures"].append({"turn": turn, "attempt": attempt, "kind": "empty"})
                resp = None
                continue
            break
        if resp is None:
            status = "model_failure"
            break
        m = resp.message
        calls = m.get("tool_calls") or []
        if calls:
            messages.append({"role": "assistant", "content": m.get("content"), "tool_calls": calls})
            for c in calls:
                name, raw = c["function"]["name"], c["function"]["arguments"]
                args, perr = runner.parse_arguments(raw)
                rec.emit("tool_call", name, data={"tool_call_id": c["id"], "name": name, "arguments": args if args is not None else raw})
                t0 = time.time()
                if perr:
                    result, st, meta = (json.dumps({"error": {"code": "bad_input", "message": perr + "; send arguments as one JSON object"}}), "error", {"truncated": False, "result_chars": 0, "malformed": True})
                else:
                    result, st, meta = runner.execute(name, args)
                summary["tool_calls_total"] += 1
                summary["tool_calls_by_name"][name] = summary["tool_calls_by_name"].get(name, 0) + 1
                summary["malformed_calls"] += 1 if meta.get("malformed") else 0
                summary["tool_errors"] += 1 if st != "ok" else 0
                summary["path_guard_denials"] += 1 if st == "denied" else 0
                rec.emit("tool_result", name, st, (time.time() - t0) * 1000, {"tool_call_id": c["id"], "name": name, "status": st, "result_chars": meta["result_chars"],
                                                                              "truncated": meta["truncated"], "result": result[:4000]})
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": result})
            continue
        text = m.get("content") or ""
        final = parse_final(text)
        if final is None:
            summary["malformed_final"] += 1
            messages.append({"role": "assistant", "content": text})
            messages.append({"role": "user", "content": FORMAT_NUDGE})
            continue
        deliverable, decision = final
        info, _ = run_self_check(runner, rec, deliverable, decision, "proposal")
        summary["proposal_self_checks"].append({"ok": info["ok"], "n_errors": info["n_errors"], "failed": [f["id"] for f in info["failed"]]})
        proposal = (deliverable, decision)
        if not info["ok"] and summary["revisions"] < max_revisions:
            summary["revisions"] += 1
            reason = "; ".join(f"{f['id']}: {f['detail']} (hint: {f['hint']})" for f in info["failed"])
            rec.emit("revision", "revision", data={"n": summary["revisions"], "reason": reason[:1500], "failed_ids": [f["id"] for f in info["failed"]]})
            messages.append({"role": "assistant", "content": text})
            messages.append({"role": "user", "content": "Revision request. The deterministic self_check found these problems with your answer:\n" + "\n".join(
                f"- {f['id']}: {f['detail']}. Hint: {f['hint']}" for f in info["failed"]) + "\nFix them (call tools if you need facts) and send the COMPLETE final answer again in the required format."})
            continue
        status = "submitted"
    # ---- finish: write whatever was proposed; record (not enforce) a final self_check
    if proposal is not None:
        (run_dir / "deliverable.md").write_text(proposal[0])
        (run_dir / "decision.json").write_text(proposal[1])
        summary["files_written"] = ["deliverable.md", "decision.json"]
        info, full = run_self_check(runner, rec, proposal[0], proposal[1], "final")
        summary["final_self_check"] = {"ok": info["ok"], "n_errors": info["n_errors"], "n_warnings": info["n_warnings"], "failed": [f["id"] for f in info["failed"]], "warnings": info["warnings"]}
        (run_dir / "final_self_check.json").write_text(json.dumps(full, indent=1, sort_keys=True) + "\n")
        if status != "submitted":
            status = f"{status}_with_proposal"
    summary["status"] = status
    summary["seconds"] = round(time.time() - started, 1)
    rec.emit("run_end", "run_end", "ok" if status == "submitted" else "error", summary["seconds"] * 1000,
             {"status": status, "turns": summary["turns"], "tool_calls": summary["tool_calls_total"], "usage": summary["usage"], "revisions": summary["revisions"]})
    rec.write_trace()
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--case")
    ap.add_argument("--cases", help="'pilot' or a comma list")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--max-turns", type=int, default=14)
    ap.add_argument("--time-limit", type=int, default=900)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="scripted fake model (no network, no key)")
    a = ap.parse_args(argv)
    cfg = load_models()
    man = json.loads((Path(a.data) / "manifest.json").read_text())
    cases = [a.case] if a.case else (man["pilot_cases"] if a.cases in (None, "pilot") else a.cases.split(","))
    base = a.run_id or ("dry-" if a.dry_run else "agent-") + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    for r in range(1, a.repeats + 1):
        run_id = f"{base}-r{r}"
        for cid in cases:
            out = ROOT / "runs" / run_id / cid
            if a.resume and (out / "summary.json").exists():
                print(run_id, cid, "skipped (finished)")
                continue
            model = DryRunModel() if a.dry_run else HostedModel(cfg, a.temperature)
            s = run_case(model, cid, a.data, out, run_id, a.max_turns, a.time_limit)
            print(run_id, cid, s["status"], f"turns={s['turns']} tools={s['tool_calls_total']} rev={s['revisions']} fail={len(s['model_failures'])} {s['seconds']}s", flush=True)


if __name__ == "__main__":
    main()
