"""Minimal client for the Hermes OpenAI-compatible API (port-forwarded to the host). Stdlib only.

Gets the bearer token from `nemohermes <sandbox> gateway-token --quiet` at call time; the token is never printed or
written. All logged text goes through _common.redact.
"""
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

from _common import redact

BASE = os.environ.get("HERMES_BASE", "http://127.0.0.1:8642")
SANDBOX = os.environ.get("SANDBOX", "my-hermes")


def gateway_token(sandbox=SANDBOX):
    out = subprocess.run(["nemohermes", sandbox, "gateway-token", "--quiet"], capture_output=True, text=True,
                         stdin=subprocess.DEVNULL, env={**os.environ, "NODE_NO_WARNINGS": "1"})
    token = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
    if not token:
        raise RuntimeError("could not read gateway token (is the sandbox running?)")
    return token


def _req(path, token, body=None, method=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method or ("POST" if body is not None else "GET"),
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout)


def get_json(path, token, timeout=60):
    with _req(path, token, timeout=timeout) as r:
        return json.load(r)


def start_run(token, text, **extra):
    """POST /v1/runs. Returns run_id. Raises RuntimeError with a REDACTED body on HTTP errors."""
    try:
        with _req("/v1/runs", token, {"input": text, **extra}) as r:
            return json.load(r)["run_id"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(redact(f"HTTP {e.code}: {e.read().decode(errors='replace')[:2000]}", token)) from None


def stream_events(token, run_id, timeout=300):
    """Yield SSE events (dicts) from GET /v1/runs/{id}/events until the stream closes. Adds `t_rel` (seconds)."""
    t0 = None
    with _req(f"/v1/runs/{run_id}/events", token, timeout=timeout) as r:
        for raw in r:
            line = raw.decode(errors="replace").strip()
            if not line.startswith("data:"):
                continue
            ev = json.loads(line[5:])
            t0 = t0 or ev.get("timestamp", time.time())
            ev["t_rel"] = round(ev.get("timestamp", t0) - t0, 3)
            yield ev


def session_messages(token, run_id):
    """Full message history incl. tool_calls (arguments) and tool results. The run id is also the session id."""
    return get_json(f"/api/sessions/{run_id}/messages", token)
