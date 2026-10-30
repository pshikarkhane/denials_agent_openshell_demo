---
name: draft_deliverable
description: Validation helpers for drafting: validate decision.json, render a deliverable.md skeleton, verify citations.
version: 1.0.0
author: R1 appeals demo
metadata:
  hermes:
    tags: [appeals, deterministic-tool]
---

# draft_deliverable

Validation helpers for drafting: validate decision.json, render a deliverable.md skeleton, verify citations.

## When to Use
When working an insurance denial case that is staged in this sandbox (the task names a case id such as `C-0005`).
This tool is deterministic and offline: it extracts or computes facts; the judgment stays with you.

## Procedure
Run with the `terminal` tool (one JSON object as the last argument; use `'{}'` if there are no arguments):

    /usr/local/share/appeals/bin/run_skill <CASE_ID> draft_deliverable '<json args>'

Arguments:
- `action` (string, required)
- `kind` (string, optional)
- `decision_path` (string, optional)
- `decision_text` (string, optional)
- `deliverable_path` (string, optional)
- `deliverable_text` (string, optional)
- `policy_id` (string, optional)

The output is one JSON object on stdout. On failure it is `{"error": {"code": ..., "message": ...}}` and the exit code is 1.
Reads: Reads case documents, the policy library and (for validation) the model's own output files.

## Pitfalls
- Never pass file roots; the wrapper binds the case, the policy library and the output folder.
- Paths are relative to the case (for example `docs/notes/...`). `..`, absolute paths and files named `truth.json`,
  `rubric.json`, `gold` or `attacks` are refused and logged.

## Verification
The JSON parses and has no top-level `error` key. Full contract: docs/SKILLS_SPEC.md in the repository.
