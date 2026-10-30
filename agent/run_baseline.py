"""No-tools baseline: the same agent model, ONE prompt with task.md, all of the case's documents and the whole policy library pasted in,
the same output instructions and decision.json schema. Same recording and layout as agent/run_case.py:
runs/<run-id>/baseline/<case_id>/{deliverable.md, decision.json, events.jsonl, trace.json, summary.json, final_self_check.json}.

  python -m agent.run_baseline --cases pilot --run-id NAME [--temperature T] [--dry-run]"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from agent.events import Recorder
from agent.fake_model import text_response
from agent.final import parse_final
from agent.model_client import HostedModel, ModelFailure, load_models
from agent.run_case import FORMAT_NUDGE, RETRY_NUDGE, ROOT, add_usage, git_state, prompt_hash, run_self_check
from agent.staging import stage_case
from agent.tools import ToolRunner

PROMPT = ROOT / "agent" / "prompts" / "baseline.md"


def build_user_message(case_root, policy_root):
    parts = [(case_root / "task.md").read_text(), "\n# CASE DOCUMENTS"]
    for p in sorted((case_root / "docs").rglob("*")):
        if p.is_file():
            parts.append(f"===== FILE: {p.relative_to(case_root / 'docs').as_posix()} =====\n{p.read_text()}")
    parts.append("\n# PAYER POLICY LIBRARY")
    for p in sorted(policy_root.glob("*.txt")):
        parts.append(f"===== FILE: policy_library/{p.name} =====\n{p.read_text()}")
    return "\n".join(parts)


def run_baseline_case(model, case_id, data_root, run_dir, run_id, max_attempts=3):
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    case_root, policy_root = stage_case(data_root, case_id, run_dir / "staged")
    rec = Recorder(run_dir, run_id, case_id, "baseline")
    runner = ToolRunner(case_root, policy_root, run_dir / "skills_events.jsonl", run_id, case_id)
    sha, dirty = git_state()
    summary = {"run_id": run_id, "case_id": case_id, "variant": "baseline", "model_id": model.model, "temperature": model.temperature, "max_tokens": model.max_tokens,
               "prompt_sha256": prompt_hash(PROMPT), "git_sha": sha, "git_dirty": dirty, "started": datetime.now(timezone.utc).isoformat(), "turns": 0,
               "tool_calls_by_name": {}, "tool_calls_total": 0, "tool_errors": 0, "malformed_calls": 0, "malformed_final": 0, "model_failures": [], "revisions": 0,
               "usage": {}, "latency_s": [], "path_guard_denials": 0, "proposal_self_checks": [], "final_self_check": None, "status": None, "files_written": []}
    rec.emit("run_start", "run_start", data={"model": model.model, "temperature": model.temperature, "prompt_sha256": summary["prompt_sha256"], "git_sha": sha, "tools": []})
    messages = [{"role": "system", "content": PROMPT.read_text()}, {"role": "user", "content": build_user_message(case_root, policy_root)}]
    final, status = None, None
    for attempt in range(1, max_attempts + 1):
        summary["turns"] = attempt
        req = messages if not (attempt > 1 and messages[-1]["role"] != "user") else messages
        rec.emit("model_request", "model_request", data={"turn": attempt, "attempt": attempt, "n_messages": len(req), "n_tools": 0, "approx_chars": sum(len(m["content"]) for m in req)})
        try:
            resp = model.chat(req, None)
        except ModelFailure as e:
            summary["model_failures"].append({"turn": attempt, "attempt": attempt, "kind": e.kind})
            rec.emit("model_response", "model_response", "error", 0, {"turn": attempt, "attempt": attempt, "ok": False, "error": f"{e.kind}: {e}"[:200]})
            time.sleep(0 if model.model in ("scripted-fake", "dry-run-fake") else 1.5 * attempt)
            continue
        text = resp.message.get("content") or ""
        add_usage(summary["usage"], resp.usage)
        summary["latency_s"].append(round(resp.secs, 2))
        rec.emit("model_response", "model_response", "ok" if text.strip() else "error", resp.secs * 1000,
                 {"turn": attempt, "attempt": attempt, "ok": bool(text.strip()), "content": text, "finish_reason": resp.finish_reason, "usage": resp.usage, "tool_calls": []})
        final = parse_final(text)
        if final:
            break
        summary["malformed_final"] += 1
        messages = messages + [{"role": "assistant", "content": text}, {"role": "user", "content": FORMAT_NUDGE if text.strip() else RETRY_NUDGE}]
    if final:
        (run_dir / "deliverable.md").write_text(final[0])
        (run_dir / "decision.json").write_text(final[1])
        summary["files_written"] = ["deliverable.md", "decision.json"]
        info, full = run_self_check(runner, rec, final[0], final[1], "final")
        summary["final_self_check"] = {"ok": info["ok"], "n_errors": info["n_errors"], "n_warnings": info["n_warnings"], "failed": [f["id"] for f in info["failed"]], "warnings": info["warnings"]}
        (run_dir / "final_self_check.json").write_text(json.dumps(full, indent=1, sort_keys=True) + "\n")
        status = "submitted"
    else:
        status = "model_failure" if summary["model_failures"] and not summary["latency_s"] else "no_final"
    summary["status"], summary["seconds"] = status, round(time.time() - started, 1)
    rec.emit("run_end", "run_end", "ok" if status == "submitted" else "error", summary["seconds"] * 1000, {"status": status, "turns": summary["turns"], "tool_calls": 0, "usage": summary["usage"], "revisions": 0})
    rec.write_trace()
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--case")
    ap.add_argument("--cases")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    cfg = load_models()
    man = json.loads((Path(a.data) / "manifest.json").read_text())
    cases = [a.case] if a.case else (man["pilot_cases"] if a.cases in (None, "pilot") else a.cases.split(","))
    run_id = a.run_id or ("dry-" if a.dry_run else "agent-") + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    for cid in cases:
        out = ROOT / "runs" / run_id / "baseline" / cid
        if a.resume and (out / "summary.json").exists():
            print(cid, "skipped (finished)")
            continue
        if a.dry_run:
            from agent.fake_model import ScriptedModel
            model = ScriptedModel([text_response("not in the required format")] * 3)
        else:
            model = HostedModel(cfg, a.temperature)
        s = run_baseline_case(model, cid, a.data, out, run_id)
        print(run_id, "baseline", cid, s["status"], f"calls={s['turns']} fail={len(s['model_failures'])} {s['seconds']}s", flush=True)


if __name__ == "__main__":
    main()
