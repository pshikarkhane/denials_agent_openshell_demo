"""truth.json schema (DEMO_SPEC section 3.3). HOST-ONLY: never mounted into the sandbox."""
from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Decision(str, Enum):
    APPEAL = "APPEAL"
    CORRECT_AND_RESUBMIT = "CORRECT_AND_RESUBMIT"
    DO_NOT_APPEAL = "DO_NOT_APPEAL"
    ESCALATE_MISSING_DOCS = "ESCALATE_MISSING_DOCS"


class Trap(str, Enum):
    DEADLINE_WITHIN_7_DAYS = "deadline_within_7_days"
    DEADLINE_PASSED = "deadline_passed"
    NOTE_AFTER_DOS = "note_after_dos"
    NOTES_DISAGREE_THERAPY_DURATION = "notes_disagree_therapy_duration"
    CRITERION_NO_SUPPORTING_DOC = "criterion_no_supporting_doc"
    POLICY_EFFECTIVE_AFTER_DOS = "policy_effective_after_dos"
    DISTRACTOR_POLICY_SIMILAR_NAME = "distractor_policy_similar_name"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Patient(_Strict):
    synthetic_id: str = Field(pattern=r"^P-\d{4}$")


class Claim(_Strict):
    claim_no: str = Field(pattern=r"^\d{7}$")
    cpt: str = Field(pattern=r"^\d{5}$")
    icd10: list[str] = Field(min_length=1)
    dos: date
    billed: float = Field(gt=0)


class Denial(_Strict):
    carc: str = Field(pattern=r"^(CO|PR)-\d+$")
    rarc: str | None = None
    denial_date: date


class PolicyCriterion(_Strict):
    id: str
    section: str
    text: str
    status: Literal["met", "unmet", "unknown"]  # same vocabulary as decision.json criteria[].status
    evidence: list[str]


class Fact(_Strict):
    """A verifiable fact the deliverable may legitimately state. `line` is filled in when documents are rendered."""
    key: str
    value: str | int | float | bool | list[str]
    source_file: str
    line: int | None = None
    evidence: str | None = None  # verbatim quote that must appear in source_file; `line` points at it


class Truth(_Strict):
    case_id: str = Field(pattern=r"^C-\d{4}$")
    category: int = Field(ge=1, le=12)
    split: Literal["dev", "test"]
    payer_id: str
    policy_id: str
    patient: Patient
    claim: Claim
    denial: Denial
    appeal_deadline: date
    policy_criteria: list[PolicyCriterion] = Field(min_length=1)
    correct_decision: Decision
    traps: list[Trap] = Field(max_length=2)
    required_enclosures: list[str]
    facts: list[Fact] = Field(min_length=1)
