"""Offline tests for the pre-sandbox agent runner. A scripted fake model drives the loop: no network, no key."""
import json
import shutil
from pathlib import Path

import pytest

from agent import run_baseline as RB
from agent import run_case as RC
from agent.events import EVENT_KEYS, KINDS, Recorder
from agent.fake_model import ScriptedModel, failure, text_response, tool_response
from agent.final import parse_final
from agent.model_client import HostedModel, ModelFailure, agent_model_id
from agent.staging import FORBIDDEN, stage_case
from agent.tools import HIDDEN, TOOL_NAMES, ToolRunner, tool_specs

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
pytestmark = pytest.mark.skipif(not (DATA / "manifest.json").exists(), reason="data not generated")
CASE = "C-0030"


def gold(cid=CASE):
    g = DATA / "cases" / cid / "gold"
    return (g / "deliverable.md").read_text(), (g / "decision.json").read_text()


def final_text(d, dec):
    return f"<<<DELIVERABLE>>>\n{d}<<<DECISION>>>\n{dec}<<<END>>>"


def run(tmp_path, script, **kw):
    model = ScriptedModel(script)
    return RC.run_case(model, CASE, DATA, tmp_path / "out", "test-run", **kw), model, tmp_path / "out"


def events(out):
    return [json.loads(x) for x in (out / "events.jsonl").read_text().splitlines()]


def kinds(out):
    return [e["kind"] for e in events(out)]


def good_script():
    d, dec = gold()
    return [tool_response(("parse_denial_eob", {})), text_response(final_text(d, dec))]


# ---------------------------------------------------------------- scenarios
def test_normal_run(tmp_path):
    s, model, out = run(tmp_path, good_script())
    d, dec = gold()
    assert s["status"] == "submitted" and s["turns"] == 2 and s["tool_calls_by_name"] == {"parse_denial_eob": 1} and s["revisions"] == 0
    assert (out / "deliverable.md").read_text() == d and json.loads((out / "decision.json").read_text()) == json.loads(dec)
    assert s["final_self_check"]["ok"] and s["proposal_self_checks"] == [{"ok": True, "n_errors": 0, "failed": []}]
    assert s["model_id"] == "scripted-fake" and len(s["prompt_sha256"]) == 64 and s["git_sha"] and s["usage"]["total_tokens"] == 30
    assert (out / "final_self_check.json").exists() and (out / "skills_events.jsonl").exists()
    # the model was given the system prompt, task.md (user) and the six tools; tool results were fed back
    first = model.requests[0]
    assert first[0]["role"] == "system" and first[1]["role"] == "user" and "Today's date for this review" in first[1]["content"]
    assert any(m["role"] == "tool" for m in model.requests[1])


def test_events_and_trace_are_well_formed(tmp_path):
    s, _, out = run(tmp_path, good_script())
    ev = events(out)
    assert all(sorted(e) == sorted(EVENT_KEYS) and e["kind"] in KINDS for e in ev)
    assert [e["seq"] for e in ev] == list(range(1, len(ev) + 1))
    ks = [e["kind"] for e in ev]
    assert ks[0] == "run_start" and ks[-1] == "run_end" and {"model_request", "model_response", "tool_call", "tool_result", "self_check"} <= set(ks)
    resp = next(e for e in ev if e["kind"] == "model_response" and e["data"]["tool_calls"])
    assert resp["data"]["tool_calls"][0]["name"] == "parse_denial_eob" and resp["data"]["usage"]["total_tokens"] == 15
    tr = json.loads((out / "trace.json").read_text())
    assert [t["n"] for t in tr] == list(range(1, len(tr) + 1)) and all(set(t) == {"n", "kind", "name", "args_summary", "result_summary", "duration_ms", "status"} for t in tr)
    assert [t["kind"] for t in tr][:3] == ["run", "model", "tool"] and tr[-1]["name"] == "end"
    blob = (out / "events.jsonl").read_text() + (out / "trace.json").read_text() + (out / "skills_events.jsonl").read_text()
    for banned in ("truth.json", "rubric.json", "/gold", "attacks"):
        assert banned not in blob, banned


