"""Shared helpers for the automated pilot review. READ-ONLY with respect to data/ and data_gen/."""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "docs" / "auto_review_raw"
sys.path.insert(0, str(ROOT / "scripts" / "phase0"))
sys.path.insert(0, str(ROOT))
from _common import chat_with_retry, load_models, redact  # noqa: E402

FORBIDDEN_PARTS = ("truth.json", "rubric", "gold", "attacks", "manifest", "PILOT_REVIEW", "validation_report")
DECISIONS = ["APPEAL", "CORRECT_AND_RESUBMIT", "DO_NOT_APPEAL", "ESCALATE_MISSING_DOCS"]


def reviewers(cfg):
    """Reviewer models = the Gemini and GPT judge entries. Never the datagen or agent model."""
    out = {k: cfg["judges"][k] for k in ("gemini", "gpt")}
    banned = {cfg["datagen"]["model_id"], cfg["agent"]["model_id"]}
    assert not banned & set(out.values()), "reviewer must not be the datagen or agent model"
    return out


def manifest_pilots():
    man = json.loads((ROOT / "data" / "manifest.json").read_text())  # host-side read; contents are never sent to reviewers
    return man["pilot_cases"]


def agent_visible(case_id):
    """(text, [relative paths]) of exactly what the agent sees: task.md, docs/**, policy_library/*."""
    base = ROOT / "data" / "cases" / case_id
    files = [base / "task.md"] + sorted(p for p in (base / "docs").rglob("*") if p.is_file())
    files += sorted((ROOT / "data" / "policy_library").glob("*.txt"))
    parts, names = [], []
    for p in files:
        rel = p.relative_to(ROOT / "data").as_posix()
        if any(x.lower() in rel.lower() for x in FORBIDDEN_PARTS):
            raise SystemExit(f"refusing to send {rel} to a reviewer")
        name = rel.replace(f"cases/{case_id}/", "")
        names.append(name)
        parts.append(f"===== FILE: {name} =====\n{p.read_text()}")
    return "\n".join(parts), names


def parse_json(text):
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    cand = m.group(1) if m else text
    for opener, closer in (("{", "}"), ("[", "]")):
        i, j = cand.find(opener), cand.rfind(closer)
        if i != -1 and j > i:
            try:
                return json.loads(cand[i:j + 1])
            except ValueError:
                continue
    return None


def ask(cfg, rkey, model, name, prompt, max_tokens=20000):
    """One reviewer call; raw response (redacted) saved under docs/auto_review_raw/<name>__<rkey>.md."""
    RAW.mkdir(parents=True, exist_ok=True)
    text, usage, secs = chat_with_retry(cfg, model, prompt, max_tokens=max_tokens, timeout=420, attempts=3, backoff=3.0)
    (RAW / f"{name}__{rkey}.md").write_text(
        f"<!-- reviewer={rkey} model={model} time={datetime.now(timezone.utc).isoformat()} secs={secs:.0f} usage={json.dumps(usage)} -->\n"
        + redact(text) + "\n")
    return text


def run_parallel(jobs, workers=4):
    """jobs: list of zero-arg callables returning (key, value). Returns dict."""
    with ThreadPoolExecutor(workers) as ex:
        return dict(f.result() for f in [ex.submit(j) for j in jobs])
