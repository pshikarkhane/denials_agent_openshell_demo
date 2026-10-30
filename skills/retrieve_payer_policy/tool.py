"""retrieve_payer_policy: filter the policy library by payer and date of service BEFORE ranking, rank by title match then BM25, return the
governing policy with its sections and stated windows. Ties and same-title distractors are reported explicitly, never silently resolved."""
from pydantic import BaseModel

from skills.common.bm25 import BM25
from skills.common.io import SkillError, SkillInput
from skills.common.policies import applicable, load_policies
from skills.common.text import jaccard, norm


class Input(SkillInput):
    payer: str                       # payer id (e.g. from parse_denial_eob.payer.id) or name
    dos: str                         # date of service YYYY-MM-DD
    cpt: str | None = None
    service_description: str | None = None
    icd10: list[str] = []
    denial_code: str | None = None
    denial_text: str | None = None   # CARC text from the letter
    reason_text: str | None = None   # reason paragraph from the letter
    policy_title: str | None = None  # title named in the letter, if any
    top_k: int = 6


class Output(BaseModel):
    status: str                      # "selected" | "tie" | "none"
    policy: dict | None
    candidates: list[dict]
    tie: dict | None
    sections: list[dict]
    date_notes: list[str]
    excluded: list[dict]
    reason: str | None


SMALL = {"and", "of", "the", "a", "an", "to", "for", "in", "on", "or"}


def smart_title(t):
    if not t.isupper():
        return t
    words = t.lower().split()
    return " ".join(w if (i and w in SMALL) else w.capitalize() for i, w in enumerate(words))


def _policy_view(p):
    return {"policy_id": p.policy_id, "title": smart_title(p.title), "payer_id": p.payer_id, "payer_name": p.payer_name,
            "effective_date": p.effective, "applies_from": p.applies_from, "applies_until": p.applies_until, "windows": p.windows,
            "appeals_address": p.address, "parameters": [{"label": a, "text": b} for a, b in p.params], "file": p.file}


def run_tool(inp, ctx):
    pols = load_policies(ctx)
    payer_key = norm(inp.payer)
    same_payer = [p for p in pols if norm(p.payer_id or "") == payer_key or payer_key in norm(p.payer_name or "")]
    excluded = []
    for p in pols:
        if p not in same_payer and inp.policy_title and jaccard(p.title, inp.policy_title) >= 0.5:
            excluded.append({"policy_id": p.policy_id, "reason": f"different payer ({p.payer_id}): excluded by the payer filter although its title resembles the letter's title"})
    if not same_payer:
        return Output(status="none", policy=None, candidates=[], tie=None, sections=[], date_notes=[], excluded=excluded, reason=f"no policy for payer {inp.payer!r}")
    cands, date_notes = [], []
    for p in same_payer:
        ok, why = applicable(p, inp.dos)
        if not ok:
            if not inp.policy_title or jaccard(p.title, inp.policy_title) >= 0.5 or p.superseded:
                excluded.append({"policy_id": p.policy_id, "reason": why})
            continue
        cands.append(p)
    if not cands:
        return Output(status="none", policy=None, candidates=[], tie=None, sections=[], date_notes=date_notes, excluded=excluded,
                      reason="no policy of this payer applies on the date of service")
    query = " ".join(x for x in [inp.policy_title, inp.service_description, inp.denial_text, inp.reason_text, inp.denial_code, inp.cpt, " ".join(inp.icd10)] if x)
    bm = BM25([p.text for p in cands])
    scored = []
    for i, p in enumerate(cands):
        t_exact = 1.0 if inp.policy_title and norm(inp.policy_title) == norm(p.title) else 0.0
        t_j = round(jaccard(inp.policy_title, p.title), 3) if inp.policy_title else 0.0
        scored.append({"p": p, "title_exact": t_exact, "title_similarity": t_j, "bm25": round(bm.score(query, i), 4)})
    scored.sort(key=lambda s: (-s["title_exact"], -s["title_similarity"], -s["bm25"], s["p"].policy_id))
    cand_view = [{"policy_id": s["p"].policy_id, "title": _policy_view(s["p"])["title"], "title_exact_match": bool(s["title_exact"]),
                  "title_similarity": s["title_similarity"], "bm25": s["bm25"]} for s in scored]
    top = scored[0]
    tied = [s for s in scored if (s["title_exact"], s["title_similarity"], s["bm25"]) == (top["title_exact"], top["title_similarity"], top["bm25"])]
    # near misses: same-payer candidates (not selected) whose title resembles the selected one
    for s in scored[1:]:
        if jaccard(s["p"].title, top["p"].title) >= 0.5:
            excluded.append({"policy_id": s["p"].policy_id, "reason": f"near-duplicate of {top['p'].policy_id} (title similarity {jaccard(s['p'].title, top['p'].title):.2f}) ranked lower: "
                                                                     f"{'title differs from the letter' if inp.policy_title and not s['title_exact'] else 'lower text match'}"})
    if len(tied) > 1:
        return Output(status="tie", policy=None, candidates=cand_view, sections=[], date_notes=[], excluded=excluded,
                      tie={"policy_ids": [t["p"].policy_id for t in tied],
                           "reason": "equal title match and text score: the documents do not distinguish these policies; choose explicitly (or escalate)"},
                      reason="tie between applicable policies")
    p = top["p"]
    if p.effective and inp.dos < p.effective:
        date_notes.append(f"policy effective date {p.effective} is after the date of service {inp.dos}; the policy states it applies to dates of service on or after {p.applies_from}")
    ids = [k for k in p.sections if k not in ("1",)]
    sbm = BM25([p.sections[k]["text"] for k in ids])
    ranked = sbm.rank(query)
    secs = [{"policy_id": p.policy_id, "section": ids[i], "heading": p.sections[ids[i]]["heading"], "text": p.sections[ids[i]]["text"], "score": round(sc, 4),
             "line": p.sections[ids[i]]["line"], "effective_date": p.effective} for i, sc in ranked[:max(1, inp.top_k)]]
    return Output(status="selected", policy=_policy_view(p), candidates=cand_view, tie=None, sections=secs, date_notes=date_notes,
                  excluded=excluded, reason=None)