def test_staging_never_contains_forbidden_entries(tmp_path):
    cr, pr = stage_case(DATA, CASE, tmp_path / "s")
    assert not [p for p in (tmp_path / "s").rglob("*") if p.name.lower() in FORBIDDEN]
    assert sorted(p.name for p in cr.iterdir()) == ["docs", "task.md"] and (pr / "MP-TF-001.txt").exists()
    s, _, out = run(tmp_path, good_script())
    assert not [p for p in (out / "staged").rglob("*") if p.name.lower() in FORBIDDEN]


def test_malformed_tool_call_then_recovery(tmp_path):
    d, dec = gold()
    script = [tool_response(("parse_denial_eob", "{not json")), tool_response(("no_such_tool", {})), tool_response(("parse_denial_eob", {})), text_response(final_text(d, dec))]
    s, model, out = run(tmp_path, script)
    assert s["status"] == "submitted" and s["malformed_calls"] == 2 and s["tool_errors"] == 2 and s["tool_calls_total"] == 3
    msgs = model.requests[1]
    assert json.loads(msgs[-1]["content"])["error"]["code"] == "bad_input" and "valid JSON" in msgs[-1]["content"]
    assert json.loads(model.requests[2][-1]["content"])["error"]["code"] == "unknown_tool"


def test_response_without_choices_is_counted_and_retried(tmp_path):
    d, dec = gold()
    s, model, out = run(tmp_path, [failure("no_choices"), failure("bad_json"), text_response(final_text(d, dec))])
    assert s["status"] == "submitted" and [f["kind"] for f in s["model_failures"]] == ["no_choices", "bad_json"] and s["turns"] == 1
    assert "empty or malformed" in model.requests[1][-1]["content"]          # repair nudge on the retry only
    assert "empty or malformed" not in json.dumps(model.requests[0])
    assert sum(1 for e in events(out) if e["kind"] == "model_response" and e["status"] == "error") == 2


def test_three_model_failures_end_the_run(tmp_path):
    s, _, out = run(tmp_path, [failure(), failure(), failure()])
    assert s["status"] == "model_failure" and len(s["model_failures"]) == 3 and (out / "summary.json").exists() and not (out / "deliverable.md").exists()
    assert kinds(out)[-1] == "run_end" and (out / "trace.json").exists()


def test_empty_response_counts_as_failure(tmp_path):
    d, dec = gold()
    s, _, _ = run(tmp_path, [text_response("   "), text_response(final_text(d, dec))])
    assert s["status"] == "submitted" and s["model_failures"][0]["kind"] == "empty"


def test_tool_error_recovery(tmp_path):
    d, dec = gold()
    script = [tool_response(("retrieve_payer_policy", {"dos": "2026-04-01"})),                       # missing required 'payer'
              tool_response(("pull_clinical_notes", {"paths": ["notes/2020-01-01_nothing.txt"]})),  # not found
              tool_response(("parse_denial_eob", {})), text_response(final_text(d, dec))]
    s, model, out = run(tmp_path, script)
    assert s["status"] == "submitted" and s["tool_errors"] == 2 and s["malformed_calls"] == 1
    assert json.loads(model.requests[1][-1]["content"])["error"]["code"] == "bad_input" and json.loads(model.requests[2][-1]["content"])["error"]["code"] == "not_found"
    assert [e["status"] for e in events(out) if e["kind"] == "tool_result"][:2] == ["error", "error"]


def test_max_turns_reached(tmp_path):
    s, _, out = run(tmp_path, [tool_response(("parse_denial_eob", {})) for _ in range(5)], max_turns=3)
    assert s["status"] == "max_turns" and s["turns"] == 3 and s["tool_calls_total"] == 3
    assert json.loads((out / "events.jsonl").read_text().splitlines()[-1])["data"]["status"] == "max_turns"


