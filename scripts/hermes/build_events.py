"""Turn one Hermes run (SSE events + session messages + agent.log lines + audit events) into the repo's recording schema
(docs/EVENTS_SPEC.md): events.jsonl, trace.json, plus summary numbers. Pure functions: no network, no sandbox access.

Mapping (see EVENTS_SPEC "Hermes runs"):
  assistant message            -> model_request + model_response   (usage/latency from agent.log `API call #k`, matched by order)
  terminal call to run_skill   -> tool_call / tool_result named after the SKILL (parsed from the wrapper command);
                                  data keeps hermes_tool="terminal", `command` (raw) and `skill`
  any other Hermes tool        -> tool_call / tool_result named after the Hermes tool (write_file, skill_view, ...)
  self_check skill result      -> an extra `self_check` event (phase "proposal", the last one "final")
  failing self_check followed by another self_check -> `revision` event (inferred: Hermes has no harness-driven revision)
"""
import json
import re
import shlex
from datetime import datetime, timezone

WRAP = re.compile(r"/usr/local/share/appeals/bin/run_skill\s+(C-\d{4})\s+([a-z_]+)(?:\s+(.*))?$", re.S)
API_CALL = re.compile(r"API call #(\d+): model=(\S+) provider=(\S+) in=(\d+) out=(\d+) total=(\d+) latency=([\d.]+)s(?: cache=(\d+)/(\d+))?")
BACKGROUND_HOSTS = ("github.com", "raw.githubusercontent.com", "openrouter.ai", "nousresearch.com", "nousresearch.github.io")   # *.github.com matches nousresearch.github.io too
SKILLS = ("parse_denial_eob", "retrieve_payer_policy", "pull_clinical_notes", "assess_appealability", "draft_deliverable", "self_check")


def iso(epoch):
    return datetime.fromtimestamp(float(epoch), timezone.utc).isoformat(timespec="milliseconds")


def parse_skill_command(cmd):
    """'.../run_skill C-0005 pull_clinical_notes '{"paths": [...]}'' -> (skill, args object or raw string) or None."""
    m = WRAP.search(cmd or "")
    if not m or m.group(2) not in SKILLS:
        return None
    raw = (m.group(3) or "").strip()
    try:
        tokens = shlex.split(raw)
    except ValueError:
        tokens = [raw]
    text = tokens[0] if tokens else "{}"
    try:
        return m.group(2), json.loads(text)
    except ValueError:
        return m.group(2), raw


def parse_api_calls(lines):
    out = []
    for ln in lines:
        m = API_CALL.search(ln)
        if m:
            out.append({"n": int(m[1]), "model": m[2], "provider": m[3], "in": int(m[4]), "out": int(m[5]), "total": int(m[6]),
                        "latency_s": float(m[7]), "cached": int(m[8]) if m[8] else None})
    return out


def _json(s):
    """Parse JSON; for tool output also accept a leading JSON object followed by text (Hermes appends a free-text hint to failed terminal results)."""
    try:
        return json.loads(s)
    except (TypeError, ValueError):
        pass
    try:
        obj, _ = json.JSONDecoder().raw_decode(s.lstrip())
        return obj
    except (TypeError, ValueError, AttributeError):
        return None


MALFORMED_MARKS = ("syntax error", "unexpected eof", "unterminated quoted", "json_invalid", "invalid json")


def _snip(s, n=4000):
    return s if len(s) <= n else s[:n]


def classify_audit(ev):
    """Tag an export_audit event: `background` = Hermes' own denied calls to github.com / openrouter.ai (not caused by the run)."""
    tgt = (ev.get("target") or "")
    if ev.get("result") == "denied" and any(h in tgt for h in BACKGROUND_HOSTS):
        return "background"
    return "run"


