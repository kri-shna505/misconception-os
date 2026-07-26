from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ProblemListItem(BaseModel):
    id: UUID
    code: str
    title: str
    topic: str
    difficulty: str | None = None
    active: bool

    class Config:
        from_attributes = True


class SupportedMisconception(BaseModel):
    id: UUID
    code: str
    name: str
    topic: str | None = None


class ProblemDetail(BaseModel):
    id: UUID
    code: str
    title: str
    topic: str
    statement: str
    difficulty: str | None = None
    expected_language: str | None = None
    rule_context: dict[str, Any] | None = None
    supported_misconceptions: list[SupportedMisconception]
    created_at: datetime

    class Config:
        from_attributes = True