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

    Sprint 10 extends retries with normalized reasoning, language metadata,
    speech-processing state, and privacy-aware audio references so retries use
    the same multimodal diagnosis contract as original attempts.
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

    normalized_reasoning: str | None = Field(
        default=None,
        max_length=20000,
        description=(
            "Optional normalized reasoning used by the Sprint 10 "
            "diagnosis pipeline."
        ),
    )

    speech_transcript: str | None = Field(
        default=None,
        max_length=20000,
    )

    speech_audio_reference: str | None = Field(
        default=None,
        max_length=2000,
        description=(
            "Optional opaque reference to temporarily retained speech audio."
        ),
    )

    speech_audio_retained: bool = Field(
        default=False,
        description=(
            "Whether raw speech audio is retained with explicit consent."
        ),
    )

    speech_processing_status: str = Field(
        default="not_provided",
        min_length=1,
        max_length=30,
    )

    input_modality: str = Field(
        default="text",
        min_length=1,
        max_length=30,
    )

    input_language: str = Field(
        default="english",
        min_length=1,
        max_length=30,
    )

    detected_language: str | None = Field(
        default=None,
        max_length=30,
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
        self.written_reasoning = self.written_reasoning.strip()

        if not self.written_reasoning:
            raise ValueError(
                "written_reasoning must not be blank."
            )

        programming_language_aliases = {
            "py": "python",
            "python3": "python",
            "python 3": "python",
            "c language": "c",
            "text / no code": "text",
            "text/no code": "text",
            "no code": "text",
        }

        normalized_programming_language = (
            self.selected_language.strip().lower()
        )

        self.selected_language = programming_language_aliases.get(
            normalized_programming_language,
            normalized_programming_language,
        )

        if not self.selected_language:
            raise ValueError(
                "selected_language must not be blank."
            )

        natural_language_aliases = {
            "en": "english",
            "eng": "english",
            "te": "telugu",
            "tel": "telugu",
            "hi": "hindi",
            "hin": "hindi",
        }

        normalized_input_language = (
            self.input_language.strip().lower()
        )

        self.input_language = natural_language_aliases.get(
            normalized_input_language,
            normalized_input_language,
        )

        if not self.input_language:
            raise ValueError(
                "input_language must not be blank."
            )

        if self.detected_language is not None:
            detected_language = self.detected_language.strip().lower()
            self.detected_language = (
                natural_language_aliases.get(
                    detected_language,
                    detected_language,
                )
                or None
            )

        optional_text_fields = (
            "final_answer",
            "normalized_reasoning",
            "source_code",
            "speech_transcript",
            "speech_audio_reference",
        )

        for field_name in optional_text_fields:
            value = getattr(self, field_name)

            if value is None:
                continue

            normalized_value = value.strip()

            setattr(
                self,
                field_name,
                normalized_value or None,
            )

        self.speech_processing_status = (
            self.speech_processing_status.strip().lower()
        )

        valid_speech_statuses = {
            "not_provided",
            "pending",
            "processing",
            "completed",
            "failed",
        }

        if (
            self.speech_processing_status
            not in valid_speech_statuses
        ):
            raise ValueError(
                "speech_processing_status must be one of: "
                "not_provided, pending, processing, completed, failed."
            )

        normalized_modality = (
            self.input_modality.strip().lower().replace("-", "_")
        )

        modality_aliases = {
            "text+code": "text_code",
            "text+speech": "text_speech",
            "code+speech": "code_speech",
            "text+code+speech": "text_code_speech",
        }

        self.input_modality = modality_aliases.get(
            normalized_modality,
            normalized_modality,
        )

        valid_modalities = {
            "text",
            "code",
            "speech",
            "text_code",
            "text_speech",
            "code_speech",
            "text_code_speech",
        }

        if self.input_modality not in valid_modalities:
            raise ValueError(
                "input_modality must be one of: "
                "text, code, speech, text_code, text_speech, "
                "code_speech, text_code_speech."
            )

        if (
            self.speech_audio_retained
            and self.speech_audio_reference is None
        ):
            raise ValueError(
                "speech_audio_reference is required when "
                "speech_audio_retained is true."
            )

        speech_present = (
            self.speech_transcript is not None
            or self.speech_audio_reference is not None
        )

        modality_has_speech = self.input_modality in {
            "speech",
            "text_speech",
            "code_speech",
            "text_code_speech",
        }

        if speech_present and not modality_has_speech:
            raise ValueError(
                "input_modality must include speech when speech "
                "input metadata is provided."
            )

        if (
            not speech_present
            and self.speech_processing_status
            in {
                "pending",
                "processing",
                "completed",
            }
        ):
            raise ValueError(
                "Active or completed speech processing requires "
                "speech input."
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

    normalized_reasoning: str | None = None
    speech_transcript: str | None = None
    speech_audio_reference: str | None = None
    speech_audio_retained: bool = False

    speech_processing_status: str = Field(
        default="not_provided",
        min_length=1,
        max_length=30,
    )

    input_modality: str = Field(
        default="text",
        min_length=1,
        max_length=30,
    )

    input_language: str = Field(
        default="english",
        min_length=1,
        max_length=30,
    )

    detected_language: str | None = Field(
        default=None,
        max_length=30,
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
    updated_at: datetime


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

    input_modality: str = "text"
    input_language: str = "english"
    detected_language: str | None = None
    speech_processing_status: str = "not_provided"
    selected_language: str | None = None

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