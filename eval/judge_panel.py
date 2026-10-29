"""Judge panel (DEMO_SPEC 6.4): three judges (Gemini 3.1 Pro, Claude Opus 4.8, GPT-5.5 from config/models.yaml) grade a deliverable
criterion by criterion; 'auto' criteria are graded in code and pooled. Judges never see the agent trace or the producing model.
Usage: python -m eval.run_eval (runs the panel + hallucination check); this module is the library."""
import json
from concurrent.futures import ThreadPoolExecutor

from eval.auto_checks import grade_auto
from eval.common import JUDGE_KEYS, fill, load_inputs, parse_json, quote_in
from eval.deliverable_schema import validate_decision_text
from eval.rubric_schema import Rubric

MAX_PER_CALL = 15


def _criteria_text(criteria):
    return "\n\n".join(f"[{c.id}] ({c.family}) {c.text}\n   REFERENCE: {c.reference}" + (f"\n   LOOK AT: {', '.join(c.sources)}" if c.sources else "")
                       for c in criteria)


def chunks(criteria, size=MAX_PER_CALL):
    """One call per judge per case; split into two calls when there are more than 15 judge criteria."""
    if len(criteria) <= size:
        return [criteria]
    half = (len(criteria) + 1) // 2
    return [criteria[:half], criteria[half:]]


def parse_results(text, wanted_ids):
    """-> list of result dicts, or None if the reply is not usable JSON."""
    obj = parse_json(text)
    if not isinstance(obj, dict) or not isinstance(obj.get("results"), list):
        return None
    out = []
    for r in obj["results"]:
        if isinstance(r, dict) and r.get("id") in wanted_ids:
            out.append(r)
    return out


def grade_chunk(call, jkey, tag, inputs, criteria):
    """One judge, one call (plus at most one repair retry). Returns (verdicts, usage, secs, failed)."""
    ids = {c.id for c in criteria}
    prompt = fill("grader.md", deliverable=inputs["deliverable"], decision=inputs["decision_text"], docs=inputs["docs"],
                  policy=inputs["policy_sections"], criteria=_criteria_text(criteria))
    text, usage, secs = call(jkey, prompt, tag)
    res = parse_results(text, ids)
    if res is None:  # malformed: one repair retry
        repair = (f"Your previous reply was not valid JSON of the required shape. Return ONLY a JSON object "
                  f'{{"results": [{{"id": ..., "verdict": "PASS"|"FAIL", "evidence_quote": ..., "reason": ...}}]}} '
                  f"covering ids {sorted(ids)}. Here is your previous reply:\n\n{text}")
        text2, usage2, secs2 = call(jkey, repair, tag + "_repair")
        usage = {k: (usage.get(k, 0) or 0) + (usage2.get(k, 0) or 0) for k in set(usage) | set(usage2) if isinstance(usage.get(k, 0) or usage2.get(k, 0), (int, float))}
        secs += secs2
        res = parse_results(text2, ids)
        if res is None:
            return {}, usage, secs, True
    verdicts = {}
    for r in res:
        v = str(r.get("verdict", "")).upper()
        verdicts[r["id"]] = {"verdict": v if v in ("PASS", "FAIL") else "FAIL", "evidence_quote": r.get("evidence_quote", ""), "reason": r.get("reason", "")}
    return verdicts, usage, secs, False


def apply_quote_rule(verdicts, deliverable, decision_text):
    """A PASS needs a quote that really appears in the deliverable (or decision.json). Fabricated quote => FAIL."""
    for v in verdicts.values():
        v["fabricated_quote"] = False
        if v["verdict"] == "PASS" and not (quote_in(deliverable, v["evidence_quote"]) or quote_in(decision_text, v["evidence_quote"])):
            v["verdict"], v["fabricated_quote"] = "FAIL", True
            v["reason"] = "[quote not found in deliverable] " + v["reason"]
    return verdicts


