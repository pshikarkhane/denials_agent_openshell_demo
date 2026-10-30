---
name: assess_appealability
description: Deterministic facts only: deadlines, day counts, timely-filing arithmetic, claim-history facts, criteria skeleton with evidence candidates. Never a decision.
format: pending Hermes docs
---

# assess_appealability  (STUB: format pending Hermes docs)

Deterministic facts only: deadlines, day counts, timely-filing arithmetic, claim-history facts, criteria skeleton with evidence candidates. Never a decision.

- Reads: Reads the case documents and the policy library.
- Run: `python -m skills.assess_appealability '<json args>'` (prints JSON; see docs/SKILLS_SPEC.md for the input/output schema, example and errors).
- Offline and deterministic: no model calls, no network, no keys. Refuses paths outside the configured roots and any `truth.json`, `rubric.json`, `gold` or `attacks`.
- NOT registered with Hermes yet: the real SKILL.md format, tool registration and sandbox mount points are unknown until the VM is available.
