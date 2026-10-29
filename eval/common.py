"""Shared helpers for the judge panel and hallucination check: model caller, quote matching, case inputs."""
import json
import re
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = Path(__file__).parent / "prompts"
sys.path.insert(0, str(ROOT / "scripts" / "phase0"))
from _common import ModelCallError, chat_with_retry, load_models, redact  # noqa: E402,F401

JUDGE_KEYS = ("gemini", "claude", "gpt")


def judge_models(cfg, keys=JUDGE_KEYS):
    """judge key -> model id from config/models.yaml. The agent model can never be a judge."""
    out = {k: cfg["judges"][k] for k in keys}
    agent = cfg["agent"]["model_id"]
    if agent in out.values() or any("nemotron" in m.lower() for m in out.values()):
        raise SystemExit("the agent model (or any Nemotron model) must not be a judge")
    return out


def fill(template_name, **kw):
    t = (PROMPTS / template_name).read_text()
    for k, v in kw.items():
        t = t.replace(f"<<{k.upper()}>>", v)
    return t


_TRANS = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})


def norm(s):
    return " ".join(str(s).translate(_TRANS).lower().split())


def quote_in(text, quote):
    """True if `quote` appears verbatim (whitespace/case/quote-style insensitive) in text. 'a ... b' requires both fragments."""
    q = str(quote or "").strip().strip('"').strip()
    if not q:
        return False
    frags = [f.strip() for f in re.split(r"\.\.\.|…", q) if f.strip()]
    hay = norm(text)
    return bool(frags) and all(len(norm(f)) >= 4 and norm(f) in hay for f in frags)


def parse_json(text):
    """Extract the first JSON object from a model reply (tolerates code fences). None if unparseable."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    cand = m.group(1) if m else text
    i, j = cand.find("{"), cand.rfind("}")
    if i == -1 or j <= i:
        return None
    try:
        return json.loads(cand[i:j + 1])
    except ValueError:
        return None


class Caller:
    """One model call per (judge, tag). Temperature 0 where the provider allows it; the retry wrapper handles transient errors.
    Raw outputs go to <run_dir>/raw/<tag>__<judge>.md with the API key redacted. Callable so tests can substitute a mock."""

    def __init__(self, cfg, run_dir, keys=JUDGE_KEYS):
        self.cfg, self.models, self.raw = cfg, judge_models(cfg, keys), Path(run_dir) / "raw"
        self.raw.mkdir(parents=True, exist_ok=True)
        self.no_temp, self.lock = set(), threading.Lock()

    def __call__(self, jkey, prompt, tag, max_tokens=16000):
        model = self.models[jkey]
        t0 = time.time()
        text = usage = None
        if model not in self.no_temp:
            try:
                text, usage, _ = chat_with_retry(self.cfg, model, prompt, max_tokens=max_tokens, temperature=0, timeout=420, attempts=2, backoff=3.0)
            except ModelCallError:
                with self.lock:
                    self.no_temp.add(model)  # provider may reject temperature; retry without it
        if text is None:
            text, usage, _ = chat_with_retry(self.cfg, model, prompt, max_tokens=max_tokens, timeout=420, attempts=4, backoff=4.0)
        secs = time.time() - t0
        (self.raw / f"{tag}__{jkey}.md").write_text(
            f"<!-- judge={jkey} model={model} time={datetime.now(timezone.utc).isoformat()} secs={secs:.0f} usage={json.dumps(usage)} -->\n{redact(text)}\n")
        return text, usage or {}, secs


# ---------------------------------------------------------------- case inputs
def policy_sections_text(policy_text, sections):
    """Header + the policy sections the rubric relies on + corrections/code-pair sections + Section 7 parameters."""
    parts = re.split(r"(?m)^(?=Section \S+)", policy_text)
    head, body = parts[0], parts[1:]
    keep = [head]
    for p in body:
        sec = re.match(r"Section (\S+)", p).group(1)
        if sec in sections or sec == "7" or re.match(r"Section \S+\s+(Corrections|Code pairs)", p):
            keep.append(p)
    return "".join(keep)


def load_inputs(root, case_id, deliverable_dir):
    """Everything a judge may see for a case. Never the agent trace or the producing model's identity."""
    from data_gen.gen_cases import load_truths
    root = Path(root)
    _, truths = load_truths(root)
    t = next(x for x in truths if x.case_id == case_id)
    base = root / "cases" / case_id
    docs = [f"===== FILE: task.md =====\n{(base / 'task.md').read_text()}"]
    docs += [f"===== FILE: {p.relative_to(base / 'docs').as_posix()} =====\n{p.read_text()}" for p in sorted((base / "docs").rglob("*")) if p.is_file()]
    secs = {c.section.lstrip("§") for c in t.policy_criteria}
    pol = policy_sections_text((root / "policy_library" / f"{t.policy_id}.txt").read_text(), secs)
    lib = "\n".join(f"===== FILE: policy_library/{p.name} =====\n{p.read_text()}" for p in sorted((root / "policy_library").glob("*.txt")))
    d = Path(deliverable_dir)
    return {
        "truth": t, "docs": "\n".join(docs), "policy_sections": pol, "policy_library": lib,
        "deliverable": (d / "deliverable.md").read_text() if (d / "deliverable.md").exists() else "",
        "decision_text": (d / "decision.json").read_text() if (d / "decision.json").exists() else "",
        "facts": json.dumps([{"key": f.key, "value": f.value, "source_file": f.source_file} for f in t.facts if f.key != "planned_document"], indent=1),
    }
