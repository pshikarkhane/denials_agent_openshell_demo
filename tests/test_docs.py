import json
import shutil
from pathlib import Path

import pytest

from data_gen import reference as R
from data_gen import validate_data as V
from data_gen.docs_util import locate, needle
from data_gen.gen_cases import DEFAULT_SEED, generate_all, load_truths, write_dataset
from data_gen.render_docs import render_all
from data_gen.schema import Decision, Fact

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
    p.write_text(p.read_text().replace("Section 2.1(b)", "Section 2.9(z)"))
    assert any("section 2.1(b) does not exist" in e for e in errors(full))


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


# ---- step 6 validators (each has a mutation test)
def edit_truth(root, case_id, fn):
    p = root / "cases" / case_id / "truth.json"
    d = json.loads(p.read_text())
    fn(d)
    p.write_text(json.dumps(d, indent=2))


def case_of(root, cat, pilot=True):
    man = json.loads((root / "manifest.json").read_text())
    return next(e["case_id"] for e in man["cases"] if e["category"] == cat and (e["case_id"] in man["pilot_cases"]) == pilot)


@needs_real
def test_validate_data_is_read_only(full):
    before = {p: p.read_bytes() for p in full.rglob("*") if p.is_file()}
    V.main(["--data", str(full)])
    assert {p: p.read_bytes() for p in full.rglob("*") if p.is_file()} == before
    with pytest.raises(SystemExit):
        V.main(["--data", str(full), "--report", str(full / "report.json")])


@needs_real
def test_detects_stacked_traps(full):
    cid = case_of(full, 6)
    edit_truth(full, cid, lambda d: d.update(traps=["deadline_within_7_days", "note_after_dos"]))
    assert any("stacked hard traps" in e for e in errors(full))


@needs_real
def test_detects_criterion_trap_on_appeal_case(full):
    cid = case_of(full, 1, pilot=False)
    edit_truth(full, cid, lambda d: d.update(traps=d["traps"][:1] + ["criterion_no_supporting_doc"]))
    assert any("criterion_no_supporting_doc must be present exactly on ESCALATE" in e for e in errors(full))


@needs_real
def test_detects_wrong_action_deadline(full):
    cid = case_of(full, 8)
    edit_truth(full, cid, lambda d: d.update(action_deadline=d["appeal_deadline"]))
    assert any("action_deadline" in e and "must be the corrected-claim" in e for e in errors(full))


@needs_real
def test_deadline_trap_is_measured_on_action_deadline(full):
    man = json.loads((full / "manifest.json").read_text())
    cid = next(e["case_id"] for e in man["cases"] if e["category"] == 8 and not any(
        x.startswith("deadline") for x in json.loads((full / e["path"]).read_text())["traps"]))
    def fn(d):
        d["traps"] = ["deadline_within_7_days"]
    edit_truth(full, cid, fn)
    assert any("deadline_within_7_days but" in e for e in errors(full))


@needs_real
def test_detects_excludes1(full):
    cid = case_of(full, 1, pilot=False)
    edit_truth(full, cid, lambda d: d["claim"].update(icd10=["M54.16", "M51.16"]))
    e = errors(full)
    assert any("Excludes1" in x for x in e) and any("exactly one diagnosis" in x for x in e)


@needs_real
def test_detects_missing_corrected_claim_sentence(full):
    p = full / "policy_library" / "MP-CLM-004.txt"
    p.write_text(p.read_text().replace("An appeal does not cure missing or invalid claim data.", "Appeals are reviewed."))
    assert any("corrected-claim sentence" in e for e in errors(full))
    p = full / "policy_library" / "MP-BND-002.txt"
    p.write_text(p.read_text().replace("CPT 97530", "CPT 11111"))
    assert any("bundled pair" in e for e in errors(full))


@needs_real
def test_detects_policy_order_gap_and_removed_wording(full):
    p = full / "policy_library" / "MP-CLM-004.txt"
    t = p.read_text()
    p.write_text(t.replace("Section 2.3", "Section 9.9").replace("Section 3  Corrections", "Section 2.3  Corrections"))
    e = errors(full)
    assert any("not in numeric order" in x for x in e)
    p = full / "policy_library" / "MP-PT-011.txt"
    p.write_text(p.read_text() + "approved exception\n")
    assert any("removed wording" in x for x in errors(full))


@needs_real
def test_detects_tf010_contradiction_and_missing_supersession(full):
    p = full / "policy_library" / "MP-TF-010.txt"
    p.write_text(p.read_text().replace("7.2 Timely filing limit: 60 days", "7.2 Timely filing limit: 90 days"))
    e = errors(full)
    assert any("7.2" in x for x in e)
    p.write_text(p.read_text().replace("SUPERSEDED", "CURRENT"))
    assert any("superseded" in x.lower() for x in errors(full))


@needs_real
def test_detects_claim_history_mismatch(full):
    cid = case_of(full, 6)
    p = full / "cases" / cid / "docs" / "claim_history.txt"
    t = json.loads((full / "cases" / cid / "truth.json").read_text())
    sub = next(f["value"] for f in t["facts"] if f["key"] == "claim_submitted_date")
    p.write_text(p.read_text().replace(sub, "2020-01-01"))
    assert any("claim_history" in e for e in errors(full))


@needs_real
def test_detects_missing_imaging_statement(full):
    cid = case_of(full, 1)
    p = next((full / "cases" / cid / "docs" / "notes").glob("*_ortho.txt"))
    p.write_text(p.read_text().replace("Imaging history:", "Imaging review:"))
    assert any("Imaging history" in e for e in errors(full))


