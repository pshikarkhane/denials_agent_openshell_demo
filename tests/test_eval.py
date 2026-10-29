"""Tests for the evaluation layer. No real API calls: judges are mocked."""
import json
from pathlib import Path

import pytest

from eval import hallucination_check as H
from eval import judge_panel as J
from eval.auto_checks import date_variants, grade_auto
from eval.common import judge_models, norm, quote_in
from eval.deliverable_schema import DecisionJson, normalize_section, validate_decision_text
from eval.gen_rubrics import build_rubric
from eval.rubric_schema import Rubric

DATA = Path(__file__).resolve().parents[1] / "data"
needs_data = pytest.mark.skipif(not (DATA / "manifest.json").exists(), reason="data not generated")
PILOTS = ["C-0005", "C-0007", "C-0030", "C-0039", "C-0056"]


def good_decision(**over):
    d = {"case_id": "C-0030", "decision": "DO_NOT_APPEAL", "denial_code": "CO-29", "policy_id": "MP-TF-001",
         "action_deadline": "2026-11-01", "deadline_ok": True,
         "criteria": [{"id": "2.1", "status": "unmet", "evidence": "claim_history.txt"}, {"id": "2.2", "status": "unmet", "evidence": None}],
         "enclosures": [], "gaps": []}
    d.update(over)
    return d


# ---------------------------------------------------------------- schema
def test_decision_schema_accepts_valid():
    d, errs = validate_decision_text(json.dumps(good_decision()), "C-0030")
    assert errs == [] and isinstance(d, DecisionJson)


@pytest.mark.parametrize("bad", [
    {"decision": "MAYBE"}, {"action_deadline": "tomorrow"}, {"policy_id": "IMG-7"}, {"case_id": "X-1"},
    {"criteria": [{"id": "C1", "status": "met", "evidence": None}]},          # internal ids are not allowed
    {"criteria": [{"id": "2.1", "status": "met"}, {"id": "2.1", "status": "unmet"}]},  # duplicates
    {"criteria": [{"id": "2.1", "status": "partly"}]}, {"extra": 1}, {"enclosures": "none"},
])
def test_decision_schema_rejects_invalid(bad):
    d, errs = validate_decision_text(json.dumps(good_decision(**bad)))
    assert d is None and errs


def test_decision_schema_other_failures():
    assert validate_decision_text("not json")[1]
    assert validate_decision_text(json.dumps(good_decision()), "C-9999")[1]
    d = good_decision()
    del d["gaps"]
    assert validate_decision_text(json.dumps(d))[0] is None


def test_section_normalization():
    assert normalize_section("§2.1(a)") == "2.1(a)" and normalize_section("Section 2.1(a)") == "2.1(a)"
    d, _ = validate_decision_text(json.dumps(good_decision(criteria=[{"id": "§2.1", "status": "met", "evidence": None}])))
    assert d.criteria[0].id == "2.1"


# ---------------------------------------------------------------- auto checks
def test_auto_checks():
    dec, _ = validate_decision_text(json.dumps(good_decision()))
    assert grade_auto({"kind": "decision_eq", "expected": "DO_NOT_APPEAL"}, dec, "")[0]
    assert not grade_auto({"kind": "decision_eq", "expected": "APPEAL"}, dec, "")[0]
    assert grade_auto({"kind": "denial_code_eq", "expected": "CO-29"}, dec, "")[0]
    assert grade_auto({"kind": "policy_id_eq", "expected": "MP-TF-001"}, dec, "")[0]
    assert grade_auto({"kind": "action_deadline_eq", "date": "2026-11-01", "deadline_ok": True}, dec, "")[0]
    assert not grade_auto({"kind": "action_deadline_eq", "date": "2026-11-02", "deadline_ok": True}, dec, "")[0]
    assert not grade_auto({"kind": "action_deadline_eq", "date": "2026-11-01", "deadline_ok": False}, dec, "")[0]
    assert grade_auto({"kind": "criteria_status_eq", "expected": {"2.1": "unmet", "2.2": "unmet"}}, dec, "")[0]
    assert not grade_auto({"kind": "criteria_status_eq", "expected": {"2.1": "met"}}, dec, "")[0]
    assert not grade_auto({"kind": "decision_eq", "expected": "APPEAL"}, None, "")[0]  # missing decision.json


