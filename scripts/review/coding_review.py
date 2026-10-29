"""Part 4: coding tables A-E from docs/PILOT_REVIEW.md. Reviewers flag each line suspect / no concern with confidence. They are NOT
authoritative and must never say 'correct'."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW, ROOT, ask, load_models, parse_json, reviewers, run_parallel  # noqa: E402

PROMPT = """You are helping triage a table of medical coding pairings used in a SYNTHETIC test dataset for a denial-appeal agent. You are NOT an authoritative coding source: never say a line is 'correct' or 'valid'. For each numbered line answer only "suspect" or "no concern", with a confidence (low/medium/high) and a one-line reason. Prioritize likely problems: CPT/ICD-10 fit and ICD-10 Excludes1 conflicts when two diagnosis codes are listed together on one claim (the table lists codes individually, so also say which COMBINATIONS you would flag if you know how they were combined: see note), RARC fit for each CARC, NCCI-style bundling pairs and whether modifier 59/XS would plausibly be allowed or the code is bundled by CPT rules, and whether the scenario text matches the CARC.

Context: claims in categories 1-2 carry TWO diagnosis codes drawn from {{M54.16, M51.16, M54.17, M51.17, M51.26}} with CPT 72148. Table A-D lines were derived from the dataset; table E lists category-to-CARC scenario pairs. Category 11 deliberately uses diagnoses that do not fit the procedure (table B), and its corrected diagnoses appear in table A.

Respond with ONE JSON object: {{"lines": [{{"id": "A1", "verdict": "suspect|no concern", "confidence": "low|medium|high", "reason": "..."}}], "combination_flags": [{{"codes": "...", "confidence": "...", "reason": "..."}}]}} covering EVERY line id.

{table}
"""


def parse_tables():
    text = (ROOT / "docs" / "PILOT_REVIEW.md").read_text()
    sec = text[text.index("## Coding review"):]
    out, cur, n = [], None, 0
    for line in sec.splitlines():
        m = re.match(r"### ([A-E])\. (.*)", line)
        if m:
            cur, n = m.group(1), 0
            out.append(f"\n### Table {cur}: {m.group(2)}")
        elif line.startswith("- ") and cur:
            n += 1
            out.append(f"{cur}{n}. " + re.split(r"\s*\|\s*\[ \]", line[2:])[0])
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
