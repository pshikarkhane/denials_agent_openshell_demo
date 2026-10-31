"""Offline tests for scripts/hermes (no sandbox, no network): command parsing, event/trace building, audit tagging, state diff, log split."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "hermes"))
import build_events as be  # noqa: E402
import run_case as rc  # noqa: E402
import sbx  # noqa: E402

WRAP = "/usr/local/share/appeals/bin/run_skill"


def test_parse_skill_command_variants():
    assert be.parse_skill_command(f"{WRAP} C-0005 parse_denial_eob '{{}}'") == ("parse_denial_eob", {})
    s, a = be.parse_skill_command(f"""{WRAP} C-0005 pull_clinical_notes '{{"paths": ["notes/a.txt"]}}'""")
    assert (s, a) == ("pull_clinical_notes", {"paths": ["notes/a.txt"]})
    s, a = be.parse_skill_command(f"cd /tmp && {WRAP} C-0030 self_check '{{\"deliverable_path\":\"deliverable.md\"}}' 2>&1")
    assert s == "self_check" and isinstance(a, (dict, str))          # trailing redirect must not crash
    assert be.parse_skill_command("ls -la /sandbox") is None
    assert be.parse_skill_command(f"{WRAP} C-0005 not_a_skill '{{}}'") is None
    s, a = be.parse_skill_command(f"{WRAP} C-0005 parse_denial_eob '{{bad json'")
    assert s == "parse_denial_eob" and isinstance(a, str)            # malformed arguments are kept raw (counted as malformed)


def _msg(i, role, ts, **kw):
    return {"id": i, "role": role, "timestamp": ts, "content": kw.pop("content", None), "tool_calls": kw.pop("tool_calls", None),
            "tool_call_id": kw.pop("tool_call_id", None), "tool_name": kw.pop("tool_name", None), "finish_reason": None, "reasoning": None, **kw}


def _call(cid, name, args):
    return {"id": cid, "function": {"name": name, "arguments": json.dumps(args)}}


def _sc(ok):
    checks = [{"id": "section_next_action", "check": "x", "pass": ok, "severity": "error", "detail": "no next action", "hint": "add one"}]
    return json.dumps({"output": json.dumps({"ok": ok, "n_errors": 0 if ok else 1, "n_warnings": 0, "checks": checks}), "exit_code": 0, "error": None})


def test_build_events_maps_skills_selfcheck_and_revision():
    t = 1000.0
    msgs = [
        _msg(1, "user", t, content="task"),
        _msg(2, "assistant", t + 1, tool_calls=[_call("a", "terminal", {"command": f"{WRAP} C-0005 parse_denial_eob '{{}}'"})]),
        _msg(3, "tool", t + 2, tool_call_id="a", tool_name="terminal", content=json.dumps({"output": '{"claim_no": "1"}', "exit_code": 0, "error": None})),
        _msg(4, "assistant", t + 3, tool_calls=[_call("b", "write_file", {"path": "/sandbox/work/output/C-0005/deliverable.md", "content": "x"})]),
        _msg(5, "tool", t + 4, tool_call_id="b", tool_name="write_file", content=json.dumps({"bytes_written": 1})),
        _msg(6, "assistant", t + 5, tool_calls=[_call("c", "terminal", {"command": f"{WRAP} C-0005 self_check '{{}}'"})]),
        _msg(7, "tool", t + 6, tool_call_id="c", tool_name="terminal", content=_sc(False)),
        _msg(8, "assistant", t + 7, tool_calls=[_call("d", "terminal", {"command": f"{WRAP} C-0005 self_check '{{}}'"})]),
        _msg(9, "tool", t + 8, tool_call_id="d", tool_name="terminal", content=_sc(True)),
        _msg(10, "assistant", t + 9, content="done"),
        _msg(11, "tool", t + 9, tool_call_id="e", tool_name="terminal", content="{}"),                      # stray result for an unknown call: ignored
    ]
    sse = [{"event": "tool.completed", "tool": "terminal", "duration": 0.2, "error": False}, {"event": "tool.completed", "tool": "write_file", "duration": 0.1, "error": False},
           {"event": "tool.completed", "tool": "terminal", "duration": 0.3, "error": False}, {"event": "tool.completed", "tool": "terminal", "duration": 0.3, "error": False}]
    log = [f"2026-10-30 22:00:0{i},000 INFO [run_x] agent.conversation_loop: API call #{i}: model=m/x provider=custom in={1000 * i} out=10 total={1000 * i + 10} latency=1.5s" for i in range(1, 6)]
    meta = {"run_id": "r1", "case_id": "C-0005", "hermes_run_id": "run_x", "prompt_sha256": "abc", "start": t, "end": t + 10, "status": "submitted"}
    ev, S = be.build(meta, sse, msgs, log)
    kinds = [e["kind"] for e in ev]
    assert kinds[0] == "run_start" and kinds[-1] == "run_end"
    assert [e["seq"] for e in ev] == list(range(1, len(ev) + 1))
    assert all(set(e) == {"seq", "ts", "run_id", "case_id", "variant", "kind", "name", "status", "duration_ms", "data"} for e in ev)
    calls = [e for e in ev if e["kind"] == "tool_call"]
    assert [c["name"] for c in calls] == ["parse_denial_eob", "write_file", "self_check", "self_check"]
    assert calls[0]["data"]["hermes_tool"] == "terminal" and calls[0]["data"]["command"].startswith(WRAP) and calls[0]["data"]["arguments"] == {}
    res = [e for e in ev if e["kind"] == "tool_result"]
    assert res[0]["data"]["result"] == '{"claim_no": "1"}' and res[0]["duration_ms"] == 200
    sc = [e for e in ev if e["kind"] == "self_check"]
    assert [e["data"]["phase"] for e in sc] == ["proposal", "final"] and [e["data"]["ok"] for e in sc] == [False, True]
    rev = [e for e in ev if e["kind"] == "revision"]
    assert len(rev) == 1 and rev[0]["data"]["failed_ids"] == ["section_next_action"] and rev[0]["data"]["inferred"] is True
    assert ev.index(rev[0]) == ev.index(sc[0]) + 1                                                         # revision directly after the failing self_check
    assert S["revisions"] == 1 and S["turns"] == 5 and S["skill_calls_total"] == 3 and S["hermes_tools_by_name"] == {"write_file": 1}
    assert S["usage"]["first_call_prompt_tokens"] == 1000 and S["usage"]["prompt_tokens"] == 15000
    mr = [e for e in ev if e["kind"] == "model_response"][0]
    assert mr["data"]["tool_calls"][0]["name"] == "parse_denial_eob" and mr["data"]["tool_calls"][0]["hermes_tool"] == "terminal"


def test_skill_error_and_denied_statuses():
    t = 5.0
    err = json.dumps({"output": json.dumps({"error": {"code": "bad_input", "message": "x"}}), "exit_code": 1, "error": None})
    den = json.dumps({"output": json.dumps({"error": {"code": "access_denied", "message": "x"}}), "exit_code": 1, "error": None})
    msgs = [_msg(1, "user", t, content="t"),
            _msg(2, "assistant", t + 1, tool_calls=[_call("a", "terminal", {"command": f"{WRAP} C-0005 pull_clinical_notes '{{}}'"}), _call("b", "terminal", {"command": f"{WRAP} C-0005 pull_clinical_notes '{{}}'"})]),
            _msg(3, "tool", t + 2, tool_call_id="a", tool_name="terminal", content=err), _msg(4, "tool", t + 2, tool_call_id="b", tool_name="terminal", content=den)]
    ev, S = be.build({"run_id": "r", "case_id": "C-0005", "hermes_run_id": "h", "prompt_sha256": "p", "start": t, "end": t + 3, "status": "no_files"}, [], msgs, [])
    st = [e["status"] for e in ev if e["kind"] == "tool_result"]
    assert st == ["error", "denied"] and S["tool_errors"] == 2 and S["path_guard_denials"] == 1
    assert ev[-1]["status"] == "error"                                                                    # run_end not submitted


def test_audit_tagging_and_window():
    t0 = 1_793_400_000.0
    iso = lambda x: be.iso(x).replace("+00:00", "Z")  # noqa: E731
    raw = [{"ts": iso(t0 - 100), "result": "denied", "target": "github.com:443"},        # before the window
           {"ts": iso(t0 + 5), "result": "denied", "target": "github.com:443"},          # Hermes background
           {"ts": iso(t0 + 6), "result": "denied", "target": "openrouter.ai:443"},
           {"ts": iso(t0 + 7), "result": "denied", "target": "collector.invalid:443"},   # a real denial
           {"ts": iso(t0 + 8), "result": "allowed", "target": "POST http://inference-api.nvidia.com:443/v1/chat/completions"},
           {"ts": iso(t0 + 40), "result": "allowed", "target": "POST http://inference-api.nvidia.com:443/v1/chat/completions"}]
    out = be.audit_window(raw, t0, t0 + 20, t0 + 50)
    assert [e["tag"] for e in out] == ["background", "background", "run", "run", "post_run"]
    assert be.classify_audit({"result": "allowed", "target": "github.com:443"}) == "run"                  # only DENIED calls to those hosts are background


def test_split_log_separates_review_calls():
    lines = ["a API call #1: model=m provider=p in=10 out=1 total=11 latency=1.0s", "b Turn ended: reason=text_response",
             "c API call #1: model=m provider=p in=999 out=9 total=1008 latency=1.0s", "d Background review complete: calls=1"]
    main, rest = rc.split_log(lines)
    assert len(main) == 2 and len(rest) == 2
    assert [x["in"] for x in be.parse_api_calls(main)] == [10] and [x["in"] for x in be.parse_api_calls(rest)] == [999]


def test_diff_state_flags_persistence():
    base = {"skills": {"a/SKILL.md": "1", "b/SKILL.md": "2"}, "soul": "s", "tmp": [], "sandbox_top": []}
    clean = {"memories": {}, "skills": dict(base["skills"]), "soul": "s", "workspace": {}, "plans": {}, "hooks": {}, "plugins": {}, "profiles": {}}
    assert sbx.diff_state(clean, base) == {}
    dirty = {**clean, "memories": {"MEMORY.md": "x"}, "skills": {"a/SKILL.md": "9", "new/SKILL.md": "3"}, "soul": "t"}
    d = sbx.diff_state(dirty, base)
    assert d["memories"] == ["MEMORY.md"] and d["skills_added"] == ["new/SKILL.md"] and d["skills_changed"] == ["a/SKILL.md"] and d["skills_removed"] == ["b/SKILL.md"] and d["soul_changed"]


def test_prompt_has_all_polish_rules_and_no_answer_content():
    p = (ROOT / "scripts" / "hermes" / "prompts" / "hermes_system.md").read_text()
    assert "Mark a criterion \"met\" only with a specific evidence file AND a fact from it" in p                 # rule 7
    assert "list in decision.json only the policy sections that apply" in p.lower() or "List in decision.json only the policy sections that apply" in p
    assert "Never state a value that no document gives" in p and "not claim or clinical facts" in p            # rules 8, 9
    assert "at most twice" in p and "deliverable.md" in p and "decision.json" in p and "<<<DELIVERABLE>>>" not in p
    lowered = p.lower()
    for banned in ("truth.json", "rubric", "gold", "attack", "trap", "category", "c-0005", "c-0030", "timely filing", "mp-tf", "mp-img"):
        assert banned not in lowered, banned


def test_failed_terminal_result_with_trailing_hint_and_malformed_flag():
    t = 9.0
    bad = json.dumps({"output": "/usr/bin/bash: eval: line 5: syntax error near unexpected token `('", "exit_code": 2, "error": None}) + "\n\n[Hint: retrying. First inspect the error.]"
    via_file = "$(cat /tmp/args.json)"
    msgs = [_msg(1, "user", t, content="t"),
            _msg(2, "assistant", t + 1, tool_calls=[_call("a", "terminal", {"command": f"{WRAP} C-0005 retrieve_payer_policy '{{\"x\": \"plan's\"}}'"}),
                                                    _call("b", "terminal", {"command": f"{WRAP} C-0005 retrieve_payer_policy \"{via_file}\""})]),
            _msg(3, "tool", t + 2, tool_call_id="a", tool_name="terminal", content=bad),
            _msg(4, "tool", t + 2, tool_call_id="b", tool_name="terminal", content=json.dumps({"output": '{"candidates": []}', "exit_code": 0, "error": None}))]
    ev, S = be.build({"run_id": "r", "case_id": "C-0005", "hermes_run_id": "h", "prompt_sha256": "p", "start": t, "end": t + 3, "status": "submitted"}, [], msgs, [])
    res = [e for e in ev if e["kind"] == "tool_result"]
    assert [e["status"] for e in res] == ["error", "ok"]                       # the trailing hint no longer hides the failure
    assert S["malformed_calls"] == 1 and S["args_via_shell_expansion"] == 1    # a shell-expanded argument is valid, not malformed
    calls = [e for e in ev if e["kind"] == "tool_call"]
    assert calls[0]["data"].get("malformed") is True and "malformed" not in calls[1]["data"]