def test_auto_identifiers_and_date_formats():
    spec = {"kind": "identifiers", "claim_no": "1234567", "patient_id": "P-1111", "dos": "2026-04-20", "cpt": "72148"}
    assert grade_auto(spec, None, "Claim 1234567 for P-1111, CPT 72148, DOS 2026-04-20")[0]
    assert grade_auto(spec, None, "Claim 1234567 for P-1111, CPT 72148, service on April 20, 2026")[0]
    assert grade_auto(spec, None, "Claim 1234567 for P-1111, CPT 72148, DOS 4/20/2026")[0]
    assert not grade_auto(spec, None, "Claim 1234568 for P-1111, CPT 72148, DOS 2026-04-20")[0]
    assert not grade_auto(spec, None, "Claim 1234567 for P-1111, CPT 72148, DOS 2026-04-21")[0]
    assert "April 20, 2026" in date_variants("2026-04-20")


# ---------------------------------------------------------------- rubric generator
@needs_data
@pytest.mark.parametrize("cid", PILOTS)
def test_rubric_structure_and_consistency(cid):
    from data_gen.gen_cases import load_truths
    _, truths = load_truths(DATA)
    t = next(x for x in truths if x.case_id == cid)
    r = Rubric.model_validate_json((DATA / "cases" / cid / "rubric.json").read_text())
    assert 8 <= len(r.criteria) <= 15
    ids = [c.id for c in r.criteria]
    assert len(set(ids)) == len(ids)
    assert not r.partial and r.decision == t.correct_decision.value
    fam = {c.family for c in r.criteria}
    assert {"decision", "identifiers", "denial_reason", "deadline", "policy_citation", "evidence_use"} <= fam
    f = {x.key: x.value for x in t.facts}
    for c in r.criteria:
        assert c.reference
        if c.check == "auto":
            k = c.auto["kind"]
            if k == "decision_eq":
                assert c.auto["expected"] == t.correct_decision.value
            if k == "identifiers":
                assert (c.auto["claim_no"], c.auto["patient_id"], c.auto["dos"], c.auto["cpt"]) == (t.claim.claim_no, t.patient.synthetic_id, t.claim.dos.isoformat(), t.claim.cpt)
            if k == "denial_code_eq":
                assert c.auto["expected"] == t.denial.carc
            if k == "action_deadline_eq":
                assert c.auto["date"] == t.action_deadline.isoformat() and c.auto["deadline_ok"] == (f["as_of_date"] <= t.action_deadline.isoformat())
            if k == "policy_id_eq":
                assert c.auto["expected"] == t.policy_id
            if k == "criteria_status_eq":
                assert c.auto["expected"] == {x.section.lstrip("§"): x.status for x in t.policy_criteria}
        else:
            assert c.auto is None
        for s in c.sources:  # every cited file exists
            p = DATA / s if s.startswith("policy_library/") else (DATA / "cases" / cid / "task.md" if s == "task.md" else DATA / "cases" / cid / "docs" / s)
            assert p.exists(), s


@needs_data
@pytest.mark.parametrize("cid", PILOTS)
def test_rubric_is_deterministic(cid):
    from data_gen.gen_cases import load_truths
    _, truths = load_truths(DATA)
    t = next(x for x in truths if x.case_id == cid)
    a, b = build_rubric(t, DATA).model_dump_json(), build_rubric(t, DATA).model_dump_json()
    assert a == b and json.loads(a) == json.loads((DATA / "cases" / cid / "rubric.json").read_text())


@needs_data
def test_auto_criteria_only_for_exact_fields_and_all_rubrics_valid():
    kinds = set()
    for p in (DATA / "cases").glob("C-*/rubric.json"):
        r = Rubric.model_validate_json(p.read_text())
        assert len(r.criteria) >= 8
        kinds |= {c.auto["kind"] for c in r.criteria if c.check == "auto"}
    assert kinds <= {"decision_eq", "identifiers", "denial_code_eq", "action_deadline_eq", "policy_id_eq", "criteria_status_eq"}


