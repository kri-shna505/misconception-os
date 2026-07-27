from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DiagnosisState(str, Enum):
    CONFIDENT = "confident"
    POSSIBLE = "possible"
    INSUFFICIENT = "insufficient"


class EvidenceSource(str, Enum):
    PROBLEM = "problem"
    WRITTEN_REASONING = "written_reasoning"
    SOURCE_CODE = "source_code"
    SPEECH_TRANSCRIPT = "speech_transcript"
    RULE_ENGINE = "rule_engine"


class EvidenceStrength(str, Enum):
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"


class DiagnosisNextAction(str, Enum):
    SHOW_HINT = "show_hint"
    ASK_DIAGNOSTIC_QUESTION = "ask_diagnostic_question"
    ASK_CLARIFICATION = "ask_clarification"
    NO_ACTION = "no_action"


class MisconceptionSummary(BaseModel):
    id: UUID
    code: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=1, max_length=255)
    topic: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DiagnosisEvidenceCreate(BaseModel):
    source: EvidenceSource
    strength: EvidenceStrength
    text: str = Field(..., min_length=3, max_length=1000)
    sort_order: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DiagnosisEvidenceResponse(BaseModel):
    id: UUID | None = None
    diagnosis_id: UUID | None = None
    source: EvidenceSource
    strength: EvidenceStrength
    text: str
    sort_order: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class DiagnosisAlternativeCreate(BaseModel):
    misconception_id: UUID
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str | None = Field(default=None, max_length=500)


class DiagnosisAlternativeResponse(BaseModel):
    id: UUID | None = None
    diagnosis_id: UUID | None = None
    misconception: MisconceptionSummary
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DiagnosisCreate(BaseModel):
    attempt_id: UUID
    state: DiagnosisState
    confidence: float = Field(..., ge=0.0, le=1.0)
    primary_misconception_id: UUID | None = None
    model_version: str = Field(default="rule-v1", min_length=1, max_length=80)
    decision_reason: str | None = Field(default=None, max_length=1000)
    next_action: DiagnosisNextAction = DiagnosisNextAction.NO_ACTION
    evidence: list[DiagnosisEvidenceCreate] = Field(default_factory=list)
    alternatives: list[DiagnosisAlternativeCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_diagnosis_consistency(self) -> "DiagnosisCreate":
        if self.state in {
            DiagnosisState.CONFIDENT,
            DiagnosisState.POSSIBLE,
        } and self.primary_misconception_id is None:
            raise ValueError(
                "primary_misconception_id is required for confident or possible diagnosis."
            )

        if self.state == DiagnosisState.CONFIDENT and self.confidence < 0.75:
            raise ValueError("confident diagnosis requires confidence >= 0.75.")

        if self.state == DiagnosisState.POSSIBLE and not (0.45 <= self.confidence < 0.75):
            raise ValueError("possible diagnosis requires confidence between 0.45 and 0.74.")

        if self.state == DiagnosisState.INSUFFICIENT and self.confidence >= 0.45:
            raise ValueError("insufficient diagnosis requires confidence < 0.45.")

        return self


class DiagnosisResponse(BaseModel):
    id: UUID
    attempt_id: UUID
    state: DiagnosisState
    confidence: float = Field(..., ge=0.0, le=1.0)
    primary_misconception: MisconceptionSummary | None = None
    evidence: list[DiagnosisEvidenceResponse] = Field(default_factory=list)
    alternatives: list[DiagnosisAlternativeResponse] = Field(default_factory=list)
    model_version: str
    decision_reason: str | None = None
    next_action: DiagnosisNextAction
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RuleEvidence(BaseModel):
    source: EvidenceSource
    strength: EvidenceStrength
    text: str = Field(..., min_length=3, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuleDetectionResult(BaseModel):
    state: DiagnosisState
    misconception_code: str | None = Field(default=None, max_length=30)
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: list[RuleEvidence] = Field(default_factory=list)
    alternative_misconception_codes: list[str] = Field(default_factory=list)
    decision_reason: str | None = Field(default=None, max_length=1000)
    next_action: DiagnosisNextAction = DiagnosisNextAction.NO_ACTION

    @model_validator(mode="after")
    def validate_rule_result(self) -> "RuleDetectionResult":
        if self.state in {
            DiagnosisState.CONFIDENT,
            DiagnosisState.POSSIBLE,
        } and not self.misconception_code:
            raise ValueError(
                "misconception_code is required for confident or possible rule result."
            )

        if self.state == DiagnosisState.CONFIDENT and self.confidence < 0.75:
            raise ValueError("confident rule result requires confidence >= 0.75.")

        if self.state == DiagnosisState.POSSIBLE and not (0.45 <= self.confidence < 0.75):
            raise ValueError("possible rule result requires confidence between 0.45 and 0.74.")

        if self.state == DiagnosisState.INSUFFICIENT and self.confidence >= 0.45:
            raise ValueError("insufficient rule result requires confidence < 0.45.")

        return self