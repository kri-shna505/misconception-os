from __future__ import annotations

from datetime import datetime
from math import ceil
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.attempt import AttemptResponse, AttemptSummary
from app.schemas.diagnosis import (
    DiagnosisResponse,
    DiagnosisState,
    DiagnosisSummary,
)
from app.schemas.problem_schema import ProblemDetail, ProblemListItem
from app.schemas.student_schema import StudentAliasSummary


class PaginationMeta(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    total_items: int = Field(default=0, ge=0)
    total_pages: int = Field(default=0, ge=0)
    has_previous: bool = False
    has_next: bool = False

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def create(
        cls,
        *,
        page: int,
        page_size: int,
        total_items: int,
    ) -> "PaginationMeta":
        total_pages = (
            ceil(total_items / page_size)
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
    total_students: int = Field(default=0, ge=0)
    total_attempts: int = Field(default=0, ge=0)
    total_diagnoses: int = Field(default=0, ge=0)

    verified_attempts: int = Field(default=0, ge=0)
    misconception_attempts: int = Field(default=0, ge=0)
    insufficient_attempts: int = Field(default=0, ge=0)
    undiagnosed_attempts: int = Field(default=0, ge=0)

    average_response_time_seconds: float | None = Field(
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

    model_config = ConfigDict(extra="forbid")


class TeacherAttemptListItem(BaseModel):
    attempt: AttemptSummary
    student: StudentAliasSummary
    problem: ProblemListItem
    diagnosis: DiagnosisSummary | None = None

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )


class TeacherAttemptListResponse(BaseModel):
    items: list[TeacherAttemptListItem] = Field(
        default_factory=list,
    )
    pagination: PaginationMeta

    model_config = ConfigDict(extra="forbid")


class TeacherAttemptDetailResponse(BaseModel):
    attempt: AttemptResponse
    student: StudentAliasSummary
    problem: ProblemDetail
    diagnosis: DiagnosisResponse | None = None

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )


class StudentHistoryItem(BaseModel):
    attempt: AttemptSummary
    problem: ProblemListItem
    diagnosis: DiagnosisSummary | None = None

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )


class StudentHistorySummary(BaseModel):
    total_attempts: int = Field(default=0, ge=0)
    diagnosed_attempts: int = Field(default=0, ge=0)
    verified_attempts: int = Field(default=0, ge=0)
    misconception_attempts: int = Field(default=0, ge=0)
    insufficient_attempts: int = Field(default=0, ge=0)

    average_response_time_seconds: float | None = Field(
        default=None,
        ge=0,
    )

    model_config = ConfigDict(extra="forbid")


class StudentHistoryResponse(BaseModel):
    student: StudentAliasSummary
    summary: StudentHistorySummary
    items: list[StudentHistoryItem] = Field(
        default_factory=list,
    )
    pagination: PaginationMeta

    model_config = ConfigDict(extra="forbid")


class DiagnosisStateMetric(BaseModel):
    state: DiagnosisState
    count: int = Field(default=0, ge=0)
    percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
    )

    model_config = ConfigDict(extra="forbid")


class ProblemAnalyticsResponse(BaseModel):
    problem: ProblemListItem

    total_attempts: int = Field(default=0, ge=0)
    diagnosed_attempts: int = Field(default=0, ge=0)
    verified_attempts: int = Field(default=0, ge=0)
    misconception_attempts: int = Field(default=0, ge=0)
    insufficient_attempts: int = Field(default=0, ge=0)

    average_response_time_seconds: float | None = Field(
        default=None,
        ge=0,
    )

    diagnosis_states: list[DiagnosisStateMetric] = Field(
        default_factory=list,
    )

    model_config = ConfigDict(extra="forbid")


class MisconceptionAnalyticsItem(BaseModel):
    misconception_id: UUID
    code: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=1, max_length=255)
    topic: str | None = Field(default=None, max_length=100)

    detection_count: int = Field(default=0, ge=0)

    percentage_of_diagnoses: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
    )

    average_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    affected_student_count: int = Field(default=0, ge=0)
    affected_problem_count: int = Field(default=0, ge=0)

    model_config = ConfigDict(extra="forbid")


class MisconceptionAnalyticsResponse(BaseModel):
    total_diagnoses: int = Field(default=0, ge=0)
    total_misconception_diagnoses: int = Field(default=0, ge=0)

    items: list[MisconceptionAnalyticsItem] = Field(
        default_factory=list,
    )

    model_config = ConfigDict(extra="forbid")


class AttemptsOverTimeItem(BaseModel):
    date: datetime
    attempt_count: int = Field(default=0, ge=0)
    diagnosis_count: int = Field(default=0, ge=0)
    verified_count: int = Field(default=0, ge=0)
    misconception_count: int = Field(default=0, ge=0)

    model_config = ConfigDict(extra="forbid")


class TeacherDashboardResponse(BaseModel):
    summary: TeacherDashboardSummary

    misconception_analytics: list[
        MisconceptionAnalyticsItem
    ] = Field(default_factory=list)

    attempts_over_time: list[AttemptsOverTimeItem] = Field(
        default_factory=list,
    )

    generated_at: datetime

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_dashboard_counts(
        self,
    ) -> "TeacherDashboardResponse":
        summary = self.summary

        categorized_diagnoses = (
            summary.verified_attempts
            + summary.misconception_attempts
            + summary.insufficient_attempts
        )

        if categorized_diagnoses > summary.total_diagnoses:
            raise ValueError(
                "Categorized diagnosis counts cannot exceed "
                "total_diagnoses."
            )

        if (
            summary.total_diagnoses
            + summary.undiagnosed_attempts
            > summary.total_attempts
        ):
            raise ValueError(
                "Diagnosed and undiagnosed attempt counts cannot exceed "
                "total_attempts."
            )

        return self