@needs_data
def test_no_rubric_or_gold_in_agent_visible_paths():
    from data_gen.validate_docs import agent_visible_files
    for p in agent_visible_files(DATA):
        assert "rubric" not in p.name.lower() and "gold" not in p.parts
        assert "rubric" not in p.read_text().lower().split()  # no rubric vocabulary in agent files
    for cid in PILOTS:
        assert not list((DATA / "cases" / cid / "docs").rglob("rubric*")) and not (DATA / "cases" / cid / "docs" / "gold").exists()


@needs_data
def test_gold_passes_schema_and_auto():
    from eval.gen_gold import check_gold
    from data_gen.gen_cases import load_truths
    _, truths = load_truths(DATA)
    for t in truths:
        g = DATA / "cases" / t.case_id / "gold"
        if t.case_id in PILOTS and (g / "deliverable.md").exists():
            r = Rubric.model_validate_json((DATA / "cases" / t.case_id / "rubric.json").read_text())
            problems, _ = check_gold(t, r, (g / "deliverable.md").read_text(), (g / "decision.json").read_text())
            assert problems == [], (t.case_id, problems)
            assert json.loads((g / "meta.json").read_text())["model_id"] != ""


# ---------------------------------------------------------------- quotes, judges
def test_quote_matching():
    assert quote_in("The filing   limit expired.", "filing limit expired")
    assert quote_in("a “smart” quote", '"smart" quote')
    assert quote_in("alpha beta gamma delta epsilon", "alpha beta ... delta epsilon")
    assert not quote_in("alpha beta", "alpha gamma")
    assert not quote_in("alpha beta", "")
    assert norm("A—B") == "a-b"


def test_agent_model_cannot_be_a_judge():
    cfg = {"judges": {"gemini": "g", "claude": "c", "gpt": "nvidia/nvidia/nemotron-3.5-super-text-preview"}, "agent": {"model_id": "nvidia/nvidia/nemotron-3.5-super-text-preview"}}
    with pytest.raises(SystemExit):
        judge_models(cfg)


def test_chunking_splits_over_15():
    cs = list(range(16))
    assert J.chunks(cs) == [cs[:8], cs[8:]] and J.chunks(cs[:15]) == [cs[:15]]


def mk_call(script, log=None):
    """script: dict judge_key -> list of replies (strings) consumed in order; each call returns the next reply."""
    state = {k: list(v) for k, v in script.items()}

    def call(jkey, prompt, tag, max_tokens=0):
        if log is not None:
            log.append((jkey, tag, prompt))
        return state[jkey].pop(0), {"total_tokens": 10}, 0.5
    return call


@pytest.fixture()
def deliverable(tmp_path):
    (tmp_path / "deliverable.md").write_text("Claim 1234567 was denied. The filing limit expired on 2026-06-30. We recommend no appeal. Source: claim_history.txt")
    (tmp_path / "decision.json").write_text(json.dumps(good_decision()))
    return tmp_path


def reply(results):
    return json.dumps({"results": results})


def pass_all(ids, quote="filing limit expired"):
    return reply([{"id": i, "verdict": "PASS", "evidence_quote": quote, "reason": "ok"} for i in ids])


