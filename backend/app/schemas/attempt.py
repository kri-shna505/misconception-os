from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


SPEECH_PROCESSING_STATUSES = {
    "not_provided",
    "pending",
    "processing",
    "completed",
    "failed",
}

INPUT_MODALITIES = {
    "text",
    "code",
    "speech",
    "text_code",
    "text_speech",
    "code_speech",
    "text_code_speech",
}


class AttemptCreate(BaseModel):
    """
    Payload used to create a student attempt.

    Sprint 10 extends the attempt contract with natural-language,
    multimodal, normalized-reasoning, and privacy-aware speech metadata.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=False,
    )

    student_alias_id: UUID = Field(
        ...,
        description="Pseudonymous student session identifier.",
    )

    problem_id: UUID = Field(
        ...,
        description="Identifier of the problem being attempted.",
    )

    final_answer: str | None = Field(
        default=None,
        max_length=4000,
        description="Student's final answer, when provided.",
    )

    written_reasoning: str = Field(
        ...,
        min_length=5,
        max_length=6000,
        description="Student's written explanation of the chosen approach.",
    )

    normalized_reasoning: str | None = Field(
        default=None,
        max_length=6000,
        description=(
            "Optional normalized reasoning used internally for diagnosis. "
            "When omitted, backend processing may derive it from the "
            "student's submitted reasoning or speech transcript."
        ),
    )

    source_code: str | None = Field(
        default=None,
        max_length=12000,
        description="Optional source code submitted with the attempt.",
    )

    speech_transcript: str | None = Field(
        default=None,
        max_length=6000,
        description="Optional transcript captured from a spoken explanation.",
    )

    speech_audio_reference: str | None = Field(
        default=None,
        max_length=2000,
        description=(
            "Optional opaque reference to retained speech audio. Raw audio "
            "content must not be embedded directly in this field."
        ),
    )

    speech_audio_retained: bool = Field(
        default=False,
        description=(
            "Whether speech audio is intentionally retained after processing."
        ),
    )

    speech_processing_status: str = Field(
        default="not_provided",
        min_length=1,
        max_length=30,
        description=(
            "Speech-processing state: not_provided, pending, processing, "
            "completed, or failed."
        ),
    )

    input_modality: str = Field(
        default="text",
        min_length=1,
        max_length=30,
        description=(
            "Input modality: text, code, speech, text_code, text_speech, "
            "code_speech, or text_code_speech."
        ),
    )

    input_language: str = Field(
        default="english",
        min_length=1,
        max_length=30,
        description="Natural language selected for the student's explanation.",
    )

    detected_language: str | None = Field(
        default=None,
        max_length=30,
        description=(
            "Optional language detected by backend language processing."
        ),
    )

    selected_language: str = Field(
        default="python",
        min_length=1,
        max_length=30,
        description="Programming language selected for the attempt.",
    )

    response_time_seconds: int | None = Field(
        default=None,
        ge=0,
        le=7200,
        description="Time spent on the attempt, measured in seconds.",
    )

    @field_validator(
        "final_answer",
        "normalized_reasoning",
        "source_code",
        "speech_transcript",
        "speech_audio_reference",
        "detected_language",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: object,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError("Text fields must contain strings.")

        normalized = value.strip()
        return normalized or None

    @field_validator(
        "written_reasoning",
        mode="before",
    )
    @classmethod
    def normalize_written_reasoning(
        cls,
        value: object,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError("Written reasoning must be a string.")

        normalized = value.strip()

        if not normalized:
            raise ValueError("Written reasoning is required.")

        return normalized

    @field_validator(
        "selected_language",
        mode="before",
    )
    @classmethod
    def normalize_selected_language(
        cls,
        value: object,
    ) -> str:
        if value is None:
            return "python"

        if not isinstance(value, str):
            raise TypeError("Selected language must be a string.")

        normalized = value.strip().lower()

        language_aliases = {
            "py": "python",
            "python3": "python",
            "c language": "c",
            "text / no code": "text",
            "text/no code": "text",
            "no code": "text",
        }

        normalized = language_aliases.get(
            normalized,
            normalized,
        )

        return normalized or "python"

    @field_validator(
        "input_language",
        "detected_language",
        mode="before",
    )
    @classmethod
    def normalize_natural_language(
        cls,
        value: object,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError("Natural-language fields must contain strings.")

        normalized = value.strip().lower()

        language_aliases = {
            "en": "english",
            "eng": "english",
            "te": "telugu",
            "tel": "telugu",
            "hi": "hindi",
            "hin": "hindi",
        }

        normalized = language_aliases.get(
            normalized,
            normalized,
        )

        return normalized or None

    @field_validator(
        "speech_processing_status",
        mode="before",
    )
    @classmethod
    def normalize_speech_processing_status(
        cls,
        value: object,
    ) -> str:
        if value is None:
            return "not_provided"

        if not isinstance(value, str):
            raise TypeError("Speech processing status must be a string.")

        normalized = value.strip().lower()

        if normalized not in SPEECH_PROCESSING_STATUSES:
            raise ValueError(
                "Invalid speech processing status. Expected one of: "
                + ", ".join(sorted(SPEECH_PROCESSING_STATUSES))
                + "."
            )

        return normalized

    @field_validator(
        "input_modality",
        mode="before",
    )
    @classmethod
    def normalize_input_modality(
        cls,
        value: object,
    ) -> str:
        if value is None:
            return "text"

        if not isinstance(value, str):
            raise TypeError("Input modality must be a string.")

        normalized = value.strip().lower().replace("-", "_")

        modality_aliases = {
            "text+code": "text_code",
            "text+speech": "text_speech",
            "code+speech": "code_speech",
            "text+code+speech": "text_code_speech",
        }

        normalized = modality_aliases.get(
            normalized,
            normalized,
        )

        if normalized not in INPUT_MODALITIES:
            raise ValueError(
                "Invalid input modality. Expected one of: "
                + ", ".join(sorted(INPUT_MODALITIES))
                + "."
            )

        return normalized

    @model_validator(mode="after")
    def validate_attempt_content(self) -> "AttemptCreate":
        if (
            self.final_answer is None
            and self.source_code is None
            and self.speech_transcript is None
        ):
            raise ValueError(
                "Attempt must include a final answer, source code, or speech "
                "transcript in addition to written reasoning."
            )

        if self.speech_audio_retained and self.speech_audio_reference is None:
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
                "input_modality must include speech when speech input "
                "metadata is provided."
            )

        if (
            not speech_present
            and self.speech_processing_status
            in {"pending", "processing", "completed"}
        ):
            raise ValueError(
                "Active or completed speech processing requires speech input."
            )

        return self


class AttemptResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    id: UUID
    student_alias_id: UUID
    problem_id: UUID

    parent_attempt_id: UUID | None = None
    retry_number: int = 0

    final_answer: str | None = None
    written_reasoning: str
    normalized_reasoning: str | None = None
    source_code: str | None = None
    speech_transcript: str | None = None

    speech_audio_reference: str | None = None
    speech_audio_retained: bool = False
    speech_processing_status: str = "not_provided"

    input_modality: str = "text"
    input_language: str = "english"
    detected_language: str | None = None

    selected_language: str
    response_time_seconds: int | None = None

    created_at: datetime
    updated_at: datetime


class AttemptSummary(BaseModel):
    """
    Lightweight attempt representation for teacher-facing lists,
    filters, pagination, and student-history responses.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    id: UUID
    student_alias_id: UUID
    problem_id: UUID

    parent_attempt_id: UUID | None = None
    retry_number: int = 0

    selected_language: str
    input_language: str = "english"
    detected_language: str | None = None
    input_modality: str = "text"
    speech_processing_status: str = "not_provided"

    response_time_seconds: int | None = None
    created_at: datetime
    updated_at: datetime