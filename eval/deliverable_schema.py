"""Schema of the agent's two outputs (DEMO_SPEC 4.2): deliverable.md (free text) and decision.json (this model).

Criterion ids in decision.json are POLICY SECTION strings (e.g. "2.1(a)"); the agent cannot see the internal C1/C2 ids.
"""
import json
import re
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

Decision = Literal["APPEAL", "CORRECT_AND_RESUBMIT", "DO_NOT_APPEAL", "ESCALATE_MISSING_DOCS"]
SECTION = re.compile(r"^\d+(\.\d+)*(\([a-z]\))?$")


def normalize_section(s):
    """'§2.1(a)', 'Section 2.1(a)', ' 2.1(a) ' -> '2.1(a)'."""
    return re.sub(r"^(?:§|Section\s*)", "", str(s).strip(), flags=re.I).strip()


class CriterionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    status: Literal["met", "unmet", "unknown"]
    evidence: str | None = None

    @field_validator("id")
    @classmethod
    def _section(cls, v):
        v = normalize_section(v)
        if not SECTION.match(v):
            raise ValueError(f"criterion id must be a policy section string like '2.1(a)', got {v!r}")
        return v


class DecisionJson(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(pattern=r"^C-\d{4}$")
    decision: Decision
    denial_code: str = Field(pattern=r"^(CO|PR)-?\d+$")
    policy_id: str = Field(pattern=r"^MP-[A-Z]+-\d{3}$")
    action_deadline: date
    deadline_ok: bool
    criteria: list[CriterionResult] = Field(min_length=1)
    enclosures: list[str]
    gaps: list[str]

    @field_validator("criteria")
    @classmethod
    def _unique(cls, v):
        ids = [c.id for c in v]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate criterion ids")
        return v


def validate_decision_text(text, expect_case_id=None):
    """Returns (DecisionJson | None, [error strings])."""
    try:
        data = json.loads(text)
    except ValueError as e:
        return None, [f"not valid JSON: {e}"]
    try:
        d = DecisionJson.model_validate(data)
    except ValidationError as e:
        return None, [f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()]
    if expect_case_id and d.case_id != expect_case_id:
        return None, [f"case_id {d.case_id} != expected {expect_case_id}"]
    return d, []


def load_decision(path, expect_case_id=None):
    p = Path(path)
    if not p.exists():
        return None, [f"{p} does not exist"]
    return validate_decision_text(p.read_text(), expect_case_id)
