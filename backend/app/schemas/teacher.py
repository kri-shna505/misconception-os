from __future__ import annotations

from datetime import datetime
from enum import Enum
from math import ceil
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.schemas.attempt import (
    AttemptResponse,
    AttemptSummary,
)
from app.schemas.diagnosis import (
    DiagnosisResponse,
    DiagnosisState,
    DiagnosisSummary,
)
from app.schemas.problem_schema import (
    ProblemDetail,
    ProblemListItem,
)
from app.schemas.student_schema import (
    StudentAliasSummary,
)
from app.schemas.teacher_review import (
    TeacherReviewResponse,
)


class MisconceptionEvolutionState(str, Enum):
    """
    Sprint 9 misconception-learning transition states.
    """

    NEWLY_DETECTED = "newly_detected"
    REPEATED = "repeated"
    IMPROVING = "improving"
    CORRECTED = "corrected"
    REPLACED = "replaced"
    UNCERTAIN = "uncertain"


class PaginationMeta(BaseModel):
    page: int = Field(
        default=1,
        ge=1,
    )

    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
    )

    total_items: int = Field(
        default=0,
        ge=0,
    )

    total_pages: int = Field(
        default=0,
        ge=0,
    )

    has_previous: bool = False

    has_next: bool = False

    model_config = ConfigDict(
        extra="forbid",
    )

    @classmethod
    def create(
        cls,
        *,
        page: int,
        page_size: int,
        total_items: int,
    ) -> "PaginationMeta":
        total_pages = (
            ceil(
                total_items / page_size,
            )
            if total_items > 0
            else 0
        )

        return cls(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_previous=page > 1,
            has_next=page < total_pages,
        )


class TeacherDashboardSummary(BaseModel):
    total_students: int = Field(
        default=0,
        ge=0,
    )

    total_attempts: int = Field(
        default=0,
        ge=0,
    )

    total_diagnoses: int = Field(
        default=0,
        ge=0,
    )

    verified_attempts: int = Field(
        default=0,
        ge=0,
    )

    misconception_attempts: int = Field(
        default=0,
        ge=0,
    )

    insufficient_attempts: int = Field(
        default=0,
        ge=0,
    )

    undiagnosed_attempts: int = Field(
        default=0,
        ge=0,
    )

    average_response_time_seconds: (
        float | None
    ) = Field(
        default=None,
        ge=0,
    )

    diagnosis_coverage_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    verified_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    misconception_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    model_config = ConfigDict(
        extra="forbid",
    )


class TeacherAttemptListItem(BaseModel):
    """
    One teacher-facing attempt-list row.

    The review is returned directly with the attempt so the
    frontend does not need to request one review endpoint per row.
    """

    attempt: AttemptSummary

    student: StudentAliasSummary

    problem: ProblemListItem

    diagnosis: DiagnosisSummary | None = None

    review: TeacherReviewResponse | None = None

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )


class TeacherAttemptListResponse(BaseModel):
    items: list[
        TeacherAttemptListItem
    ] = Field(
        default_factory=list,
    )

    pagination: PaginationMeta

    model_config = ConfigDict(
        extra="forbid",
    )


class TeacherAttemptDetailResponse(BaseModel):
    """
    Complete teacher-facing attempt record.

    The automated diagnosis and teacher review remain separate
    so both machine output and human decision are traceable.
    """

    attempt: AttemptResponse

    student: StudentAliasSummary

    problem: ProblemDetail

    diagnosis: DiagnosisResponse | None = None

    review: TeacherReviewResponse | None = None

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )


class StudentHistoryItem(BaseModel):
    """
    One attempt in the teacher-facing student learning timeline.

    Sprint 9 adds intervention and evolution metadata while keeping the
    timeline attempt-centric. The displayed diagnosis is the latest diagnosis
    snapshot for the attempt, while hint/question activity may be aggregated
    across all immutable diagnosis snapshots for that attempt.
    """

    attempt: AttemptSummary

    problem: ProblemListItem

    diagnosis: DiagnosisSummary | None = None

    parent_attempt_id: UUID | None = None

    retry_number: int = Field(
        default=0,
        ge=0,
    )

    hint_levels_used: list[int] = Field(
        default_factory=list,
    )

    diagnostic_question_answered: bool = False

    evolution_state: (
        MisconceptionEvolutionState | None
    ) = None

    review: TeacherReviewResponse | None = None

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_history_intervention_state(
        self,
    ) -> "StudentHistoryItem":
        normalized_levels = sorted(
            set(
                self.hint_levels_used
            )
        )

        if any(
            level < 1 or level > 3
            for level in normalized_levels
        ):
            raise ValueError(
                "Hint levels used must be within the approved L1-L3 range."
            )

        expected_prefix = list(
            range(
                1,
                len(normalized_levels) + 1,
            )
        )

        if normalized_levels != expected_prefix:
            raise ValueError(
                "Hint levels used must form a sequential L1-L3 progression."
            )

        self.hint_levels_used = (
            normalized_levels
        )

        if (
            self.retry_number == 0
            and self.parent_attempt_id
            is not None
        ):
            raise ValueError(
                "An original attempt must not contain a parent attempt ID."
            )

        if (
            self.retry_number > 0
            and self.parent_attempt_id
            is None
        ):
            raise ValueError(
                "A retry attempt requires a parent attempt ID."
            )

        return self


