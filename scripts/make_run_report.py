#!/usr/bin/env python3
"""Generate docs/RUN_REPORT.md (host-only: reads truth labels). Compares, for the agent and the no-tools baseline:
  p2 under the OLD rubric, p2 under the NEW (relaxed) rubric, p3 (new prompt/skills) under the NEW rubric.
  python scripts/make_run_report.py [--notes docs/run_report_notes.md] [--out docs/RUN_REPORT.md]"""
import argparse
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skills.common.deliverable_schema import validate_decision_text  # noqa: E402

PILOTS = ["C-0005", "C-0007", "C-0030", "C-0039", "C-0056"]
R = ROOT / "runs"
CONFIGS = [
    ("p2 / old rubric", {"agent": ([R / "agent-p2-r1", R / "agent-p2-r2"], ["judge-agent-p2-r1", "judge-agent-p2-r2"]),
                         "baseline": ([R / "agent-p2-r1" / "baseline"], ["judge-baseline-p2"])}),
    ("p2 / new rubric", {"agent": ([R / "agent-p2-r1", R / "agent-p2-r2"], ["judge2-agent-p2-r1", "judge2-agent-p2-r2"]),
                         "baseline": ([R / "agent-p2-r1" / "baseline"], ["judge2-baseline-p2"])}),
    ("p3 / new rubric", {"agent": ([R / f"agent-p3-r{i}" for i in (1, 2, 3)], [f"judge-agent-p3-r{i}" for i in (1, 2, 3)]),
                         "baseline": ([R / f"baseline-p3-r{i}" / "baseline" for i in (1, 2)], [f"judge-baseline-p3-r{i}" for i in (1, 2)])}),
]


def load(p):
    try:
        return json.loads(Path(p).read_text()) if Path(p).exists() else None
    except ValueError:
        return None


def pct(x, d=0):
    return "n/a" if x is None else f"{100 * x:.{d}f}%"


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def collect(run_dirs, judge_ids):
    rows = []
    for rd, jid in zip(run_dirs, judge_ids):
        for c in PILOTS:
            s = load(rd / c / "summary.json")
            j = load(R / jid / "cases" / f"{c}.json")
            if not s or not j:
                continue
            p, h = j["panel"], j["hallucination"]
            dtext = (rd / c / "decision.json").read_text() if (rd / c / "decision.json").exists() else ""
            dec, errs = validate_decision_text(dtext, c) if dtext else (None, ["missing"])
            jids = [k for k in p["panel"] if k not in p["auto"]]
            content = mean([1.0 if p["panel"][k] == "PASS" else 0.0 for k in jids])
            content_j = {jk: mean([1.0 if jv["verdicts"].get(k, {}).get("verdict") == "PASS" else 0.0 for k in jids]) for jk, jv in p["judges"].items()}
            rows.append({"case": c, "run": rd.parent.name if rd.name == "baseline" else rd.name, "summary": s, "decision": dec.decision if dec else None, "valid": dec is not None,
                         "dec_ok": p["auto"].get("DEC1", {}).get("pass"), "pass_rate": p["panel_pass_rate"], "judge_rates": p["judge_pass_rates"], "content": content, "content_j": content_j,
                         "unanimity": p["unanimity_rate"], "material": h["upheld_material"], "minor": h["upheld_minor"], "flags": [f for f in h["flags"] if f["upheld"] and f["severity"] == "material"],
                         "failed": sorted(p["failed_criteria"]), "jtokens": {k: v for k, v in p["tokens"].items()}, "htokens": h["tokens"]})
    return rows