@needs_data
def test_grade_case_majority_quote_rule_and_pooling(deliverable):
    from eval.rubric_schema import Rubric as RB
    rub = RB.model_validate_json((DATA / "cases" / "C-0030" / "rubric.json").read_text())
    jids = [c.id for c in rub.criteria if c.check == "judge"]
    first = jids[0]
    gem = reply([{"id": i, "verdict": "PASS", "evidence_quote": "filing limit expired", "reason": ""} for i in jids])
    # claude: fabricated quote on the first criterion; gpt: FAIL on the first criterion
    cla = reply([{"id": i, "verdict": "PASS", "evidence_quote": ("never written here" if i == first else "filing limit expired"), "reason": ""} for i in jids])
    gpt = reply([{"id": i, "verdict": ("FAIL" if i == first else "PASS"), "evidence_quote": "filing limit expired", "reason": ""} for i in jids])
    res = J.grade_case(mk_call({"gemini": [gem], "claude": [cla], "gpt": [gpt]}), DATA, "C-0030", deliverable)
    assert res["fabricated_quotes"] == 1
    assert res["judges"]["claude"]["verdicts"][first]["verdict"] == "FAIL" and res["judges"]["claude"]["verdicts"][first]["fabricated_quote"]
    assert res["panel"][first] == "FAIL"                      # 1 PASS of 3
    assert all(res["panel"][i] == "PASS" for i in jids[1:])    # 3 PASS
    assert res["unanimity_rate"] == pytest.approx((len(jids) - 1) / len(jids))
    n = res["criteria_total"]
    # the deliverable's identifiers/decision.json are only partly right, but auto results are pooled identically into every judge's rate
    a = sum(v["pass"] for v in res["auto"].values())
    assert res["judge_pass_rates"]["gemini"] == pytest.approx((a + len(jids)) / n)
    assert res["judge_pass_rates"]["claude"] == pytest.approx((a + len(jids) - 1) / n)
    assert res["tokens"]["gemini"]["total_tokens"] == 10


@needs_data
def test_malformed_json_is_repaired_once_then_recorded_as_failure(deliverable):
    from eval.rubric_schema import Rubric as RB
    rub = RB.model_validate_json((DATA / "cases" / "C-0030" / "rubric.json").read_text())
    jids = [c.id for c in rub.criteria if c.check == "judge"]
    ok = pass_all(jids)
    log = []
    script = {"gemini": ["garbage", ok], "claude": ["garbage", "still garbage"], "gpt": [ok]}
    res = J.grade_case(mk_call(script, log), DATA, "C-0030", deliverable)
    assert res["judge_failures"] == ["claude"] and res["judges"]["gemini"]["failed"] is False
    assert sum(1 for jk, tag, _ in log if jk == "gemini") == 2 and sum(1 for jk, tag, _ in log if jk == "claude") == 2
    assert all(res["panel"][i] == "PASS" for i in jids)       # majority of the two valid judges
    assert res["judge_pass_rates"]["claude"] < res["judge_pass_rates"]["gemini"]  # failed judge's missing verdicts count as FAIL


@needs_data
def test_missing_decision_json_fails_auto(tmp_path):
    (tmp_path / "deliverable.md").write_text("x")
    from eval.rubric_schema import Rubric as RB
    jids = [c.id for c in RB.model_validate_json((DATA / "cases" / "C-0030" / "rubric.json").read_text()).criteria if c.check == "judge"]
    res = J.grade_case(mk_call({k: [pass_all(jids)] for k in ("gemini", "claude", "gpt")}), DATA, "C-0030", tmp_path)
    assert res["decision_json_errors"] and not any(v["pass"] for k, v in res["auto"].items() if k != "IDN1")


# ---------------------------------------------------------------- hallucination check
def test_union_dedupes_and_discards_fabricated_quotes():
    text = "The claim was received on 2026-07-15 and the visit limit is 25 visits."
    flags = {"gemini": [{"quote": "received on 2026-07-15", "problem": "a"}, {"quote": "invented sentence", "problem": "b"}],
             "claude": [{"quote": "The claim was received on 2026-07-15", "problem": "c"}], "gpt": [{"quote": "visit limit is 25 visits", "problem": "d"}]}
    union, discarded = H.union_flags(flags, text, "")
    assert len(union) == 2 and union[0]["raised_by"] == ["gemini", "claude"] and union[1]["raised_by"] == ["gpt"]
    assert [d["quote"] for d in discarded] == ["invented sentence"]


