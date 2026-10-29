import json
import shutil
from pathlib import Path

import pytest

from data_gen import validate_data as V
from data_gen.docs_util import locate, needle
from data_gen.gen_cases import DEFAULT_SEED, generate_all, load_truths, write_dataset
from data_gen.render_docs import render_all
from data_gen.schema import Fact

REAL = Path(__file__).resolve().parents[1] / "data"
needs_real = pytest.mark.skipif(not (REAL / "policy_library").exists() or not (REAL / "manifest.json").exists(),
                                reason="run gen_cases/render_docs/gen_policies/gen_clinical first")


@pytest.fixture()
def full(tmp_path):
    shutil.copytree(REAL, tmp_path / "data")
    return tmp_path / "data"


def errors(root):
    rep, _ = V.validate(root)
    return [e["message"] for e in rep.errors]


def pilot_case(root):
    return json.loads((root / "manifest.json").read_text())["pilot_cases"][0]


# ---- deterministic rendering
def test_render_is_deterministic(tmp_path):
    for name in ("a", "b"):
        write_dataset(generate_all(DEFAULT_SEED), tmp_path / name, DEFAULT_SEED)
        render_all(tmp_path / name, DEFAULT_SEED)
    snap = lambda r: {p.relative_to(r): p.read_bytes() for p in (r / "cases").rglob("*") if p.is_file()}  # noqa: E731
    assert snap(tmp_path / "a") == snap(tmp_path / "b")


def test_rendered_docs_follow_truth_and_hide_answers(tmp_path):
    write_dataset(generate_all(DEFAULT_SEED), tmp_path, DEFAULT_SEED)
    render_all(tmp_path, DEFAULT_SEED)
    _, truths = load_truths(tmp_path)
    for t in truths:
        base = tmp_path / "cases" / t.case_id
        eob, den, task = (base / "docs" / "eob_835.txt").read_text(), (base / "docs" / "denial_letter.txt").read_text(), (base / "task.md").read_text()
        assert t.claim.claim_no in eob and t.claim.claim_no in den and t.appeal_deadline.isoformat() in den
        assert [f.value for f in t.facts if f.key == "as_of_date"][0] in task  # every task states the as-of date
        for text in (eob, den):
            assert text.rstrip().endswith("SYNTHETIC DATA - NOT REAL PHI")
            assert t.correct_decision.value not in text and "trap" not in text.lower()


def test_task_phrasing_varies(tmp_path):
    write_dataset(generate_all(DEFAULT_SEED), tmp_path, DEFAULT_SEED)
    render_all(tmp_path, DEFAULT_SEED)
    bodies = {(p.read_text().split("\n\n")[1]).split(str(1))[0][:25] for p in (tmp_path / "cases").glob("C-*/task.md")}
    assert len(bodies) >= 5


def test_locate_and_needle():
    f = Fact(key="k", value="x", source_file="a.txt", evidence="alpha  beta")
    assert locate("one\nalpha beta gamma\n", f) == 2
    assert needle(Fact(key="billed", value=12.5, source_file="a")) == "12.50"
    assert needle(Fact(key="flag", value=True, source_file="a")) is None


# ---- full-dataset validation (uses the generated pilot data)
@needs_real
def test_full_dataset_validates(full):
    assert errors(full) == []


@needs_real
def test_pilot_set_and_lines(full):
    man = json.loads((full / "manifest.json").read_text())
    assert len(man["pilot_cases"]) == 5 and man["datagen"]["model_id"] != man["datagen"]["agent_model_id"]
    _, truths = load_truths(full)
    by = {t.case_id: t for t in truths}
    for cid in man["pilot_cases"]:
        quotes = [f for f in by[cid].facts if f.evidence]
        assert quotes and all(f.line for f in quotes)


@needs_real
def test_detects_missing_footer(full):
    p = full / "cases" / pilot_case(full) / "docs" / "denial_letter.txt"
    p.write_text(p.read_text().replace("SYNTHETIC DATA - NOT REAL PHI", ""))
    assert any("does not end with" in e for e in errors(full))


@needs_real
def test_detects_leaks(full):
    p = next((full / "cases" / pilot_case(full) / "docs" / "notes").glob("*pcp.txt"))
    p.write_text(p.read_text().replace("SYNTHETIC DATA", "see truth.json; deadline_passed\nSYNTHETIC DATA"))
    assert any("leaks answer-key vocabulary" in e for e in errors(full))


@needs_real
def test_detects_decision_word_in_agent_file(full):
    p = full / "cases" / pilot_case(full) / "docs" / "eob_835.txt"
    p.write_text(p.read_text().replace("SYNTHETIC DATA", "DO_NOT_APPEAL\nSYNTHETIC DATA"))
    assert any("mentions decision value" in e for e in errors(full))


