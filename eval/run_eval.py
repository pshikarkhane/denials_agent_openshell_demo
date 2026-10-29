"""Run the judge panel and the hallucination check on a set of deliverables and write runs/<run_id>/.
  python -m eval.run_eval --source gold [--cases C-0005 ...] [--judges gemini claude gpt] [--run-id NAME]
--source gold reads data/cases/<id>/gold/ ; any other value is a directory of <case_id>/{deliverable.md,decision.json}.
runs/ is gitignored; raw judge outputs are saved under runs/<run_id>/raw/ with keys redacted."""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from data_gen.gen_cases import load_truths
from eval.common import ROOT, Caller, load_models
from eval.hallucination_check import hallucination_case
from eval.judge_panel import grade_case


def run(cfg, root, source, cases, judges, run_id):
    run_dir = Path(ROOT / "runs" / run_id)
    (run_dir / "cases").mkdir(parents=True, exist_ok=True)
    call = Caller(cfg, run_dir, judges)
    t0 = time.time()
    summary = {"run_id": run_id, "source": source, "judges": call.models, "started": datetime.now(timezone.utc).isoformat(), "cases": {}}
    for cid in cases:
        d = root / "cases" / cid / "gold" if source == "gold" else Path(source) / cid
        panel = grade_case(call, root, cid, d, tuple(judges))
        hal = hallucination_case(call, root, cid, d, tuple(judges))
        (run_dir / "cases" / f"{cid}.json").write_text(json.dumps({"panel": panel, "hallucination": hal}, indent=1, default=str) + "\n")
        summary["cases"][cid] = {"panel_pass_rate": panel["panel_pass_rate"], "judge_pass_rates": panel["judge_pass_rates"],
                                 "unanimity_rate": panel["unanimity_rate"], "judge_failures": panel["judge_failures"] + hal["judge_failures"],
                                 "fabricated_quotes": panel["fabricated_quotes"], "upheld_material": hal["upheld_material"], "upheld_minor": hal["upheld_minor"],
                                 "failed": sorted(panel["failed_criteria"]), "tokens": panel["tokens"], "hal_tokens": hal["tokens"]}
        print(cid, {k: v for k, v in summary["cases"][cid].items() if k not in ("tokens", "hal_tokens")}, flush=True)
    summary["seconds"] = round(time.time() - t0, 1)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--source", default="gold")
    ap.add_argument("--cases", nargs="*")
    ap.add_argument("--judges", nargs="*", default=["gemini", "claude", "gpt"])
    ap.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))
    a = ap.parse_args(argv)
    root = Path(a.data)
    man, _ = load_truths(root)
    run(load_models(), root, a.source, a.cases or man["pilot_cases"], a.judges, a.run_id)


if __name__ == "__main__":
    main()
