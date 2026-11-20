"""Judge-validation runner: production criterion grading + two-stage hallucination check on mutations, controls and test-retest repeats.
Throttled (default 2 concurrent calls; a Hermes run shares the key/endpoints), cached per call, resumable per item. Nothing in data/ is touched.
  python -m eval.validation_run --run-id val1 --estimate
  python -m eval.validation_run --run-id val1 --set mutations --limit 5          # pilot
  python -m eval.validation_run --run-id val1 --set mutations --resume           # full set; skips finished items
  python -m eval.validation_run --run-id val1 --set retest --resume
Item sets: mutations (runs/<mut_run>/mutations/*), retest (p3 agent + p3 baseline outputs, x2 repeats) and goldrepeat (unchanged gold x2)."""
import argparse
import hashlib
import json
import random
import re
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from eval.common import ROOT, Caller, JUDGE_KEYS, load_models
from eval.hallucination_check import hallucination_case
from eval.judge_panel import grade_case

TOKENS_PER_ITEM = {"prompt": 88_000, "completion": 15_000}   # measured on earlier judge runs, 3 judges, grading + hallucination
SECS_PER_ITEM_AT_2 = 330                                      # rough wall-clock for one item at concurrency 2
RATE_MARKERS = ("429", "rate limit", "too many requests", "overloaded", "503", "502", "timed out", "timeout")


class ThrottledCaller:
    """Wraps a judge caller: at most `max_concurrency` calls in flight, outer backoff on rate limits, a per-call disk cache and
    a tag prefix so raw files of different items never collide. `inner(jkey, prompt, tag, max_tokens)` -> (text, usage, secs)."""

    def __init__(self, inner, cache_dir, max_concurrency=2, prefix="", repeat=1, max_wait=60.0, sleep=time.sleep):
        self.inner, self.cache = inner, Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.sem = threading.Semaphore(max_concurrency)
        self.prefix, self.repeat, self.max_wait, self.sleep = prefix, repeat, max_wait, sleep
        self.stats = {"calls": 0, "cache_hits": 0, "retries": 0}
        self.lock = threading.Lock()

    def for_item(self, prefix, repeat):
        c = ThrottledCaller.__new__(ThrottledCaller)
        c.__dict__.update(self.__dict__)
        c.prefix, c.repeat = prefix, repeat
        return c

    def key(self, jkey, tag, prompt):
        return hashlib.sha256(f"{jkey}|{self.prefix}{tag}|{self.repeat}|{prompt}".encode()).hexdigest()

    def __call__(self, jkey, prompt, tag, max_tokens=16000):
        k = self.key(jkey, tag, prompt)
        f = self.cache / f"{k}.json"
        if f.exists():
            with self.lock:
                self.stats["cache_hits"] += 1
            d = json.loads(f.read_text())
            return d["text"], d["usage"], d["secs"]
        delay = 5.0
        while True:
            with self.sem:
                try:
                    text, usage, secs = self.inner(jkey, prompt, f"{self.prefix}{tag}", max_tokens)
                    break
                except Exception as e:
                    if not any(m in str(e).lower() for m in RATE_MARKERS) or delay > self.max_wait:
                        raise
            with self.lock:
                self.stats["retries"] += 1
            self.sleep(delay + random.random())
            delay *= 2
        with self.lock:
            self.stats["calls"] += 1
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps({"text": text, "usage": usage, "secs": secs}))
        tmp.replace(f)
        return text, usage, secs


# ---------------------------------------------------------------- item sets
def mutation_items(run_dir):
    base = Path(run_dir) / "mutations"
    out = []
    for e in json.loads((base / "items.json").read_text()):
        out.append({"item_id": e["item_id"], "case_id": e["case_id"], "type": e["type"], "dir": base / e["item_id"], "repeat": 1})
    return round_robin(out)


def round_robin(items):
    """Interleave by type so a small --limit pilot covers varied mutation types."""
    by = {}
    for it in items:
        by.setdefault(it["type"], []).append(it)
    out = []
    while any(by.values()):
        for ty in sorted(by):
            if by[ty]:
                out.append(by[ty].pop(0))
    return out


def retest_items(runs_dir, repeats=(2, 3)):
    """Same outputs as the p3 agent and baseline runs (repeat 1 already exists as judge-*-p3-*): re-judged for repeats 2 and 3."""
    runs = Path(runs_dir)
    out = []
    for r in repeats:
        for n in (1, 2, 3):
            for c in sorted((runs / f"agent-p3-r{n}").glob("C-*")):
                out.append({"item_id": f"agent-p3-r{n}__{c.name}", "case_id": c.name, "type": "agent", "dir": c, "repeat": r})
        for n in (1, 2):
            for c in sorted((runs / f"baseline-p3-r{n}" / "baseline").glob("C-*")):
                out.append({"item_id": f"baseline-p3-r{n}__{c.name}", "case_id": c.name, "type": "baseline", "dir": c, "repeat": r})
    return out


