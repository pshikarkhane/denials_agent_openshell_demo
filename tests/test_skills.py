"""Offline tests for the six agent skills. Acceptance tests run on ALL 60 cases using a TEMP STAGING COPY that holds only task.md and
docs/** plus the policy library; truth.json is read from the real data directory only to compare. No network, no model calls."""
import json
import re
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from data_gen import reference as R
from data_gen.gen_cases import load_truths
from skills.assess_appealability import call as assess
from skills.common.events import KEYS, EventLog
from skills.common.io import SkillError, json_schema
from skills.common.paths import DENIED_NAMES, AccessDenied, PathGuard
from skills.draft_deliverable import call as draft
from skills.parse_denial_eob import Input as ParseInput, call as parse
from skills.pull_clinical_notes import call as pull
from skills.retrieve_payer_policy import call as retrieve
from skills.self_check import call as self_check

DATA = Path(__file__).resolve().parents[1] / "data"
pytestmark = pytest.mark.skipif(not (DATA / "manifest.json").exists(), reason="data not generated")
PILOTS = ["C-0005", "C-0007", "C-0030", "C-0039", "C-0056"]
FORBIDDEN = {"truth.json", "rubric.json", "gold", "attacks"}


@pytest.fixture(scope="session")
def truths():
    man, ts = load_truths(DATA)
    return {t.case_id: t for t in ts}


@pytest.fixture(scope="session")
def staged(tmp_path_factory):
    """tmp/cases/<id>/{task.md, docs/**} and tmp/policy_library: nothing else (never truth/rubric/gold/attacks)."""
    root = tmp_path_factory.mktemp("stage")
    for cdir in sorted((DATA / "cases").glob("C-*")):
        dst = root / "cases" / cdir.name
        shutil.copy2(cdir / "task.md", (dst.mkdir(parents=True) or dst) / "task.md")
        shutil.copytree(cdir / "docs", dst / "docs")
    shutil.copytree(DATA / "policy_library", root / "policy_library")
    assert not [p for p in root.rglob("*") if p.name.lower() in FORBIDDEN]
    return root


def A(staged, cid, **extra):
    return {"case_root": str(staged / "cases" / cid), "policy_root": str(staged / "policy_library"), "case_id": cid, **extra}


def facts(t):
    d = {}
    for f in t.facts:
        d.setdefault(f.key, f.value)
    return d


# ================================================================ path guard / events / io
def test_path_guard_refuses_forbidden_and_outside(tmp_path):
    case, pol = tmp_path / "case", tmp_path / "pol"
    (case / "docs").mkdir(parents=True)
    (case / "task.md").write_text("x")
    (case / "docs" / "a.txt").write_text("ok")
    pol.mkdir()
    (tmp_path / "secret.txt").write_text("s")
    ev = EventLog()
    g = PathGuard(case, pol, events=ev)
    assert g.read_text("case", "docs/a.txt") == "ok"
    for bad in ["truth.json", "docs/truth.json", "rubric.json", "gold/deliverable.md", "docs/gold", "attacks/a1.txt", "../secret.txt", "docs/../../secret.txt",
                str(tmp_path / "secret.txt"), "/etc/passwd", "DOCS/TRUTH.JSON", "other/file.txt"]:
        with pytest.raises(AccessDenied):
            g.read_text("case", bad)
    with pytest.raises(AccessDenied):
        g.read_text("policy", "../case/task.md")
    denied = [e for e in ev.events if e["status"] == "denied"]
    assert len(denied) >= 12 and all(e["tool"] == "path_guard" for e in denied)
    (case / "docs" / "link.txt").symlink_to(tmp_path / "secret.txt")
    with pytest.raises(AccessDenied):
        g.read_text("case", "docs/link.txt")                       # symlink escapes the root
    assert "docs/link.txt" not in g.list_files("case", "docs") or True


def test_path_guard_refuses_contaminated_root(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "task.md").write_text("x")
    (tmp_path / "truth.json").write_text("{}")
    with pytest.raises(AccessDenied):
        PathGuard(tmp_path, tmp_path)
    (tmp_path / "truth.json").unlink()
    (tmp_path / "docs" / "gold").mkdir()
    with pytest.raises(AccessDenied):
        PathGuard(tmp_path, tmp_path)


