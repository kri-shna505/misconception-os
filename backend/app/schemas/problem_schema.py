from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProblemListItem(BaseModel):
    id: UUID
    code: str = Field(..., min_length=1, max_length=30)
    title: str = Field(..., min_length=1, max_length=255)
    topic: str = Field(..., min_length=1, max_length=100)
    difficulty: str | None = Field(default=None, max_length=50)
    expected_language: str | None = Field(default=None, max_length=50)
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportedMisconception(BaseModel):
    id: UUID
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    topic: str | None = Field(default=None, max_length=100)
    active: bool = True

    model_config = ConfigDict(from_attributes=True)


class ProblemDetail(BaseModel):
    id: UUID
    code: str = Field(..., min_length=1, max_length=30)
    title: str = Field(..., min_length=1, max_length=255)
    topic: str = Field(..., min_length=1, max_length=100)
    statement: str = Field(..., min_length=1)
    difficulty: str | None = Field(default=None, max_length=50)
    expected_language: str | None = Field(default=None, max_length=50)
    rule_context: dict[str, Any] | None = None
    active: bool
    supported_misconceptions: list[SupportedMisconception] = Field(
        default_factory=list
    )
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)