def gold_repeat_items(data_root, repeats=(2, 3)):
    out = []
    for r in repeats:
        for c in sorted((Path(data_root) / "cases").glob("C-*")):
            if (c / "gold" / "deliverable.md").exists():
                out.append({"item_id": f"gold__{c.name}", "case_id": c.name, "type": "gold", "dir": c / "gold", "repeat": r})
    return out


def estimate(items, max_concurrency):
    n = len(items)
    p, c = n * TOKENS_PER_ITEM["prompt"], n * TOKENS_PER_ITEM["completion"]
    hours = n * SECS_PER_ITEM_AT_2 * (2 / max_concurrency) / 3600
    return {"items": n, "prompt_tokens": p, "completion_tokens": c, "approx_hours_at_concurrency": round(hours, 2), "max_concurrency": max_concurrency}


# ---------------------------------------------------------------- run
def item_file(run_dir, it):
    return Path(run_dir) / "items" / f"{it['item_id']}__r{it['repeat']}.json"


def run_item(caller, data_root, run_dir, it, judge_keys=JUDGE_KEYS):
    c = caller.for_item(f"{it['item_id']}_r{it['repeat']}_", it["repeat"])
    t0 = time.time()
    panel = grade_case(c, data_root, it["case_id"], it["dir"], judge_keys, workers=2)
    hal = hallucination_case(c, data_root, it["case_id"], it["dir"], judge_keys, workers=2)
    out = {"item_id": it["item_id"], "case_id": it["case_id"], "type": it["type"], "repeat": it["repeat"], "panel": panel, "hallucination": hal,
           "wall_s": round(time.time() - t0, 1)}
    f = item_file(run_dir, it)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, indent=1))
    tmp.replace(f)
    return out


def record_failure(run_dir, it, exc):
    """Failed items are never treated as 'no flag' / 'not detected': they are logged with the full traceback and marked FAILED."""
    rec = {"item_id": it["item_id"], "repeat": it["repeat"], "type": it["type"], "case_id": it["case_id"], "status": "FAILED",
           "error": f"{type(exc).__name__}: {exc}", "traceback": "".join(traceback.format_exception(exc)), "time": datetime.now(timezone.utc).isoformat()}
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "errors.jsonl").open("a") as fh:
        fh.write(json.dumps(rec) + "\n")
    fdir = run_dir / "failed"
    fdir.mkdir(exist_ok=True)
    (fdir / item_file(run_dir, it).name).write_text(json.dumps(rec, indent=1))
    return rec


def run_items(caller, data_root, run_dir, items, resume=True, limit=None, judge_keys=JUDGE_KEYS, log=print, debug=False):
    done = failed = 0
    todo = [it for it in items if not (resume and item_file(run_dir, it).exists())]  # only OK items have an item file; FAILED ones are retried
    if limit:
        todo = todo[:limit]
    for i, it in enumerate(todo, 1):
        try:
            r = run_item(caller, data_root, run_dir, it, judge_keys)
            (Path(run_dir) / "failed" / item_file(run_dir, it).name).unlink(missing_ok=True)
            done += 1
            log(f"[{i}/{len(todo)}] {it['item_id']} r{it['repeat']} ok  panel_pass={r['panel']['panel_pass_rate']:.2f} material={r['hallucination']['upheld_material']}  {r['wall_s']}s")
        except Exception as e:
            failed += 1
            rec = record_failure(run_dir, it, e)
            log(f"[{i}/{len(todo)}] {it['item_id']} r{it['repeat']} FAILED: {rec['error'][:160]}  (traceback in errors.jsonl)")
            if debug:
                log(rec["traceback"])
    return {"done": done, "failed": failed, "pending_after": len(todo) - done - failed if limit else None, "stats": caller.stats}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--mutations-run", default=None, help="run id holding mutations/ (default: --run-id)")
    ap.add_argument("--set", choices=["mutations", "retest", "goldrepeat"], default="mutations")
    ap.add_argument("--data", default="data")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--resume", action="store_true", default=True)
    ap.add_argument("--no-resume", dest="resume", action="store_false")
    ap.add_argument("--debug", action="store_true", help="print the full traceback of failed items")
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--max-concurrency", type=int, default=2)
    a = ap.parse_args(argv)
    run_dir = ROOT / "runs" / a.run_id
    data_root = Path(a.data)
    if a.set == "mutations":
        items = mutation_items(ROOT / "runs" / (a.mutations_run or a.run_id))
    elif a.set == "retest":
        items = retest_items(ROOT / "runs")
    else:
        items = gold_repeat_items(data_root)
    if a.estimate:
        print(json.dumps(estimate(items, a.max_concurrency), indent=1))
        return
    cfg = load_models()
    caller = ThrottledCaller(Caller(cfg, run_dir), run_dir / "cache", a.max_concurrency)
    print(json.dumps(run_items(caller, data_root, run_dir, items, a.resume, a.limit, debug=a.debug), default=str))


if __name__ == "__main__":
    main()