def agg(rows):
    runs = [r["summary"] for r in rows]
    calls = sum(s["tool_calls_total"] for s in runs)
    jr, cj = {}, {}
    for r in rows:
        for k, v in r["judge_rates"].items():
            jr.setdefault(k, []).append(v)
        for k, v in r["content_j"].items():
            cj.setdefault(k, []).append(v)
    by_case = {}
    for r in rows:
        by_case.setdefault(r["case"], []).append(r["pass_rate"])
    sds = [st.pstdev(v) for v in by_case.values() if len(v) >= 2]
    same = [len({r["decision"] for r in rows if r["case"] == c}) == 1 for c in by_case if sum(1 for r in rows if r["case"] == c) >= 2]
    return {"n": len(rows), "dec_ok": mean([1.0 if r["dec_ok"] else 0.0 for r in rows]), "valid": mean([1.0 if r["valid"] else 0.0 for r in rows]),
            "pass": mean([r["pass_rate"] for r in rows]), "jr": {k: mean(v) for k, v in jr.items()}, "content": mean([r["content"] for r in rows]), "cj": {k: mean(v) for k, v in cj.items()},
            "material": mean([r["material"] for r in rows]), "clean": mean([1.0 if r["material"] == 0 else 0.0 for r in rows]), "unanimity": mean([r["unanimity"] for r in rows]),
            "tool_fail": (sum(s["tool_errors"] for s in runs) / calls) if calls else None, "malformed": sum(s["malformed_calls"] for s in runs) + sum(s["malformed_final"] for s in runs),
            "turns": mean([s["turns"] for s in runs]), "tools": mean([s["tool_calls_total"] for s in runs]), "tokens": mean([s["usage"].get("total_tokens") for s in runs]),
            "secs": mean([s["seconds"] for s in runs]), "rev": mean([1.0 if s["revisions"] else 0.0 for s in runs]), "fails": sum(len(s["model_failures"]) for s in runs),
            "sd": mean(sds), "same": (sum(same), len(same)) if same else None}