@needs_real
def test_detects_misspelling_in_note(full):
    cid = case_of(full, 6)
    p = next((full / "cases" / cid / "docs" / "notes").glob("*_visit.txt"))
    p.write_text(p.read_text().replace("Reason for visit", "Reason for visit nontagender", 1))
    assert any("possible misspelling" in e for e in errors(full))


@needs_real
def test_detects_missing_lint_record_and_git_sha(full):
    m = json.loads((full / "manifest.json").read_text())
    m["note_lint"].pop(next(iter(m["note_lint"])))
    m.pop("git_sha")
    (full / "manifest.json").write_text(json.dumps(m))
    e = errors(full)
    assert any("note_lint" in x for x in e) and any("git_sha" in x for x in e)


@needs_real
def test_detects_unplanned_clinical_file(full):
    cid = case_of(full, 6)
    d = full / "cases" / cid / "docs" / "notes"
    (d / "2026-01-01_stale.txt").write_text("x\nSYNTHETIC DATA - NOT REAL PHI\n")
    assert any("not in the plan" in e for e in errors(full))


@needs_real
def test_detects_basis_status_disagreement(full):
    cid = case_of(full, 6)
    edit_truth(full, cid, lambda d: d["policy_criteria"][1].update(basis="missing_evidence"))
    assert any("disagree (unknown <=> missing_evidence)" in e for e in errors(full))


@needs_real
def test_detects_eob_realism_regressions(full):
    cid = case_of(full, 1)
    p = full / "cases" / cid / "docs" / "eob_835.txt"
    p.write_text(p.read_text().replace("835 REMITTANCE ADVICE", "835 REMITTANCE ADVICE (SYNTHETIC RENDERING)").replace("XXX-XX-", "912-34-"))
    e = " ".join(errors(full))
    assert "title must be" in e and "SSN" in e


# ---- generator rules



def test_clinical_truth_is_protected(tmp_path):
    root = tmp_path / "d"
    write_dataset(generate_all(DEFAULT_SEED), root, DEFAULT_SEED)
    p = root / "cases" / "C-0001" / "truth.json"
    d = json.loads(p.read_text())
    d["facts"][0]["evidence"] = "quote"
    p.write_text(json.dumps(d))
    with pytest.raises(SystemExit):
        write_dataset(generate_all(DEFAULT_SEED), root, DEFAULT_SEED)
    write_dataset(generate_all(DEFAULT_SEED), root, DEFAULT_SEED, force=True)


def test_claim_history_rendered_for_every_case(tmp_path):
    write_dataset(generate_all(DEFAULT_SEED), tmp_path, DEFAULT_SEED)
    render_all(tmp_path, DEFAULT_SEED)
    for p in (tmp_path / "cases").glob("C-*/docs/claim_history.txt"):
        assert p.read_text().rstrip().endswith("SYNTHETIC DATA - NOT REAL PHI")
    assert len(list((tmp_path / "cases").glob("C-*/docs/claim_history.txt"))) == 60


def test_eob_realism(tmp_path):
    write_dataset(generate_all(DEFAULT_SEED), tmp_path, DEFAULT_SEED)
    render_all(tmp_path, DEFAULT_SEED)
    _, truths = load_truths(tmp_path)
    for t in truths:
        eob = (tmp_path / "cases" / t.case_id / "docs" / "eob_835.txt").read_text()
        assert "SYNTHETIC RENDERING" not in eob and "SSN: XXX-XX-" in eob
        assert eob.count("SYN-") == 1 and "MRN: SYN-" in eob  # SYN- stays on the MRN only
        if t.claim.cpt in ("72148", "73721"):
            assert "(Radiology)" in eob
        if t.claim.cpt.startswith("97") and "(not provided)" not in eob.split("Rendering provider:")[1].splitlines()[0]:
            assert ", PT" in eob.split("Rendering provider:")[1].splitlines()[0]


def test_functional_metric_follows_diagnosis():
    import random as rnd

    from data_gen.gen_clinical import functional_sentence
    from data_gen.schema import Claim
    class T:  # minimal stand-in
        pass
    t = T()
    t.claim = Claim(claim_no="1234567", cpt="97110", icd10=["M25.562"], dos="2026-05-01", billed=100)
    s = functional_sentence(t, rnd.Random(1))
    assert "left knee" in s and "lumbar" not in s
    t.claim.icd10 = ["M54.50"]
    assert "lumbar flexion" in functional_sentence(t, rnd.Random(1))


def test_spellcheck_catches_typo_and_accepts_clinical_terms():
    from data_gen.note_lint import spell_issues
    assert [x["word"] for x in spell_issues("Abdomen soft, nontagender.")] == ["nontagender"]
    assert spell_issues("Radiculopathy with antalgic gait; metformin continued; paraspinal tenderness.") == []


def test_lint_reviewer_must_not_be_datagen_or_agent():
    from data_gen.llm import reviewer_model
    base = {"judges": {"gpt": "azure/openai/gpt-5.5", "claude": "azure/anthropic/claude-opus-4-8"}, "agent": {"model_id": "a"},
            "datagen": {"model_id": "azure/anthropic/claude-opus-4-8"}}
    assert reviewer_model({**base, "lint": {"reviewer": "gpt"}}) == "azure/openai/gpt-5.5"
    with pytest.raises(SystemExit):
        reviewer_model({**base, "lint": {"reviewer": "claude"}})


@needs_real
def test_detects_syn_prefix_on_non_mrn_ids_and_wrong_rendering_provider(full):
    cid = case_of(full, 1)
    p = full / "cases" / cid / "docs" / "eob_835.txt"
    p.write_text(p.read_text().replace("Trace number: ", "Trace number: SYN-EFT-").replace("(Radiology)", "(PCP)"))
    e = " ".join(errors(full))
    assert "SYN-" in e and "rendering provider" in e
