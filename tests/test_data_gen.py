import json
import shutil
from collections import Counter

import pytest
from pydantic import ValidationError

from data_gen import reference as R
from data_gen import validate_data as V
from data_gen.gen_cases import DEFAULT_SEED, generate_all, write_dataset
from data_gen.schema import Decision, Truth


@pytest.fixture(scope="module")
def truths():
    return generate_all(DEFAULT_SEED)


@pytest.fixture()
def dataset(tmp_path, truths):
    write_dataset(truths, tmp_path, DEFAULT_SEED)
    return tmp_path


def load(t):
    return Truth.model_validate_json(t.model_dump_json())


def check(t, raw=""):
    rep = V.Report()
    V.check_case(t, rep, raw)
    return rep


# ---- schema
def test_schema_roundtrip(truths):
    t = truths[0]
    assert Truth.model_validate_json(t.model_dump_json()) == t


def test_schema_rejects_extra_and_bad_fields(truths):
    d = json.loads(truths[0].model_dump_json())
    with pytest.raises(ValidationError):
        Truth.model_validate({**d, "surprise": 1})
    with pytest.raises(ValidationError):
        Truth.model_validate({**d, "claim": {**d["claim"], "claim_no": "12"}})
    with pytest.raises(ValidationError):
        Truth.model_validate({**d, "traps": ["note_after_dos", "deadline_passed", "deadline_within_7_days"]})
    d.pop("facts")
    with pytest.raises(ValidationError):
        Truth.model_validate(d)


# ---- generator
def test_determinism(tmp_path, truths):
    a, b, c = tmp_path / "a", tmp_path / "b", tmp_path / "c"
    write_dataset(truths, a, DEFAULT_SEED)
    write_dataset(generate_all(DEFAULT_SEED), b, DEFAULT_SEED)
    write_dataset(generate_all(DEFAULT_SEED + 1), c, DEFAULT_SEED + 1)
    files = lambda r: {p.relative_to(r): p.read_bytes() for p in r.rglob("*.json")}  # noqa: E731
    assert files(a) == files(b)
    assert files(a) != files(c)


def test_counts_and_split(truths):
    assert len(truths) == 60
    assert Counter(t.split for t in truths) == {"dev": 12, "test": 48}
    for cat in range(1, 13):
        assert Counter(t.split for t in truths if t.category == cat) == {"dev": 1, "test": 4}


def test_decision_mix(truths):
    c = Counter(t.correct_decision for t in truths)
    assert c[Decision.APPEAL] == 22 and c[Decision.CORRECT_AND_RESUBMIT] == 13
    assert c[Decision.DO_NOT_APPEAL] + c[Decision.ESCALATE_MISSING_DOCS] == 25


def test_traps_and_fictional_payers(truths):
    assert all(len(t.traps) <= 2 for t in truths)
    assert {t.payer_id for t in truths} <= set(R.PAYERS)
    assert any(t.traps for t in truths) and any(not t.traps for t in truths)


def test_deadline_math(truths):
    for t in truths:
        assert (t.appeal_deadline - t.denial.denial_date).days == R.PAYERS[t.payer_id]["appeal_days"]


# ---- validators
def test_clean_dataset_passes(dataset):
    rep, ts = V.validate(dataset, check_docs=False)
    assert rep.errors == [] and len(ts) == 60


def test_validator_main_exit_codes(dataset):
    assert V.main(["--data", str(dataset), "--truth-only"]) == 0
    (dataset / "manifest.json").write_text("{}")
    assert V.main(["--data", str(dataset), "--truth-only"]) == 1


def test_wrong_deadline_detected(truths):
    t = load(truths[0])
    t.appeal_deadline = t.appeal_deadline.replace(year=t.appeal_deadline.year + 1)
    assert any("appeal_deadline" in e["message"] for e in check(t).errors)


def test_dates_out_of_order_detected(truths):
    t = load(truths[0])
    t.claim.dos = t.denial.denial_date.replace(year=t.denial.denial_date.year + 1)
    assert any("expected DOS <= submitted" in e["message"] for e in check(t).errors)


def test_decision_category_mismatch_detected(truths):
    t = load(next(x for x in truths if x.category == 6))
    t.correct_decision = Decision.APPEAL
    assert any("not allowed for category" in e["message"] for e in check(t).errors)


def test_split_count_tamper_detected(dataset):
    man = json.loads((dataset / "manifest.json").read_text())
    tpath = dataset / next(c for c in man["cases"] if c["split"] == "test")["path"]
    d = json.loads(tpath.read_text())
    d["split"] = "dev"
    tpath.write_text(json.dumps(d))
    rep, _ = V.validate(dataset, check_docs=False)
    assert any("split" in e["message"] for e in rep.errors)
    assert any("dataset_hash" in e["message"] for e in rep.errors)