def majority(verdicts_by_judge, cid):
    """PASS if more than half of the judges that produced a verdict say PASS (ties fail)."""
    votes = [v[cid]["verdict"] for v in verdicts_by_judge.values() if cid in v]
    return "PASS" if votes and votes.count("PASS") > len(votes) / 2 else "FAIL"


def grade_case(call, root, case_id, deliverable_dir, judge_keys=JUDGE_KEYS, workers=6):
    root_inputs = load_inputs(root, case_id, deliverable_dir)
    rubric = Rubric.model_validate_json((root / "cases" / case_id / "rubric.json").read_text())
    decision, derrs = validate_decision_text(root_inputs["decision_text"], case_id) if root_inputs["decision_text"] else (None, ["decision.json missing"])
    auto = {}
    for c in rubric.criteria:
        if c.check == "auto":
            ok, detail = grade_auto(c.auto, decision, root_inputs["deliverable"])
            auto[c.id] = {"pass": ok, "detail": detail}
    judged = [c for c in rubric.criteria if c.check == "judge"]
    jobs = {}
    with ThreadPoolExecutor(workers) as ex:
        for jk in judge_keys:
            for i, ch in enumerate(chunks(judged)):
                jobs[(jk, i)] = ex.submit(grade_chunk, call, jk, f"grade_{case_id}_{i}", root_inputs, ch)
    per = {jk: {"verdicts": {}, "usage": {}, "secs": 0.0, "failed": False} for jk in judge_keys}
    for (jk, i), fut in jobs.items():
        v, usage, secs, failed = fut.result()
        p = per[jk]
        p["verdicts"].update(v)
        p["secs"] += secs
        p["failed"] = p["failed"] or failed
        for k, val in usage.items():
            if isinstance(val, (int, float)):
                p["usage"][k] = p["usage"].get(k, 0) + val
    for jk, p in per.items():
        apply_quote_rule(p["verdicts"], root_inputs["deliverable"], root_inputs["decision_text"])
    valid = {jk: p["verdicts"] for jk, p in per.items() if not p["failed"]}
    panel = {c.id: ("PASS" if auto[c.id]["pass"] else "FAIL") for c in rubric.criteria if c.check == "auto"}
    for c in judged:
        panel[c.id] = majority(valid, c.id)
    n = len(rubric.criteria)
    rates = {}
    for jk, p in per.items():  # per-judge pass rate with the auto criteria pooled in; a failed judge's missing verdicts count as FAIL
        passes = sum(a["pass"] for a in auto.values()) + sum(1 for c in judged if p["verdicts"].get(c.id, {}).get("verdict") == "PASS")
        rates[jk] = passes / n
    unanimous = [c.id for c in judged if len(valid) >= 2 and len({v.get(c.id, {}).get("verdict") for v in valid.values()}) == 1]
    return {
        "case_id": case_id, "criteria_total": n, "auto": auto, "judges": per, "panel": panel,
        "panel_pass_rate": sum(v == "PASS" for v in panel.values()) / n,
        "judge_pass_rates": rates, "unanimity_rate": (len(unanimous) / len(judged)) if judged else None,
        "judge_failures": [jk for jk, p in per.items() if p["failed"]],
        "fabricated_quotes": sum(1 for p in per.values() for v in p["verdicts"].values() if v.get("fabricated_quote")),
        "decision_json_errors": derrs,
        "tokens": {jk: p["usage"] for jk, p in per.items()}, "latency_s": {jk: round(p["secs"], 1) for jk, p in per.items()},
        "failed_criteria": {c.id: {"text": c.text, "reference": c.reference, "auto": auto.get(c.id),
                                   "votes": {jk: p["verdicts"].get(c.id) for jk, p in per.items()}}
                            for c in rubric.criteria if panel[c.id] == "FAIL" or any(p["verdicts"].get(c.id, {}).get("verdict") == "FAIL" for p in per.values())},
    }
