from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class AttemptCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=False,
    )

    student_alias_id: UUID
    problem_id: UUID

    final_answer: Optional[str] = Field(
        default=None,
        max_length=4000,
    )

    written_reasoning: str = Field(
        min_length=5,
        max_length=6000,
    )

    source_code: Optional[str] = Field(
        default=None,
        max_length=12000,
    )

    speech_transcript: Optional[str] = Field(
        default=None,
        max_length=6000,
    )

    selected_language: str = Field(
        default="python",
        min_length=1,
        max_length=30,
    )

    response_time_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        le=7200,
    )

    @field_validator(
        "final_answer",
        "source_code",
        "speech_transcript",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: object,
    ) -> Optional[str]:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError("Text fields must contain strings.")

        normalized = value.strip()

        if not normalized:
            return None

        return normalized

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

        if not normalized:
            return "python"

        return normalized

    @model_validator(mode="after")
    def validate_attempt_content(self) -> AttemptCreate:
        if (
            self.final_answer is None
            and self.source_code is None
            and self.speech_transcript is None
        ):
            raise ValueError(
                "Attempt must include a final answer, source code, or speech "
                "transcript in addition to written reasoning."
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

    final_answer: Optional[str] = None
    written_reasoning: str
    source_code: Optional[str] = None
    speech_transcript: Optional[str] = None
    selected_language: str
    response_time_seconds: Optional[int] = None
    created_at: datetime