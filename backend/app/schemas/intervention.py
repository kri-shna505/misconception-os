from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.schemas.diagnosis import (
    DiagnosisResponse,
    DiagnosisState,
)


class MisconceptionEvolutionState(str, Enum):
    NEWLY_DETECTED = "newly_detected"
    REPEATED = "repeated"
    IMPROVING = "improving"
    CORRECTED = "corrected"
    REPLACED = "replaced"
    UNCERTAIN = "uncertain"


class HintTemplateSummary(BaseModel):
    """
    Public representation of one approved hint template.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    id: UUID
    misconception_id: UUID

    level: int = Field(
        ...,
        ge=1,
        le=3,
    )

    hint_text: str = Field(
        ...,
        min_length=10,
        max_length=2000,
    )

    active: bool


class HintProgressResponse(BaseModel):
    """
    Current progressive-hint status for one diagnosis.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )

    diagnosis_id: UUID
    attempt_id: UUID
    student_alias_id: UUID
    misconception_id: UUID

    revealed_levels: list[int] = Field(
        default_factory=list,
    )

    next_level: int | None = Field(
        default=None,
        ge=1,
        le=3,
    )

    maximum_level: int = Field(
        default=3,
        ge=1,
        le=3,
    )

    completed: bool

    @model_validator(mode="after")
    def validate_hint_progress(
        self,
    ) -> "HintProgressResponse":
        normalized_levels = sorted(
            set(self.revealed_levels)
        )

        if any(
            level < 1 or level > self.maximum_level
            for level in normalized_levels
        ):
            raise ValueError(
                "Revealed hint levels must be within the configured range."
            )

        expected_prefix = list(
            range(
                1,
                len(normalized_levels) + 1,
            )
        )

        if normalized_levels != expected_prefix:
            raise ValueError(
                "Revealed hint levels must form a sequential progression."
            )

        if self.completed and self.next_level is not None:
            raise ValueError(
                "Completed hint progress must not contain a next level."
            )

        if (
            not self.completed
            and self.next_level is None
        ):
            raise ValueError(
                "Incomplete hint progress requires a next level."
            )

        return self


class HintDeliveryResponse(BaseModel):
    """
    Response returned when the next progressive hint is revealed.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )

    hint_event_id: UUID
    diagnosis_id: UUID
    attempt_id: UUID
    student_alias_id: UUID

    hint_template_id: UUID
    misconception_id: UUID

    level: int = Field(
        ...,
        ge=1,
        le=3,
    )

    hint_text: str = Field(
        ...,
        min_length=10,
        max_length=2000,
    )

    is_final_level: bool

    remaining_levels: int = Field(
        ...,
        ge=0,
        le=2,
    )

    created_at: datetime

    @model_validator(mode="after")
    def validate_hint_delivery(
        self,
    ) -> "HintDeliveryResponse":
        expected_remaining_levels = max(
            0,
            3 - self.level,
        )

        if (
            self.remaining_levels
            != expected_remaining_levels
        ):
            raise ValueError(
                "remaining_levels does not match the delivered hint level."
            )

        if (
            self.is_final_level
            != (self.level == 3)
        ):
            raise ValueError(
                "is_final_level must be true only for level 3."
            )

        return self


class RevealedHintListResponse(BaseModel):
    """
    Previously revealed hints for one diagnosis.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    diagnosis_id: UUID

    items: list[HintDeliveryResponse] = Field(
        default_factory=list,
    )

    total_items: int = Field(
        default=0,
        ge=0,
    )

    @model_validator(mode="after")
    def validate_total_items(
        self,
    ) -> "RevealedHintListResponse":
        if self.total_items != len(self.items):
            raise ValueError(
                "total_items must match the number of hint items."
            )

        return self


class DiagnosticQuestionResponse(BaseModel):
    """
    One approved diagnostic question selected for a diagnosis.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )

    id: UUID
    diagnosis_id: UUID
    attempt_id: UUID
    student_alias_id: UUID

    misconception_id: UUID

    competing_misconception_id: UUID | None = None

    question_text: str = Field(
        ...,
        min_length=10,
        max_length=2000,
    )

    created_at: datetime


class DiagnosticResponseCreate(BaseModel):
    """
    Student answer submitted for a diagnostic question.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    response_text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
    )

    @model_validator(mode="after")
    def validate_response_text(
        self,
    ) -> "DiagnosticResponseCreate":
        normalized_text = (
            self.response_text.strip()
        )

        if not normalized_text:
            raise ValueError(
                "Diagnostic response must not be blank."
            )

        self.response_text = normalized_text

        return self


