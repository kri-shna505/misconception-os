from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AttemptCreate(BaseModel):
    student_alias_id: UUID
    problem_id: UUID

    final_answer: Optional[str] = Field(default=None, max_length=4000)
    written_reasoning: str = Field(min_length=5, max_length=6000)
    source_code: Optional[str] = Field(default=None, max_length=12000)
    speech_transcript: Optional[str] = Field(default=None, max_length=6000)
    selected_language: str = Field(default="python", max_length=20)
    response_time_seconds: Optional[int] = Field(default=None, ge=0, le=7200)

    @model_validator(mode="after")
    def validate_attempt_content(self):
        reasoning = (self.written_reasoning or "").strip()
        final_answer = (self.final_answer or "").strip()
        source_code = (self.source_code or "").strip()
        speech = (self.speech_transcript or "").strip()

        if not reasoning:
            raise ValueError("Written reasoning is required.")

        if not final_answer and not source_code and not speech:
            raise ValueError(
                "Attempt must include final answer, source code, or speech transcript in addition to written reasoning."
            )

        return self


class AttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_alias_id: UUID
    problem_id: UUID

    final_answer: Optional[str]
    written_reasoning: str
    source_code: Optional[str]
    speech_transcript: Optional[str]
    selected_language: str
    response_time_seconds: Optional[int]
    created_at: datetime