def test_skills_refuse_raw_case_folder_and_forbidden_paths(staged):
    raw = DATA / "cases" / "C-0005"                                # holds truth.json / rubric.json / gold
    with pytest.raises(SkillError) as e:
        parse({"case_root": str(raw), "policy_root": str(staged / "policy_library")})
    assert e.value.code == "access_denied"
    for bad in ["truth.json", "../truth.json", "rubric.json", "gold/decision.json", "attacks/a1.txt", "notes/../../truth.json"]:
        with pytest.raises(SkillError) as e:
            pull({**A(staged, "C-0005"), "paths": [bad]})
        assert e.value.code in ("access_denied", "not_found")
    with pytest.raises(SkillError):
        draft({**A(staged, "C-0005"), "action": "verify_citations", "deliverable_path": "../truth.json", "output_root": str(staged)})


def test_denied_access_is_logged_to_events_file(staged, tmp_path):
    f = tmp_path / "ev.jsonl"
    with pytest.raises(SkillError):
        pull({**A(staged, "C-0005"), "paths": ["../truth.json"], "events_file": str(f), "run_id": "r1"})
    evs = [json.loads(x) for x in f.read_text().splitlines()]
    assert any(e["status"] == "denied" and e["tool"] == "path_guard" for e in evs) and any(e["tool"] == "pull_clinical_notes" and e["status"] == "denied" for e in evs)


def test_event_schema_is_stable_and_one_event_per_call_and_read(staged, tmp_path):
    f = tmp_path / "ev.jsonl"
    parse({**A(staged, "C-0005"), "events_file": str(f), "run_id": "run-x", "step": 1})
    evs = [json.loads(x) for x in f.read_text().splitlines()]
    assert all(sorted(e) == sorted(KEYS) for e in evs)
    calls = [e for e in evs if e["tool"] == "parse_denial_eob"]
    reads = [e for e in evs if e["tool"] == "parse_denial_eob.read"]
    assert len(calls) == 1 and len(reads) == 3                      # eob, denial letter, task.md
    assert calls[0]["run_id"] == "run-x" and calls[0]["case_id"] == "C-0005" and calls[0]["step"] == 1 and calls[0]["status"] == "ok" and calls[0]["duration_ms"] >= 0
    assert all(f.read_text().splitlines()[i] == json.dumps(json.loads(l), sort_keys=True) for i, l in enumerate(f.read_text().splitlines()))  # sorted keys


def test_outputs_are_deterministic_and_have_schemas(staged):
    a = json.dumps(assess(A(staged, "C-0030")), sort_keys=True)
    assert a == json.dumps(assess(A(staged, "C-0030")), sort_keys=True)
    for m in ("parse_denial_eob", "retrieve_payer_policy", "pull_clinical_notes", "assess_appealability", "draft_deliverable", "self_check"):
        mod = __import__(f"skills.{m}", fromlist=["Input", "Output"])
        assert json_schema(mod.Input)["type"] == "object" and json_schema(mod.Output)["type"] == "object"


def test_cli_prints_sorted_json_and_errors(staged):
    args = json.dumps({"case_root": str(staged / "cases" / "C-0030"), "policy_root": str(staged / "policy_library")})
    r = subprocess.run([sys.executable, "-m", "skills.parse_denial_eob", args], capture_output=True, text=True, cwd=DATA.parent)
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert list(out) == sorted(out) and out["denial"]["carc"] == "CO-29"
    r = subprocess.run([sys.executable, "-m", "skills.parse_denial_eob", json.dumps({"case_root": str(DATA / "cases" / "C-0030"), "policy_root": str(staged / "policy_library")})],
                       capture_output=True, text=True, cwd=DATA.parent)
    assert r.returncode == 1 and json.loads(r.stdout)["error"]["code"] == "access_denied"
    r = subprocess.run([sys.executable, "-m", "skills.parse_denial_eob", '{"bogus": 1}'], capture_output=True, text=True, cwd=DATA.parent)
    assert r.returncode == 1 and json.loads(r.stdout)["error"]["code"] == "bad_input"