class DiagnosticResponseResult(BaseModel):
    """
    Persisted answer to one diagnostic question.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )

    id: UUID
    student_alias_id: UUID
    attempt_id: UUID
    diagnosis_id: UUID
    diagnostic_question_id: UUID

    resulting_diagnosis_id: UUID | None = None

    response_text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
    )

    evaluated: bool
    evaluated_at: datetime | None = None

    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_evaluation_state(
        self,
    ) -> "DiagnosticResponseResult":
        if (
            self.evaluated
            and self.evaluated_at is None
        ):
            raise ValueError(
                "An evaluated response requires evaluated_at."
            )

        if (
            not self.evaluated
            and self.evaluated_at is not None
        ):
            raise ValueError(
                "A pending response must not contain evaluated_at."
            )

        if (
            not self.evaluated
            and self.resulting_diagnosis_id is not None
        ):
            raise ValueError(
                "A pending response must not reference a resulting diagnosis."
            )

        return self


class DiagnosticReevaluationResponse(BaseModel):
    """
    Result returned after a diagnostic response is evaluated.

    The original diagnosis remains immutable. Re-evaluation creates a new
    diagnosis snapshot and links it back through the diagnostic response.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    diagnostic_response: DiagnosticResponseResult

    original_diagnosis_id: UUID

    resulting_diagnosis_id: UUID | None = None

    previous_state: DiagnosisState

    resulting_state: DiagnosisState | None = None

    resulting_diagnosis: DiagnosisResponse | None = None

    reevaluated: bool

    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
    )

    @model_validator(mode="after")
    def validate_reevaluation_result(
        self,
    ) -> "DiagnosticReevaluationResponse":
        if self.reevaluated:
            if self.resulting_diagnosis_id is None:
                raise ValueError(
                    "A completed re-evaluation requires a resulting diagnosis ID."
                )

            if self.resulting_state is None:
                raise ValueError(
                    "A completed re-evaluation requires a resulting state."
                )

            if self.resulting_diagnosis is None:
                raise ValueError(
                    "A completed re-evaluation requires the resulting diagnosis."
                )

            if (
                self.resulting_diagnosis.id
                != self.resulting_diagnosis_id
            ):
                raise ValueError(
                    "resulting_diagnosis_id must match resulting_diagnosis.id."
                )

            if (
                self.resulting_diagnosis.state
                != self.resulting_state
            ):
                raise ValueError(
                    "resulting_state must match resulting_diagnosis.state."
                )

            if (
                self.diagnostic_response.resulting_diagnosis_id
                != self.resulting_diagnosis_id
            ):
                raise ValueError(
                    "The diagnostic response must link to the resulting diagnosis."
                )

        else:
            if self.resulting_diagnosis_id is not None:
                raise ValueError(
                    "A non-reevaluated result must not contain a resulting diagnosis ID."
                )

            if self.resulting_state is not None:
                raise ValueError(
                    "A non-reevaluated result must not contain a resulting state."
                )

            if self.resulting_diagnosis is not None:
                raise ValueError(
                    "A non-reevaluated result must not contain a resulting diagnosis."
                )

        return self


