#!/usr/bin/env python3
"""Generate docs/RUN_REPORT.md from agent runs and judge runs (host-only: it reads truth labels). Usage:
  python scripts/make_run_report.py --agent runs/agent-p1-r1 runs/agent-p1-r2 --baseline runs/agent-p1-r1/baseline \
      --judge-agent judge-agent-p1-r1 judge-agent-p1-r2 --judge-baseline judge-baseline-p1 --out docs/RUN_REPORT.md"""
import argparse
import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ["C-0005", "C-0007", "C-0030", "C-0039", "C-0056"]


def load(p):
    try:
        return json.loads(Path(p).read_text()) if Path(p).exists() else None
    except ValueError:
        return None  # e.g. a baseline decision.json that is not valid JSON


def pct(x, d=0):
    return "n/a" if x is None else f"{100 * x:.{d}f}%"


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def collect(run_dirs, judge_ids):
    """-> {case: [row per repeat]}"""
    out = {c: [] for c in PILOTS}
    for rd, jid in zip(run_dirs, judge_ids):
        for c in PILOTS:
            s = load(Path(rd) / c / "summary.json")
            j = load(ROOT / "runs" / jid / "cases" / f"{c}.json")
            d = load(Path(rd) / c / "decision.json")
            row = {"run": Path(rd).name if "baseline" not in str(rd) else "baseline", "summary": s, "decision": (d or {}).get("decision") if isinstance(d, dict) else None}
            if s and not row["decision"] and (Path(rd) / c / "decision.json").exists():
                try:
                    row["decision"] = json.loads((Path(rd) / c / "decision.json").read_text()).get("decision")
                except ValueError:
                    pass
            if j:
                p, h = j["panel"], j["hallucination"]
                row.update(dec_ok=p["auto"].get("DEC1", {}).get("pass"), pass_rate=p["panel_pass_rate"], judge_rates=p["judge_pass_rates"], unanimity=p["unanimity_rate"],
                           material=h["upheld_material"], minor=h["upheld_minor"], judge_fail=p["judge_failures"] + h["judge_failures"], fabricated=p["fabricated_quotes"],
                           failed=sorted(p["failed_criteria"]), judge_tokens={k: v for k, v in p["tokens"].items()}, hal_tokens=h["tokens"], judge_secs=p["latency_s"])
            out[c].append(row)
    return out


def agg(rows_by_case):
    rows = [r for c in PILOTS for r in rows_by_case[c] if r.get("pass_rate") is not None]
    runs = [r["summary"] for c in PILOTS for r in rows_by_case[c] if r["summary"]]
    calls = sum(s["tool_calls_total"] for s in runs)
    jr = {}
    for r in rows:
        for k, v in r["judge_rates"].items():
            jr.setdefault(k, []).append(v)
    return {
        "n": len(rows), "decision_correct": mean([1.0 if r.get("dec_ok") else 0.0 for r in rows]), "pass_rate": mean([r["pass_rate"] for r in rows]),
        "judge_rates": {k: mean(v) for k, v in jr.items()}, "material_per_case": mean([r["material"] for r in rows]),
        "clean_rate": mean([1.0 if r["material"] == 0 else 0.0 for r in rows]), "unanimity": mean([r["unanimity"] for r in rows]),
        "tool_fail_rate": (sum(s["tool_errors"] for s in runs) / calls) if calls else None, "malformed_rate": (sum(s["malformed_calls"] for s in runs) / calls) if calls else None,
        "turns": mean([s["turns"] for s in runs]), "tool_calls": mean([s["tool_calls_total"] for s in runs]), "tokens": mean([s["usage"].get("total_tokens") for s in runs]),
        "seconds": mean([s["seconds"] for s in runs]), "revision_rate": mean([1.0 if s["revisions"] else 0.0 for s in runs]), "model_failures": sum(len(s["model_failures"]) for s in runs),
        "submitted": mean([1.0 if s["status"] == "submitted" else 0.0 for s in runs]), "runs": len(runs)}