def build(meta, sse, messages, agent_log):
    """meta: run_id, case_id, hermes_run_id, model, prompt_sha256, git_sha, max_turns, time_limit_s, start, end (epoch), status, usage (run.completed).
    -> (events, summary_bits)"""
    run_id, case_id = meta["run_id"], meta["case_id"]
    events, seq = [], [0]

    def emit(kind, name, ts, status="ok", duration_ms=0, data=None):
        seq[0] += 1
        events.append({"seq": seq[0], "ts": iso(ts), "run_id": run_id, "case_id": case_id, "variant": "hermes", "kind": kind, "name": name,
                       "status": status, "duration_ms": int(duration_ms), "data": data or {}})

    api = parse_api_calls(agent_log)
    tool_dur = {}                                   # FIFO of SSE durations per tool name
    for e in sse:
        if e.get("event") == "tool.completed":
            tool_dur.setdefault(e.get("tool"), []).append((float(e.get("duration") or 0), bool(e.get("error"))))
    model_id = api[0]["model"] if api else meta.get("model")
    emit("run_start", "run_start", meta["start"], data={
        "model": model_id, "temperature": None, "prompt_sha256": meta["prompt_sha256"], "git_sha": meta.get("git_sha"), "max_turns": meta.get("max_turns"),
        "time_limit_s": meta.get("time_limit_s"), "tools": list(SKILLS), "runtime": "hermes", "hermes_run_id": meta["hermes_run_id"], "hermes_version": meta.get("hermes_version"),
        **({"attack_id": meta["attack_id"], "attack_mode": meta.get("attack_mode")} if meta.get("attack_id") else {})})
    S = {"turns": 0, "tool_calls_total": 0, "skill_calls_total": 0, "skill_errors": 0, "tool_errors": 0, "tool_calls_by_name": {}, "hermes_tools_by_name": {},
         "malformed_calls": 0, "path_guard_denials": 0, "self_checks": [], "revisions": 0, "n_api_calls_logged": len(api), "files_written_by_agent": [],
         "terminal_non_skill": 0, "args_via_shell_expansion": 0, "latency_s": [x["latency_s"] for x in api]}
    pending, results_by_id, n_msgs, chars, prev_ts = {}, {}, 0, 0, meta["start"]
    msgs = [m for m in messages if m.get("role") in ("user", "assistant", "tool")]
    for m in msgs:
        if m["role"] == "tool":
            results_by_id[m.get("tool_call_id")] = m
    sc_idx = []                                     # indexes into events of self_check events, for phase fix-up
    for m in msgs:
        ts = m.get("timestamp") or prev_ts
        if m["role"] == "user":
            n_msgs += 1
            chars += len(str(m.get("content") or ""))
            prev_ts = ts
            continue
        if m["role"] == "assistant":
            S["turns"] += 1
            turn = S["turns"]
            a = api[turn - 1] if turn <= len(api) else None
            calls = m.get("tool_calls") or []
            described = []
            for c in calls:
                fn = c.get("function") or {}
                hname, raw = fn.get("name"), fn.get("arguments") or ""
                args = _json(raw)
                skill = None
                if hname == "terminal" and isinstance(args, dict):
                    ps = parse_skill_command(args.get("command", ""))
                    skill = ps[0] if ps else None
                described.append({"id": c.get("id"), "name": skill or hname, "hermes_tool": hname, "skill": skill, "arguments": raw})
            emit("model_request", "model_request", max(prev_ts, ts - (a["latency_s"] if a else 0)),
                 data={"turn": turn, "attempt": 1, "n_messages": n_msgs, "n_tools": None, "approx_chars": chars})
            usage = ({"prompt_tokens": a["in"], "completion_tokens": a["out"], "total_tokens": a["total"], "cached_tokens": a["cached"]} if a else None)
            emit("model_response", "model_response", ts, "ok", (a["latency_s"] * 1000) if a else 0, {
                "turn": turn, "attempt": 1, "ok": True, "content": m.get("content") or None, "tool_calls": described, "usage": usage,
                "finish_reason": m.get("finish_reason"), "reasoning_chars": len(m.get("reasoning") or m.get("reasoning_content") or "")})
            n_msgs += 1
            chars += len(str(m.get("content") or "")) + sum(len(d["arguments"]) for d in described)
            prev_ts = ts
            for c, d in zip(calls, described):
                args = _json(d["arguments"])
                hname = d["hermes_tool"]
                data = {"tool_call_id": d["id"], "name": d["name"], "hermes_tool": hname}
                if d["skill"]:
                    ps = parse_skill_command(args.get("command", ""))
                    data.update({"skill": d["skill"], "arguments": ps[1], "command": args.get("command")})
                    S["skill_calls_total"] += 1
                    S["tool_calls_by_name"][d["skill"]] = S["tool_calls_by_name"].get(d["skill"], 0) + 1
                    if isinstance(ps[1], str) and "$(" in ps[1]:
                        S["args_via_shell_expansion"] += 1             # e.g. "$(cat /tmp/args.json)": valid, but the arguments are not visible in the command
                else:
                    data["arguments"] = args if args is not None else d["arguments"]
                    S["hermes_tools_by_name"][hname] = S["hermes_tools_by_name"].get(hname, 0) + 1
                    if hname == "terminal":
                        S["terminal_non_skill"] += 1
                    if hname in ("write_file", "patch") and isinstance(args, dict):
                        S["files_written_by_agent"].append(args.get("path") or args.get("file_path"))
                S["tool_calls_total"] += 1
                emit("tool_call", d["name"], ts, data=data)
                pending[d["id"]] = (d, data)
                r = results_by_id.get(d["id"])
                rts = (r.get("timestamp") if r else None) or ts
                dur_s, sse_err = (tool_dur.get(hname) or [(max(0.0, rts - ts), False)]).pop(0) if tool_dur.get(hname) else (max(0.0, rts - ts), False)
                content = (r or {}).get("content") or ""
                status, result = "ok", content
                out_obj = None
                if hname == "terminal":
                    wrapped = _json(content)
                    if isinstance(wrapped, dict) and "output" in wrapped:
                        result = wrapped.get("output") or ""
                        if wrapped.get("exit_code") not in (0, None) or wrapped.get("error"):
                            status = "error"
                    if d["skill"]:
                        out_obj = _json(result)
                        err = out_obj.get("error") if isinstance(out_obj, dict) else None
                        if err:
                            status = "denied" if (isinstance(err, dict) and err.get("code") == "access_denied") else "error"
                else:
                    wrapped = _json(content)
                    if sse_err or (isinstance(wrapped, dict) and wrapped.get("error")):
                        status = "error"
                if r is None:
                    status = "error"
                if d["skill"] and any(k in (result if isinstance(result, str) else "").lower() for k in MALFORMED_MARKS) and not isinstance(out_obj, dict):
                    S["malformed_calls"] += 1                           # the command never reached the skill (shell quoting broke) or the skill rejected the JSON
                    data["malformed"] = True
                    status = "error"
                if status == "error":
                    S["tool_errors"] += 1
                    S["skill_errors"] += 1 if d["skill"] else 0
                if status == "denied":
                    S["path_guard_denials"] += 1
                    S["tool_errors"] += 1
                    S["skill_errors"] += 1
                rts_emit = max(rts, ts)
                emit("tool_result", d["name"], rts_emit, status, dur_s * 1000, {
                    "tool_call_id": d["id"], "name": d["name"], "hermes_tool": hname, "status": status, "result_chars": len(result), "truncated": len(result) > 4000,
                    "result": _snip(result)})
                chars += len(content)
                if d["skill"] == "self_check" and isinstance(out_obj, dict) and "checks" in out_obj:
                    failed = [c for c in out_obj["checks"] if not c["pass"] and c["severity"] == "error"]
                    info = {"phase": "proposal", "ok": bool(out_obj.get("ok")), "n_errors": out_obj.get("n_errors"), "n_warnings": out_obj.get("n_warnings"),
                            "failed": [{"id": c["id"], "detail": c["detail"], "hint": c["hint"]} for c in failed[:12]],
                            "warnings": [c["id"] for c in out_obj["checks"] if not c["pass"] and c["severity"] == "warn"], "source": "agent_call"}
                    emit("self_check", "self_check", rts_emit, "ok" if info["ok"] else "error", dur_s * 1000, info)
                    sc_idx.append(len(events) - 1)
                    S["self_checks"].append({"ok": info["ok"], "n_errors": info["n_errors"], "failed": [f["id"] for f in info["failed"]]})
    # last self_check call is the "final" one; a failing self_check followed by another one is a (model-driven) revision
    if sc_idx:
        events[sc_idx[-1]]["data"]["phase"] = "final"
    rev_events = []
    for i, idx in enumerate(sc_idx[:-1]):
        d = events[idx]["data"]
        if not d["ok"]:
            S["revisions"] += 1
            rev_events.append((idx, {"n": S["revisions"], "failed_ids": [f["id"] for f in d["failed"]], "inferred": True,
                                    "reason": "; ".join(f"{f['id']}: {f['detail']}" for f in d["failed"])[:1500]}))
    for off, (idx, data) in enumerate(rev_events):          # insert after the failing self_check
        ev = events[idx + off]
        events.insert(idx + off + 1, {"seq": 0, "ts": ev["ts"], "run_id": run_id, "case_id": case_id, "variant": "hermes", "kind": "revision", "name": "revision",
                                      "status": "ok", "duration_ms": 0, "data": data})
    usage = meta.get("usage") or {}
    S["usage"] = {"prompt_tokens": sum(x["in"] for x in api) or usage.get("input_tokens", 0), "completion_tokens": sum(x["out"] for x in api) or usage.get("output_tokens", 0),
                  "total_tokens": sum(x["total"] for x in api) or usage.get("total_tokens", 0), "cached_tokens": sum(x["cached"] or 0 for x in api),
                  "first_call_prompt_tokens": api[0]["in"] if api else None, "run_completed_usage": usage}
    emit("run_end", "run_end", meta["end"], "ok" if meta["status"] == "submitted" else "error", (meta["end"] - meta["start"]) * 1000,
         {"status": meta["status"], "turns": S["turns"], "tool_calls": S["tool_calls_total"], "usage": S["usage"], "revisions": S["revisions"],
          **({"attack_id": meta["attack_id"], "attack_mode": meta.get("attack_mode")} if meta.get("attack_id") else {})})
    for i, e in enumerate(events, 1):
        e["seq"] = i
    return events, S


