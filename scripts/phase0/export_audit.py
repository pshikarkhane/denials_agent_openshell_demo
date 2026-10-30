"""Convert the OpenShell sandbox audit log (OCSF lines) to JSONL, one event per line.

Output keys: ts (UTC ISO-8601), event_class (e.g. NET:OPEN, HTTP:POST, PROC:LAUNCH), severity, result ("allowed" |
"denied" | null when the event has no verdict), target (host:port or URL), actor (binary(pid), when present),
policy, engine, reason, raw (the original line, so nothing is lost).

Inputs (both formats of the same events are parsed):
  - live from the gateway:   python scripts/phase0/export_audit.py --sandbox my-hermes [--since 30m] [-n 5000]
  - a saved file or stdin:    python scripts/phase0/export_audit.py FILE|-     (e.g. /var/log/openshell.<date>.log copied
                              out of the sandbox, or the output of `openshell logs`)
Options: --only-denied, --only-ocsf (default: only OCSF lines; operational log lines are skipped).
Stdlib only; no secrets are involved (the audit log holds none), but the line is still passed through redact().
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import redact  # noqa: E402

ANSI = re.compile(r"\x1b\[[0-9;]*m")
# "[1793399522.063] [sandbox] [OCSF ] [ocsf] NET:OPEN ..."   (openshell logs)  or  "2026-10-30T22:32:02.063Z OCSF NET:OPEN ..." (file)
GW = re.compile(r"^\[(?P<ts>\d+\.\d+)\]\s+\[[^\]]*\]\s+\[OCSF\s*\]\s+\[ocsf\]\s+(?P<body>.*)$")
FILE = re.compile(r"^(?P<ts>\d{4}-\d\d-\d\dT[\d:.]+Z)\s+OCSF\s+(?P<body>.*)$")
BODY = re.compile(r"^(?P<cls>[A-Z]+:[A-Z]+)\s+(?:\[(?P<sev>[A-Z]+)\]\s*)?(?P<rest>.*)$")
TAG = re.compile(r"\[(\w+):((?:[^\[\]]|\[[^\]]*\])*)\]")  # [policy:x] [engine:y] [reason:z] [msg:...]


def parse_tags(rest):
    """[policy:x engine:y] holds several pairs; [reason:...] and [msg:...] hold free text."""
    tags = {}
    for k, v in TAG.findall(rest):
        if k in ("reason", "msg"):
            tags[k] = v
        else:
            for pair in v.split():
                if ":" in pair:
                    pk, pv = pair.split(":", 1)
                    tags[pk] = pv
                elif k not in tags:
                    tags[k] = pair
            tags.setdefault(k, v.split()[0] if v.split() else "")
    return tags


def iso(epoch):
    return datetime.fromtimestamp(float(epoch), timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_line(line):
    line = ANSI.sub("", line.rstrip("\n"))
    m = GW.match(line)
    if m:
        ts = iso(m["ts"])
    else:
        m = FILE.match(line)
        if not m:
            return None
        ts = m["ts"]
    b = BODY.match(m["body"])
    if not b:
        return None
    rest = b["rest"]
    tags = parse_tags(rest)
    head = TAG.sub("", rest).strip()
    result = None
    r = re.match(r"^(ALLOWED|DENIED)\b\s*(.*)$", head)
    if r:
        result, head = r[1].lower(), r[2]
    actor, target = None, head or None
    if " -> " in head:
        actor, target = (x.strip() for x in head.split(" -> ", 1))
    elif re.match(r"^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s", head):
        target = head
    reason = tags.get("reason") or (tags.get("msg") if result is None else None)
    return {"ts": ts, "event_class": b["cls"], "severity": b["sev"], "result": result, "target": target,
            "actor": actor, "policy": tags.get("policy"), "engine": tags.get("engine"), "reason": reason, "raw": line}


def read_source(args):
    if args.sandbox:
        cmd = ["openshell", "logs", args.sandbox, "--source", "sandbox", "-n", str(args.n)]
        if args.since:
            cmd += ["--since", args.since]
        return subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, check=True).stdout.splitlines()
    if args.file in (None, "-"):
        return sys.stdin  # lazy: lets `openshell logs --tail | export_audit.py -` stream
    with open(args.file) as f:
        return f.read().splitlines()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file", nargs="?")
    ap.add_argument("--sandbox")
    ap.add_argument("--since")
    ap.add_argument("-n", type=int, default=5000)
    ap.add_argument("--only-denied", action="store_true")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    events = (e for e in map(parse_line, read_source(args)) if e and (e["result"] == "denied" or not args.only_denied))
    streaming = args.file == "-" or (args.file is None and not args.sandbox)
    out = open(args.output, "w") if args.output else sys.stdout
    count = 0
    for e in (events if streaming else sorted(events, key=lambda e: e["ts"])):
        out.write(redact(json.dumps(e, ensure_ascii=False)) + "\n")
        out.flush()
        count += 1
    if args.output:
        out.close()
        print(f"{count} events -> {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
