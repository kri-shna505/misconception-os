from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.diagnosis import DiagnosisState
from app.schemas.teacher import (
    MisconceptionAnalyticsResponse,
    ProblemAnalyticsResponse,
    StudentHistoryResponse,
    TeacherAttemptDetailResponse,
    TeacherAttemptListResponse,
    TeacherDashboardResponse,
)
from app.services.teacher_service import (
    get_misconception_analytics,
    get_problem_analytics,
    get_student_history,
    get_teacher_attempt_detail,
    get_teacher_dashboard,
    list_teacher_attempts,
)


router = APIRouter(
    prefix="/teacher",
    tags=["Teacher"],
)


@router.get(
    "/dashboard",
    response_model=TeacherDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get teacher dashboard",
    description=(
        "Return class-level dashboard metrics, top misconception trends, "
        "and attempt activity over time."
    ),
    response_description="Teacher dashboard metrics and trend data.",
)
def read_teacher_dashboard(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of calendar days included in the timeline.",
    ),
    top_misconceptions: int = Query(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of misconception metrics returned.",
    ),
    db: Session = Depends(get_db),
) -> TeacherDashboardResponse:
    return get_teacher_dashboard(
        db=db,
        days=days,
        top_misconceptions=top_misconceptions,
    )


@router.get(
    "/attempts",
    response_model=TeacherAttemptListResponse,
    status_code=status.HTTP_200_OK,
    summary="List attempts for teacher review",
    description=(
        "Return a paginated teacher-facing list of student attempts with "
        "student, problem, diagnosis, and teacher-review summaries. "
        "When a review exists, its current status, decision, final state, "
        "and review metadata are included directly in the corresponding "
        "attempt row."
    ),
    response_description=(
        "Paginated attempt review list with diagnosis and review context."
    ),
)
def read_teacher_attempts(
    page: int = Query(
        default=1,
        ge=1,
        description="One-based page number.",
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of records returned per page.",
    ),
    student_alias_id: UUID | None = Query(
        default=None,
        description="Filter by student alias ID.",
    ),
    problem_id: UUID | None = Query(
        default=None,
        description="Filter by problem ID.",
    ),
    diagnosis_state: DiagnosisState | None = Query(
        default=None,
        description="Filter by diagnosis state.",
    ),
    misconception_code: str | None = Query(
        default=None,
        min_length=1,
        max_length=30,
        description="Filter by misconception code, such as M1.",
    ),
    created_from: datetime | None = Query(
        default=None,
        description="Include attempts created on or after this timestamp.",
    ),
    created_to: datetime | None = Query(
        default=None,
        description="Include attempts created on or before this timestamp.",
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=120,
        description=(
            "Search student alias, pseudonymous ID, problem code/title, "
            "or misconception code/name."
        ),
    ),
    db: Session = Depends(get_db),
) -> TeacherAttemptListResponse:
    return list_teacher_attempts(
        db=db,
        page=page,
        page_size=page_size,
        student_alias_id=student_alias_id,
        problem_id=problem_id,
        diagnosis_state=diagnosis_state,
        misconception_code=misconception_code,
        created_from=created_from,
        created_to=created_to,
        search=search,
    )


@router.get(
    "/attempts/{attempt_id}",
    response_model=TeacherAttemptDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get attempt review details",
    description=(
        "Return one complete student attempt with the student alias, "
        "problem, diagnosis, evidence, alternatives, and the latest "
        "teacher-review record when one exists."
    ),
    response_description=(
        "Complete teacher-facing attempt review record with review context."
    ),
)
def read_teacher_attempt_detail(
    attempt_id: UUID,
    db: Session = Depends(get_db),
) -> TeacherAttemptDetailResponse:
    return get_teacher_attempt_detail(
        db=db,
        attempt_id=attempt_id,
    )


@router.get(
    "/students/{student_alias_id}/history",
    response_model=StudentHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get student attempt history",
    description=(
        "Return a paginated history of attempts and diagnoses for one "
        "pseudonymous student alias."
    ),
    response_description="Student history summary and paginated records.",
)
def read_student_history(
    student_alias_id: UUID,
    page: int = Query(
        default=1,
        ge=1,
        description="One-based page number.",
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of history records returned per page.",
    ),
    db: Session = Depends(get_db),
) -> StudentHistoryResponse:
    return get_student_history(
        db=db,
        student_alias_id=student_alias_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/problems/{problem_id}/analytics",
    response_model=ProblemAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get problem analytics",
    description=(
        "Return attempt volume, diagnosis distribution, verification counts, "
        "misconception counts, and average response time for one problem."
    ),
    response_description="Problem-level analytics.",
)
def read_problem_analytics(
    problem_id: UUID,
    db: Session = Depends(get_db),
) -> ProblemAnalyticsResponse:
    return get_problem_analytics(
        db=db,
        problem_id=problem_id,
    )


@router.get(
    "/misconceptions/analytics",
    response_model=MisconceptionAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get misconception analytics",
    description=(
        "Return misconception frequency, average confidence, affected "
        "student count, and affected problem count."
    ),
    response_description="Misconception analytics collection.",
)
def read_misconception_analytics(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of misconception rows returned.",
    ),
    db: Session = Depends(get_db),
) -> MisconceptionAnalyticsResponse:
    return get_misconception_analytics(
        db=db,
        limit=limit,
    )