class StudentHistorySummary(BaseModel):
    total_attempts: int = Field(
        default=0,
        ge=0,
    )

    diagnosed_attempts: int = Field(
        default=0,
        ge=0,
    )

    verified_attempts: int = Field(
        default=0,
        ge=0,
    )

    misconception_attempts: int = Field(
        default=0,
        ge=0,
    )

    insufficient_attempts: int = Field(
        default=0,
        ge=0,
    )

    average_response_time_seconds: (
        float | None
    ) = Field(
        default=None,
        ge=0,
    )

    model_config = ConfigDict(
        extra="forbid",
    )

    @model_validator(mode="after")
    def validate_attempt_counts(
        self,
    ) -> "StudentHistorySummary":
        if (
            self.diagnosed_attempts
            > self.total_attempts
        ):
            raise ValueError(
                "Diagnosed attempts cannot exceed total attempts."
            )

        categorized_attempts = (
            self.verified_attempts
            + self.misconception_attempts
            + self.insufficient_attempts
        )

        if (
            categorized_attempts
            > self.diagnosed_attempts
        ):
            raise ValueError(
                "Categorized attempt counts cannot exceed diagnosed attempts."
            )

        return self


class StudentHistoryResponse(BaseModel):
    student: StudentAliasSummary

    summary: StudentHistorySummary

    items: list[
        StudentHistoryItem
    ] = Field(
        default_factory=list,
    )

    pagination: PaginationMeta

    model_config = ConfigDict(
        extra="forbid",
    )


class DiagnosisStateMetric(BaseModel):
    state: DiagnosisState

    count: int = Field(
        default=0,
        ge=0,
    )

    percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
    )

    model_config = ConfigDict(
        extra="forbid",
    )


class ProblemAnalyticsResponse(BaseModel):
    problem: ProblemListItem

    total_attempts: int = Field(
        default=0,
        ge=0,
    )

    diagnosed_attempts: int = Field(
        default=0,
        ge=0,
    )

    verified_attempts: int = Field(
        default=0,
        ge=0,
    )

    misconception_attempts: int = Field(
        default=0,
        ge=0,
    )

    insufficient_attempts: int = Field(
        default=0,
        ge=0,
    )

    average_response_time_seconds: (
        float | None
    ) = Field(
        default=None,
        ge=0,
    )

    diagnosis_states: list[
        DiagnosisStateMetric
    ] = Field(
        default_factory=list,
    )

    model_config = ConfigDict(
        extra="forbid",
    )


class MisconceptionAnalyticsItem(BaseModel):
    misconception_id: UUID

    code: str = Field(
        ...,
        min_length=1,
        max_length=30,
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )

    topic: str | None = Field(
        default=None,
        max_length=100,
    )

    detection_count: int = Field(
        default=0,
        ge=0,
    )

    percentage_of_diagnoses: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
    )

    average_confidence: (
        float | None
    ) = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    affected_student_count: int = Field(
        default=0,
        ge=0,
    )

    affected_problem_count: int = Field(
        default=0,
        ge=0,
    )

    model_config = ConfigDict(
        extra="forbid",
    )


class MisconceptionAnalyticsResponse(BaseModel):
    total_diagnoses: int = Field(
        default=0,
        ge=0,
    )

    total_misconception_diagnoses: int = Field(
        default=0,
        ge=0,
    )

    items: list[
        MisconceptionAnalyticsItem
    ] = Field(
        default_factory=list,
    )

    model_config = ConfigDict(
        extra="forbid",
    )


class AttemptsOverTimeItem(BaseModel):
    date: datetime

    attempt_count: int = Field(
        default=0,
        ge=0,
    )

    diagnosis_count: int = Field(
        default=0,
        ge=0,
    )

    verified_count: int = Field(
        default=0,
        ge=0,
    )

    misconception_count: int = Field(
        default=0,
        ge=0,
    )

    model_config = ConfigDict(
        extra="forbid",
    )


class TeacherDashboardResponse(BaseModel):
    summary: TeacherDashboardSummary

    misconception_analytics: list[
        MisconceptionAnalyticsItem
    ] = Field(
        default_factory=list,
    )

    attempts_over_time: list[
        AttemptsOverTimeItem
    ] = Field(
        default_factory=list,
    )

    generated_at: datetime

    model_config = ConfigDict(
        extra="forbid",
    )

    @model_validator(
        mode="after",
    )
    def validate_dashboard_counts(
        self,
    ) -> "TeacherDashboardResponse":
        summary = self.summary

        categorized_diagnoses = (
            summary.verified_attempts
            + summary.misconception_attempts
            + summary.insufficient_attempts
        )

        if (
            categorized_diagnoses
            > summary.total_diagnoses
        ):
            raise ValueError(
                "Categorized diagnosis counts cannot exceed total_diagnoses."
            )

        # Sprint 9 note:
        # One attempt may now have multiple immutable diagnosis snapshots
        # after diagnostic-question re-evaluation. Therefore total_diagnoses
        # may legitimately exceed total_attempts and must not be validated
        # against total_attempts.

        return self


__all__ = [
    "AttemptsOverTimeItem",
    "DiagnosisStateMetric",
    "MisconceptionAnalyticsItem",
    "MisconceptionAnalyticsResponse",
    "MisconceptionEvolutionState",
    "PaginationMeta",
    "ProblemAnalyticsResponse",
    "StudentHistoryItem",
    "StudentHistoryResponse",
    "StudentHistorySummary",
    "TeacherAttemptDetailResponse",
    "TeacherAttemptListItem",
    "TeacherAttemptListResponse",
    "TeacherDashboardResponse",
    "TeacherDashboardSummary",
]