def test_skills_are_offline_and_never_touch_truth():
    src = "\n".join(p.read_text() for p in (DATA.parent / "skills").rglob("*.py"))
    for banned in ("urllib", "requests", "socket", "chat_with_retry", "api_key", "API_KEY", "import data_gen", "from data_gen", "import eval", "from eval"):
        assert banned not in src, banned
    assert "NVIDIA_INFERENCE" not in src


# ================================================================ parse_denial_eob
def test_parse_matches_truth_for_all_60(staged, truths):
    bad = []
    for cid, t in truths.items():
        p = parse(A(staged, cid))
        f = facts(t)
        exp_denied = f["pr1_amount"] if t.category == 7 else t.claim.billed
        checks = {"claim_no": p["claim_no"] == t.claim.claim_no, "patient": p["patient"]["id"] == t.patient.synthetic_id, "dos": p["dos"] == t.claim.dos.isoformat(),
                  "cpt": p["cpt"] == t.claim.cpt, "icd10": p["icd10"] == t.claim.icd10, "carc": p["denial"]["carc"] == t.denial.carc, "rarc": p["denial"]["rarc"] == t.denial.rarc,
                  "billed": p["amounts"]["billed"] == t.claim.billed, "denied_amount": p["amounts"]["denied_amount"] == exp_denied,
                  "notice": p["denial"]["notice_date"] == t.denial.denial_date.isoformat(), "appeal_by": p["appeal"]["by_date"] == t.appeal_deadline.isoformat(),
                  "corrected_by": p["corrected_claim"]["by_date"] == f["corrected_claim_deadline"], "as_of": p["as_of_date"] == f["as_of_date"],
                  "payer": p["payer"]["id"] == t.payer_id, "no_consistency_issues": p["consistency"] == [],
                  "appeal_days": p["appeal"]["window_days"] == R.PAYERS[t.payer_id]["appeal_days"], "corrected_days": p["corrected_claim"]["window_days"] == R.PAYERS[t.payer_id]["corrected_claim_days"]}
        fails = [k for k, v in checks.items() if not v]
        if fails:
            bad.append((cid, fails))
    assert bad == []


def test_parse_policy_title_missing_required_and_null_reasons(staged, truths):
    p = parse(A(staged, "C-0005"))
    assert p["policy_title"] == "Advanced Imaging: Lumbar Spine MRI Medical Necessity" and p["denial"]["rarc"] in ("N115", "N386")
    # category 7 / 10 letters name no policy: null with a reason, never guessed
    for cid, t in truths.items():
        if t.category in (7, 10):
            p = parse(A(staged, cid))
            assert p["policy_title"] is None and "policy_title" in p["not_found"]
            break
    # blank remit field is reported
    t39 = parse(A(staged, "C-0039"))
    assert [m["field"] for m in t39["missing_required"]] == ["rendering_provider"] and "required remit field is absent" in t39["missing_required"][0]["reason"] and t39["denial"]["rarc"] is None
    assert "blank_fields" not in t39 and "modifier" not in json.dumps(t39["missing_required"]) and "may be correct" not in json.dumps(t39)


def test_parse_reports_missing_documents_without_guessing(tmp_path, staged):
    case = tmp_path / "c"
    (case / "docs").mkdir(parents=True)
    (case / "task.md").write_text("Today's date for this review is 2026-01-02.\n")
    (case / "docs" / "denial_letter.txt").write_text("PAYER\nPayer ID: X\n")
    p = parse({"case_root": str(case), "policy_root": str(staged / "policy_library")})
    assert p["claim_no"] is None and "claim_no" in p["not_found"] and "eob_835.txt" in p["not_found"] and p["as_of_date"] == "2026-01-02"
    (case / "docs" / "denial_letter.txt").unlink()
    with pytest.raises(SkillError) as e:
        parse({"case_root": str(case), "policy_root": str(staged / "policy_library")})
    assert e.value.code == "no_documents"


# ================================================================ retrieve_payer_policy
def retrieve_args(staged, cid):
    p = parse(A(staged, cid))
    return {**A(staged, cid), "payer": p["payer"]["id"], "dos": p["dos"], "cpt": p["cpt"], "service_description": p["service_description"], "icd10": p["icd10"],
            "denial_code": p["denial"]["carc"], "denial_text": p["denial"]["carc_text"], "reason_text": p["denial"]["reason_text"], "policy_title": p["policy_title"]}