class RetryAttemptCreate(BaseModel):
    """
    Student submission used to create a retry attempt.

    The parent attempt is normally supplied through the route path.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    final_answer: str | None = Field(
        default=None,
        max_length=10000,
    )

    written_reasoning: str = Field(
        ...,
        min_length=1,
        max_length=20000,
    )

    source_code: str | None = Field(
        default=None,
        max_length=50000,
    )

    speech_transcript: str | None = Field(
        default=None,
        max_length=20000,
    )

    selected_language: str = Field(
        default="python",
        min_length=1,
        max_length=30,
    )

    response_time_seconds: int | None = Field(
        default=None,
        ge=0,
    )

    @model_validator(mode="after")
    def normalize_retry_submission(
        self,
    ) -> "RetryAttemptCreate":
        self.written_reasoning = (
            self.written_reasoning.strip()
        )

        self.selected_language = (
            self.selected_language.strip().lower()
        )

        if not self.written_reasoning:
            raise ValueError(
                "written_reasoning must not be blank."
            )

        if not self.selected_language:
            raise ValueError(
                "selected_language must not be blank."
            )

        if self.final_answer is not None:
            normalized_final_answer = (
                self.final_answer.strip()
            )

            self.final_answer = (
                normalized_final_answer
                or None
            )

        if self.source_code is not None:
            normalized_source_code = (
                self.source_code.strip()
            )

            self.source_code = (
                normalized_source_code
                or None
            )

        if (
            self.speech_transcript
            is not None
        ):
            normalized_transcript = (
                self.speech_transcript.strip()
            )

            self.speech_transcript = (
                normalized_transcript
                or None
            )

        return self


class RetryAttemptResponse(BaseModel):
    """
    Retry attempt created from an existing student attempt.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )

    id: UUID
    student_alias_id: UUID
    problem_id: UUID

    parent_attempt_id: UUID

    retry_number: int = Field(
        ...,
        ge=1,
    )

    selected_language: str = Field(
        ...,
        min_length=1,
        max_length=30,
    )

    response_time_seconds: int | None = Field(
            default=None,
            ge=0,
        )

    created_at: datetime


class MisconceptionEvolutionResponse(BaseModel):
    """
    Conceptual transition calculated between related attempts.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )

    id: UUID

    student_alias_id: UUID
    problem_id: UUID

    attempt_id: UUID
    diagnosis_id: UUID

    previous_attempt_id: UUID | None = None

    previous_diagnosis_id: UUID | None = None

    previous_misconception_id: UUID | None = None

    current_misconception_id: UUID | None = None

    previous_diagnosis_state: DiagnosisState | None = None

    current_diagnosis_state: DiagnosisState

    evolution_state: MisconceptionEvolutionState

    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_previous_context(
        self,
    ) -> "MisconceptionEvolutionResponse":
        has_previous_attempt = (
            self.previous_attempt_id
            is not None
        )

        has_previous_diagnosis = (
            self.previous_diagnosis_id
            is not None
        )

        if (
            has_previous_attempt
            != has_previous_diagnosis
        ):
            raise ValueError(
                "Previous attempt and diagnosis references must appear together."
            )

        if (
            self.evolution_state
            == MisconceptionEvolutionState.NEWLY_DETECTED
            and has_previous_attempt
        ):
            raise ValueError(
                "A newly detected evolution must not reference a previous attempt."
            )

        return self


class LearningHistoryItem(BaseModel):
    """
    One attempt in a student's intervention and retry timeline.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    attempt_id: UUID
    problem_id: UUID

    parent_attempt_id: UUID | None = None

    retry_number: int = Field(
        default=0,
        ge=0,
    )

    diagnosis_id: UUID | None = None

    diagnosis_state: DiagnosisState | None = None

    misconception_id: UUID | None = None

    confidence: float | None = Field(
            default=None,
            ge=0.0,
            le=1.0,
        )

    hint_levels_used: list[int] = Field(
            default_factory=list,
        )

    diagnostic_question_answered: bool = False

    evolution_state: MisconceptionEvolutionState | None = None

    created_at: datetime


class LearningHistoryResponse(BaseModel):
    """
    Student learning timeline for one problem or across all problems.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    student_alias_id: UUID

    problem_id: UUID | None = None

    items: list[LearningHistoryItem] = Field(
        default_factory=list,
    )

    total_items: int = Field(
        default=0,
        ge=0,
    )

    @model_validator(mode="after")
    def validate_history_total(
        self,
    ) -> "LearningHistoryResponse":
        if self.total_items != len(
            self.items
        ):
            raise ValueError(
                "total_items must match the number of history items."
            )

        return self


__all__ = [
    "DiagnosticQuestionResponse",
    "DiagnosticReevaluationResponse",
    "DiagnosticResponseCreate",
    "DiagnosticResponseResult",
    "HintDeliveryResponse",
    "HintProgressResponse",
    "HintTemplateSummary",
    "LearningHistoryItem",
    "LearningHistoryResponse",
    "MisconceptionEvolutionResponse",
    "MisconceptionEvolutionState",
    "RetryAttemptCreate",
    "RetryAttemptResponse",
    "RevealedHintListResponse",
]