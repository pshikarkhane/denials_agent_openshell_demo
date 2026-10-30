---
name: assess_appealability
description: Deterministic facts only: deadlines, day counts, timely-filing arithmetic, claim-history facts, criteria skeleton with evidence candidates. Never a decision.
version: 1.0.0
author: R1 appeals demo
metadata:
  hermes:
    tags: [appeals, deterministic-tool]
---

# assess_appealability

Deterministic facts only: deadlines, day counts, timely-filing arithmetic, claim-history facts, criteria skeleton with evidence candidates. Never a decision.

## When to Use
When working an insurance denial case that is staged in this sandbox (the task names a case id such as `C-0005`).
This tool is deterministic and offline: it extracts or computes facts; the judgment stays with you.

## Procedure
Run with the `terminal` tool (one JSON object as the last argument; use `'{}'` if there are no arguments):

    /usr/local/share/appeals/bin/run_skill <CASE_ID> assess_appealability '<json args>'

Arguments:
- `policy_id` (string, optional)
- `evidence_per_section` (integer, optional)

The output is one JSON object on stdout. On failure it is `{"error": {"code": ..., "message": ...}}` and the exit code is 1.
Reads: Reads the case documents and the policy library.

## Pitfalls
- Never pass file roots; the wrapper binds the case, the policy library and the output folder.
- Paths are relative to the case (for example `docs/notes/...`). `..`, absolute paths and files named `truth.json`,
  `rubric.json`, `gold` or `attacks` are refused and logged.

## Verification
The JSON parses and has no top-level `error` key. Full contract: docs/SKILLS_SPEC.md in the repository.
