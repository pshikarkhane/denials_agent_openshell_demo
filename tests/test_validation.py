"""Judge-validation tooling: mutation generator and throttled/cached runner. No network: judges are mocked."""
import json
import threading
import time
from pathlib import Path

import pytest

from eval import mutations as M
from eval import validation_run as V

DATA = Path("data")
CASES = ["C-0005", "C-0007", "C-0030", "C-0039", "C-0056"]
pytestmark = pytest.mark.skipif(not (DATA / "cases" / "C-0005" / "gold" / "deliverable.md").exists(), reason="pilot gold not generated")


def gold(cid):
    g = DATA / "cases" / cid / "gold"
    return (g / "deliverable.md").read_text(), (g / "decision.json").read_text()


def test_deterministic():
    a, sa = M.generate(DATA, CASES)
    b, sb = M.generate(DATA, CASES)
    assert [(i["item_id"], i["deliverable"], i["decision"]) for i in a] == [(i["item_id"], i["deliverable"], i["decision"]) for i in b]
    assert sa == sb


def test_seed_changes_output():
    a, _ = M.generate(DATA, ["C-0005"], seed=1, types=["M1"])
    b, _ = M.generate(DATA, ["C-0005"], seed=2, types=["M1"])
    assert a[0]["record"]["mutated"] != b[0]["record"]["mutated"] or a[0]["record"]["original"] != b[0]["record"]["original"]


def test_each_item_changes_something_and_has_record():
    items, _ = M.generate(DATA, CASES)
    assert items
    for it in items:
        text, dec = gold(it["case_id"])
        assert (it["deliverable"], it["decision"]) != (text, dec), it["item_id"]
        r = it["record"]
        assert {"type", "original", "mutated", "expected", "case_id", "occurrences"} <= set(r)


def test_value_mutations_replace_exactly_the_recorded_fact():
    items, _ = M.generate(DATA, CASES, types=["M1", "M2", "M3", "M4", "M9"])
    for it in items:
        text, dec = gold(it["case_id"])
        r = it["record"]
        assert it["decision"] == dec
        assert it["deliverable"].count(r["mutated"]) >= r["occurrences"]
        assert it["deliverable"].replace(r["mutated"], r["original"]) == text, it["item_id"]  # reversible: one fact, everywhere


def test_m12_changes_only_decision_json():
    items, _ = M.generate(DATA, CASES, types=["M12"])
    for it in items:
        text, dec = gold(it["case_id"])
        assert it["deliverable"] == text
        a, b = json.loads(dec), json.loads(it["decision"])
        assert [k for k in a if a[k] != b[k]] == ["decision"]


def test_m10_removes_enclosure_only_for_appeals():
    items, skipped = M.generate(DATA, CASES, types=["M10"])
    for it in items:
        text, dec = gold(it["case_id"])
        assert json.loads(dec)["decision"] == "APPEAL"
        gone = it["record"]["original"]
        assert gone not in json.loads(it["decision"])["enclosures"]
        assert len(json.loads(it["decision"])["enclosures"]) == len(json.loads(dec)["enclosures"]) - 1
    assert all("not an appeal" in s["reason"] for s in skipped)


def test_m11_nulls_one_criterion_evidence():
    items, _ = M.generate(DATA, CASES, types=["M11"])
    assert items
    for it in items:
        _, dec = gold(it["case_id"])
        a, b = json.loads(dec)["criteria"], json.loads(it["decision"])["criteria"]
        diff = [x["id"] for x, y in zip(a, b) if x != y]
        assert diff == [it["record"]["section"]]
        assert [y for y in b if y["id"] == diff[0]][0]["evidence"] is None


def test_m6_only_where_distractor_exists_and_skips_are_logged():
    items, skipped = M.generate(DATA, CASES, types=["M6"])
    assert {i["case_id"] for i in items} == {"C-0005", "C-0007", "C-0030"}
    assert {s["case_id"] for s in skipped} == {"C-0039", "C-0056"} and all(s["reason"] for s in skipped)


