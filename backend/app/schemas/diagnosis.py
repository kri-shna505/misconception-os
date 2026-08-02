from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class DiagnosisState(str, Enum):
    CONFIDENT = "confident"
    POSSIBLE = "possible"
    INSUFFICIENT = "insufficient"
    NO_MISCONCEPTION = "no_misconception"


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
    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    id: UUID
    code: str = Field(
        ...,
        min_length=1,
        max_length=30,
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )
    topic: str | None = Field(
        default=None,
        max_length=100,
    )


class DiagnosisEvidenceCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    source: EvidenceSource
    strength: EvidenceStrength
    text: str = Field(
        ...,
        min_length=3,
        max_length=1000,
    )
    sort_order: int = Field(
        default=0,
        ge=0,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class DiagnosisEvidenceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    id: UUID | None = None
    diagnosis_id: UUID | None = None
    source: EvidenceSource
    strength: EvidenceStrength
    text: str = Field(
        ...,
        min_length=3,
        max_length=1000,
    )
    sort_order: int = Field(
        default=0,
        ge=0,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class DiagnosisAlternativeCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    misconception_id: UUID
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
    )
    reason: str | None = Field(
        default=None,
        max_length=500,
    )


class DiagnosisAlternativeResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    id: UUID | None = None
    diagnosis_id: UUID | None = None
    misconception: MisconceptionSummary
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
    )
    reason: str | None = Field(
        default=None,
        max_length=500,
    )


class DiagnosisCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    attempt_id: UUID
    state: DiagnosisState

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
    )

    primary_misconception_id: UUID | None = None

    model_version: str = Field(
        default="rule-v1.3",
        min_length=1,
        max_length=80,
    )

    decision_reason: str | None = Field(
        default=None,
        max_length=1000,
    )

    next_action: DiagnosisNextAction = DiagnosisNextAction.NO_ACTION

    evidence: list[DiagnosisEvidenceCreate] = Field(
        default_factory=list,
    )

    alternatives: list[DiagnosisAlternativeCreate] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_diagnosis_consistency(self) -> "DiagnosisCreate":
        _validate_diagnosis_state(
            state=self.state,
            confidence=self.confidence,
            misconception_present=(
                self.primary_misconception_id is not None
            ),
            next_action=self.next_action,
            has_alternatives=bool(self.alternatives),
            context="diagnosis",
        )

        return self


class DiagnosisResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    id: UUID
    attempt_id: UUID
    state: DiagnosisState

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
    )

    primary_misconception: MisconceptionSummary | None = None

    evidence: list[DiagnosisEvidenceResponse] = Field(
        default_factory=list,
    )

    alternatives: list[DiagnosisAlternativeResponse] = Field(
        default_factory=list,
    )

    model_version: str = Field(
        ...,
        min_length=1,
        max_length=80,
    )

    decision_reason: str | None = Field(
        default=None,
        max_length=1000,
    )

    next_action: DiagnosisNextAction
    created_at: datetime


class DiagnosisSummary(BaseModel):
    """
    Lightweight diagnosis representation for Sprint 5 teacher-facing
    tables, filters, pagination, and analytics responses.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    id: UUID
    attempt_id: UUID
    state: DiagnosisState

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
    )

    primary_misconception_id: UUID | None = None

    model_version: str = Field(
        ...,
        min_length=1,
        max_length=80,
    )

    next_action: DiagnosisNextAction
    created_at: datetime


class RuleEvidence(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    source: EvidenceSource
    strength: EvidenceStrength

    text: str = Field(
        ...,
        min_length=3,
        max_length=1000,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class RuleDetectionResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    state: DiagnosisState

    misconception_code: str | None = Field(
        default=None,
        max_length=30,
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
    )

    evidence: list[RuleEvidence] = Field(
        default_factory=list,
    )

    alternative_misconception_codes: list[str] = Field(
        default_factory=list,
    )

    decision_reason: str | None = Field(
        default=None,
        max_length=1000,
    )

    next_action: DiagnosisNextAction = DiagnosisNextAction.NO_ACTION

    @model_validator(mode="after")
    def validate_rule_result(self) -> "RuleDetectionResult":
        _validate_diagnosis_state(
            state=self.state,
            confidence=self.confidence,
            misconception_present=bool(self.misconception_code),
            next_action=self.next_action,
            has_alternatives=bool(
                self.alternative_misconception_codes
            ),
            context="rule result",
        )

        return self


def _validate_diagnosis_state(
    *,
    state: DiagnosisState,
    confidence: float,
    misconception_present: bool,
    next_action: DiagnosisNextAction,
    has_alternatives: bool,
    context: str,
) -> None:
    if state in {
        DiagnosisState.CONFIDENT,
        DiagnosisState.POSSIBLE,
    } and not misconception_present:
        raise ValueError(
            f"A misconception is required for a {state.value} {context}."
        )

    if state in {
        DiagnosisState.INSUFFICIENT,
        DiagnosisState.NO_MISCONCEPTION,
    } and misconception_present:
        raise ValueError(
            f"A misconception must not be set for a "
            f"{state.value} {context}."
        )

    if (
        state == DiagnosisState.CONFIDENT
        and confidence < 0.75
    ):
        raise ValueError(
            f"A confident {context} requires confidence >= 0.75."
        )

    if (
        state == DiagnosisState.POSSIBLE
        and not 0.45 <= confidence < 0.75
    ):
        raise ValueError(
            f"A possible {context} requires confidence between "
            f"0.45 and 0.74."
        )

    if state == DiagnosisState.INSUFFICIENT:
        if confidence >= 0.45:
            raise ValueError(
                f"An insufficient {context} requires confidence < 0.45."
            )

        if next_action == DiagnosisNextAction.NO_ACTION:
            raise ValueError(
                f"An insufficient {context} must request clarification "
                f"or a diagnostic question."
            )

    if state == DiagnosisState.NO_MISCONCEPTION:
        if confidence < 0.75:
            raise ValueError(
                f"A no-misconception {context} requires "
                f"confidence >= 0.75."
            )

        if next_action != DiagnosisNextAction.NO_ACTION:
            raise ValueError(
                f"A no-misconception {context} requires "
                f"next_action=no_action."
            )

        if has_alternatives:
            raise ValueError(
                f"A no-misconception {context} must not contain "
                f"alternatives."
            )