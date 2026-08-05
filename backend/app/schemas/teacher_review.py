from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


TeacherReviewStatus = Literal[
    "pending",
    "in_review",
    "reviewed",
]

TeacherReviewDecision = Literal[
    "accepted",
    "overridden",
]

TeacherFinalDiagnosisState = Literal[
    "confident",
    "possible",
    "insufficient",
    "no_misconception",
]


class TeacherReviewDraftRequest(BaseModel):
    """
    Save or update a teacher review without finalizing it.
    """

    status: Literal[
        "pending",
        "in_review",
    ] = "in_review"

    decision: TeacherReviewDecision | None = None

    final_state: TeacherFinalDiagnosisState | None = None

    final_misconception_id: uuid.UUID | None = None

    override_reason: str | None = Field(
        default=None,
        max_length=4000,
    )

    teacher_note: str | None = Field(
        default=None,
        max_length=4000,
    )

    @model_validator(mode="after")
    def validate_draft_consistency(
        self,
    ) -> "TeacherReviewDraftRequest":
        if (
            self.decision == "accepted"
            and self.override_reason
        ):
            raise ValueError(
                "override_reason must be empty when "
                "the system diagnosis is accepted."
            )

        if (
            self.final_state == "no_misconception"
            and self.final_misconception_id is not None
        ):
            raise ValueError(
                "final_misconception_id must be empty "
                "when final_state is no_misconception."
            )

        return self


class TeacherReviewAcceptRequest(BaseModel):
    """
    Accept the system diagnosis as the teacher's final decision.
    """

    teacher_note: str | None = Field(
        default=None,
        max_length=4000,
    )


class TeacherReviewOverrideRequest(BaseModel):
    """
    Override the system diagnosis with a teacher-selected result.
    """

    final_state: TeacherFinalDiagnosisState

    final_misconception_id: uuid.UUID | None = None

    override_reason: str = Field(
        min_length=1,
        max_length=4000,
    )

    teacher_note: str | None = Field(
        default=None,
        max_length=4000,
    )

    @model_validator(mode="after")
    def validate_override_consistency(
        self,
    ) -> "TeacherReviewOverrideRequest":
        if (
            self.final_state == "no_misconception"
            and self.final_misconception_id is not None
        ):
            raise ValueError(
                "final_misconception_id must be empty "
                "when final_state is no_misconception."
            )

        if (
            self.final_state
            in {
                "confident",
                "possible",
            }
            and self.final_misconception_id is None
        ):
            raise ValueError(
                "final_misconception_id is required "
                "for confident or possible "
                "misconception outcomes."
            )

        return self


class TeacherReviewFinalizeRequest(BaseModel):
    """
    Finalize a review using either an accepted or overridden decision.
    """

    decision: TeacherReviewDecision

    final_state: TeacherFinalDiagnosisState

    final_misconception_id: uuid.UUID | None = None

    override_reason: str | None = Field(
        default=None,
        max_length=4000,
    )

    teacher_note: str | None = Field(
        default=None,
        max_length=4000,
    )

    @model_validator(mode="after")
    def validate_finalize_consistency(
        self,
    ) -> "TeacherReviewFinalizeRequest":
        if (
            self.decision == "overridden"
            and not self.override_reason
        ):
            raise ValueError(
                "override_reason is required when "
                "decision is overridden."
            )

        if (
            self.decision == "accepted"
            and self.override_reason
        ):
            raise ValueError(
                "override_reason must be empty when "
                "decision is accepted."
            )

        if (
            self.final_state == "no_misconception"
            and self.final_misconception_id is not None
        ):
            raise ValueError(
                "final_misconception_id must be empty "
                "when final_state is no_misconception."
            )

        if (
            self.final_state
            in {
                "confident",
                "possible",
            }
            and self.final_misconception_id is None
        ):
            raise ValueError(
                "final_misconception_id is required "
                "for confident or possible "
                "misconception outcomes."
            )

        return self


class TeacherReviewResponse(BaseModel):
    """
    Persisted teacher-review record.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID

    attempt_id: uuid.UUID

    teacher_id: uuid.UUID

    system_diagnosis_id: uuid.UUID | None

    status: TeacherReviewStatus

    decision: TeacherReviewDecision | None

    final_state: TeacherFinalDiagnosisState | None

    final_misconception_id: uuid.UUID | None

    override_reason: str | None

    teacher_note: str | None

    reviewed_at: datetime | None

    created_at: datetime

    updated_at: datetime


class TeacherReviewStudentSummary(BaseModel):
    """
    Minimal student information for the review queue and detail page.
    """

    id: uuid.UUID

    alias: str

    pseudonymous_id: str


class TeacherReviewProblemSummary(BaseModel):
    """
    Minimal problem information for the review queue and detail page.
    """

    id: uuid.UUID

    code: str

    title: str

    topic: str


class TeacherReviewDiagnosisSummary(BaseModel):
    """
    System diagnosis information shown beside a teacher review.
    """

    id: uuid.UUID

    state: TeacherFinalDiagnosisState

    confidence: float

    primary_misconception_id: uuid.UUID | None

    model_version: str

    next_action: str

    created_at: datetime


class TeacherReviewAttemptSummary(BaseModel):
    """
    Compact attempt information required by the review queue.
    """

    id: uuid.UUID

    selected_language: str

    response_time_seconds: int | None

    created_at: datetime


class TeacherReviewAttemptDetail(BaseModel):
    """
    Full student-attempt content required by the review detail page.
    """

    id: uuid.UUID

    final_answer: str | None

    written_reasoning: str

    source_code: str | None

    speech_transcript: str | None

    selected_language: str

    response_time_seconds: int | None

    created_at: datetime


class TeacherReviewQueueItem(BaseModel):
    """
    One teacher-review queue entry.
    """

    attempt: TeacherReviewAttemptSummary

    student: TeacherReviewStudentSummary

    problem: TeacherReviewProblemSummary

    system_diagnosis: (
        TeacherReviewDiagnosisSummary | None
    )

    review: TeacherReviewResponse | None


class TeacherReviewPaginationMeta(BaseModel):
    """
    Pagination metadata for teacher-review queue responses.
    """

    page: int = Field(
        ge=1,
    )

    page_size: int = Field(
        ge=1,
        le=100,
    )

    total_items: int = Field(
        ge=0,
    )

    total_pages: int = Field(
        ge=0,
    )

    has_previous: bool

    has_next: bool


class TeacherReviewQueueResponse(BaseModel):
    """
    Paginated teacher-review queue.
    """

    items: list[TeacherReviewQueueItem]

    pagination: TeacherReviewPaginationMeta


class TeacherReviewDetailResponse(BaseModel):
    """
    Full review detail response returned to the teacher console.
    """

    attempt_id: uuid.UUID

    attempt: TeacherReviewAttemptDetail

    student: TeacherReviewStudentSummary

    problem: TeacherReviewProblemSummary

    system_diagnosis: (
        TeacherReviewDiagnosisSummary | None
    )

    review: TeacherReviewResponse | None


class TeacherReviewMessageResponse(BaseModel):
    """
    Standard confirmation response for review actions.
    """

    message: str

    review: TeacherReviewResponse