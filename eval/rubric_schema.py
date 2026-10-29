"""rubric.json schema (HOST-ONLY). 8-15 binary criteria per case, each with a reference the grader verifies against."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Family = Literal["decision", "identifiers", "denial_reason", "deadline", "policy_citation", "evidence_use",
                 "honesty_about_gaps", "remedy_and_enclosures"]


class RubricCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    family: Family
    check: Literal["auto", "judge"]
    text: str
    reference: str
    auto: dict | None = None          # machine-checkable spec for check == "auto"
    sources: list[str] = []           # agent-visible files the grader should look at (judge criteria)


class Rubric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    decision: str
    criteria: list[RubricCriterion] = Field(min_length=1)
    partial: bool = False             # True when criteria were skipped because documents are not rendered yet
    skipped: list[str] = []
