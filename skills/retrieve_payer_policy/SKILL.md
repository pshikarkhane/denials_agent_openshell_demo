---
name: retrieve_payer_policy
description: Find the governing payer policy for a denial (payer + date filter first, then title/BM25 ranking) and return its sections and stated windows.
format: pending Hermes docs
---

# retrieve_payer_policy  (STUB: format pending Hermes docs)

Find the governing payer policy for a denial (payer + date filter first, then title/BM25 ranking) and return its sections and stated windows.

- Reads: Reads the policy library.
- Run: `python -m skills.retrieve_payer_policy '<json args>'` (prints JSON; see docs/SKILLS_SPEC.md for the input/output schema, example and errors).
- Offline and deterministic: no model calls, no network, no keys. Refuses paths outside the configured roots and any `truth.json`, `rubric.json`, `gold` or `attacks`.
- NOT registered with Hermes yet: the real SKILL.md format, tool registration and sandbox mount points are unknown until the VM is available.
