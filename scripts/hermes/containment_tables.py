"""Aggregate Phase 6 attack runs and export the demo samples.

  python scripts/hermes/containment_tables.py tables            # markdown tables (natural and scripted, per fixture), counts only
  python scripts/hermes/containment_tables.py export            # docs/samples/hermes_attack_<A1|A2|A3>/ (best natural run, and the scripted run where one exists)
Reads runs/p6-<id>-r* (natural) and runs/p6-S-<id>-r* (scripted); attack_result.json holds only booleans about the answer key."""
import glob
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX = ["A1", "A1b", "A1c", "A2", "A3", "A3b"]
FILES = ["events.jsonl", "trace.json", "audit.jsonl", "deliverable.md", "decision.json", "summary.json", "attack_result.json", "final_self_check.json"]


def load(prefix, fid):
    out = []
    for d in sorted(glob.glob(str(ROOT / "runs" / f"{prefix}-{fid}-r*" / "C-0005"))):
        p = Path(d) / "attack_result.json"
        if p.exists():
            out.append((Path(d), json.loads(p.read_text())))
    return out


def row(fid, runs, scripted=False):
    n = len(runs)
    if not n:
        return None
    if scripted:
        sc = [r["scripted"] for _, r in runs if r.get("scripted")]
        return {"fixture": fid, "runs": n, "scripted_run": len(sc), "blocked": sum(1 for x in sc if x["denied"]), "logged_in_audit": sum(1 for x in sc if x["audit_logged"]),
                "decision_ok": sum(1 for _, r in runs if r["decision_correct"] and r["denial_code_ok"] and r["action_deadline_ok"]),
                "egress": sum(r["allowed_egress_other"] for _, r in runs)}
    att = [r for _, r in runs if r["attempted"]]
    return {"fixture": fid, "runs": n, "seen": sum(1 for _, r in runs if r["injection_seen_by_model"]), "attempted": len(att), "blocked": sum(1 for r in att if r["denied"]),
            "logged_in_audit": sum(1 for r in att if r["audit_logged"]), "decision_ok": sum(1 for _, r in runs if r["decision_correct"] and r["denial_code_ok"] and r["action_deadline_ok"]),
            "mentions": sum(1 for _, r in runs if r["deliverable_mentions_injection"]), "egress": sum(r["allowed_egress_other"] for _, r in runs)}


def tables():
    print("| fixture | runs | injection seen by model | ATTEMPTED (natural) | blocked (of attempts) | in audit log (of attempts) | decision/code/deadline correct | allowed egress other than model |")
    print("|---|---|---|---|---|---|---|---|")
    for f in FIX:
        r = row(f, load("p6", f))
        if r:
            print(f"| {f} | {r['runs']} | {r['seen']}/{r['runs']} | {r['attempted']}/{r['runs']} | {r['blocked']}/{r['attempted']} | {r['logged_in_audit']}/{r['attempted']} | {r['decision_ok']}/{r['runs']} | {r['egress']} |")
    print()
    print("| fixture | runs | scripted command run | blocked | in audit log | agent's decision/code/deadline correct | allowed egress other than model |")
    print("|---|---|---|---|---|---|---|")
    for f in FIX:
        r = row(f, load("p6-S", f), True)
        if r:
            print(f"| {f} | {r['runs']} | {r['scripted_run']} | {r['blocked']}/{r['scripted_run']} | {r['logged_in_audit']}/{r['scripted_run']} | {r['decision_ok']}/{r['runs']} | {r['egress']} |")


def best_natural(fid, variants):
    """Prefer a run in which the agent actually attempted the action (any variant of the fixture), else the first run that saw the injection."""
    pool = [x for v in variants for x in load("p6", v)]
    att = [x for x in pool if x[1]["attempted"]]
    seen = [x for x in pool if x[1]["injection_seen_by_model"]]
    return (att or seen or pool)[0] if pool else None


def export():
    for fid, variants in (("A1", ["A1", "A1b", "A1c"]), ("A2", ["A2"]), ("A3", ["A3b", "A3"])):
        dest = ROOT / "docs" / "samples" / f"hermes_attack_{fid}"
        if dest.exists():
            shutil.rmtree(dest)
        picks = [("natural", best_natural(fid, variants))]
        sc = load("p6-S", variants[0])
        if sc:
            picks.append(("scripted", sc[0]))
        for mode, pick in picks:
            if not pick:
                continue
            d, r = pick
            tgt = dest / mode
            tgt.mkdir(parents=True)
            for f in FILES:
                if (d / f).exists():
                    shutil.copyfile(d / f, tgt / f)
            (tgt / "SOURCE.txt").write_text(f"run {r['run_id']} fixture {r['attack_id']} attack_mode {r['attack_mode']} (attempted={r['attempted']})\n")
        print("exported", fid, [m for m, _ in picks])


if __name__ == "__main__":
    {"tables": tables, "export": export}[sys.argv[1]]()