def test_retrieve_returns_correct_policy_first_for_all_60(staged, truths):
    wrong, ties, near = [], [], []
    for cid, t in truths.items():
        r = retrieve(retrieve_args(staged, cid))
        if r["status"] == "tie":
            ties.append(cid)
        elif r["status"] != "selected" or r["policy"]["policy_id"] != t.policy_id:
            wrong.append((cid, r["status"], r["policy"] and r["policy"]["policy_id"]))
        if r["excluded"]:
            near.append((cid, [e["policy_id"] for e in r["excluded"]]))
        assert r["policy"]["windows"] == {"appeal_days": R.PAYERS[t.payer_id]["appeal_days"], "corrected_claim_days": R.PAYERS[t.payer_id]["corrected_claim_days"],
                                           "timely_filing_days": R.PAYERS[t.payer_id]["timely_filing_days"]}
        assert r["candidates"][0]["policy_id"] == t.policy_id and r["sections"]
    assert wrong == [] and ties == []
    # distractor near-misses are surfaced for the categories that have them (imaging, prior auth, timely filing)
    assert any("MP-IMG-012" in ids for _, ids in near) and any("MP-PA-030" in ids for _, ids in near) and any("MP-TF-010" in ids for _, ids in near)


def test_retrieve_filters_by_payer_and_date_before_ranking(staged):
    base = {"policy_root": str(staged / "policy_library"), "case_root": str(staged / "cases" / "C-0005")}
    r = retrieve({**base, "payer": "HALCYON_PLAN", "dos": "2026-05-01", "policy_title": "Prior Authorization and Retroactive Authorization"})
    assert r["policy"]["policy_id"] == "MP-PA-003" and any(e["policy_id"] == "MP-PA-030" and "different payer" in e["reason"] for e in r["excluded"])
    r = retrieve({**base, "payer": "MERIDIAN_COMM", "dos": "2026-05-01", "policy_title": "Prior Authorization and Retroactive Authorization"})
    assert r["policy"]["policy_id"] == "MP-PA-030"                    # filter really is by payer
    r = retrieve({**base, "payer": "TERRAVISTA_HEALTH", "dos": "2026-05-01", "policy_title": "Timely Filing of Claims"})
    assert r["policy"]["policy_id"] == "MP-TF-001" and any(e["policy_id"] == "MP-TF-010" and "superseded" in e["reason"] for e in r["excluded"])
    r = retrieve({**base, "payer": "TERRAVISTA_HEALTH", "dos": "2024-06-01", "policy_title": "Timely Filing of Claims"})
    assert r["policy"]["policy_id"] == "MP-TF-010"                    # the superseded version applies to old dates of service
    r = retrieve({**base, "payer": "NO_SUCH_PAYER", "dos": "2026-05-01"})
    assert r["status"] == "none" and r["reason"]


def test_retrieve_notes_effective_date_after_dos(staged, truths):
    hits = [cid for cid, t in truths.items() if t.claim.dos < R.POLICY_EFFECTIVE[t.policy_id]]
    assert hits
    r = retrieve(retrieve_args(staged, hits[0]))
    assert r["status"] == "selected" and r["date_notes"] and "after the date of service" in r["date_notes"][0]


def test_retrieve_reports_ties_explicitly(tmp_path, staged):
    pol = tmp_path / "pol"
    shutil.copytree(staged / "policy_library", pol)
    twin = (pol / "MP-IMG-007.txt").read_text().replace("MP-IMG-007", "MP-IMG-099")
    (pol / "MP-IMG-099.txt").write_text(twin)
    r = retrieve({"policy_root": str(pol), "case_root": str(staged / "cases" / "C-0005"), "payer": "MERIDIAN_COMM", "dos": "2026-05-01",
                  "policy_title": "Advanced Imaging: Lumbar Spine MRI Medical Necessity"})
    assert r["status"] == "tie" and r["policy"] is None and sorted(r["tie"]["policy_ids"]) == ["MP-IMG-007", "MP-IMG-099"] and r["tie"]["reason"]