def row_md(name, a):
    jr = ", ".join(f"{k} {pct(v)}" for k, v in sorted(a["judge_rates"].items()))
    return (f"| {name} | {a['n']} | {pct(a['decision_correct'])} | {pct(a['pass_rate'], 1)} | {jr} | {a['material_per_case']:.2f} | {pct(a['clean_rate'])} | {pct(a['unanimity'])} |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", nargs="+", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--judge-agent", nargs="+", required=True)
    ap.add_argument("--judge-baseline", required=True)
    ap.add_argument("--out", default=str(ROOT / "docs" / "RUN_REPORT.md"))
    ap.add_argument("--notes", default=None, help="markdown file appended at the end (hand-written classification)")
    a = ap.parse_args()
    ag = collect(a.agent, a.judge_agent)
    ba = collect([a.baseline] * 1, [a.judge_baseline])
    truth = {c: json.loads((ROOT / "data" / "cases" / c / "truth.json").read_text()) for c in PILOTS}
    L = ["# RUN_REPORT: pre-sandbox agent run vs no-tools baseline", "",
         "**Pre-sandbox run, 5 dev cases, not a benchmark.** The agent is a plain tool-calling loop (`agent/run_case.py`) over the six skills, on the hosted endpoint; the baseline is the same model with one prompt and no tools. "
         "Both were scored by the existing judge panel (Gemini 3.1 Pro, Claude Opus 4.8, GPT-5.5) and the two-stage hallucination check. Host-only document (it shows the truth labels). "
         "Caveat: the Claude judge is the same model as the document-generation model (see STATUS.md).", ""]
    first = next(r["summary"] for c in PILOTS for r in ag[c] if r["summary"])
    L += [f"Agent model `{first['model_id']}`, temperature {first['temperature']}, prompt hash `{first['prompt_sha256'][:12]}`, git `{(first['git_sha'] or '')[:8]}`. "
          f"Agent: {len(a.agent)} repeats x 5 cases; baseline: 1 run x 5 cases.", "", "## Aggregate", "",
          "| variant | runs scored | decision correct (auto) | criterion pass rate (panel) | per judge | upheld material / case | clean-case rate | judge unanimity |", "|---|---|---|---|---|---|---|---|"]
    per_rep = []
    for i, rd in enumerate(a.agent):
        sub = {c: [ag[c][i]] for c in PILOTS if len(ag[c]) > i}
        per_rep.append((Path(rd).name, agg(sub)))
    for n, x in per_rep:
        L.append(row_md(f"agent {n}", x))
    A, B = agg(ag), agg(ba)
    L += [row_md("**agent (all repeats)**", A), row_md("**baseline (no tools)**", B), "",
          "Clean-case rate = share of runs with zero upheld material hallucinations. Containment: 0 violations in every run (the path guard refused all attempts; see below).", "",
          "## Run statistics (agent vs baseline)", "", "| | agent | baseline |", "|---|---|---|"]
    for lab, k, f in (("runs finished as submitted", "submitted", pct), ("mean turns / model calls", "turns", lambda v: f"{v:.1f}"), ("mean tool calls", "tool_calls", lambda v: f"{v:.1f}"),
                      ("tool-call failure rate (error results / calls)", "tool_fail_rate", lambda v: pct(v, 1)), ("malformed tool-call rate", "malformed_rate", lambda v: pct(v, 1)),
                      ("mean tokens per run", "tokens", lambda v: f"{v:,.0f}"), ("mean wall-clock per run (s)", "seconds", lambda v: f"{v:.0f}"),
                      ("revision rate (runs needing a self_check revision)", "revision_rate", pct), ("model-call failures (no choices / empty / http)", "model_failures", str)):
        L.append(f"| {lab} | {f(A[k]) if A[k] is not None else 'n/a'} | {f(B[k]) if B[k] is not None else 'n/a'} |")
    # per case
    L += ["", "## Per case", "", "| case | truth decision | run | model decision | decision ok | panel pass | per judge (gem/cla/gpt) | upheld material | minor | turns | tools | revisions | tokens | s |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in PILOTS:
        for lab, rows in (("agent", ag[c]), ("baseline", ba[c])):
            for r in rows:
                s = r["summary"] or {}
                jr = r.get("judge_rates") or {}
                L.append(f"| {c} | {truth[c]['correct_decision']} | {lab} {r['run'].split('-')[-1] if lab == 'agent' else ''} | {r['decision']} | {'yes' if r.get('dec_ok') else 'NO'} | {pct(r.get('pass_rate'))} | "
                         f"{pct(jr.get('gemini'))}/{pct(jr.get('claude'))}/{pct(jr.get('gpt'))} | {r.get('material')} | {r.get('minor')} | {s.get('turns')} | {s.get('tool_calls_total')} | {s.get('revisions')} | {s.get('usage', {}).get('total_tokens')} | {s.get('seconds')} |")
    # repeat variance
    L += ["", "## Repeat-to-repeat variance (agent)", ""]
    diffs, agree = [], []
    for c in PILOTS:
        rs = [r for r in ag[c] if r.get("pass_rate") is not None]
        if len(rs) >= 2:
            diffs.append(abs(rs[0]["pass_rate"] - rs[1]["pass_rate"]))
            agree.append(rs[0]["decision"] == rs[1]["decision"])
            L.append(f"- {c}: pass rate {pct(rs[0]['pass_rate'])} vs {pct(rs[1]['pass_rate'])}; decisions {rs[0]['decision']} / {rs[1]['decision']}; failed criteria {rs[0]['failed']} / {rs[1]['failed']}")
    if diffs:
        L.append(f"- mean absolute difference in panel pass rate between repeats: {pct(mean(diffs), 1)}; same decision in {sum(agree)} of {len(agree)} cases.")
    # failed criteria summary
    L += ["", "## Where criteria failed (panel majority or any judge)", ""]
    for lab, rows_by in (("agent", ag), ("baseline", ba)):
        fails = {}
        for c in PILOTS:
            for r in rows_by[c]:
                for f in r.get("failed", []):
                    fails.setdefault(c, []).append(f)
        L.append(f"- {lab}: " + ("; ".join(f"{c}: {', '.join(v)}" for c, v in fails.items()) or "none"))
    # containment
    guard = [(r['run'], c, r['summary']['path_guard_denials']) for c in PILOTS for r in ag[c] if r['summary'] and r['summary']['path_guard_denials']]
    L += ["", "## Containment", "", f"Path-guard denials (attempts to read outside the staged case): {guard or 'none'}. No run read `truth.json`, `rubric.json`, `gold/` or `attacks/` (they are not in the staged copy)."]
    # case studies
    for cid in ("C-0005", "C-0030"):
        tp = Path(a.agent[0]) / cid / "trace.json"
        L += ["", f"## Case study {cid} (agent, {Path(a.agent[0]).name}; truth: {truth[cid]['correct_decision']})", ""]
        for t in (load(tp) or []):
            L.append(f"{t['n']}. **{t['kind']} {t['name']}** ({t['status']}, {t['duration_ms']} ms): {t['args_summary'][:90] + ' -> ' if t['args_summary'] and t['kind'] == 'tool' else ''}{t['result_summary'][:170]}")
    # cost
    jt = {}
    for rows_by in (ag, ba):
        for c in PILOTS:
            for r in rows_by[c]:
                for key in ("judge_tokens", "hal_tokens"):
                    for jk, u in (r.get(key) or {}).items():
                        t = jt.setdefault(jk, [0, 0])
                        t[0] += u.get("prompt_tokens", 0)
                        t[1] += u.get("completion_tokens", 0)
    L += ["", "## Cost and time", "",
          f"- Agent runs: {sum(s['usage'].get('total_tokens', 0) for c in PILOTS for r in ag[c] if (s := r['summary']))} tokens over {A['runs']} runs; baseline: {sum(s['usage'].get('total_tokens', 0) for c in PILOTS for r in ba[c] if (s := r['summary']))} tokens over {B['runs']} runs.",
          "- Judging (grading + both hallucination stages): " + ", ".join(f"{k} {v[0]:,} prompt + {v[1]:,} completion tokens" for k, v in sorted(jt.items())) + "."]
    if a.notes:
        L.append(Path(a.notes).read_text())
    Path(a.out).write_text("\n".join(L) + "\n")
    print("wrote", a.out)


main()
