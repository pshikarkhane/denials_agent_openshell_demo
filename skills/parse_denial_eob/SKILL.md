---
name: parse_denial_eob
description: Parse eob_835.txt, denial_letter.txt and task.md into structured denial facts.
format: pending Hermes docs
---

# parse_denial_eob  (STUB: format pending Hermes docs)

Parse eob_835.txt, denial_letter.txt and task.md into structured denial facts.

- Reads: Reads docs/eob_835.txt, docs/denial_letter.txt, task.md.
- Run: `python -m skills.parse_denial_eob '<json args>'` (prints JSON; see docs/SKILLS_SPEC.md for the input/output schema, example and errors).
- Offline and deterministic: no model calls, no network, no keys. Refuses paths outside the configured roots and any `truth.json`, `rubric.json`, `gold` or `attacks`.
- NOT registered with Hermes yet: the real SKILL.md format, tool registration and sandbox mount points are unknown until the VM is available.
