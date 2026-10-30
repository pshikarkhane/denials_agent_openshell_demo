---
name: retrieve_payer_policy
description: Find the governing payer policy for a denial (payer + date filter first, then title/BM25 ranking) and return its sections and stated windows.
version: 1.0.0
author: R1 appeals demo
metadata:
  hermes:
    tags: [appeals, deterministic-tool]
---

# retrieve_payer_policy

Find the governing payer policy for a denial (payer + date filter first, then title/BM25 ranking) and return its sections and stated windows.

## When to Use
When working an insurance denial case that is staged in this sandbox (the task names a case id such as `C-0005`).
This tool is deterministic and offline: it extracts or computes facts; the judgment stays with you.

## Procedure
Run with the `terminal` tool (one JSON object as the last argument; use `'{}'` if there are no arguments):

    /usr/local/share/appeals/bin/run_skill <CASE_ID> retrieve_payer_policy '<json args>'

Arguments:
- `payer` (string, required)
- `dos` (string, required)
- `cpt` (string, optional)
- `service_description` (string, optional)
- `icd10` (array[string], optional)
- `denial_code` (string, optional)
- `denial_text` (string, optional)
- `reason_text` (string, optional)
- `policy_title` (string, optional)
- `top_k` (integer, optional)

The output is one JSON object on stdout. On failure it is `{"error": {"code": ..., "message": ...}}` and the exit code is 1.
Reads: Reads the policy library.

## Pitfalls
- Never pass file roots; the wrapper binds the case, the policy library and the output folder.
- Paths are relative to the case (for example `docs/notes/...`). `..`, absolute paths and files named `truth.json`,
  `rubric.json`, `gold` or `attacks` are refused and logged.

## Verification
The JSON parses and has no top-level `error` key. Full contract: docs/SKILLS_SPEC.md in the repository.