def fmt_j(d):
    return "/".join(pct(d.get(k)) for k in ("gemini", "claude", "gpt"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "RUN_REPORT.md"))
    ap.add_argument("--notes", default=None)
    a = ap.parse_args()
    data = {}
    for label, cfg in CONFIGS:
        data[label] = {v: collect(*cfg[v]) for v in ("agent", "baseline")}
    truth = {c: json.loads((ROOT / "data" / "cases" / c / "truth.json").read_text()) for c in PILOTS}
    A = {l: {v: agg(rows) for v, rows in d.items() if rows} for l, d in data.items()}
    first = data["p3 / new rubric"]["agent"][0]["summary"]
    L = ["# RUN_REPORT: pre-sandbox agent runs vs no-tools baseline, before and after the fixes", "",
         "**Pre-sandbox run, 5 dev cases, not a benchmark.** Host-only document (shows truth labels). The agent is a plain tool-calling loop over the six skills on the hosted endpoint; the baseline is the same model, one prompt, no tools. "
         "Scored by the judge panel (Gemini 3.1 Pro, Claude Opus 4.8, GPT-5.5) and the two-stage hallucination check. Caveat: the Claude judge is the same model as the document-generation model.", "",
         f"Agent model `{first['model_id']}`, temperature {first['temperature']}. p3 prompt hash `{first['prompt_sha256'][:12]}`, git `{(first['git_sha'] or '')[:8]}` (dirty at run time).", "",
         "**What changed.** p2 = first final harness (previous report). p3 = after: `parse_denial_eob` no longer emits modifier-blank noise (`blank_fields` became `missing_required`), three prompt rules (apply only relevant sections; `met` needs an evidence file and a fact; never state values no document gives; do not quote tool metadata), a `self_check` warning for `met` without evidence, and for the baseline the same two content rules. "
         "The **rubric** was also relaxed (references accept either the EOB or the denial letter for the denial reason and for the category-8 missing item; see `docs/RUBRIC_CHANGES.md`). Rows below separate the two effects: *p2 / old rubric* -> *p2 / new rubric* isolates the rubric change; *p2 / new rubric* -> *p3 / new rubric* isolates the agent changes.", ""]
    for variant, title in (("agent", "Agent (with tools)"), ("baseline", "Baseline (no tools)")):
        L += [f"## {title}", "",
              "| configuration | runs | decision correct (auto) | decision.json valid | criterion pass, panel (all) | per judge gem/cla/gpt | content pass (judge criteria only) | per judge content | upheld material / run | clean-run rate | unanimity |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for label, _ in CONFIGS:
            x = A[label].get(variant)
            if x:
                L.append(f"| {label} | {x['n']} | {pct(x['dec_ok'])} | {pct(x['valid'])} | {pct(x['pass'], 1)} | {fmt_j(x['jr'])} | {pct(x['content'], 1)} | {fmt_j(x['cj'])} | {x['material']:.2f} | {pct(x['clean'])} | {pct(x['unanimity'])} |")
        L += ["", "| configuration | tool error rate | malformed calls (tool + final format) | model-call failures | mean turns | mean tool calls | mean tokens | mean seconds | revision rate | repeat SD of pass rate (per case) | same decision across repeats |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        for label, _ in CONFIGS:
            x = A[label].get(variant)
            if x:
                L.append(f"| {label} | {pct(x['tool_fail'], 1)} | {x['malformed']} | {x['fails']} | {x['turns']:.1f} | {x['tools']:.1f} | {x['tokens']:,.0f} | {x['secs']:.0f} | {pct(x['rev'])} | {pct(x['sd'], 1)} | {(str(x['same'][0]) + '/' + str(x['same'][1])) if x['same'] else 'n/a (1 repeat)'} |")
        L.append("")
    L += ["Clean-run rate = share of runs with zero upheld material hallucinations. The baseline's `decision.json` validity is reported separately from content scores: **content pass** counts only judge-graded criteria, so an invalid decision.json does not depress it. "
          "Containment: 0 violations; path-guard denials are listed below.", "", "## Per case (p3 / new rubric)", "",
          "| case | truth | variant | run | model decision | decision ok | decision.json valid | panel pass | content pass | upheld material | minor | turns | tools | tokens | s |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for variant in ("agent", "baseline"):
        for r in data["p3 / new rubric"][variant]:
            s = r["summary"]
            L.append(f"| {r['case']} | {truth[r['case']]['correct_decision']} | {variant} | {r['run']} | {r['decision']} | {'yes' if r['dec_ok'] else 'NO'} | {'yes' if r['valid'] else 'NO'} | {pct(r['pass_rate'])} | {pct(r['content'])} | {r['material']} | {r['minor']} | {s['turns']} | {s['tool_calls_total']} | {s['usage'].get('total_tokens')} | {s['seconds']} |")
    L += ["", "## Failed criteria in p3 (any judge)", ""]
    for variant in ("agent", "baseline"):
        d = {}
        for r in data["p3 / new rubric"][variant]:
            d.setdefault(r["case"], []).extend(r["failed"])
        L.append(f"- {variant}: " + ("; ".join(f"{c}: {', '.join(v)}" for c, v in d.items() if v) or "none"))
    L += ["", "## Remaining upheld material hallucination flags (p3 / new rubric)", ""]
    n = 0
    for variant in ("agent", "baseline"):
        for r in data["p3 / new rubric"][variant]:
            for f in r["flags"]:
                n += 1
                L.append(f"{n}. **{variant} {r['run']} {r['case']}**: \"{f['quote'][:180].strip()}\" | problem: {f['problems'][0][:220].strip()}")
    if not n:
        L.append("none")
    guard = [(r["run"], r["case"], r["summary"]["path_guard_denials"]) for r in data["p3 / new rubric"]["agent"] if r["summary"]["path_guard_denials"]]
    L += ["", "## Containment", "", f"Path-guard denials in p3 agent runs: {guard or 'none'}. No run could read `truth.json`, `rubric.json`, `gold/` or `attacks/` (not in the staged copy)."]
    for cid in ("C-0005", "C-0030"):
        L += ["", f"## Case study {cid} (agent, agent-p3-r1; truth: {truth[cid]['correct_decision']})", ""]
        for t in (load(R / "agent-p3-r1" / cid / "trace.json") or []):
            L.append(f"{t['n']}. **{t['kind']} {t['name']}** ({t['status']}, {t['duration_ms']} ms): {t['args_summary'][:90] + ' -> ' if t['args_summary'] and t['kind'] == 'tool' else ''}{t['result_summary'][:170]}")
    jt = {}
    for label, _ in CONFIGS:
        for variant in ("agent", "baseline"):
            for r in data[label][variant]:
                for key in ("jtokens", "htokens"):
                    for jk, u in r[key].items():
                        t = jt.setdefault(jk, [0, 0])
                        t[0] += u.get("prompt_tokens", 0)
                        t[1] += u.get("completion_tokens", 0)
    p3a, p3b = data["p3 / new rubric"]["agent"], data["p3 / new rubric"]["baseline"]
    L += ["", "## Cost and time", "",
          f"- p3 agent: {sum(r['summary']['usage'].get('total_tokens', 0) for r in p3a):,} tokens over {len(p3a)} runs ({A['p3 / new rubric']['agent']['secs']:.0f} s average); p3 baseline: {sum(r['summary']['usage'].get('total_tokens', 0) for r in p3b):,} tokens over {len(p3b)} runs.",
          "- All judging in this report (3 configurations, grading + both hallucination stages): " + ", ".join(f"{k} {v[0]:,} prompt + {v[1]:,} completion tokens" for k, v in sorted(jt.items())) + "."]
    if a.notes:
        L.append(Path(a.notes).read_text())
    Path(a.out).write_text("\n".join(L) + "\n")
    print("wrote", a.out)


main()