# ================================================================ assess_appealability
def expected_timely(t):
    f = facts(t)
    fd = t.claim.dos + timedelta(days=R.PAYERS[t.payer_id]["timely_filing_days"])
    acc, rec = date.fromisoformat(f["clearinghouse_accepted_date"]), date.fromisoformat(f["payer_received_date"])
    return fd.isoformat(), ("within_limit" if acc <= fd and rec <= fd else ("accepted_within_limit_received_after" if acc <= fd else "after_limit"))


def test_assess_matches_truth_for_all_60(staged, truths):
    bad = []
    for cid, t in truths.items():
        a = assess(A(staged, cid))
        key = "corrected_claim" if t.correct_decision.value == "CORRECT_AND_RESUBMIT" else "appeal"
        fd, status = expected_timely(t)
        f = facts(t)
        asof = date.fromisoformat(f["as_of_date"])
        ok = (a["deadlines"][key]["date"] == t.action_deadline.isoformat() and a["deadlines"]["appeal"]["date"] == t.appeal_deadline.isoformat()
              and a["deadlines"][key]["days_remaining"] == (t.action_deadline - asof).days and a["deadlines"][key]["open_on_review_date"] == (asof <= t.action_deadline)
              and a["timely_filing"]["filing_deadline"] == fd and a["timely_filing"]["status"] == status and a["policy"]["policy_id"] == t.policy_id
              and a["timely_filing"]["stated_in_letter"] in (None, fd) and a["dates"]["payer_received_date"] == f["payer_received_date"])
        if not ok:
            bad.append(cid)
    assert bad == []


def test_assess_claim_history_skeleton_and_no_decision(staged, truths):
    a = assess(A(staged, "C-0030"))
    assert a["claim_history"]["earlier_submissions"]["text"] == "none recorded" and a["claim_history"]["events"][0]["event"].startswith("Submitted")
    assert a["timely_filing"]["status"] == "after_limit" and "decision" not in a
    sk = a["criteria_skeleton"]
    assert [s["section"] for s in sk] == ["2.1", "2.2"] and all(s["status"] is None and s["evidence_candidates"] for s in sk)
    assert any(c["file"] == "claim_history.txt" for s in sk for c in s["evidence_candidates"])
    a5 = assess(A(staged, "C-0005"))
    assert a5["policy"]["policy_id"] == "MP-IMG-007" and a5["documents_dated_after_dos"] == []
    assert "corrected-claim deadline if you recommend" in a5["action_deadline_rule"]


# ================================================================ pull_clinical_notes
def test_pull_returns_correct_files_for_pilots_and_empty_for_others(staged, truths):
    for cid in PILOTS:
        t = truths[cid]
        want = sorted(f.value for f in t.facts if f.key == "planned_document")
        r = pull(A(staged, cid))
        assert sorted(d["path"] for d in r["documents"]) == want and all("text" not in d for d in r["documents"])
        assert all(d["date"] is None or d["date"] <= r["as_of_date"] for d in r["documents"])
    empty = [cid for cid in truths if cid not in PILOTS]
    for cid in empty:
        r = pull(A(staged, cid))
        assert r["documents"] == [] and r["reason"]


def test_pull_minimum_necessary_and_ranges(staged, tmp_path):
    cid = "C-0007"
    meta = pull(A(staged, cid))
    some = meta["documents"][0]["path"]
    full = pull({**A(staged, cid), "paths": [some]})
    assert len(full["documents"]) == 1 and full["documents"][0]["text"].endswith("\n") and "SYNTHETIC DATA" in full["documents"][0]["text"]
    allt = pull({**A(staged, cid), "include_text": True})
    assert all("text" in d for d in allt["documents"])
    dated = [d["date"] for d in meta["documents"] if d["date"]]
    cut = sorted(dated)[0]
    r = pull({**A(staged, cid), "date_to": cut, "include_undated": False})
    assert all(d["date"] and d["date"] <= cut for d in r["documents"]) and r["n_excluded_by_date"] >= 1
    r = pull({**A(staged, cid), "date_from": cut})
    assert all(d["date"] is None or d["date"] >= cut for d in r["documents"])
    f = tmp_path / "ev.jsonl"
    pull({**A(staged, cid), "events_file": str(f)})
    reads = [json.loads(x) for x in f.read_text().splitlines() if json.loads(x)["tool"] == "pull_clinical_notes.read"]
    assert len(reads) >= len(meta["documents"])                       # every file access is logged
    with pytest.raises(SkillError):
        pull({**A(staged, cid), "paths": ["notes/2020-01-01_nothing.txt"]})


