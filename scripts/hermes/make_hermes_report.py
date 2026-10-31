#!/usr/bin/env python3
"""Generate docs/HERMES_RUN_REPORT.md (host-only: reads truth labels). Metrics are computed with the SAME code as docs/RUN_REPORT.md
(scripts/make_run_report.py: collect/agg), side by side with the pre-sandbox p3 numbers parsed from docs/RUN_REPORT.md.
  python scripts/hermes/make_hermes_report.py --runs hermes-p1-r1 hermes-p1-r2 --judges judge-hermes-p1-r1 judge-hermes-p1-r2 [--notes docs/hermes_report_notes.md]"""
import argparse
import json
import re
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import types  # noqa: E402

# scripts/make_run_report.py calls main() at import time and must not be edited here: load its functions without that last call.
_src = (ROOT / "scripts" / "make_run_report.py").read_text().rstrip()
assert _src.endswith("\nmain()")
m = types.ModuleType("make_run_report")
m.__file__ = str(ROOT / "scripts" / "make_run_report.py")
exec(compile(_src[: -len("main()")], m.__file__, "exec"), m.__dict__)

_orig_load = m.load


def _load(p):
    d = _orig_load(p)
    if isinstance(d, dict) and d.get("runtime") == "hermes":      # fields the stand-in summary has and Hermes does not
        d.setdefault("malformed_final", 0)
        d.setdefault("model_failures", [])
    return d


m.load = _load
pct, mean = m.pct, m.mean