def test_missing_field_detected(dataset):
    man = json.loads((dataset / "manifest.json").read_text())
    p = dataset / man["cases"][0]["path"]
    d = json.loads(p.read_text())
    del d["claim"]["cpt"]
    p.write_text(json.dumps(d))
    rep, _ = V.validate(dataset, check_docs=False)
    assert any("cannot load" in e["message"] for e in rep.errors)


def test_ssn_detected(truths):
    t = truths[0]
    assert check(t, "ssn 123-45-6789").errors
    rep = check(t, "ssn 912-45-6789")
    assert not rep.errors and rep.reviews


def test_unknown_code_goes_to_review_not_silent(truths):
    t = load(truths[0])
    t.claim.icd10 = ["Z99.99"]
    rep = check(t)
    assert any("not in local code table" in r["message"] for r in rep.reviews)


def test_invalid_pairing_is_error(truths):
    t = load(next(x for x in truths if x.category == 1))
    t.claim.icd10 = ["J06.9"]
    assert any("not valid in the table" in e["message"] for e in check(t).errors)


def test_category_11_pairing_is_invalid_by_design(truths):
    t = next(x for x in truths if x.category == 11)
    assert not check(t).errors
    for x in (t,):
        assert x.claim.icd10[0] not in R.VALID_PAIRS[x.claim.cpt]


def test_evidence_must_be_planned_document(truths):
    t = load(truths[0])
    t.policy_criteria[0].evidence = ["notes/2020-01-01_nonexistent.txt"]
    assert any("not a planned document" in e["message"] for e in check(t).errors)


# ---- tri-state criterion status (Step 0)
def test_status_is_tristate_and_met_bool_is_gone(truths):
    assert {c.status for t in truths for c in t.policy_criteria} == {"met", "unmet", "unknown"}
    d = json.loads(truths[0].model_dump_json())
    d["policy_criteria"][0]["status"] = "maybe"
    with pytest.raises(ValidationError):
        Truth.model_validate(d)
    d["policy_criteria"][0].pop("status")
    d["policy_criteria"][0]["met"] = True
    with pytest.raises(ValidationError):
        Truth.model_validate(d)


def test_escalate_cases_use_unknown(truths):
    esc = [t for t in truths if t.correct_decision == Decision.ESCALATE_MISSING_DOCS]
    assert len(esc) == 2
    for t in esc:
        assert [c.status for c in t.policy_criteria].count("unknown") >= 1
    for t in truths:
        if t.correct_decision != Decision.ESCALATE_MISSING_DOCS:
            assert all(c.status != "unknown" for c in t.policy_criteria)


def test_unknown_on_non_escalate_is_flagged(truths):
    t = load(next(x for x in truths if x.category == 6))
    t.policy_criteria[0].status = "unknown"
    assert any("'unknown' criterion" in e["message"] for e in check(t).errors)


def test_policy_effective_trap_matches_dos(truths):
    for t in truths:
        eff = R.POLICY_EFFECTIVE[t.policy_id]
        assert (t.claim.dos < eff) == ("policy_effective_after_dos" in [x.value for x in t.traps])


# ---- step 2/5 generator rules

def test_no_stacked_traps_and_action_deadline(truths):
    from data_gen.gen_cases import HARD_TRAPS
    for t in truths:
        assert sum(x in HARD_TRAPS for x in t.traps) <= 1 and len(t.traps) <= 2
        want = [f.value for f in t.facts if f.key == "corrected_claim_deadline"][0] \
            if t.correct_decision == Decision.CORRECT_AND_RESUBMIT else t.appeal_deadline.isoformat()
        assert t.action_deadline.isoformat() == want


def test_criterion_trap_only_on_escalate(truths):
    for t in truths:
        has = "criterion_no_supporting_doc" in [x.value for x in t.traps]
        assert has == (t.correct_decision == Decision.ESCALATE_MISSING_DOCS)


def test_coding_data_rules(truths):
    for t in truths:
        if t.category in (1, 2):
            assert len(t.claim.icd10) == 1
        if t.denial.carc in ("CO-197", "CO-4", "CO-18", "CO-16"):
            assert t.denial.rarc is None
        assert t.claim.cpt != "99214"
        if t.category == 9:
            f = {x.key: x.value for x in t.facts}
            assert (f["column1_code"], t.claim.cpt) in R.BUNDLE_PAIRS and ("20610", "76942") not in R.BUNDLE_PAIRS
        if t.category == 12:
            assert [x.value for x in t.facts if x.key == "denied_visit_number"][0] == R.PT_VISIT_LIMIT + 1