def test_max_turns_with_a_proposal_still_writes_files(tmp_path):
    d, dec = gold()
    bad = d.replace(RC_CLAIM(), "9999999")
    s, _, out = run(tmp_path, [text_response(final_text(bad, dec)), tool_response(("parse_denial_eob", {}))], max_turns=2, max_revisions=2)
    assert s["status"] == "max_turns_with_proposal" and (out / "deliverable.md").exists() and s["final_self_check"]["ok"] is False


def RC_CLAIM():
    return json.loads((DATA / "cases" / CASE / "truth.json").read_text())["claim"]["claim_no"]


def test_path_guard_attack_is_refused_and_logged(tmp_path):
    d, dec = gold()
    script = [tool_response(("pull_clinical_notes", {"paths": ["../truth.json"]}), ("pull_clinical_notes", {"paths": ["truth.json"]}),
                            ("pull_clinical_notes", {"paths": ["gold/deliverable.md"]}), ("parse_denial_eob", {"case_root": str(DATA / "cases" / CASE)}),
                            ("draft_deliverable", {"action": "verify_citations", "deliverable_path": "../../data/cases/C-0030/truth.json"})),
              text_response(final_text(d, dec))]
    s, model, out = run(tmp_path, script)
    assert s["status"] == "submitted" and s["path_guard_denials"] >= 3 and s["tool_errors"] == 5
    results = [json.loads(m["content"]) for m in model.requests[1] if m["role"] == "tool"]
    assert all("error" in r for r in results)
    assert "access_denied" in {r["error"]["code"] for r in results}
    assert any("cannot be passed" in r["error"]["message"] for r in results)          # hidden argument rejected
    sk = [json.loads(x) for x in (out / "skills_events.jsonl").read_text().splitlines()]
    assert sum(1 for e in sk if e["tool"] == "path_guard" and e["status"] == "denied") >= 3
    assert "truth.json" not in "".join(m["content"] for m in model.requests[1] if m["role"] == "tool" and "denied" not in m["content"])


def test_revision_loop_after_self_check_failure(tmp_path):
    d, dec = gold()
    bad = d.replace(RC_CLAIM(), "9999999")
    s, model, out = run(tmp_path, [text_response(final_text(bad, dec)), text_response(final_text(d, dec))])
    assert s["status"] == "submitted" and s["revisions"] == 1 and s["turns"] == 2 and [p["ok"] for p in s["proposal_self_checks"]] == [False, True]
    assert s["proposal_self_checks"][0]["failed"] == ["identifier_claim_no"]
    rev = model.requests[1][-1]
    assert rev["role"] == "user" and "Revision request" in rev["content"] and "identifier_claim_no" in rev["content"]
    assert "revision" in kinds(out) and (out / "deliverable.md").read_text() == d
    assert [t["kind"] for t in json.loads((out / "trace.json").read_text()) if t["kind"] in ("revision", "self_check")] == ["self_check", "revision", "self_check", "self_check"]


def test_revisions_are_capped_and_final_self_check_not_enforced(tmp_path):
    d, dec = gold()
    bad = d.replace(RC_CLAIM(), "9999999")
    s, _, out = run(tmp_path, [text_response(final_text(bad, dec))] * 3)
    assert s["status"] == "submitted" and s["revisions"] == 2 and s["turns"] == 3 and s["final_self_check"]["ok"] is False
    assert (out / "deliverable.md").read_text() == bad                      # written anyway; the last check is recorded, not enforced


def test_format_nudge_for_unparseable_final(tmp_path):
    d, dec = gold()
    s, model, _ = run(tmp_path, [text_response("I think we should not appeal."), text_response(final_text(d, dec))])
    assert s["status"] == "submitted" and s["malformed_final"] == 1 and "required final format" in model.requests[1][-1]["content"]


def test_time_limit(tmp_path):
    s, _, _ = run(tmp_path, [tool_response(("parse_denial_eob", {}))], time_limit=-1)
    assert s["status"] == "time_limit" and s["turns"] == 0