def stand_in_p3():
    """Pull the p3 / new rubric agent rows out of docs/RUN_REPORT.md (the raw pre-sandbox runs are not in this checkout)."""
    txt = (ROOT / "docs" / "RUN_REPORT.md").read_text()
    agent = txt.split("## Agent (with tools)")[1].split("## Baseline")[0]
    rows = [ln for ln in agent.splitlines() if ln.startswith("| p3 / new rubric |")]
    t1, t2 = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
    return {"runs": t1[1], "dec": t1[2], "valid": t1[3], "panel": t1[4], "per_judge": t1[5], "content": t1[6], "content_j": t1[7], "material": t1[8], "clean": t1[9], "unan": t1[10],
            "tool_err": t2[1], "malformed": t2[2], "model_fail": t2[3], "turns": t2[4], "tools": t2[5], "tokens": t2[6], "secs": t2[7], "rev": t2[8], "sd": t2[9], "same": t2[10]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--judges", nargs="+", required=True)
    ap.add_argument("--notes")
    ap.add_argument("--out", default=str(ROOT / "docs" / "HERMES_RUN_REPORT.md"))
    a = ap.parse_args()
    rows = m.collect([m.R / r for r in a.runs], a.judges)
    x = m.agg(rows)
    sums = [r["summary"] for r in rows]
    S = stand_in_p3()
    truth = {c: json.loads((ROOT / "data" / "cases" / c / "truth.json").read_text()) for c in m.PILOTS}
    allsum = []
    for r in a.runs:
        for c in m.PILOTS:
            s = _orig_load(m.R / r / c / "summary.json")
            if s:
                allsum.append(s)
    n = len(allsum)
    both = [s for s in allsum if {"deliverable.md", "decision.json"} <= set(s["files_copied"])]
    sc_ok = [s for s in allsum if (s.get("final_self_check") or {}).get("ok")]
    rev = [s for s in allsum if s["revisions"]]
    agent_ok = [s for s in allsum if s.get("agent_last_self_check_ok")]
    first_call = [s["usage"]["first_call_prompt_tokens"] for s in allsum if s["usage"].get("first_call_prompt_tokens")]
    rv = [s["background_review"] for s in allsum]
    persisted = [s for s in allsum if s["persisted_after_run"]]
    f = lambda v, d=0: "n/a" if v is None else f"{v:,.{d}f}"  # noqa: E731
    g = sums[0]
    L = ["# HERMES_RUN_REPORT: the six skills through the real Hermes agent in the OpenShell sandbox", "",
         f"**Hermes in OpenShell, {len(m.PILOTS)} dev cases, not a benchmark.** Host-only document (shows truth labels). Same cases, same skills (restaged from the current `skills/`), same scoring as docs/RUN_REPORT.md "
         "(judge panel Gemini 3.1 Pro / Claude Opus 4.8 / GPT-5.5 plus the two-stage hallucination check). Caveat: the Claude judge is the same model as the document-generation model. "
         "Pre-sandbox numbers are the p3 / new-rubric agent row of RUN_REPORT.md (15 runs); the raw pre-sandbox run folders are not in this checkout, so they are quoted, not recomputed.", "",
         f"Agent: Hermes Agent {g['hermes_version']} in sandbox `my-hermes`, upstream model `{g['model_id']}` (route set by NemoClaw; temperature not exposed). Prompt (`scripts/hermes/prompts/hermes_system.md`) hash `{g['prompt_sha256'][:12]}`, git `{(g['git_sha'] or '')[:8]}`. "
         f"Runs: {', '.join(a.runs)}; judge runs: {', '.join(a.judges)}.", "",
         "## What happened to the runs", "",
         "| measure | count |", "|---|---|",
         f"| runs started | {n} |", f"| runs that finished (stream completed) | {sum(1 for s in allsum if s['hermes_stream_state'] == 'completed')} |",
         f"| runs that wrote both files (deliverable.md and decision.json) | {len(both)} |",
         f"| runs whose final files pass `self_check` (run by the harness after the run) | {len(sc_ok)} |",
         f"| runs whose agent's own last self_check call passed | {len(agent_ok)} |",
         f"| runs that used the revision step (a failing self_check followed by another) | {len(rev)} |",
         f"| runs that needed a gateway-restart retry | {sum(1 for s in allsum if s['retries'])} |",
         f"| runs where Hermes persisted anything beyond the baseline before our reset (excluding `.curator_state`) | {sum(1 for s in allsum if set(s['persisted_after_run']) - {'skills_added'} or [k for k in s['persisted_after_run'].get('skills_added', []) if k != '.curator_state'])} |", "",
         "## Side by side: Hermes vs the pre-sandbox stand-in (p3, new rubric)", "",
         "| measure | Hermes in OpenShell | pre-sandbox stand-in (p3) |", "|---|---|---|",
         f"| runs | {x['n']} | {S['runs']} |", f"| decision correct (auto) | {pct(x['dec_ok'])} | {S['dec']} |", f"| decision.json valid | {pct(x['valid'])} | {S['valid']} |",
         f"| criterion pass, panel (all) | {pct(x['pass'], 1)} | {S['panel']} |", f"| per judge gem/cla/gpt | {m.fmt_j(x['jr'])} | {S['per_judge']} |",
         f"| content pass (judge criteria only) | {pct(x['content'], 1)} | {S['content']} |", f"| per judge content | {m.fmt_j(x['cj'])} | {S['content_j']} |",
         f"| upheld material hallucinations / run | {x['material']:.2f} | {S['material']} |", f"| clean-run rate (0 upheld material) | {pct(x['clean'])} | {S['clean']} |", f"| judge unanimity | {pct(x['unanimity'])} | {S['unan']} |",
         f"| tool error rate (skill + other Hermes tools) | {pct(x['tool_fail'], 1)} | {S['tool_err']} (skills only) |",
         f"| tool error rate, skill calls only | {pct(sum(s['skill_errors'] for s in allsum) / max(1, sum(s['skill_calls_total'] for s in allsum)), 1)} | {S['tool_err']} |",
         f"| malformed skill calls | {sum(s['malformed_calls'] for s in allsum)} | {S['malformed']} |",
         f"| mean turns (model calls) | {x['turns']:.1f} | {S['turns']} |", f"| mean tool calls (all Hermes tools) | {x['tools']:.1f} | {S['tools']} (skills only) |",
         f"| mean skill calls | {mean([s['skill_calls_total'] for s in allsum]):.1f} | {S['tools']} |",
         f"| mean tokens / run (run's own model calls) | {f(x['tokens'])} | {S['tokens']} |",
         f"| Hermes fixed prompt overhead (first call prompt tokens, mean) | {f(mean(first_call))} | about 2,750 |",
         f"| mean tokens / run in Hermes' post-run background review (NOT in the line above) | {f(mean([r['prompt_tokens'] + r['completion_tokens'] for r in rv]))} | n/a |",
         f"| mean wall-clock seconds / run | {x['secs']:.0f} | {S['secs']} |", f"| revision rate | {pct(x['rev'])} | {S['rev']} |",
         f"| repeat SD of pass rate (per case) | {pct(x['sd'], 1)} | {S['sd']} |", f"| same decision across repeats | {(str(x['same'][0]) + '/' + str(x['same'][1])) if x['same'] else 'n/a'} | {S['same']} |", "",
         "Clean-run rate = share of runs with zero upheld material hallucinations. Stand-in `revision rate` is harness-enforced (self_check failure triggers a revision request); in Hermes it is inferred from the agent's own calls (EVENTS_SPEC, Hermes runs).", ""]
    L += ["## Per case", "",
          "| case | truth | run | model decision | decision ok | decision.json valid | panel pass | content pass | upheld material | minor | turns | skill calls | other tools | tokens | s | final self_check | revisions |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        s = r["summary"]
        L.append(f"| {r['case']} | {truth[r['case']]['correct_decision']} | {r['run']} | {r['decision']} | {'yes' if r['dec_ok'] else 'NO'} | {'yes' if r['valid'] else 'NO'} | {pct(r['pass_rate'])} | {pct(r['content'])} | {r['material']} | {r['minor']} | "
                 f"{s['turns']} | {s['skill_calls_total']} | {sum(s['hermes_tools_by_name'].values())} | {s['usage']['total_tokens']} | {s['seconds']} | {'pass' if (s['final_self_check'] or {}).get('ok') else 'FAIL'} | {s['revisions']} |")
    L += ["", "## Failed criteria (any judge)", ""]
    d = {}
    for r in rows:
        d.setdefault(r["case"], []).extend(r["failed"])
    L.append("- " + ("; ".join(f"{c}: {', '.join(v)}" for c, v in d.items() if v) or "none"))
    L += ["", "## Upheld material hallucination flags", ""]
    k = 0
    for r in rows:
        for fl in r["flags"]:
            k += 1
            L.append(f"{k}. **{r['run']} {r['case']}**: \"{fl['quote'][:200].strip()}\" | problem: {(fl['problems'][0] if fl['problems'] else '')[:240].strip()}")
    if not k:
        L.append("None.")
    L += ["", "## Repeat variance (same case, two repeats)", "", "| case | decisions | panel pass | skill calls | tokens | s |", "|---|---|---|---|---|---|"]
    for c in m.PILOTS:
        rr = [r for r in rows if r["case"] == c]
        L.append(f"| {c} | {' / '.join(str(r['decision']) for r in rr)} | {' / '.join(pct(r['pass_rate']) for r in rr)} | {' / '.join(str(r['summary']['skill_calls_total']) for r in rr)} | "
                 f"{' / '.join(str(r['summary']['usage']['total_tokens']) for r in rr)} | {' / '.join(str(r['summary']['seconds']) for r in rr)} |")
    L += ["", "## Containment and audit", ""]
    L.append(f"- Path-guard denials in all runs: {sum(s['path_guard_denials'] for s in allsum)}. Denied egress attributable to the run (tag `run`): {sum(s['audit_denied_run'] for s in allsum)}. "
             f"Hermes background denials (github.com, openrouter.ai; tag `background`): {sum(s['audit_background'] for s in allsum)} events across all runs.")
    L.append(f"- Non-skill terminal commands: {sum(s['terminal_non_skill_calls'] for s in allsum)}; reads/searches outside the skills (`read_file`, `search_files`): "
             f"{sum(s['hermes_tools_by_name'].get('read_file', 0) + s['hermes_tools_by_name'].get('search_files', 0) for s in allsum)}.")
    L.append(f"- State left behind by Hermes (before our reset), per run: " + ("; ".join(f"{s['run_id']} {s['case_id']}: {json.dumps(s['persisted_after_run'])}" for s in persisted) or "nothing") + ".")
    L.append(f"- Background self-review: {sum(1 for r in rv if r['calls'])} of {n} runs started one (mean {mean([r['calls'] for r in rv if r['calls']]) or 0:.1f} model calls, "
             f"{f(mean([r['prompt_tokens'] for r in rv if r['calls']]))} prompt tokens each).")
    if a.notes:
        L += ["", Path(a.notes).read_text().rstrip(), ""]
    Path(a.out).write_text("\n".join(L) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
