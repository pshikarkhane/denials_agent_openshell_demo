---
name: parse_denial_eob
description: Parse eob_835.txt, denial_letter.txt and task.md into structured denial facts.
version: 1.0.0
author: R1 appeals demo
metadata:
  hermes:
    tags: [appeals, deterministic-tool]
---

# parse_denial_eob

Parse eob_835.txt, denial_letter.txt and task.md into structured denial facts.

## When to Use
When working an insurance denial case that is staged in this sandbox (the task names a case id such as `C-0005`).
This tool is deterministic and offline: it extracts or computes facts; the judgment stays with you.

## Procedure
Run with the `terminal` tool (one JSON object as the last argument; use `'{}'` if there are no arguments):

    /usr/local/share/appeals/bin/run_skill <CASE_ID> parse_denial_eob '<json args>'

Arguments:
- (none)

The output is one JSON object on stdout. On failure it is `{"error": {"code": ..., "message": ...}}` and the exit code is 1.
Reads: Reads docs/eob_835.txt, docs/denial_letter.txt, task.md.

## Pitfalls
- Never pass file roots; the wrapper binds the case, the policy library and the output folder.
- Paths are relative to the case (for example `docs/notes/...`). `..`, absolute paths and files named `truth.json`,
  `rubric.json`, `gold` or `attacks` are refused and logged.

## Verification
The JSON parses and has no top-level `error` key. Full contract: docs/SKILLS_SPEC.md in the repository.