def add_scripted_step(events, sc, meta):
    """Insert the harness-run (scripted) attack command as a labeled terminal tool_call/tool_result pair just before run_end (attack_mode "scripted")."""
    cid = "scripted-1"
    out = (sc["stdout"] + sc["stderr"]).strip()
    base = {"run_id": meta["run_id"], "case_id": meta["case_id"], "variant": "hermes"}
    call = {**base, "seq": 0, "ts": iso(sc["ts_start"]), "kind": "tool_call", "name": "terminal", "status": "ok", "duration_ms": 0,
            "data": {"tool_call_id": cid, "name": "terminal", "hermes_tool": "terminal", "command": sc["command"], "arguments": {"command": sc["command"]}, "scripted": True, "attack_mode": "scripted"}}
    res = {**base, "seq": 0, "ts": iso(sc["ts_end"]), "kind": "tool_result", "name": "terminal", "status": "ok" if sc["rc"] == 0 else "error",
           "duration_ms": int((sc["ts_end"] - sc["ts_start"]) * 1000),
           "data": {"tool_call_id": cid, "name": "terminal", "hermes_tool": "terminal", "status": "ok" if sc["rc"] == 0 else "error", "result_chars": len(out), "truncated": False,
                    "result": _snip(out), "exit_code": sc["rc"], "scripted": True, "attack_mode": "scripted"}}
    evs = events[:-1] + [call, res] + events[-1:]
    for i, e in enumerate(evs, 1):
        e["seq"] = i
    return evs