@needs_real
def test_detects_answer_key_under_mount(full):
    (full / "cases" / pilot_case(full) / "docs" / "truth.json").write_text("{}")
    assert any("answer-key file" in e for e in errors(full))


@needs_real
def test_detects_wrong_policy_window(full):
    p = full / "policy_library" / "MP-IMG-007.txt"
    p.write_text(p.read_text().replace("7.1 Appeal deadline: 180 days", "7.1 Appeal deadline: 170 days"))
    assert any("Appeal deadline must state 180" in e for e in errors(full))


@needs_real
def test_detects_missing_policy_section(full):
    p = full / "policy_library" / "MP-IMG-007.txt"
    p.write_text(p.read_text().replace("Section 3.2(b)", "Section 3.9(z)"))
    assert any("section 3.2(b) does not exist" in e for e in errors(full))


@needs_real
def test_detects_wrong_denial_deadline(full):
    _, truths = load_truths(full)
    t = truths[0]
    p = full / "cases" / t.case_id / "docs" / "denial_letter.txt"
    p.write_text(p.read_text().replace(t.appeal_deadline.isoformat(), "2031-01-01"))
    assert any("expected" in e and t.appeal_deadline.isoformat() in e for e in errors(full))


@needs_real
def test_detects_missing_evidence_quote(full):
    man = json.loads((full / "manifest.json").read_text())
    _, truths = load_truths(full)
    t = next(x for x in truths if x.case_id in man["pilot_cases"] and any(f.evidence and f.source_file.startswith("notes/") for f in x.facts))
    f = next(f for f in t.facts if f.evidence and f.source_file.startswith("notes/"))
    p = full / "cases" / t.case_id / "docs" / f.source_file
    p.write_text(p.read_text().replace(f.evidence, "removed"))
    assert any("does not appear" in e for e in errors(full))


@needs_real
def test_detects_clinical_docs_outside_pilot(full):
    man = json.loads((full / "manifest.json").read_text())
    other = next(e["case_id"] for e in man["cases"] if e["case_id"] not in man["pilot_cases"])
    d = full / "cases" / other / "docs" / "notes"
    d.mkdir(parents=True)
    (d / "x.txt").write_text("x\nSYNTHETIC DATA - NOT REAL PHI\n")
    assert any("non-pilot case has clinical documents" in e for e in errors(full))


@needs_real
def test_detects_ssn_and_phone(full):
    p = full / "cases" / pilot_case(full) / "docs" / "eob_835.txt"
    p.write_text(p.read_text().replace("SYNTHETIC DATA", "SSN 123-45-6789 phone 212-5551\nSYNTHETIC DATA"))
    e = errors(full)
    assert any("invalid 9xx range" in x for x in e) and any("is not 555-01xx" in x for x in e)


@needs_real
def test_detects_hash_drift(full):
    p = full / "cases" / pilot_case(full) / "task.md"
    p.write_text(p.read_text() + "\n")
    assert any("dataset_hash" in e for e in errors(full))


# ---- generation guards
def test_clinical_body_guards():
    from datetime import date

    from data_gen.gen_clinical import Doc, check_body
    d = Doc("notes/x.txt", "pcp", date(2026, 3, 1), "Dr X", ["Started on 2026-03-01."])
    ok = "Plan: Started on 2026-03-01. Continue exercises."
    assert check_body(ok, d, {date(2026, 3, 1)}, set()) == []
    bad = "Started on 2026-03-01. Seen again 2026-04-02 after 6 weeks; claim filed; code Z99.9."
    msg = " ".join(check_body(bad, d, {date(2026, 3, 1)}, set()))
    assert "dates not allowed" in msg and "durations" in msg and "forbidden word" in msg and "codes not allowed" in msg
    assert any("missing required" in m for m in check_body("nothing", d, {date(2026, 3, 1)}, set()))


def test_policy_helpers():
    from data_gen.gen_policies import _parse, perturb
    assert perturb("at least 6 weeks within 12 months") == "at least 4 weeks within 6 months"
    got = _parse("### 1\nPurpose text\n### 3.2(a)\nBody  one\n### 3.2(b)\nBody two")
    assert got == {"1": "Purpose text", "3.2(a)": "Body one", "3.2(b)": "Body two"}


def test_datagen_model_must_not_be_agent():
    from data_gen.llm import datagen_model
    with pytest.raises(SystemExit):
        datagen_model({"datagen": {"model_id": "nvidia/nvidia/nemotron-3.5-super-text-preview"}, "agent": {"model_id": "x"}})
    assert datagen_model({"datagen": {"model_id": "azure/anthropic/claude-opus-4-8"}, "agent": {"model_id": "x"}})
