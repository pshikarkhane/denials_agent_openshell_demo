"""LLM access for document generation: the shared client (retry + redacted failure log) and the manifest record."""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "phase0"))
from _common import chat_with_retry, load_models  # noqa: E402

PROMPT_FILES = ["data_gen/gen_policies.py", "data_gen/gen_clinical.py"]


def datagen_model(cfg):
    m = cfg["datagen"]["model_id"]
    agent = cfg["agent"]["model_id"]
    if "nemotron" in m.lower() or m == agent:
        raise SystemExit("datagen model must not be the agent model / a Nemotron model")
    return m


def generate(cfg, prompt, system=None):
    """One datagen call (retried). Returns text. `system` is prepended to the prompt."""
    full = f"{system}\n\n{prompt}" if system else prompt
    text, usage, _ = chat_with_retry(cfg, datagen_model(cfg), full, max_tokens=int(cfg["datagen"]["max_tokens"]),
                                     temperature=float(cfg["datagen"]["temperature"]))
    return text


def prompts_sha256():
    """Content hash of the prompt-bearing source files (no git repository exists yet; see docs/STATUS.md)."""
    h = hashlib.sha256()
    for f in PROMPT_FILES:
        p = ROOT / f
        if p.exists():
            h.update(f.encode() + p.read_bytes())
    return h.hexdigest()


def datagen_record(cfg, stage_file=None, old=None):
    """Manifest record of the datagen model and prompts. Each stage (policy library, clinical notes) stamps the hash of its own
    prompt-bearing file when it generates, so the record stays truthful if one stage's prompts are edited later."""
    prompts = dict((old or {}).get("prompts_sha256_by_file", {}))
    if stage_file:
        prompts[stage_file] = hashlib.sha256((ROOT / stage_file).read_bytes()).hexdigest()
    return {"model_id": datagen_model(cfg), "agent_model_id": cfg["agent"]["model_id"],
            "temperature": float(cfg["datagen"]["temperature"]), "max_tokens": int(cfg["datagen"]["max_tokens"]),
            "prompts_sha256_by_file": prompts, "prompts_sha256": prompts_sha256(),
            "prompts_git_sha": None,
            "prompts_git_sha_note": "project is not a git repository; per-file sha256 of the prompt-bearing source is recorded instead"}
