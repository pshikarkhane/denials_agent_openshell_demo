"""Hosted-endpoint client for the AGENT model with tool calling. Reuses the Phase 0 helpers (transport, key handling, redaction, failure log).
Any failure (HTTP error, no `choices`, unparseable JSON) is logged in full (status, headers, body, key redacted) to logs/model_errors.jsonl and
raised as ModelFailure so the loop can count it and retry. Keys come from the environment only."""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "phase0"))
import _common  # noqa: E402
from _common import api_key, load_models, log_error, redact  # noqa: E402,F401


class ModelFailure(Exception):
    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind          # http | no_choices | bad_json | empty


class Response:
    def __init__(self, message, usage, secs, finish_reason=None):
        self.message, self.usage, self.secs, self.finish_reason = message, usage or {}, secs, finish_reason


def agent_model_id(cfg):
    """The agent model from config. It must not be a judge or the datagen model."""
    m = cfg["agent"]["model_id"]
    others = set(cfg["judges"].values()) | {cfg["datagen"]["model_id"]}
    if m in others:
        raise SystemExit("the agent model must not be a judge or the datagen model")
    return m


class HostedModel:
    def __init__(self, cfg, temperature=None, max_tokens=None, timeout=300, post=None):
        self.cfg, self.model = cfg, agent_model_id(cfg)
        self.temperature = float(temperature if temperature is not None else cfg["agent"].get("temperature", 0.2))
        self.max_tokens = int(max_tokens or cfg["agent"].get("max_tokens", 8000))
        self.timeout, self._post = timeout, post or _common._post

    def chat(self, messages, tools=None):
        key = api_key(self.cfg)
        url = self.cfg["api"]["base_url"].rstrip("/") + "/chat/completions"
        payload = {"model": self.model, "messages": messages, "max_tokens": self.max_tokens, "temperature": self.temperature}
        if tools:
            payload["tools"] = tools
        t0 = time.time()
        status, headers, body, err = None, {}, "", None
        try:
            status, headers, body = self._post(url, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                                               json.dumps(payload).encode(), self.timeout)
            data = json.loads(body)
            choice = data["choices"][0]
            msg = choice["message"]
        except KeyError as e:
            kind, err = "no_choices", f"response has no {e}"
        except (ValueError, IndexError, TypeError) as e:
            kind, err = "bad_json", f"{type(e).__name__}: {e}"
        except Exception as e:  # noqa: BLE001 - network errors
            kind, err = "http", f"{type(e).__name__}: {e}"
        else:
            if status != 200:
                kind, err = "http", f"HTTP {status}"
            else:
                m = {"role": "assistant", "content": msg.get("content")}
                if msg.get("tool_calls"):
                    m["tool_calls"] = [{"id": c.get("id") or f"call_{i}", "type": "function",
                                        "function": {"name": (c.get("function") or {}).get("name", ""), "arguments": (c.get("function") or {}).get("arguments", "")}}
                                       for i, c in enumerate(msg["tool_calls"])]
                return Response(m, data.get("usage"), time.time() - t0, choice.get("finish_reason"))
        log_error({"ts": datetime.now(timezone.utc).isoformat(), "model": self.model, "url": url, "error": err, "status": status, "headers": headers,
                   "body": body, "where": "agent"}, secret=key)
        raise ModelFailure(kind, err)
