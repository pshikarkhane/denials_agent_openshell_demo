"""Generate Hermes-format SKILL.md adapters (one per real skill) into sandbox/hermes_skills/<name>/SKILL.md.

The real skills (skills/<name>/, stdlib + pydantic) are NOT changed. A Hermes skill is an instruction document; the agent
runs the command it names through its `terminal` tool. Descriptions come from skills/<name>/SKILL.md and the
argument lists from each skill's pydantic Input model, so the adapters cannot drift from the code.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import importlib  # noqa: E402

SKILLS = ["parse_denial_eob", "retrieve_payer_policy", "pull_clinical_notes", "assess_appealability",
          "draft_deliverable", "self_check"]
COMMON = {"case_root", "policy_root", "output_root", "events_file", "run_id", "case_id", "step"}
RUN = "/usr/local/share/appeals/bin/run_skill"


def type_name(p):
    if "anyOf" in p:
        t = [type_name(x) for x in p["anyOf"] if x.get("type") != "null"]
        return "|".join(t) or "any"
    t = p.get("type", "any")
    return f"{t}[{type_name(p['items'])}]" if t == "array" and "items" in p else t


def describe(name):
    text = (ROOT / "skills" / name / "SKILL.md").read_text()
    desc = re.search(r"^description:\s*(.+)$", text, re.M).group(1).strip()
    reads = re.search(r"^- Reads:\s*(.+)$", text, re.M)
    schema = importlib.import_module(f"skills.{name}").Input.model_json_schema()
    req = set(schema.get("required", []))
    args = [(k, type_name(v), k in req) for k, v in schema["properties"].items() if k not in COMMON]
    return desc, (reads.group(1).strip() if reads else ""), args


def render(name):
    desc, reads, args = describe(name)
    arglines = "\n".join(f"- `{k}` ({t}{', required' if r else ', optional'})" for k, t, r in args) or "- (none)"
    return f"""---
name: {name}
description: {desc}
version: 1.0.0
author: R1 appeals demo
metadata:
  hermes:
    tags: [appeals, deterministic-tool]
---

# {name}

{desc}

## When to Use
When working an insurance denial case that is staged in this sandbox (the task names a case id such as `C-0005`).
This tool is deterministic and offline: it extracts or computes facts; the judgment stays with you.

## Procedure
Run with the `terminal` tool (one JSON object as the last argument; use `'{{}}'` if there are no arguments):

    {RUN} <CASE_ID> {name} '<json args>'

Arguments:
{arglines}

The output is one JSON object on stdout. On failure it is `{{"error": {{"code": ..., "message": ...}}}}` and the exit code is 1.
Reads: {(reads or 'the staged case documents').rstrip('.')}.

## Pitfalls
- Never pass file roots; the wrapper binds the case, the policy library and the output folder.
- Paths are relative to the case (for example `docs/notes/...`). `..`, absolute paths and files named `truth.json`,
  `rubric.json`, `gold` or `attacks` are refused and logged.

## Verification
The JSON parses and has no top-level `error` key. Full contract: docs/SKILLS_SPEC.md in the repository.
"""


def main():
    out = ROOT / "sandbox" / "hermes_skills"
    for n in SKILLS:
        d = out / n
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(render(n))
    print(f"wrote {len(SKILLS)} adapters to {out}")


if __name__ == "__main__":
    main()