def audit_window(raw_events, start, end, review_end=None, pad_before=2.0, pad_after=3.0):
    """Keep export_audit events from the run start to the end of Hermes' post-run background review and tag each with `tag`:
    'background' (Hermes' own denied github.com / openrouter.ai / nousresearch calls), 'post_run' (after the run ended: the review fork's traffic), else 'run'."""
    out = []
    for e in raw_events:
        t = datetime.fromisoformat(e["ts"].replace("Z", "+00:00")).timestamp()
        if start - pad_before <= t <= (review_end or end) + pad_after:
            tag = classify_audit(e)
            if tag == "run" and t > end + pad_after:
                tag = "post_run"
            out.append({**e, "tag": tag})
    return out


def derived_fields(S):
    """The summary.json keys that come from the built trace (shared by run_case.py and rebuild_events.py)."""
    return {"turns": S["turns"], "tool_calls_by_name": S["tool_calls_by_name"], "hermes_tools_by_name": S["hermes_tools_by_name"], "tool_calls_total": S["tool_calls_total"],
            "skill_calls_total": S["skill_calls_total"], "tool_errors": S["tool_errors"], "skill_errors": S["skill_errors"], "malformed_calls": S["malformed_calls"],
            "args_via_shell_expansion": S["args_via_shell_expansion"], "path_guard_denials": S["path_guard_denials"], "terminal_non_skill_calls": S["terminal_non_skill"],
            "revisions": S["revisions"], "self_check_calls": S["self_checks"], "usage": S["usage"], "latency_s": S["latency_s"], "n_api_calls_logged": S["n_api_calls_logged"],
            "files_written_by_agent": S["files_written_by_agent"]}
