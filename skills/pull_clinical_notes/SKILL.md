---
name: pull_clinical_notes
description: List (metadata first) or fetch clinical notes and supporting documents in a date range, minimum necessary.
format: pending Hermes docs
---

# pull_clinical_notes  (STUB: format pending Hermes docs)

List (metadata first) or fetch clinical notes and supporting documents in a date range, minimum necessary.

- Reads: Reads docs/notes/** and docs/supporting/**.
- Run: `python -m skills.pull_clinical_notes '<json args>'` (prints JSON; see docs/SKILLS_SPEC.md for the input/output schema, example and errors).
- Offline and deterministic: no model calls, no network, no keys. Refuses paths outside the configured roots and any `truth.json`, `rubric.json`, `gold` or `attacks`.
- NOT registered with Hermes yet: the real SKILL.md format, tool registration and sandbox mount points are unknown until the VM is available.
