"""Tool layer: the six skills as OpenAI-compatible function tools, generated from their pydantic input models (same JSON as skills/ CLI).
The harness injects case_root / policy_root / events_file / run_id / case_id; the model can never set them (such arguments are rejected).
Errors are returned to the model as tool results, never raised. Results are capped, and truncation is announced."""
import importlib
import json

from pydantic import ValidationError

from skills.common.io import SkillError, SkillInput

TOOL_NAMES = ["parse_denial_eob", "retrieve_payer_policy", "pull_clinical_notes", "assess_appealability", "draft_deliverable", "self_check"]
HIDDEN = set(SkillInput.model_fields)  # case_root, policy_root, output_root, events_file, run_id, case_id, step
MAX_RESULT_CHARS = 14000
DESCRIPTIONS = {
    "parse_denial_eob": "Parse the denial: claim number, patient ID, date of service, CPT, ICD-10, amounts, CARC/RARC, notice date, appeal and corrected-claim windows and dates, the policy title the payer names, the review date, blank remit fields. Takes no arguments.",
    "retrieve_payer_policy": "Find the governing payer policy (filters by payer and date of service first, then ranks by title and text). Pass payer id, date of service, CPT, service description, ICD-10 list, denial code and text, reason text and policy title from parse_denial_eob. Returns the policy, its sections and windows, excluded near-duplicates, and any tie.",
    "pull_clinical_notes": "List the clinical notes and supporting documents (metadata only: path, kind, date, title). To read documents, call again with paths (for example [\"notes/2026-03-23_pcp.txt\"]) which returns their full text. Optional date_from/date_to.",
    "assess_appealability": "Deterministic facts: appeal and corrected-claim deadlines with days remaining, timely-filing arithmetic, claim history, and a criteria skeleton listing each policy requirement section with evidence candidates (file, line, excerpt). Never a decision or a status. Optional policy_id.",
    "draft_deliverable": "Validation helpers. action='validate_decision' (needs decision_text), 'render_skeleton' (needs kind='letter' or 'memo'), 'verify_citations' (needs deliverable_text, optional decision_text).",
    "self_check": "Deterministic checklist of your deliverable (deliverable_text) and decision.json (decision_text): identifiers, deadline, policy and section ids, evidence files, enclosures, gaps, required sections, appeal-letter rule, citations.",
}


def _simplify(schema):
    defs = schema.get("$defs", {})

    def walk(n):
        if isinstance(n, dict):
            if "$ref" in n:
                return walk(defs[n["$ref"].split("/")[-1]])
            n = {k: walk(v) for k, v in n.items() if k not in ("title", "$defs", "default")}
            if "anyOf" in n:
                opts = [o for o in n["anyOf"] if o.get("type") != "null"]
                if len(opts) == 1:
                    rest = {k: v for k, v in n.items() if k != "anyOf"}
                    return {**opts[0], **rest}
            return n
        if isinstance(n, list):
            return [walk(x) for x in n]
        return n
    return walk(schema)


def _module(name):
    return importlib.import_module(f"skills.{name}")


def tool_specs():
    specs = []
    for name in TOOL_NAMES:
        s = _simplify(_module(name).Input.model_json_schema())
        props = {k: v for k, v in s.get("properties", {}).items() if k not in HIDDEN and not (name in ("draft_deliverable", "self_check") and k.endswith("_path"))}
        params = {"type": "object", "properties": props, "additionalProperties": False}
        if name == "retrieve_payer_policy":
            params["required"] = ["payer", "dos"]
        if name == "draft_deliverable":
            params["required"] = ["action"]
        specs.append({"type": "function", "function": {"name": name, "description": DESCRIPTIONS[name], "parameters": params}})
    return specs


class ToolRunner:
    def __init__(self, case_root, policy_root, events_file, run_id, case_id, max_chars=MAX_RESULT_CHARS):
        self.base = {"case_root": str(case_root), "policy_root": str(policy_root), "events_file": str(events_file), "run_id": run_id, "case_id": case_id}
        self.max_chars, self.step = max_chars, 0

    def parse_arguments(self, raw):
        """-> (dict | None, error | None) for the arguments string a model sent."""
        if isinstance(raw, dict):
            return raw, None
        if raw is None or str(raw).strip() == "":
            return {}, None
        try:
            v = json.loads(raw)
        except ValueError as e:
            return None, f"arguments are not valid JSON ({e})"
        return (v, None) if isinstance(v, dict) else (None, "arguments must be a JSON object")

    def execute(self, name, args):
        """-> (result_text, status, meta). status: ok | error | denied. Never raises."""
        meta = {"truncated": False, "result_chars": 0}
        if name not in TOOL_NAMES:
            return self._finish({"error": {"code": "unknown_tool", "message": f"no tool named {name!r}; available: {', '.join(TOOL_NAMES)}"}}, "error", meta, malformed=True)
        bad = sorted(set(args) & HIDDEN)
        if bad:
            return self._finish({"error": {"code": "bad_input", "message": f"argument(s) {bad} are set by the system and cannot be passed"}}, "error", meta, malformed=True)
        self.step += 1
        try:
            out = _module(name).call({**args, **self.base, "step": self.step})
            return self._finish(out, "ok", meta)
        except SkillError as e:
            return self._finish({"error": {"code": e.code, "message": e.message}}, "denied" if e.code == "access_denied" else "error", meta)
        except ValidationError as e:
            msg = "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()[:5])
            return self._finish({"error": {"code": "bad_input", "message": msg}}, "error", meta, malformed=True)
        except Exception as e:  # noqa: BLE001 - a tool bug must not crash the run
            return self._finish({"error": {"code": "tool_exception", "message": f"{type(e).__name__}: {e}"[:300]}}, "error", meta)

    def _finish(self, obj, status, meta, malformed=False):
        text = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
        meta["result_chars"] = len(text)
        meta["malformed"] = malformed
        if len(text) > self.max_chars:
            meta["truncated"] = True
            text = text[:self.max_chars] + f"\n[TRUNCATED: {len(text) - self.max_chars} of {len(text)} characters omitted. Narrow the request, for example pull_clinical_notes with specific paths.]"
        return text, status, meta
