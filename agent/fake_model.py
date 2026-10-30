"""Scripted fake models for offline tests and --dry-run. No network, no key."""
import json

from agent.model_client import ModelFailure, Response


_COUNTER = [0]


def tool_response(*calls, content=None, usage=None):
    """calls: (name, args) where args is a dict or an already-encoded string (for malformed-call tests)."""
    tcs = []
    for n, a in calls:
        _COUNTER[0] += 1
        tcs.append({"id": f"call_{_COUNTER[0]}", "type": "function", "function": {"name": n, "arguments": a if isinstance(a, str) else json.dumps(a)}})
    return Response({"role": "assistant", "content": content, "tool_calls": tcs}, usage or {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}, 0.01)


def text_response(text, usage=None):
    return Response({"role": "assistant", "content": text}, usage or {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}, 0.01)


def failure(kind="no_choices"):
    return ModelFailure(kind, f"scripted {kind}")


class ScriptedModel:
    """chat() pops the next scripted item: a Response, a callable(messages) -> Response, or an Exception to raise."""
    model, temperature, max_tokens = "scripted-fake", 0.0, 0

    def __init__(self, script):
        self.script, self.requests = list(script), []

    def chat(self, messages, tools=None):
        self.requests.append([dict(m) for m in messages])
        if not self.script:
            raise AssertionError("scripted model ran out of responses")
        item = self.script.pop(0)
        if callable(item):
            item = item(messages)
        if isinstance(item, Exception):
            raise item
        return item


def _last_tool_json(messages, name_order):
    """JSON of the most recent tool result whose position matches the n-th tool call name."""
    names = {}
    for m in messages:
        if m["role"] == "assistant":
            for c in m.get("tool_calls", []) or []:
                names[c["id"]] = c["function"]["name"]
    out = {}
    for m in messages:
        if m["role"] == "tool":
            try:
                out[names.get(m["tool_call_id"])] = json.loads(m["content"])
            except ValueError:
                pass
    return out


class DryRunModel:
    """Deterministic stand-in used by --dry-run: runs the four read-only tools, then writes a plausible memo from their results."""
    model, temperature, max_tokens = "dry-run-fake", 0.0, 0

    def chat(self, messages, tools=None):
        res = _last_tool_json(messages, None)
        if "parse_denial_eob" not in res:
            return tool_response(("parse_denial_eob", {}))
        p = res["parse_denial_eob"]
        if "retrieve_payer_policy" not in res:
            return tool_response(("retrieve_payer_policy", {"payer": p["payer"]["id"], "dos": p["dos"], "cpt": p["cpt"], "service_description": p["service_description"],
                                                            "icd10": p["icd10"], "denial_code": p["denial"]["carc"], "denial_text": p["denial"]["carc_text"],
                                                            "reason_text": p["denial"]["reason_text"], "policy_title": p["policy_title"]}))
        if "pull_clinical_notes" not in res:
            return tool_response(("pull_clinical_notes", {}))
        if "assess_appealability" not in res:
            return tool_response(("assess_appealability", {}))
        a, r = res["assess_appealability"], res["retrieve_payer_policy"]
        pid = r["policy"]["policy_id"] if r.get("policy") else "MP-UNKNOWN-000"
        ad = a["deadlines"]["appeal"]["date"]
        crit = [{"id": s["section"], "status": "unmet", "evidence": (s["evidence_candidates"][0]["file"] if s["evidence_candidates"] else None)} for s in a["criteria_skeleton"]]
        ok = a["as_of_date"] <= ad
        d = {"case_id": p.get("claim_details", {}).get("case_id_in_task") or "C-0000", "decision": "DO_NOT_APPEAL", "denial_code": p["denial"]["carc"], "policy_id": pid,
             "action_deadline": ad, "deadline_ok": ok, "criteria": crit, "enclosures": [], "gaps": []}
        memo = (f"# Decision Memo: Claim {p['claim_no']}\n\n## Claim identification\n- Claim number: {p['claim_no']} (source: denial_letter.txt)\n- Patient ID: {p['patient']['id']}\n"
                f"- Date of service: {p['dos']}\n- CPT: {p['cpt']}\n- Denial code: {p['denial']['carc']}\n- Policy: {pid}\n\n## Deadline\nAction deadline {ad}; review date {a['as_of_date']}.\n\n"
                "## Next action\nNo appeal.\n\n## Gaps\nGaps: none identified\n")
        return text_response(f"<<<DELIVERABLE>>>\n{memo}<<<DECISION>>>\n{json.dumps(d, indent=1)}\n<<<END>>>")
