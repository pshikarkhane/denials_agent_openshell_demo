#!/usr/bin/env python3
"""Print a condensed digest of the raw reviewer outputs (docs/auto_review_raw/) so findings can be merged by hand."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW, parse_json  # noqa: E402


def load(name):
    p = RAW / name
    return json.loads(p.read_text()) if p.exists() else {}


def main():
    print("== BLIND SOLVE (vs truth) ==")
    for k, v in load("blind_compare.json").items():
        print(f"{k}: decision={v.get('decision')} policy={str(v.get('policy'))[:60]} deadline={v.get('deadline')}")
        for m in v["mismatches"]:
            print("   MISMATCH", m)
        print("   suspicion:", str(v.get("suspicion"))[:500])
    print("\n== REALISM / EVIDENCE ==")
    for k, v in load("realism_parsed.json").items():
        if not v:
            print(k, "UNPARSEABLE")
            continue
        print(f"-- {k}: {v.get('overall')}")
        for f in v.get("findings", []):
            print(f"   [{f.get('severity')}/{f.get('area')}] {f.get('file')}: {str(f.get('problem'))[:260]} | quote={str(f.get('quote'))[:140]!r} | fix={str(f.get('suggested_fix'))[:140]}")
        print("   clean:", v.get("clean_areas"))
    print("\n== POLICY LIBRARY ==")
    for k, v in load("policy_parsed.json").items():
        if not v:
            print(k, "UNPARSEABLE")
            continue
        print(f"-- {k}: {v.get('overall')}")
        for f in v.get("findings", []):
            print(f"   [{f.get('severity')}/{f.get('area')}] {f.get('policy')}: {str(f.get('problem'))[:260]} | quote={str(f.get('quote'))[:140]!r} | fix={str(f.get('suggested_fix'))[:140]}")
    print("\n== CODING TABLES ==")
    for k, v in load("coding_parsed.json").items():
        if not v:
            print(k, "UNPARSEABLE")
            continue
        print(f"-- {k}")
        for ln in v.get("lines", []):
            if ln.get("verdict") == "suspect":
                print(f"   {ln['id']} suspect/{ln.get('confidence')}: {str(ln.get('reason'))[:200]}")
        for c in v.get("combination_flags", []):
            print(f"   COMBO {c.get('codes')} {c.get('confidence')}: {str(c.get('reason'))[:200]}")


main()
