"""Backward-compatible import: the schema now lives in skills/common/deliverable_schema.py so the sandbox image needs no eval/ folder."""
from skills.common.deliverable_schema import (  # noqa: F401
    SECTION, CriterionResult, Decision, DecisionJson, load_decision, normalize_section, validate_decision_text)
