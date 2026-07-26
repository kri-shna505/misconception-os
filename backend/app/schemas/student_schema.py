from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class StudentSessionCreate(BaseModel):
    alias: str = Field(..., min_length=3, max_length=80)
    consent_status: bool


class StudentSessionResponse(BaseModel):
    student_alias_id: UUID
    alias: str
    pseudonymous_id: str
    consent_status: bool
    created_at: datetime

    class Config:
        from_attributes = True