"""Part 4: coding tables A-E from docs/PILOT_REVIEW.md. Reviewers flag each line suspect / no concern with confidence. They are NOT
authoritative and must never say 'correct'."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW, ROOT, ask, load_models, parse_json, reviewers, run_parallel  # noqa: E402

PROMPT = """You are helping triage a table of medical coding pairings used in a SYNTHETIC test dataset for a denial-appeal agent. You are NOT an authoritative coding source: never say a line is 'correct' or 'valid'. For each numbered line answer only "suspect" or "no concern", with a confidence (low/medium/high) and a one-line reason. Prioritize likely problems: CPT/ICD-10 fit and ICD-10 Excludes1 conflicts when two diagnosis codes are listed together on one claim (the table lists codes individually, so also say which COMBINATIONS you would flag if you know how they were combined: see note), RARC fit for each CARC, NCCI-style bundling pairs and whether modifier 59/XS would plausibly be allowed or the code is bundled by CPT rules, and whether the scenario text matches the CARC.

Context: the lines come from the current dataset. Section 1 = pairings meant to be valid (categories 1-2 now carry ONE diagnosis per claim), section 2 = deliberate mismatches (category 11), section 3 = CARC/RARC pairs (RARCs were deliberately omitted for CO-197, CO-4, CO-18, CO-16), section 4 = bundling pairs, section 5 = modifier/claim-data scenarios.

Respond with ONE JSON object: {{"lines": [{{"id": "S1.1", "verdict": "suspect|no concern", "confidence": "low|medium|high", "reason": "..."}}], "combination_flags": [{{"codes": "...", "confidence": "...", "reason": "..."}}]}} covering EVERY line id.

{table}
"""


def parse_tables():
    """Numbered lines of docs/CODER_CHECKLIST.md sections 1-5 (ids S<section>.<n>)."""
    text = (ROOT / "docs" / "CODER_CHECKLIST.md").read_text()
    out, sec, n = [], None, 0
    for line in text.splitlines():
        m = re.match(r"## (\d)\. (.*)", line)
        if m:
            sec, n = m.group(1), 0
            out.append(f"\n### Section {sec}: {m.group(2)}")
        elif line.startswith("- ") and sec and sec != "6":
            n += 1
            out.append(f"S{sec}.{n}. " + re.split(r"\s*\|\s*\[ \]", line[2:])[0])
    return "\n".join(out)


def run(cfg):
    prompt = PROMPT.format(table=parse_tables())
    outs = run_parallel([lambda rk=rk, m=m: (rk, ask(cfg, rk, m, "coding_tables", prompt)) for rk, m in reviewers(cfg).items()])
    (RAW / "coding_parsed.json").write_text(json.dumps({k: parse_json(v) for k, v in outs.items()}, indent=2) + "\n")
    (RAW / "coding_table_ids.txt").write_text(parse_tables() + "\n")
    return outs


if __name__ == "__main__":
    for k, v in run(load_models()).items():
        p = parse_json(v)
        print(k, "unparseable" if p is None else f"{len(p.get('lines', []))} lines")