# ---------------------------------------------------------------- baseline
def test_baseline_parses_final_and_retries_on_bad_format(tmp_path):
    d, dec = gold()
    model = ScriptedModel([text_response("no format here"), text_response(final_text(d, dec))])
    s = RB.run_baseline_case(model, CASE, DATA, tmp_path / "b", "test-run")
    assert s["status"] == "submitted" and s["variant"] == "baseline" and s["malformed_final"] == 1 and s["turns"] == 2 and s["final_self_check"]["ok"]
    assert (tmp_path / "b" / "deliverable.md").read_text() == d and (tmp_path / "b" / "trace.json").exists()
    user = model.requests[0][1]["content"]
    assert "# CASE DOCUMENTS" in user and "claim_history.txt" in user and "MP-TF-010.txt" in user and "MP-IMG-007.txt" in user      # all docs + whole library pasted
    assert model.requests[0][0]["content"] == RB.PROMPT.read_text()
    ev = [json.loads(x) for x in (tmp_path / "b" / "events.jsonl").read_text().splitlines()]
    assert all(e["variant"] == "baseline" for e in ev) and not any(e["kind"] in ("tool_call", "tool_result") for e in ev)
    s2 = RB.run_baseline_case(ScriptedModel([failure(), failure(), failure()]), CASE, DATA, tmp_path / "b2", "test-run")
    assert s2["status"] == "model_failure"


def test_parse_final_tolerates_slipped_brackets():
    # seen in the first pilot run: the model closed the markers with two brackets and the run hit max_turns
    d, dec = parse_final("<<<DELIVERABLE>>\n# T\n\n<<<DECISION>>\n{\"a\": 1}\n<<<END>>>")
    assert d == "# T\n" and json.loads(dec) == {"a": 1}
    d, dec = parse_final("<<DELIVERABLE>>\n# T\n<<DECISION>>\n{}\n<<END>>")
    assert d == "# T\n" and dec == "{}\n"


def test_parse_final_variants():
    assert parse_final("x") is None and parse_final("<<<DELIVERABLE>>>\n<<<DECISION>>>\n{}") is None
    d, dec = parse_final("<<<DELIVERABLE>>>\n# T\n<<<DECISION>>>\n```json\n{\"a\": 1}\n```\n<<<END>>>")
    assert d == "# T\n" and json.loads(dec) == {"a": 1}


# ---------------------------------------------------------------- tools / client / prompt
def test_tool_specs_match_skill_inputs_and_hide_system_fields():
    specs = tool_specs()
    assert [s["function"]["name"] for s in specs] == TOOL_NAMES
    for s in specs:
        p = s["function"]["parameters"]
        assert p["type"] == "object" and not (HIDDEN & set(p["properties"])) and "$ref" not in json.dumps(p) and "anyOf" not in json.dumps(p)
    assert set(specs[4]["function"]["parameters"]["properties"]) == {"action", "kind", "decision_text", "deliverable_text", "policy_id"}
    json.dumps(specs)


def test_tool_runner_truncation_unknown_tool_and_hidden_args(tmp_path):
    cr, pr = stage_case(DATA, "C-0007", tmp_path / "s")
    r = ToolRunner(cr, pr, tmp_path / "ev.jsonl", "r", "C-0007", max_chars=500)
    text, st, meta = r.execute("pull_clinical_notes", {"include_text": True})
    assert st == "ok" and meta["truncated"] and "[TRUNCATED:" in text and len(text) < 800
    big = ToolRunner(cr, pr, tmp_path / "ev2.jsonl", "r", "C-0007")
    text, st, meta = big.execute("assess_appealability", {})
    assert st == "ok" and not meta["truncated"] and json.loads(text)["policy"]["policy_id"] == "MP-IMG-007"
    assert r.execute("nope", {})[1] == "error" and r.execute("parse_denial_eob", {"case_root": "/x"})[1] == "error"
    assert r.execute("self_check", {"deliverable_text": "x"})[1] == "error"       # tool exception / bad input becomes a result, not a crash


