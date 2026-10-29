#!/usr/bin/env python3
"""One-call test for the agent model and each judge model in config/models.yaml.

Usage: NVIDIA_INFERENCE_API_KEY=... python3 scripts/phase0/judge_smoke.py [--judges-only]
Exit code 0 only if every model answers "pong".
"""
import sys

from _common import chat_with_retry, load_models

cfg = load_models()
targets = {}
if "--judges-only" not in sys.argv:
    targets["agent"] = cfg["agent"]["model_id"]
targets.update({f"judge.{k}": v for k, v in cfg["judges"].items()})

failed = 0
for name, model in targets.items():
    try:
        # 1000 tokens: reasoning models spend tokens thinking before answering.
        text, usage, secs = chat_with_retry(cfg, model, "Reply with exactly one word: pong", max_tokens=1000)
        ok = "pong" in text.lower()
        print(f"{'PASS' if ok else 'FAIL'}  {name:14s} {model}  {secs:5.1f}s  "
              f"tokens={usage.get('total_tokens')}  reply={text[:40]!r}")
        failed += not ok
    except Exception as e:  # noqa: BLE001 - report every model, don't stop at the first
        print(f"FAIL  {name:14s} {model}  {e}")
        failed += 1
sys.exit(1 if failed else 0)
