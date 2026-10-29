"""Shared helpers for model calls: stdlib only (no pyyaml/openai needed).

Every failed call is logged in full (status, headers, body) to logs/model_errors.jsonl
with the API key redacted. Use chat_with_retry() for all model calls.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ERROR_LOG = ROOT / "logs" / "model_errors.jsonl"

_KEY_PATTERN = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9._\-]{8,})")


class ModelCallError(RuntimeError):
    """A model call failed (HTTP error, network error, or malformed response)."""


def load_models(path=ROOT / "config" / "models.yaml"):
    """Parse the two-level `section:\n  key: value` YAML used in models.yaml."""
    cfg, section = {}, None
    for raw in Path(path).read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        key, _, val = line.strip().partition(":")
        if not line.startswith(" "):
            section = key
            cfg[section] = {}
        else:
            cfg[section][key] = val.strip()
    return cfg


def api_key(cfg):
    env = cfg["api"]["key_env"]
    key = os.environ.get(env)
    if not key:
        sys.exit(f"Set {env} in your environment (never commit it).")
    return key


def redact(text, secret=None):
    """Remove the API key (exact value and key-shaped strings) from text."""
    if secret:
        text = text.replace(secret, "[REDACTED]")
    return _KEY_PATTERN.sub("[REDACTED]", text)


def log_error(record, secret=None):
    """Append one redacted JSON line to logs/model_errors.jsonl."""
    line = redact(json.dumps(record, default=str), secret)
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ERROR_LOG.open("a") as f:
        f.write(line + "\n")


def _post(url, headers, body, timeout):
    """Transport layer. Returns (status, response_headers, body_text); never raises on HTTP status."""
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")


def chat(cfg, model, prompt=None, max_tokens=1000, timeout=120, messages=None, tools=None, temperature=None):
    """One chat-completions call. Returns (text, usage, seconds). Raises ModelCallError on any failure."""
    key = api_key(cfg)
    url = cfg["api"]["base_url"].rstrip("/") + "/chat/completions"
    payload = {"model": model, "max_tokens": max_tokens,
               "messages": messages or [{"role": "user", "content": prompt}]}
    if tools:
        payload["tools"] = tools
    if temperature is not None:
        payload["temperature"] = temperature
    t0 = time.time()
    status, headers, text, err = None, {}, "", None
    try:
        status, headers, text = _post(
            url, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json.dumps(payload).encode(), timeout)
        data = json.loads(text)
        msg = data["choices"][0]["message"]
    except Exception as e:  # noqa: BLE001 - network, JSON and schema failures are all logged
        err = f"{type(e).__name__}: {e}"
    else:
        if status == 200:
            return (msg.get("content") or "").strip(), data.get("usage", {}), time.time() - t0
        err = f"HTTP {status}"
    log_error({"ts": datetime.now(timezone.utc).isoformat(), "model": model, "url": url,
               "error": err, "status": status, "headers": headers, "body": text}, secret=key)
    raise ModelCallError(f"{model}: {err} (see logs/model_errors.jsonl)")


def chat_with_retry(cfg, model, *args, attempts=3, backoff=1.0, sleep=time.sleep, **kwargs):
    """chat() with up to `attempts` tries and exponential backoff (backoff, 2*backoff, ...)."""
    for i in range(attempts):
        try:
            return chat(cfg, model, *args, **kwargs)
        except ModelCallError:
            if i == attempts - 1:
                raise
            sleep(backoff * 2 ** i)