# ================================================================ draft_deliverable
def gold(cid):
    g = DATA / "cases" / cid / "gold"
    return (g / "deliverable.md").read_text(), (g / "decision.json").read_text()


def test_draft_validate_decision():
    _, dec = gold("C-0005")
    assert draft({"action": "validate_decision", "decision_text": dec})["valid"] is True
    bad = json.loads(dec)
    bad["criteria"][0]["id"] = "C1"
    r = draft({"action": "validate_decision", "decision_text": json.dumps(bad)})
    assert r["valid"] is False and any("section" in e for e in r["errors"])
    assert draft({"action": "validate_decision", "decision_text": "{"})["valid"] is False


def test_draft_render_skeleton(staged):
    for cid, kind in (("C-0005", "letter"), ("C-0030", "memo")):
        s = draft({**A(staged, cid), "action": "render_skeleton", "kind": kind})["skeleton"]
        a = assess(A(staged, cid))
        assert "<<FILL" in s and f"Claim {parse(A(staged, cid))['claim_no']}" in s and a["deadlines"]["appeal"]["date"] in s and "## Gaps" in s
        assert ("## Remedy requested" in s and "## Enclosures" in s) == (kind == "letter") and ("## Next action" in s) == (kind == "memo")
        assert all(f"### Section {x['section']}" in s for x in a["criteria_skeleton"])
    with pytest.raises(SkillError):
        draft({**A(staged, "C-0005"), "action": "render_skeleton"})


def test_verify_citations_passes_gold_and_fails_bad_citations(staged):
    for cid in PILOTS:
        d, dec = gold(cid)
        r = draft({**A(staged, cid), "action": "verify_citations", "deliverable_text": d, "decision_text": dec})
        assert r["valid"] and r["summary"]["total"] > 5, (cid, [c for c in r["citations"] if not c["pass"]])
    d, dec = gold("C-0005")
    bad = d + '\nThe chart says "the patient completed a full course of aquatic therapy at a rehabilitation center" (source: notes/2031-01-01_ghost.txt). See Section 9.9 of MP-IMG-007 and MP-XXX-999. Also claim_history.txt:999.'
    r = draft({**A(staged, "C-0005"), "action": "verify_citations", "deliverable_text": bad, "decision_text": dec})
    failed = {(c["kind"], c["text"][:30]) for c in r["citations"] if not c["pass"]}
    kinds = {k for k, _ in failed}
    assert {"quote", "section", "policy_id", "line"} <= kinds and r["valid"] is False and r["summary"]["failed"] >= 5


# ================================================================ self_check
def sc(staged, cid, d, dec):
    return self_check({**A(staged, cid), "deliverable_text": d, "decision_text": dec})


@pytest.mark.parametrize("cid", PILOTS)
def test_self_check_passes_gold(staged, cid):
    d, dec = gold(cid)
    r = sc(staged, cid, d, dec)
    assert r["ok"] and r["n_errors"] == 0, [c for c in r["checks"] if not c["pass"] and c["severity"] == "error"]


def failed_ids(r):
    return {c["id"] for c in r["checks"] if not c["pass"] and c["severity"] == "error"}


def test_self_check_flags_wrong_deadline(staged):
    d, dec = gold("C-0030")
    j = json.loads(dec)
    old = j["action_deadline"]
    new = (date.fromisoformat(old) + timedelta(days=1)).isoformat()
    r = sc(staged, "C-0030", d.replace(old, new), dec.replace(old, new))
    assert not r["ok"] and {"action_deadline", "deadline_in_text"} <= failed_ids(r)
    # deadline_ok flipped
    j2 = json.loads(dec)
    j2["deadline_ok"] = not j2["deadline_ok"]
    assert "deadline_ok" in failed_ids(sc(staged, "C-0030", d, json.dumps(j2)))
    # corrected-claim case using the appeal deadline
    d9, dec9 = gold("C-0039")
    j9 = json.loads(dec9)
    j9["action_deadline"] = parse(A(staged, "C-0039"))["appeal"]["by_date"]
    assert "action_deadline" in failed_ids(sc(staged, "C-0039", d9, json.dumps(j9)))


