---
name: draft_deliverable
description: Validation helpers for drafting: validate decision.json, render a deliverable.md skeleton, verify citations.
format: pending Hermes docs
---

# draft_deliverable  (STUB: format pending Hermes docs)

Validation helpers for drafting: validate decision.json, render a deliverable.md skeleton, verify citations.

- Reads: Reads case documents, the policy library and (for validation) the model's own output files.
- Run: `python -m skills.draft_deliverable '<json args>'` (prints JSON; see docs/SKILLS_SPEC.md for the input/output schema, example and errors).
- Offline and deterministic: no model calls, no network, no keys. Refuses paths outside the configured roots and any `truth.json`, `rubric.json`, `gold` or `attacks`.
- NOT registered with Hermes yet: the real SKILL.md format, tool registration and sandbox mount points are unknown until the VM is available.