def test_hosted_model_logs_full_failure_body_with_redaction(tmp_path, monkeypatch):
    import _common
    monkeypatch.setattr(_common, "ERROR_LOG", tmp_path / "logs" / "model_errors.jsonl")
    monkeypatch.setenv("NVIDIA_INFERENCE_API_KEY", "sk-TESTSECRET1234567890")
    cfg = {"api": {"base_url": "https://example.invalid/v1", "key_env": "NVIDIA_INFERENCE_API_KEY"}, "agent": {"model_id": "agent-x", "temperature": 0.1, "max_tokens": 50},
           "judges": {"gpt": "j"}, "datagen": {"model_id": "dg"}}
    body = json.dumps({"error": "overloaded", "echo": "Bearer sk-TESTSECRET1234567890"})
    m = HostedModel(cfg, post=lambda *a, **k: (200, {"x-key": "sk-TESTSECRET1234567890"}, body))
    with pytest.raises(ModelFailure) as e:
        m.chat([{"role": "user", "content": "hi"}], [])
    assert e.value.kind == "no_choices"
    log = (tmp_path / "logs" / "model_errors.jsonl").read_text()
    assert "overloaded" in log and "sk-TESTSECRET" not in log and json.loads(log.splitlines()[0])["status"] == 200
    ok = json.dumps({"choices": [{"message": {"content": None, "tool_calls": [{"function": {"name": "self_check", "arguments": "{}"}}]}, "finish_reason": "tool_calls"}], "usage": {"total_tokens": 3}})
    r = HostedModel(cfg, post=lambda *a, **k: (200, {}, ok)).chat([], [])
    assert r.message["tool_calls"][0]["id"] and r.usage["total_tokens"] == 3 and "reasoning_content" not in r.message
    assert HostedModel(cfg, post=lambda *a, **k: (500, {}, "boom")).__class__ and True
    with pytest.raises(ModelFailure) as e:
        HostedModel(cfg, post=lambda *a, **k: (500, {}, "boom")).chat([], [])
    assert e.value.kind in ("bad_json", "http")


def test_agent_model_cannot_be_judge_or_datagen():
    base = {"agent": {"model_id": "m"}, "judges": {"gpt": "m"}, "datagen": {"model_id": "d"}}
    with pytest.raises(SystemExit):
        agent_model_id(base)
    with pytest.raises(SystemExit):
        agent_model_id({**base, "judges": {"gpt": "j"}, "datagen": {"model_id": "m"}})
    assert agent_model_id({**base, "judges": {"gpt": "j"}}) == "m"


def test_prompts_do_not_reveal_category_trap_or_answer():
    from data_gen import reference as R
    from data_gen.schema import Trap
    for f in (RC.PROMPT, RB.PROMPT):
        t = f.read_text()
        for name in [c["name"] for c in R.CATEGORIES.values()] + [x.value for x in Trap]:
            assert name not in t, (f.name, name)
        for word in ("truth.json", "rubric", "gold", "trap", "attack", "MP-", "C-00", "CO-50", "CO-29"):
            assert word not in t, (f.name, word)
        assert all(d in t for d in ("APPEAL", "CORRECT_AND_RESUBMIT", "DO_NOT_APPEAL", "ESCALATE_MISSING_DOCS"))
    assert "action_deadline_rule" in RC.PROMPT.read_text()


def test_dry_run_cli_and_resume(tmp_path, capsys):
    run_id = "pytest-dry"
    shutil.rmtree(ROOT / "runs" / f"{run_id}-r1", ignore_errors=True)
    try:
        RC.main(["--dry-run", "--case", CASE, "--repeats", "1", "--run-id", run_id])
        assert "submitted" in capsys.readouterr().out
        RC.main(["--dry-run", "--case", CASE, "--repeats", "1", "--run-id", run_id, "--resume"])
        assert "skipped" in capsys.readouterr().out
    finally:
        shutil.rmtree(ROOT / "runs" / f"{run_id}-r1", ignore_errors=True)


def test_events_recorder_redacts_keys(tmp_path):
    rec = Recorder(tmp_path / "r", "r", "C-0001")
    rec.emit("model_response", "model_response", data={"content": "my key is sk-ABCDEFGH12345678 ok"})
    rec.write_trace()
    assert "sk-ABCDEFGH" not in (tmp_path / "r" / "events.jsonl").read_text() + (tmp_path / "r" / "trace.json").read_text()
