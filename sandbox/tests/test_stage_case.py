"""Staging never exposes anything outside the allowlist. Run: .venv/bin/python -m pytest sandbox/tests -q"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase0"))
import stage_case as sc  # noqa: E402

DATA = ROOT / "data"


def make_data(tmp_path):
    d = tmp_path / "data"
    (d / "cases" / "C-0001" / "docs" / "notes").mkdir(parents=True)
    (d / "cases" / "C-0001" / "gold").mkdir()
    (d / "policy_library").mkdir()
    c = d / "cases" / "C-0001"
    (c / "task.md").write_text("task")
    (c / "docs" / "eob_835.txt").write_text("eob")
    (c / "docs" / "notes" / "n.txt").write_text("note")
    for name in ("truth.json", "rubric.json", "extra_secret.txt", "notes.md"):
        (c / name).write_text("SECRET")
    (c / "gold" / "deliverable.md").write_text("SECRET")
    (c / "attacks").mkdir()
    (c / "attacks" / "a.json").write_text("SECRET")
    (d / "policy_library" / "MP-1.txt").write_text("policy")
    s = tmp_path / "skills"
    (s / "x" / "tests").mkdir(parents=True)
    (s / "x" / "__pycache__").mkdir()
    (s / "x" / "tool.py").write_text("pass")
    (s / "x" / "SKILL.md").write_text("md")
    (s / "x" / "secret.json").write_text("SECRET")
    (s / "x" / "tests" / "t.py").write_text("SECRET")
    (s / "x" / "__pycache__" / "a.pyc").write_text("SECRET")
    return d, s


def listing(stage):
    return sorted(p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file())


def test_only_allowlisted_files_are_copied(tmp_path):
    d, s = make_data(tmp_path)
    stage = sc.stage_case("C-0001", d, tmp_path / "out", s)
    assert listing(stage) == ["case/docs/eob_835.txt", "case/docs/notes/n.txt", "case/task.md",
                              "policy_library/MP-1.txt", "skills/x/SKILL.md", "skills/x/tool.py"]
    assert "SECRET" not in "".join((stage / p).read_text() for p in listing(stage))


@pytest.mark.parametrize("name", ["truth.json", "rubric.json", "gold", "attacks"])
def test_forbidden_name_inside_docs_fails_closed(tmp_path, name):
    d, s = make_data(tmp_path)
    p = d / "cases" / "C-0001" / "docs" / name
    p.mkdir() if name in ("gold", "attacks") else p.write_text("SECRET")
    if p.is_dir():
        (p / "f.txt").write_text("SECRET")
    with pytest.raises(sc.StagingError):
        sc.stage_case("C-0001", d, tmp_path / "out", s)
    assert not (tmp_path / "out" / "C-0001").exists()


def test_symlink_refused(tmp_path):
    d, s = make_data(tmp_path)
    (d / "cases" / "C-0001" / "docs" / "link.txt").symlink_to(d / "cases" / "C-0001" / "truth.json")
    with pytest.raises(sc.StagingError):
        sc.stage_case("C-0001", d, tmp_path / "out", s)


def test_policy_library_subfolder_or_forbidden_name_refused(tmp_path):
    d, s = make_data(tmp_path)
    (d / "policy_library" / "sub").mkdir()
    with pytest.raises(sc.StagingError):
        sc.stage_case("C-0001", d, tmp_path / "out", s)


def test_verify_rejects_an_injected_file(tmp_path):
    d, s = make_data(tmp_path)
    stage = sc.stage_case("C-0001", d, tmp_path / "out", s)
    (stage / "case" / "truth.json").write_text("x")
    with pytest.raises(sc.StagingError):
        sc.verify(stage)


@pytest.mark.parametrize("cid", ["../C-0001", "C-1", "c-0001", "C-0001/x"])
def test_bad_case_id(tmp_path, cid):
    d, s = make_data(tmp_path)
    with pytest.raises(sc.StagingError):
        sc.stage_case(cid, d, tmp_path / "out", s)


@pytest.mark.skipif(not (DATA / "cases" / "C-0005").exists(), reason="data not generated")
def test_real_case_c0005(tmp_path):
    stage = sc.stage_case("C-0005", DATA, tmp_path / "out")
    files = listing(stage)
    assert "case/task.md" in files and any(f.startswith("policy_library/") for f in files)
    for f in files:
        assert not any(part.lower() in sc.FORBIDDEN_NAMES for part in Path(f).parts)
        assert sc.allowed(Path(f))
    assert not (stage / "case" / "truth.json").exists() and not (stage / "case" / "gold").exists()
    assert {Path(f).parts[0] for f in files} == {"case", "policy_library", "skills"}