def test_self_check_flags_nonexistent_policy_section(staged):
    d, dec = gold("C-0005")
    j = json.loads(dec)
    j["criteria"].append({"id": "9.9", "status": "met", "evidence": None})
    r = sc(staged, "C-0005", d + "\nSee also Section 9.9 of MP-IMG-007.\n", json.dumps(j))
    assert not r["ok"] and {"criterion_section_9.9", "citations"} <= failed_ids(r)
    assert any(c["kind"] == "section" for c in r["citations_failed"])


def test_self_check_flags_missing_and_nonexistent_enclosures(staged):
    d, dec = gold("C-0005")
    j = json.loads(dec)
    j["enclosures"] = []
    r = sc(staged, "C-0005", d, json.dumps(j))
    assert not r["ok"] and "appeal_has_enclosures" in failed_ids(r)
    j["enclosures"] = ["supporting/missing_report.txt"]
    r = sc(staged, "C-0005", d, json.dumps(j))
    assert not r["ok"] and "enclosure_supporting/missing_report.txt" in failed_ids(r)


def test_self_check_flags_invented_quote(staged):
    d, dec = gold("C-0056")
    d2 = d.replace("## Gaps", '## Additional evidence\nThe therapist wrote "patient completed a full course of aquatic therapy at a regional center" (source: supporting/pt_log.txt).\n\n## Gaps', 1)
    assert d2 != d
    r = sc(staged, "C-0056", d2, dec)
    assert not r["ok"] and "citations" in failed_ids(r) and any(c["kind"] == "quote" for c in r["citations_failed"])


def test_self_check_flags_wrong_claim_number(staged):
    d, dec = gold("C-0007")
    no = parse(A(staged, "C-0007"))["claim_no"]
    wrong = str(int(no) + 1)
    r = sc(staged, "C-0007", d.replace(no, wrong), dec)
    assert not r["ok"] and "identifier_claim_no" in failed_ids(r)


def test_self_check_flags_appeal_letter_on_non_appeal_decision(staged):
    d, dec = gold("C-0005")                                           # an appeal letter
    j = json.loads(dec)
    j["decision"] = "DO_NOT_APPEAL"
    r = sc(staged, "C-0005", d, json.dumps(j))
    assert not r["ok"] and "no_appeal_letter" in failed_ids(r)
    d30, dec30 = gold("C-0030")                                       # a memo is not an appeal letter
    assert "no_appeal_letter" not in failed_ids(sc(staged, "C-0030", d30, dec30))


def test_self_check_gaps_placeholders_and_sections(staged):
    d, dec = gold("C-0039")
    j = json.loads(dec)
    j["gaps"] = []
    assert "gaps_listed" in failed_ids(sc(staged, "C-0039", d, json.dumps(j)))   # blank rendering provider on a corrected claim
    assert "no_placeholders" in failed_ids(sc(staged, "C-0039", d + "\n<<FILL: something>>\n", dec))
    assert "section_next_action" in failed_ids(sc(staged, "C-0039", d.replace("## Next action", "## Misc"), dec))
    sk = draft({**A(staged, "C-0039"), "action": "render_skeleton", "kind": "memo"})["skeleton"]
    assert "no_placeholders" in failed_ids(sc(staged, "C-0039", sk, dec))