def test_controls_keep_facts():
    items, _ = M.generate(DATA, CASES, types=["C2", "C3", "C4"])
    for it in items:
        text, dec = gold(it["case_id"])
        assert it["decision"] == dec
        for pat in (r"\d{4}-\d{2}-\d{2}", r"\b\d{5}\b", r"CO-\d+", r"MP-[A-Z]+-\d+"):
            import re
            if it["type"] != "C4":  # C4 only adds a courtesy line and one typo; compare fact tokens too
                assert sorted(re.findall(pat, it["deliverable"])) == sorted(re.findall(pat, text)), (it["item_id"], pat)
            else:
                assert sorted(re.findall(pat, it["deliverable"])) == sorted(re.findall(pat, text))


def test_nothing_written_under_data(tmp_path):
    items, skipped = M.generate(DATA, ["C-0005"], types=["M1"])
    M.write_items(items, skipped, tmp_path / "mutations")
    assert (tmp_path / "mutations" / "C-0005__M1" / "record.json").exists()


# ---------------------------------------------------------------- runner
def test_throttle_never_exceeds_limit(tmp_path):
    live, peak, lock = 0, 0, threading.Lock()

    def inner(j, p, tag, mt):
        nonlocal live, peak
        with lock:
            live += 1
            peak = max(peak, live)
        time.sleep(0.02)
        with lock:
            live -= 1
        return "ok", {}, 0.0

    c = V.ThrottledCaller(inner, tmp_path / "c", max_concurrency=2)
    ts = [threading.Thread(target=c, args=("gemini", f"p{i}", "t")) for i in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert peak <= 2 and c.stats["calls"] == 8


def test_cache_prevents_repeat_calls_and_repeat_number_separates(tmp_path):
    n = []
    c = V.ThrottledCaller(lambda j, p, t, m: (n.append(1) or "x", {}, 0.0), tmp_path / "c")
    c("gemini", "p", "t")
    c("gemini", "p", "t")
    assert len(n) == 1 and c.stats["cache_hits"] == 1
    c.for_item("", 2)("gemini", "p", "t")
    assert len(n) == 2


def test_backoff_on_rate_limit_then_success(tmp_path):
    seq = ["429 too many requests", "429 too many requests", None]
    sleeps = []

    def inner(j, p, t, m):
        e = seq.pop(0)
        if e:
            raise RuntimeError(e)
        return "ok", {}, 0.0

    c = V.ThrottledCaller(inner, tmp_path / "c", sleep=sleeps.append)
    assert c("gemini", "p", "t")[0] == "ok" and len(sleeps) == 2 and sleeps[1] > sleeps[0]


def test_non_rate_error_propagates(tmp_path):
    def inner(*a):
        raise ValueError("bad request")
    with pytest.raises(ValueError):
        V.ThrottledCaller(inner, tmp_path / "c")("gemini", "p", "t")


def test_resume_and_limit_skip_finished_items(tmp_path, monkeypatch):
    seen = []

    def fake(call, root, run_dir, it, keys):
        seen.append(it["item_id"])
        f = V.item_file(run_dir, it)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("{}")
        return {"panel": {"panel_pass_rate": 1.0}, "hallucination": {"upheld_material": []}, "wall_s": 0}

    monkeypatch.setattr(V, "run_item", fake)
    items = [{"item_id": f"i{k}", "case_id": "C-0005", "type": "M1", "dir": tmp_path, "repeat": 1} for k in range(4)]
    caller = V.ThrottledCaller(lambda *a: ("", {}, 0), tmp_path / "c")
    V.run_items(caller, DATA, tmp_path, items, limit=2, log=lambda *_: None)
    assert seen == ["i0", "i1"]
    V.run_items(caller, DATA, tmp_path, items, resume=True, log=lambda *_: None)
    assert seen == ["i0", "i1", "i2", "i3"]  # finished items not repeated


def test_round_robin_covers_types_in_first_five():
    items = [{"type": t, "item_id": f"{t}{k}"} for t in ("M1", "M2", "M3", "M4", "M5") for k in range(3)]
    assert {i["type"] for i in V.round_robin(items)[:5]} == {"M1", "M2", "M3", "M4", "M5"}


def test_estimate_scales():
    e = V.estimate([{}] * 10, 2)
    assert e["items"] == 10 and e["prompt_tokens"] == 880_000


# ---------------------------------------------------------------- regression: every control and mutation type through the real runner path
def mock_inner_for(item_dir):
    """Mock judge: grader passes every criterion quoting a real deliverable line; stage 1 flags one real line; stage 2 upholds as material."""
    import re
    text = (Path(item_dir) / "deliverable.md").read_text()
    quote = next(ln.strip() for ln in text.split("\n") if len(ln.strip()) > 40)

    def inner(jkey, prompt, tag, max_tokens):
        usage = {"prompt_tokens": 10, "completion_tokens": 5}
        if "REFERENCE:" in prompt:
            ids = re.findall(r"(?m)^\[([A-Z]+\d+)\] \(", prompt)
            return json.dumps({"results": [{"id": i, "verdict": "PASS", "evidence_quote": quote, "reason": "ok"} for i in ids]}), usage, 0.0
        fids = re.findall(r"(?m)^\[(F\d+)\] quote:", prompt)
        if fids:
            return json.dumps({"adjudications": [{"flag_id": f, "upheld": True, "severity": "material", "reason": "x"} for f in fids]}), usage, 0.0
        return json.dumps({"flags": [{"quote": quote, "problem": "unsupported"}]}), usage, 0.0

    return inner


def test_every_control_and_mutation_type_runs_through_runner(tmp_path):
    items, _ = M.generate(DATA, CASES)
    first = {}
    for it in items:
        first.setdefault(it["type"], it)
    assert set(first) == set(M.TYPES + M.CONTROLS)
    M.write_items(items, [], tmp_path / "mutations")
    run_items = V.mutation_items(tmp_path)
    picks = [i for i in run_items if i["item_id"] == first[i["type"]]["item_id"]]
    picks.append({"item_id": "C1__C-0005", "case_id": "C-0005", "type": "C1", "dir": DATA / "cases" / "C-0005" / "gold", "repeat": 1})
    logs = []
    for it in picks:  # per-item mock, since the mock quotes that item's own deliverable
        caller = V.ThrottledCaller(mock_inner_for(it["dir"]), tmp_path / "cache")
        res = V.run_items(caller, DATA, tmp_path / "run", [it], log=logs.append)
        assert res["failed"] == 0, (it["item_id"], logs[-1])
        out = json.loads(V.item_file(tmp_path / "run", it).read_text())
        assert {"item_id", "case_id", "type", "repeat", "panel", "hallucination", "wall_s"} <= set(out)
        assert set(out["panel"]["panel"]) and isinstance(out["hallucination"]["upheld_material"], int)
        assert {"flags", "upheld_material", "upheld_minor"} <= set(out["hallucination"])
    assert len(picks) == 16 and not (tmp_path / "run" / "errors.jsonl").exists()


def test_failed_item_is_logged_with_traceback_and_retried_on_resume(tmp_path):
    it = {"item_id": "C-0005__C2", "case_id": "C-0005", "type": "C2", "dir": DATA / "cases" / "C-0005" / "gold", "repeat": 1}

    def boom(*a):
        raise ValueError("bad response")

    logs = []
    res = V.run_items(V.ThrottledCaller(boom, tmp_path / "cache"), DATA, tmp_path / "run", [it], log=logs.append, debug=True)
    assert res["failed"] == 1 and "FAILED" in logs[0] and "Traceback" in logs[1]
    rec = json.loads((tmp_path / "run" / "errors.jsonl").read_text().splitlines()[0])
    assert rec["status"] == "FAILED" and "ValueError" in rec["traceback"]
    assert not V.item_file(tmp_path / "run", it).exists()  # never recorded as a result
    res2 = V.run_items(V.ThrottledCaller(mock_inner_for(it["dir"]), tmp_path / "cache"), DATA, tmp_path / "run", [it], log=lambda *_: None)
    assert res2["done"] == 1 and not (tmp_path / "run" / "failed" / V.item_file(tmp_path / "run", it).name).exists()
