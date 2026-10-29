import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "phase0"))
import _common  # noqa: E402

SECRET = "sk-TESTSECRET1234567890"
CFG = {"api": {"base_url": "https://example.invalid/v1", "key_env": "TEST_KEY"}}
GOOD = json.dumps({"choices": [{"message": {"content": "pong"}}], "usage": {"total_tokens": 3}})


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("TEST_KEY", SECRET)
    monkeypatch.setattr(_common, "ERROR_LOG", tmp_path / "logs" / "model_errors.jsonl")


def script(monkeypatch, responses):
    calls = iter(responses)
    monkeypatch.setattr(_common, "_post", lambda *a, **k: next(calls))


def test_missing_choices_is_logged_with_redaction(monkeypatch):
    body = json.dumps({"error": "overloaded", "echo": f"Bearer {SECRET}"})
    script(monkeypatch, [(200, {"x-key": SECRET, "retry-after": "1"}, body)])
    with pytest.raises(_common.ModelCallError):
        _common.chat(CFG, "m", "hi")
    rec = json.loads(_common.ERROR_LOG.read_text().splitlines()[0])
    assert rec["status"] == 200 and rec["headers"]["retry-after"] == "1"
    assert "overloaded" in rec["body"]
    assert SECRET not in _common.ERROR_LOG.read_text()


def test_http_error_logged(monkeypatch):
    script(monkeypatch, [(503, {}, "upstream down")])
    with pytest.raises(_common.ModelCallError):
        _common.chat(CFG, "m", "hi")
    assert json.loads(_common.ERROR_LOG.read_text())["status"] == 503


def test_retry_succeeds_after_failures(monkeypatch):
    script(monkeypatch, [(500, {}, "x"), (200, {}, "{}"), (200, {}, GOOD)])
    sleeps = []
    text, _, _ = _common.chat_with_retry(CFG, "m", "hi", sleep=sleeps.append)
    assert text == "pong"
    assert sleeps == [1.0, 2.0]  # exponential backoff
    assert len(_common.ERROR_LOG.read_text().splitlines()) == 2


def test_retry_gives_up_after_three(monkeypatch):
    script(monkeypatch, [(500, {}, "x")] * 3)
    with pytest.raises(_common.ModelCallError):
        _common.chat_with_retry(CFG, "m", "hi", sleep=lambda s: None)
    assert len(_common.ERROR_LOG.read_text().splitlines()) == 3