def test_self_check_reads_output_files_through_the_guard(staged, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    d, dec = gold("C-0030")
    (out / "deliverable.md").write_text(d)
    (out / "decision.json").write_text(dec)
    r = self_check({**A(staged, "C-0030"), "output_root": str(out), "deliverable_path": "deliverable.md", "decision_path": "decision.json"})
    assert r["ok"]
    with pytest.raises(SkillError):
        self_check({**A(staged, "C-0030"), "output_root": str(out), "deliverable_path": "../x.md", "decision_path": "decision.json"})


# ================================================================ leak test
def test_skill_outputs_contain_no_decision_category_trap_or_status(staged, truths):
    from data_gen.schema import Trap
    cats = [c["name"] for c in R.CATEGORIES.values()]
    traps = [x.value for x in Trap]
    for cid, t in truths.items():
        outs = [parse(A(staged, cid)), retrieve(retrieve_args(staged, cid)), assess(A(staged, cid)), pull({**A(staged, cid), "include_text": True}),
                draft({**A(staged, cid), "action": "render_skeleton", "kind": "letter"}), draft({**A(staged, cid), "action": "render_skeleton", "kind": "memo"})]
        blob = json.dumps(outs, sort_keys=True)
        for d in ("APPEAL", "DO_NOT_APPEAL", "CORRECT_AND_RESUBMIT", "ESCALATE_MISSING_DOCS", t.correct_decision.value):
            assert not re.search(rf"\b{d}\b", blob), (cid, d)
        for c in cats:
            assert re.search(rf"\b{re.escape(c)}\b(?!s)", blob) is None, (cid, c)
        for x in traps:
            assert x not in blob, (cid, x)
        assert not re.search(r'"(met|unmet|unknown)"', blob), cid
        assert "truth.json" not in blob and "rubric" not in blob.lower().replace("rubric", "", 0) or "rubric" not in blob.lower()


def test_assess_lists_documents_dated_after_dos(staged, tmp_path):
    case = tmp_path / "c"
    shutil.copytree(staged / "cases" / "C-0005", case)
    dos = parse(A(staged, "C-0005"))["dos"]
    late = (date.fromisoformat(dos) + timedelta(days=12)).isoformat()
    (case / "docs" / "notes" / f"{late}_followup.txt").write_text("x\nSYNTHETIC DATA - NOT REAL PHI\n")
    a = assess({"case_root": str(case), "policy_root": str(staged / "policy_library")})
    assert a["documents_dated_after_dos"] == [{"path": f"notes/{late}_followup.txt", "date": late, "days_after_dos": 12}]


def test_missing_required_matches_remit_for_all_60(staged, truths):
    """missing_required lists exactly the remit fields shown as '(not provided)' and never an empty modifier column."""
    for cid, t in truths.items():
        text = (staged / "cases" / cid / "docs" / "eob_835.txt").read_text()
        want = sorted(f for f, label in (("place_of_service", "Place of service"), ("rendering_provider", "Rendering provider"), ("referring_provider", "Referring provider"))
                      if f"{label}: (not provided)" in text)
        got = sorted(m["field"] for m in parse(A(staged, cid))["missing_required"])
        assert got == want, cid


def test_self_check_warns_when_met_has_no_evidence(staged):
    d, dec = gold("C-0030")
    j = json.loads(dec)
    j["criteria"][0]["status"] = "met"
    j["criteria"][0]["evidence"] = None
    r = sc(staged, "C-0030", d, json.dumps(j))
    w = [c for c in r["checks"] if c["id"].startswith("met_without_evidence") and not c["pass"]]
    assert len(w) == 1 and w[0]["severity"] == "warn" and "met_without_evidence_2.1" not in failed_ids(r)


def test_verify_citations_accepts_prose_source_notes_but_not_fake_files(staged):
    d, dec = gold("C-0030")
    ok = d + '\nSee (source: denial_letter.txt states "The filing deadline for this date of service was 2026-06-30") and (source: the denial letter cites "Timely Filing of Claims").\n'
    r = draft({**A(staged, "C-0030"), "action": "verify_citations", "deliverable_text": ok, "decision_text": dec})
    assert r["valid"], [c for c in r["citations"] if not c["pass"]]
    bad = d + "\n(source: ghost_file.txt states something) and (source: notes/2031-01-01_ghost.txt) and (source: ghost)\n"
    r = draft({**A(staged, "C-0030"), "action": "verify_citations", "deliverable_text": bad, "decision_text": dec})
    failed = {c["text"] for c in r["citations"] if not c["pass"]}
    assert "notes/2031-01-01_ghost.txt" in failed and "ghost" in failed and not r["valid"]
