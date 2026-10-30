---
name: self_check
description: Deterministic checklist of a candidate deliverable.md + decision.json against the case documents and policy library.
format: pending Hermes docs
---

# self_check  (STUB: format pending Hermes docs)

Deterministic checklist of a candidate deliverable.md + decision.json against the case documents and policy library.

- Reads: Reads case documents, the policy library and the model's output files.
- Run: `python -m skills.self_check '<json args>'` (prints JSON; see docs/SKILLS_SPEC.md for the input/output schema, example and errors).
- Offline and deterministic: no model calls, no network, no keys. Refuses paths outside the configured roots and any `truth.json`, `rubric.json`, `gold` or `attacks`.
- NOT registered with Hermes yet: the real SKILL.md format, tool registration and sandbox mount points are unknown until the VM is available.
