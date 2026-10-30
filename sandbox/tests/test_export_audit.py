import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "phase0"))
import export_audit as ea  # noqa: E402

GW = ("[1793399522.063] [sandbox] [OCSF ] [ocsf] NET:OPEN [MED] DENIED /usr/bin/curl(4337) -> collector.invalid:443 "
      "[policy:- engine:opa] [reason:endpoint collector.invalid:443 is not allowed by any policy]")
FILE = ("2026-10-30T22:15:56.919Z OCSF HTTP:POST [INFO] ALLOWED POST http://inference-api.nvidia.com:443/v1/chat/completions "
        "[policy:p1 engine:l7]")


def test_denied_network_event():
    e = ea.parse_line(GW)
    assert (e["ts"], e["event_class"], e["result"], e["target"], e["actor"]) == (
        "2026-10-30T22:32:02.063Z", "NET:OPEN", "denied", "collector.invalid:443", "/usr/bin/curl(4337)")
    assert e["engine"] == "opa" and e["reason"] == "endpoint collector.invalid:443 is not allowed by any policy"


def test_file_format_allowed_http():
    e = ea.parse_line(FILE)
    assert e["result"] == "allowed" and e["target"].startswith("POST http://inference-api") and e["policy"] == "p1"


def test_non_ocsf_line_skipped_and_ansi_stripped():
    assert ea.parse_line("[1793398543.903] [sandbox] [INFO ] [openshell_sandbox] Starting sandbox") is None
    assert ea.parse_line("\x1b[2m" + FILE + "\x1b[0m")["event_class"] == "HTTP:POST"