def test_decide_two_of_three_and_severity_majority():
    union = [{"id": "F1", "quote": "q1", "problems": [""], "raised_by": ["gemini"]}, {"id": "F2", "quote": "q2", "problems": [""], "raised_by": ["gpt"]},
             {"id": "F3", "quote": "q3", "problems": [""], "raised_by": ["gpt"]}]
    def a(up, sev="material"):
        return {"upheld": up, "severity": sev, "reason": ""}
    adj = {"gemini": {"F1": a(True), "F2": a(True, "minor"), "F3": a(False)},
           "claude": {"F1": a(True, "minor"), "F2": a(True, "minor"), "F3": a(False)},
           "gpt": {"F1": a(False), "F2": a(False), "F3": a(True)}}
    res = {f["id"]: f for f in H.decide(union, adj)}
    assert res["F1"]["upheld"] and res["F1"]["severity"] == "material"      # tie of upholders -> material
    assert res["F2"]["upheld"] and res["F2"]["severity"] == "minor"
    assert not res["F3"]["upheld"] and res["F3"]["severity"] is None         # only 1 of 3


@needs_data
def test_two_stage_flow_and_no_stage2_when_no_flags(deliverable):
    log = []
    none = json.dumps({"flags": []})
    r = H.hallucination_case(mk_call({k: [none] for k in ("gemini", "claude", "gpt")}, log), DATA, "C-0030", deliverable)
    assert r["upheld_material"] == 0 and all(tag.startswith("hal1") for _, tag, _ in log) and len(log) == 3
    flag = json.dumps({"flags": [{"quote": "The filing limit expired on 2026-06-30", "problem": "x", "evidence": "y"}]})
    adj = lambda up, sev: json.dumps({"adjudications": [{"flag_id": "F1", "upheld": up, "severity": sev, "reason": ""}]})  # noqa: E731
    log = []
    script = {"gemini": [flag, adj(True, "material")], "claude": [none, adj(True, "material")], "gpt": [none, adj(False, "minor")]}
    r = H.hallucination_case(mk_call(script, log), DATA, "C-0030", deliverable)
    assert r["upheld_material"] == 1 and r["upheld_minor"] == 0 and r["flags"][0]["raised_by"] == ["gemini"]
    assert sum(1 for _, tag, _ in log if tag.startswith("hal2")) == 3


@needs_data
def test_stage1_malformed_json_repair_and_failure(deliverable):
    none = json.dumps({"flags": []})
    script = {"gemini": ["bad", none], "claude": ["bad", "bad"], "gpt": [none]}
    r = H.hallucination_case(mk_call(script), DATA, "C-0030", deliverable)
    assert r["judge_failures"] == ["stage1:claude"]


@needs_data
def test_prompts_never_name_the_producer(deliverable):
    log = []
    from eval.rubric_schema import Rubric as RB
    jids = [c.id for c in RB.model_validate_json((DATA / "cases" / "C-0030" / "rubric.json").read_text()).criteria if c.check == "judge"]
    J.grade_case(mk_call({k: [pass_all(jids)] for k in ("gemini", "claude", "gpt")}, log), DATA, "C-0030", deliverable)
    for _, _, prompt in log:
        low = prompt.lower()
        assert "nemotron" not in low and "gold" not in low and "agent trace" not in low.replace("not the agent trace", "")
    assert "truth.json" not in log[0][2] and "correct_decision" not in log[0][2]


def test_caller_temperature_fallback(monkeypatch, tmp_path):
    from eval import common
    seen = []

    def fake(cfg, model, prompt, **kw):
        seen.append(kw.get("temperature", "none"))
        if "temperature" in kw and model.endswith("noTemp"):
            raise common.ModelCallError("HTTP 400")
        return "ok", {"total_tokens": 1}, 0.1
    monkeypatch.setattr(common, "chat_with_retry", fake)
    cfg = {"judges": {"gemini": "a", "claude": "b-noTemp", "gpt": "c"}, "agent": {"model_id": "z"}}
    c = common.Caller(cfg, tmp_path)
    assert c("gemini", "p", "t")[0] == "ok" and c("claude", "p", "t")[0] == "ok"
    assert seen == [0, 0, "none"]
    c("claude", "p", "t2")
    assert seen[-1] == "none"  # remembered: no further temperature attempts
    assert (tmp_path / "raw" / "t__claude.md").exists()
