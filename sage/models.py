"""Pydantic models for Sage."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SageInput(BaseModel):
    """What Sage receives from the pipeline (or from a direct caller)."""

    model_config = ConfigDict(extra="ignore")

    submission_id: str
    insured_name: str
    state: str
    zip_code: str
    sic_code: str
    tiv: float
    credit_score_used: bool = False
    new_business: bool = True

    # Full upstream agent results — pre-populated by the pipeline.
    jura_result: dict = Field(default_factory=dict)
    aria_result: dict | None = None


class CitedPassage(BaseModel):
    passage_id: str
    text: str
    relevance_note: str


class ReasoningOutput(BaseModel):
    submission_id: str
    insured_name: str
    recommendation: Literal["pass", "decline", "refer"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    cited_passages: list[CitedPassage]
    risk_factors: list[str]
    questions_for_uw: list[str]
    grounding_check_passed: bool
    routing_decision: Literal["auto_pass", "auto_decline", "hitl_review"]
    timestamp: str


class AuditEvent(BaseModel):
    event_id: str
    submission_id: str
    event_type: Literal[
        "REASONED",
        "AUTO_PASSED",
        "AUTO_DECLINED",
        "HITL_TRIGGERED",
    ]
    payload: dict
    sha256_hash: str
    timestamp: str
