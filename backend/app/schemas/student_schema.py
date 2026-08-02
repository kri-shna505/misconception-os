from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class StudentSessionCreate(BaseModel):
    alias: str = Field(
        ...,
        min_length=3,
        max_length=80,
        description="Student-facing alias used for the pseudonymous session.",
    )

    consent_status: bool = Field(
        ...,
        description="Indicates whether the student consented to data collection.",
    )

    @field_validator("alias")
    @classmethod
    def normalize_alias(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())

        if len(normalized) < 3:
            raise ValueError(
                "Alias must contain at least 3 non-whitespace characters."
            )

        return normalized


class StudentSessionResponse(BaseModel):
    student_alias_id: UUID
    alias: str
    pseudonymous_id: str = Field(
        ...,
        min_length=1,
        max_length=40,
    )
    consent_status: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentAliasSummary(BaseModel):
    """
    Lightweight student representation for teacher-facing lists,
    filters, and attempt-history responses.
    """

    id: UUID
    alias: str
    pseudonymous_id: str
    consent_status: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)