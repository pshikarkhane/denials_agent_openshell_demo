"""Two-stage hallucination check (DEMO_SPEC 6.6).
Stage 1: each judge extracts verifiable claims from the deliverable and flags those unsupported by the case documents, the policy
library and truth.facts; the union of flags goes to stage 2. Stage 2: each judge independently adjudicates every flag (upheld /
not upheld, material / minor); a flag is upheld if at least 2 judges uphold it, severity by majority of the upholding judges.
Only upheld MATERIAL flags feed the headline metrics. A flag whose quote does not appear in the deliverable is discarded."""
from concurrent.futures import ThreadPoolExecutor

from eval.common import JUDGE_KEYS, fill, load_inputs, norm, parse_json, quote_in

UPHOLD_NEEDED = 2


def _repair_call(call, jkey, tag, text, shape):
    prompt = f"Your previous reply was not valid JSON of the required shape ({shape}). Return ONLY the corrected JSON object. Previous reply:\n\n{text}"
    return call(jkey, prompt, tag + "_repair")


def _add_usage(a, b):
    for k, v in b.items():
        if isinstance(v, (int, float)):
            a[k] = a.get(k, 0) + v
    return a


def stage1(call, jkey, tag, inputs):
    prompt = fill("halluc_flag.md", deliverable=inputs["deliverable"], decision=inputs["decision_text"], docs=inputs["docs"],
                  policy=inputs["policy_library"], facts=inputs["facts"])
    text, usage, secs = call(jkey, prompt, tag)
    obj = parse_json(text)
    if not isinstance(obj, dict) or not isinstance(obj.get("flags"), list):
        text2, u2, s2 = _repair_call(call, jkey, tag, text, '{"flags": [...]}')
        usage, secs = _add_usage(dict(usage), u2), secs + s2
        obj = parse_json(text2)
        if not isinstance(obj, dict) or not isinstance(obj.get("flags"), list):
            return [], usage, secs, True
    flags = [f for f in obj["flags"] if isinstance(f, dict) and f.get("quote")]
    return flags, usage, secs, False


def _same(a, b):
    na, nb = norm(a), norm(b)
    if na in nb or nb in na:
        return True
    ta, tb = set(na.split()), set(nb.split())
    return bool(ta and tb) and len(ta & tb) / len(ta | tb) >= 0.6


def union_flags(flags_by_judge, deliverable, decision_text):
    """Merge flags from all judges; discard flags whose quote is not in the deliverable (fabricated)."""
    union, discarded = [], []
    for jk, flags in flags_by_judge.items():
        for f in flags:
            if not (quote_in(deliverable, f["quote"]) or quote_in(decision_text, f["quote"])):
                discarded.append({"judge": jk, "quote": f["quote"], "reason": "quote not found in deliverable"})
                continue
            for u in union:
                if _same(u["quote"], f["quote"]):
                    u["raised_by"].append(jk)
                    u["problems"].append(f.get("problem", ""))
                    break
            else:
                union.append({"quote": f["quote"], "problems": [f.get("problem", "")], "raised_by": [jk]})
    for i, u in enumerate(union, 1):
        u["id"] = f"F{i}"
    return union, discarded


def stage2(call, jkey, tag, inputs, union):
    flags_text = "\n\n".join(f"[{u['id']}] quote: {u['quote']}\n   concern: {u['problems'][0]}" for u in union)
    prompt = fill("halluc_adjudicate.md", deliverable=inputs["deliverable"], decision=inputs["decision_text"], flags=flags_text,
                  docs=inputs["docs"], policy=inputs["policy_library"], facts=inputs["facts"])
    ids = {u["id"] for u in union}
    text, usage, secs = call(jkey, prompt, tag)
    obj = parse_json(text)
    if not isinstance(obj, dict) or not isinstance(obj.get("adjudications"), list):
        text2, u2, s2 = _repair_call(call, jkey, tag, text, '{"adjudications": [...]}')
        usage, secs = _add_usage(dict(usage), u2), secs + s2
        obj = parse_json(text2)
        if not isinstance(obj, dict) or not isinstance(obj.get("adjudications"), list):
            return {}, usage, secs, True
    out = {}
    for a in obj["adjudications"]:
        if isinstance(a, dict) and a.get("flag_id") in ids:
            sev = str(a.get("severity", "")).lower()
            out[a["flag_id"]] = {"upheld": bool(a.get("upheld")), "severity": sev if sev in ("material", "minor") else "material", "reason": a.get("reason", "")}
    return out, usage, secs, False


def decide(union, adjud_by_judge):
    """Upheld if >= 2 judges uphold; severity = majority among upholding judges (ties are material)."""
    res = []
    for u in union:
        votes = {jk: a[u["id"]] for jk, a in adjud_by_judge.items() if u["id"] in a}
        up = {jk: v for jk, v in votes.items() if v["upheld"]}
        upheld = len(up) >= UPHOLD_NEEDED
        mat = sum(v["severity"] == "material" for v in up.values())
        sev = None if not upheld else ("material" if mat >= len(up) - mat else "minor")
        res.append({**u, "votes": votes, "upheld": upheld, "severity": sev})
    return res


def hallucination_case(call, root, case_id, deliverable_dir, judge_keys=JUDGE_KEYS, workers=6):
    inputs = load_inputs(root, case_id, deliverable_dir)
    usage = {jk: {} for jk in judge_keys}
    secs = {jk: 0.0 for jk in judge_keys}
    failures = []
    with ThreadPoolExecutor(workers) as ex:
        futs = {jk: ex.submit(stage1, call, jk, f"hal1_{case_id}", inputs) for jk in judge_keys}
    flags_by = {}
    for jk, fut in futs.items():
        flags, u, s, failed = fut.result()
        flags_by[jk] = flags
        _add_usage(usage[jk], u)
        secs[jk] += s
        if failed:
            failures.append(f"stage1:{jk}")
    union, discarded = union_flags(flags_by, inputs["deliverable"], inputs["decision_text"])
    adjud = {}
    if union:
        with ThreadPoolExecutor(workers) as ex:
            futs = {jk: ex.submit(stage2, call, jk, f"hal2_{case_id}", inputs, union) for jk in judge_keys}
        for jk, fut in futs.items():
            a, u, s, failed = fut.result()
            adjud[jk] = a
            _add_usage(usage[jk], u)
            secs[jk] += s
            if failed:
                failures.append(f"stage2:{jk}")
    flags = decide(union, adjud)
    return {"case_id": case_id, "flags": flags, "discarded_flags": discarded, "judge_failures": failures,
            "upheld_material": sum(f["upheld"] and f["severity"] == "material" for f in flags),
            "upheld_minor": sum(f["upheld"] and f["severity"] == "minor" for f in flags),
            "stage1_flag_counts": {jk: len(v) for jk, v in flags_by.items()},
            "tokens": usage, "latency_s": {jk: round(v, 1) for jk, v in secs.items()}}
