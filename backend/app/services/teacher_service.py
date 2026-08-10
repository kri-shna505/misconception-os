from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Date, and_, cast, func, or_
from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.models.diagnosis import Diagnosis
from app.models.diagnosis_alternative import DiagnosisAlternative
from app.models.diagnosis_evidence import DiagnosisEvidence
from app.models.diagnostic_response import DiagnosticResponse
from app.models.hint_event import HintEvent
from app.models.misconception_evolution import MisconceptionEvolution
from app.models.misconception import Misconception
from app.models.problem import Problem
from app.models.problem_misconception import ProblemMisconception
from app.models.student_alias import StudentAlias
from app.models.teacher_review import TeacherReview
from app.schemas.attempt import AttemptResponse, AttemptSummary
from app.schemas.diagnosis import (
    DiagnosisAlternativeResponse,
    DiagnosisEvidenceResponse,
    DiagnosisNextAction,
    DiagnosisResponse,
    DiagnosisState,
    DiagnosisSummary,
    EvidenceSource,
    EvidenceStrength,
    MisconceptionSummary,
)
from app.schemas.problem_schema import (
    ProblemDetail,
    ProblemListItem,
    SupportedMisconception,
)
from app.schemas.student_schema import StudentAliasSummary
from app.schemas.teacher_review import TeacherReviewResponse
from app.schemas.teacher import (
    AttemptsOverTimeItem,
    DiagnosisStateMetric,
    MisconceptionAnalyticsItem,
    MisconceptionAnalyticsResponse,
    PaginationMeta,
    ProblemAnalyticsResponse,
    StudentHistoryItem,
    StudentHistoryResponse,
    StudentHistorySummary,
    TeacherAttemptDetailResponse,
    TeacherAttemptListItem,
    TeacherAttemptListResponse,
    TeacherDashboardResponse,
    TeacherDashboardSummary,
)


SUPPORTED_MISCONCEPTION_STATES = {
    DiagnosisState.CONFIDENT.value,
    DiagnosisState.POSSIBLE.value,
}


def get_teacher_dashboard(
    db: Session,
    *,
    days: int = 30,
    top_misconceptions: int = 5,
) -> TeacherDashboardResponse:
    """
    Return teacher dashboard totals, top misconception metrics, and
    attempt activity over time.

    The dashboard is intentionally derived from source tables instead of
    storing duplicate aggregate counters.
    """

    days = max(1, min(days, 365))
    top_misconceptions = max(1, min(top_misconceptions, 20))

    total_students = db.query(func.count(StudentAlias.id)).scalar() or 0
    total_attempts = db.query(func.count(Attempt.id)).scalar() or 0
    total_diagnoses = db.query(func.count(Diagnosis.id)).scalar() or 0

    verified_attempts = (
        db.query(func.count(Diagnosis.id))
        .filter(Diagnosis.state == DiagnosisState.NO_MISCONCEPTION.value)
        .scalar()
        or 0
    )

    misconception_attempts = (
        db.query(func.count(Diagnosis.id))
        .filter(Diagnosis.state.in_(SUPPORTED_MISCONCEPTION_STATES))
        .scalar()
        or 0
    )

    insufficient_attempts = (
        db.query(func.count(Diagnosis.id))
        .filter(Diagnosis.state == DiagnosisState.INSUFFICIENT.value)
        .scalar()
        or 0
    )

    diagnosed_attempt_ids = (
        db.query(func.count(func.distinct(Diagnosis.attempt_id))).scalar()
        or 0
    )

    undiagnosed_attempts = max(total_attempts - diagnosed_attempt_ids, 0)

    average_response_time = (
        db.query(func.avg(Attempt.response_time_seconds))
        .filter(Attempt.response_time_seconds.isnot(None))
        .scalar()
    )

    summary = TeacherDashboardSummary(
        total_students=total_students,
        total_attempts=total_attempts,
        total_diagnoses=total_diagnoses,
        verified_attempts=verified_attempts,
        misconception_attempts=misconception_attempts,
        insufficient_attempts=insufficient_attempts,
        undiagnosed_attempts=undiagnosed_attempts,
        average_response_time_seconds=_optional_float(
            average_response_time
        ),
        diagnosis_coverage_rate=_safe_ratio(
            diagnosed_attempt_ids,
            total_attempts,
        ),
        verified_rate=_safe_ratio(
            verified_attempts,
            total_diagnoses,
        ),
        misconception_rate=_safe_ratio(
            misconception_attempts,
            total_diagnoses,
        ),
    )

    misconception_analytics = get_misconception_analytics(
        db,
        limit=top_misconceptions,
    ).items

    start_date = datetime.utcnow().date() - timedelta(days=days - 1)
    attempts_over_time = _get_attempts_over_time(
        db,
        start_date=start_date,
        days=days,
    )

    return TeacherDashboardResponse(
        summary=summary,
        misconception_analytics=misconception_analytics,
        attempts_over_time=attempts_over_time,
        generated_at=datetime.utcnow(),
    )


def list_teacher_attempts(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    student_alias_id: UUID | None = None,
    problem_id: UUID | None = None,
    diagnosis_state: DiagnosisState | None = None,
    misconception_code: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    search: str | None = None,
) -> TeacherAttemptListResponse:
    """
    Return the teacher attempt-review list with filtering and pagination.

    Pagination is attempt-centric. This prevents one attempt from appearing
    multiple times after Sprint 9 diagnostic-question re-evaluation creates
    additional immutable diagnosis snapshots.
    """

    page, page_size = _normalize_pagination(
        page,
        page_size,
    )

    query = (
        db.query(
            Attempt,
            StudentAlias,
            Problem,
        )
        .join(
            StudentAlias,
            StudentAlias.id
            == Attempt.student_alias_id,
        )
        .join(
            Problem,
            Problem.id
            == Attempt.problem_id,
        )
    )

    if student_alias_id is not None:
        query = query.filter(
            Attempt.student_alias_id
            == student_alias_id
        )

    if problem_id is not None:
        query = query.filter(
            Attempt.problem_id
            == problem_id
        )

    if created_from is not None:
        query = query.filter(
            Attempt.created_at
            >= created_from
        )

    if created_to is not None:
        query = query.filter(
            Attempt.created_at
            <= created_to
        )

    if search:
        normalized_search = (
            f"%{search.strip()}%"
        )

        query = query.filter(
            or_(
                StudentAlias.alias.ilike(
                    normalized_search
                ),
                StudentAlias.pseudonymous_id.ilike(
                    normalized_search
                ),
                Problem.code.ilike(
                    normalized_search
                ),
                Problem.title.ilike(
                    normalized_search
                ),
            )
        )

    candidate_rows = (
        query.order_by(
            Attempt.created_at.desc(),
            Attempt.id.desc(),
        )
        .all()
    )

    candidate_attempt_ids = [
        attempt.id
        for (
            attempt,
            _,
            _,
        ) in candidate_rows
    ]

    latest_diagnoses = (
        _get_latest_diagnoses_by_attempt(
            db=db,
            attempt_ids=candidate_attempt_ids,
        )
    )

    misconception_by_id: dict[
        UUID,
        Misconception,
    ] = {}

    misconception_ids = {
        diagnosis.primary_misconception_id
        for diagnosis in latest_diagnoses.values()
        if (
            diagnosis.primary_misconception_id
            is not None
        )
    }

    if misconception_ids:
        misconception_by_id = {
            item.id: item
            for item in (
                db.query(
                    Misconception
                )
                .filter(
                    Misconception.id.in_(
                        misconception_ids
                    )
                )
                .all()
            )
        }

    filtered_rows: list[
        tuple[
            Attempt,
            StudentAlias,
            Problem,
        ]
    ] = []

    normalized_code = (
        misconception_code
        .strip()
        .upper()
        if misconception_code
        else None
    )

    for (
        attempt,
        student,
        problem,
    ) in candidate_rows:
        diagnosis = (
            latest_diagnoses.get(
                attempt.id
            )
        )

        if (
            diagnosis_state
            is not None
            and (
                diagnosis is None
                or diagnosis.state
                != diagnosis_state.value
            )
        ):
            continue

        if normalized_code:
            if (
                diagnosis is None
                or diagnosis.primary_misconception_id
                is None
            ):
                continue

            misconception = (
                misconception_by_id.get(
                    diagnosis.primary_misconception_id
                )
            )

            if (
                misconception is None
                or misconception.code
                .strip()
                .upper()
                != normalized_code
            ):
                continue

        filtered_rows.append(
            (
                attempt,
                student,
                problem,
            )
        )

    total_items = len(
        filtered_rows
    )

    page_rows = filtered_rows[
        (page - 1) * page_size:
        page * page_size
    ]

    page_attempt_ids = [
        attempt.id
        for (
            attempt,
            _,
            _,
        ) in page_rows
    ]

    reviews_by_attempt = {
        review.attempt_id: review
        for review in (
            db.query(
                TeacherReview
            )
            .filter(
                TeacherReview.attempt_id.in_(
                    page_attempt_ids
                )
            )
            .all()
            if page_attempt_ids
            else []
        )
    }

    items = [
        TeacherAttemptListItem(
            attempt=_attempt_summary(
                attempt
            ),
            student=_student_summary(
                student
            ),
            problem=_problem_list_item(
                problem
            ),
            diagnosis=(
                _diagnosis_summary(
                    latest_diagnoses[
                        attempt.id
                    ]
                )
                if attempt.id
                in latest_diagnoses
                else None
            ),
            review=(
                TeacherReviewResponse.model_validate(
                    reviews_by_attempt[
                        attempt.id
                    ]
                )
                if attempt.id
                in reviews_by_attempt
                else None
            ),
        )
        for (
            attempt,
            student,
            problem,
        ) in page_rows
    ]

    return TeacherAttemptListResponse(
        items=items,
        pagination=PaginationMeta.create(
            page=page,
            page_size=page_size,
            total_items=total_items,
        ),
    )


def get_teacher_attempt_detail(
    db: Session,
    *,
    attempt_id: UUID,
) -> TeacherAttemptDetailResponse:
    """
    Return one complete attempt with student, problem, diagnosis,
    evidence, and alternatives for teacher review.
    """

    row = (
        db.query(Attempt, StudentAlias, Problem)
        .join(
            StudentAlias,
            StudentAlias.id == Attempt.student_alias_id,
        )
        .join(
            Problem,
            Problem.id == Attempt.problem_id,
        )
        .filter(Attempt.id == attempt_id)
        .first()
    )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attempt not found.",
        )

    attempt, student, problem = row

    diagnosis = (
        db.query(Diagnosis)
        .filter(Diagnosis.attempt_id == attempt.id)
        .order_by(Diagnosis.created_at.desc())
        .first()
    )

    return TeacherAttemptDetailResponse(
        attempt=AttemptResponse.model_validate(attempt),
        student=_student_summary(student),
        problem=_problem_detail(db, problem),
        diagnosis=(
            _diagnosis_response(db, diagnosis)
            if diagnosis is not None
            else None
        ),
    )


def get_student_history(
    db: Session,
    *,
    student_alias_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> StudentHistoryResponse:
    """
    Return a paginated Sprint 9 learning history for one pseudonymous student.

    The history is attempt-centric. An attempt may contain more than one
    immutable diagnosis snapshot after diagnostic-question re-evaluation, so
    only the latest diagnosis is used as the current display state while hint
    usage and question-response activity are aggregated across the attempt.

    Each history item exposes, where supported by the response schema:

    - parent_attempt_id;
    - retry_number;
    - revealed hint levels;
    - whether a diagnostic question was answered;
    - the latest misconception-evolution state.
    """

    page, page_size = _normalize_pagination(
        page,
        page_size,
    )

    student = (
        db.query(StudentAlias)
        .filter(
            StudentAlias.id
            == student_alias_id
        )
        .first()
    )

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student alias not found.",
        )

    attempt_query = (
        db.query(Attempt, Problem)
        .join(
            Problem,
            Problem.id
            == Attempt.problem_id,
        )
        .filter(
            Attempt.student_alias_id
            == student_alias_id
        )
    )

    total_items = (
        db.query(
            func.count(Attempt.id)
        )
        .filter(
            Attempt.student_alias_id
            == student_alias_id
        )
        .scalar()
        or 0
    )

    attempt_rows = (
        attempt_query
        .order_by(
            Attempt.created_at.desc(),
            Attempt.id.desc(),
        )
        .offset(
            (page - 1) * page_size
        )
        .limit(page_size)
        .all()
    )

    attempt_ids = [
        attempt.id
        for attempt, _ in attempt_rows
    ]

    latest_diagnoses_by_attempt = (
        _get_latest_diagnoses_by_attempt(
            db=db,
            attempt_ids=attempt_ids,
        )
    )

    all_diagnosis_ids_by_attempt = (
        _get_diagnosis_ids_by_attempt(
            db=db,
            attempt_ids=attempt_ids,
        )
    )

    hint_levels_by_attempt = (
        _get_hint_levels_by_attempt(
            db=db,
            diagnosis_ids_by_attempt=(
                all_diagnosis_ids_by_attempt
            ),
        )
    )

    answered_questions_by_attempt = (
        _get_answered_question_attempt_ids(
            db=db,
            attempt_ids=attempt_ids,
        )
    )

    evolution_by_attempt = (
        _get_latest_evolution_by_attempt(
            db=db,
            attempt_ids=attempt_ids,
        )
    )

    summary = _build_student_history_summary(
        db=db,
        student_alias_id=student_alias_id,
    )

    items: list[StudentHistoryItem] = []

    for attempt, problem in attempt_rows:
        diagnosis = (
            latest_diagnoses_by_attempt.get(
                attempt.id
            )
        )

        evolution = (
            evolution_by_attempt.get(
                attempt.id
            )
        )

        item_payload: dict[str, Any] = {
            "attempt": _attempt_summary(
                attempt
            ),
            "problem": _problem_list_item(
                problem
            ),
            "diagnosis": (
                _diagnosis_summary(
                    diagnosis
                )
                if diagnosis is not None
                else None
            ),
            "parent_attempt_id": (
                attempt.parent_attempt_id
            ),
            "retry_number": int(
                attempt.retry_number or 0
            ),
            "hint_levels_used": (
                hint_levels_by_attempt.get(
                    attempt.id,
                    [],
                )
            ),
            "diagnostic_question_answered": (
                attempt.id
                in answered_questions_by_attempt
            ),
            "evolution_state": (
                evolution.evolution_state
                if evolution is not None
                else None
            ),
        }

        items.append(
            StudentHistoryItem.model_validate(
                item_payload
            )
        )

    return StudentHistoryResponse(
        student=_student_summary(
            student
        ),
        summary=summary,
        items=items,
        pagination=PaginationMeta.create(
            page=page,
            page_size=page_size,
            total_items=total_items,
        ),
    )


def _build_student_history_summary(
    *,
    db: Session,
    student_alias_id: UUID,
) -> StudentHistorySummary:
    """
    Build attempt-level summary metrics without double-counting attempts that
    have multiple diagnosis snapshots.
    """

    attempts = (
        db.query(Attempt)
        .filter(
            Attempt.student_alias_id
            == student_alias_id
        )
        .all()
    )

    if not attempts:
        return StudentHistorySummary(
            total_attempts=0,
            diagnosed_attempts=0,
            verified_attempts=0,
            misconception_attempts=0,
            insufficient_attempts=0,
            average_response_time_seconds=None,
        )

    attempt_ids = [
        attempt.id
        for attempt in attempts
    ]

    latest_diagnoses = (
        _get_latest_diagnoses_by_attempt(
            db=db,
            attempt_ids=attempt_ids,
        )
    )

    diagnosed_attempts = len(
        latest_diagnoses
    )

    verified_attempts = 0
    misconception_attempts = 0
    insufficient_attempts = 0

    for diagnosis in (
        latest_diagnoses.values()
    ):
        state_value = (
            diagnosis.state
        )

        if (
            state_value
            == DiagnosisState.NO_MISCONCEPTION.value
        ):
            verified_attempts += 1
        elif (
            state_value
            in SUPPORTED_MISCONCEPTION_STATES
        ):
            misconception_attempts += 1
        elif (
            state_value
            == DiagnosisState.INSUFFICIENT.value
        ):
            insufficient_attempts += 1

    response_times = [
        float(
            attempt.response_time_seconds
        )
        for attempt in attempts
        if (
            attempt.response_time_seconds
            is not None
        )
    ]

    average_response_time = (
        sum(response_times)
        / len(response_times)
        if response_times
        else None
    )

    return StudentHistorySummary(
        total_attempts=len(attempts),
        diagnosed_attempts=diagnosed_attempts,
        verified_attempts=verified_attempts,
        misconception_attempts=misconception_attempts,
        insufficient_attempts=insufficient_attempts,
        average_response_time_seconds=(
            _optional_float(
                average_response_time
            )
        ),
    )


def _get_latest_diagnoses_by_attempt(
    *,
    db: Session,
    attempt_ids: list[UUID],
) -> dict[UUID, Diagnosis]:
    """
    Return the newest diagnosis snapshot for each requested attempt.
    """

    if not attempt_ids:
        return {}

    rows = (
        db.query(Diagnosis)
        .filter(
            Diagnosis.attempt_id.in_(
                attempt_ids
            )
        )
        .order_by(
            Diagnosis.attempt_id.asc(),
            Diagnosis.created_at.asc(),
            Diagnosis.id.asc(),
        )
        .all()
    )

    latest: dict[
        UUID,
        Diagnosis,
    ] = {}

    for diagnosis in rows:
        latest[
            diagnosis.attempt_id
        ] = diagnosis

    return latest


def _get_diagnosis_ids_by_attempt(
    *,
    db: Session,
    attempt_ids: list[UUID],
) -> dict[UUID, list[UUID]]:
    """
    Return every immutable diagnosis ID grouped by attempt.
    """

    grouped: dict[
        UUID,
        list[UUID],
    ] = {
        attempt_id: []
        for attempt_id in attempt_ids
    }

    if not attempt_ids:
        return grouped

    rows = (
        db.query(
            Diagnosis.attempt_id,
            Diagnosis.id,
        )
        .filter(
            Diagnosis.attempt_id.in_(
                attempt_ids
            )
        )
        .order_by(
            Diagnosis.created_at.asc(),
            Diagnosis.id.asc(),
        )
        .all()
    )

    for attempt_id, diagnosis_id in rows:
        grouped.setdefault(
            attempt_id,
            [],
        ).append(
            diagnosis_id
        )

    return grouped


def _get_hint_levels_by_attempt(
    *,
    db: Session,
    diagnosis_ids_by_attempt: dict[
        UUID,
        list[UUID],
    ],
) -> dict[UUID, list[int]]:
    """
    Aggregate revealed hint levels across all diagnosis snapshots of each
    attempt.
    """

    diagnosis_to_attempt: dict[
        UUID,
        UUID,
    ] = {}

    diagnosis_ids: list[UUID] = []

    for (
        attempt_id,
        attempt_diagnosis_ids,
    ) in diagnosis_ids_by_attempt.items():
        for diagnosis_id in (
            attempt_diagnosis_ids
        ):
            diagnosis_to_attempt[
                diagnosis_id
            ] = attempt_id

            diagnosis_ids.append(
                diagnosis_id
            )

    result: dict[
        UUID,
        set[int],
    ] = {}

    if not diagnosis_ids:
        return {}

    rows = (
        db.query(
            HintEvent.diagnosis_id,
            HintEvent.level,
        )
        .filter(
            HintEvent.diagnosis_id.in_(
                diagnosis_ids
            )
        )
        .order_by(
            HintEvent.level.asc()
        )
        .all()
    )

    for diagnosis_id, level in rows:
        attempt_id = (
            diagnosis_to_attempt.get(
                diagnosis_id
            )
        )

        if attempt_id is None:
            continue

        result.setdefault(
            attempt_id,
            set(),
        ).add(
            int(level)
        )

    return {
        attempt_id: sorted(
            levels
        )
        for (
            attempt_id,
            levels,
        ) in result.items()
    }


def _get_answered_question_attempt_ids(
    *,
    db: Session,
    attempt_ids: list[UUID],
) -> set[UUID]:
    """
    Return attempts that have at least one stored diagnostic response.
    """

    if not attempt_ids:
        return set()

    rows = (
        db.query(
            DiagnosticResponse.attempt_id
        )
        .filter(
            DiagnosticResponse.attempt_id.in_(
                attempt_ids
            )
        )
        .distinct()
        .all()
    )

    return {
        row[0]
        for row in rows
    }


def _get_latest_evolution_by_attempt(
    *,
    db: Session,
    attempt_ids: list[UUID],
) -> dict[
    UUID,
    MisconceptionEvolution,
]:
    """
    Return the latest stored evolution record for every requested attempt.
    """

    if not attempt_ids:
        return {}

    rows = (
        db.query(
            MisconceptionEvolution
        )
        .filter(
            MisconceptionEvolution.attempt_id.in_(
                attempt_ids
            )
        )
        .order_by(
            MisconceptionEvolution.attempt_id.asc(),
            MisconceptionEvolution.created_at.asc(),
            MisconceptionEvolution.id.asc(),
        )
        .all()
    )

    result: dict[
        UUID,
        MisconceptionEvolution,
    ] = {}

    for evolution in rows:
        result[
            evolution.attempt_id
        ] = evolution

    return result


def get_problem_analytics(
    db: Session,
    *,
    problem_id: UUID,
) -> ProblemAnalyticsResponse:
    """
    Return attempt and diagnosis metrics for one problem.
    """

    problem = (
        db.query(Problem)
        .filter(Problem.id == problem_id)
        .first()
    )

    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found.",
        )

    rows = (
        db.query(
            func.count(Attempt.id),
            func.count(Diagnosis.id),
            func.count(
                Diagnosis.id
            ).filter(
                Diagnosis.state
                == DiagnosisState.NO_MISCONCEPTION.value
            ),
            func.count(
                Diagnosis.id
            ).filter(
                Diagnosis.state.in_(
                    SUPPORTED_MISCONCEPTION_STATES
                )
            ),
            func.count(
                Diagnosis.id
            ).filter(
                Diagnosis.state
                == DiagnosisState.INSUFFICIENT.value
            ),
            func.avg(Attempt.response_time_seconds),
        )
        .outerjoin(Diagnosis, Diagnosis.attempt_id == Attempt.id)
        .filter(Attempt.problem_id == problem_id)
        .one()
    )

    state_rows = (
        db.query(
            Diagnosis.state,
            func.count(Diagnosis.id),
        )
        .join(Attempt, Attempt.id == Diagnosis.attempt_id)
        .filter(Attempt.problem_id == problem_id)
        .group_by(Diagnosis.state)
        .all()
    )

    diagnosed_attempts = rows[1] or 0

    diagnosis_states = [
        DiagnosisStateMetric(
            state=_diagnosis_state(state_value),
            count=count,
            percentage=round(
                _safe_ratio(count, diagnosed_attempts) * 100,
                2,
            ),
        )
        for state_value, count in state_rows
    ]

    return ProblemAnalyticsResponse(
        problem=_problem_list_item(problem),
        total_attempts=rows[0] or 0,
        diagnosed_attempts=diagnosed_attempts,
        verified_attempts=rows[2] or 0,
        misconception_attempts=rows[3] or 0,
        insufficient_attempts=rows[4] or 0,
        average_response_time_seconds=_optional_float(rows[5]),
        diagnosis_states=diagnosis_states,
    )


def get_misconception_analytics(
    db: Session,
    *,
    limit: int = 20,
) -> MisconceptionAnalyticsResponse:
    """
    Return misconception frequency, confidence, and affected entity counts.
    """

    limit = max(1, min(limit, 100))

    total_diagnoses = db.query(func.count(Diagnosis.id)).scalar() or 0

    total_misconception_diagnoses = (
        db.query(func.count(Diagnosis.id))
        .filter(
            Diagnosis.state.in_(SUPPORTED_MISCONCEPTION_STATES),
            Diagnosis.primary_misconception_id.isnot(None),
        )
        .scalar()
        or 0
    )

    rows = (
        db.query(
            Misconception.id,
            Misconception.code,
            Misconception.name,
            Misconception.topic,
            func.count(Diagnosis.id).label("detection_count"),
            func.avg(Diagnosis.confidence).label(
                "average_confidence"
            ),
            func.count(
                func.distinct(Attempt.student_alias_id)
            ).label("student_count"),
            func.count(
                func.distinct(Attempt.problem_id)
            ).label("problem_count"),
        )
        .join(
            Diagnosis,
            Diagnosis.primary_misconception_id
            == Misconception.id,
        )
        .join(Attempt, Attempt.id == Diagnosis.attempt_id)
        .filter(
            Diagnosis.state.in_(SUPPORTED_MISCONCEPTION_STATES)
        )
        .group_by(
            Misconception.id,
            Misconception.code,
            Misconception.name,
            Misconception.topic,
        )
        .order_by(func.count(Diagnosis.id).desc())
        .limit(limit)
        .all()
    )

    items = [
        MisconceptionAnalyticsItem(
            misconception_id=row.id,
            code=row.code,
            name=row.name,
            topic=row.topic,
            detection_count=row.detection_count,
            percentage_of_diagnoses=round(
                _safe_ratio(
                    row.detection_count,
                    total_misconception_diagnoses,
                )
                * 100,
                2,
            ),
            average_confidence=_optional_float(
                row.average_confidence
            ),
            affected_student_count=row.student_count,
            affected_problem_count=row.problem_count,
        )
        for row in rows
    ]

    return MisconceptionAnalyticsResponse(
        total_diagnoses=total_diagnoses,
        total_misconception_diagnoses=(
            total_misconception_diagnoses
        ),
        items=items,
    )


def _get_attempts_over_time(
    db: Session,
    *,
    start_date: date,
    days: int,
) -> list[AttemptsOverTimeItem]:
    attempt_rows = (
        db.query(
            cast(Attempt.created_at, Date).label("activity_date"),
            func.count(Attempt.id).label("attempt_count"),
        )
        .filter(Attempt.created_at >= datetime.combine(
            start_date,
            time.min,
        ))
        .group_by(cast(Attempt.created_at, Date))
        .all()
    )

    diagnosis_rows = (
        db.query(
            cast(Diagnosis.created_at, Date).label("activity_date"),
            func.count(Diagnosis.id).label("diagnosis_count"),
            func.count(
                Diagnosis.id
            ).filter(
                Diagnosis.state
                == DiagnosisState.NO_MISCONCEPTION.value
            ).label("verified_count"),
            func.count(
                Diagnosis.id
            ).filter(
                Diagnosis.state.in_(
                    SUPPORTED_MISCONCEPTION_STATES
                )
            ).label("misconception_count"),
        )
        .filter(Diagnosis.created_at >= datetime.combine(
            start_date,
            time.min,
        ))
        .group_by(cast(Diagnosis.created_at, Date))
        .all()
    )

    attempts_by_date = {
        row.activity_date: row.attempt_count
        for row in attempt_rows
    }

    diagnoses_by_date = {
        row.activity_date: (
            row.diagnosis_count,
            row.verified_count,
            row.misconception_count,
        )
        for row in diagnosis_rows
    }

    items: list[AttemptsOverTimeItem] = []

    for offset in range(days):
        current_date = start_date + timedelta(days=offset)
        diagnosis_counts = diagnoses_by_date.get(
            current_date,
            (0, 0, 0),
        )

        items.append(
            AttemptsOverTimeItem(
                date=datetime.combine(current_date, time.min),
                attempt_count=attempts_by_date.get(
                    current_date,
                    0,
                ),
                diagnosis_count=diagnosis_counts[0],
                verified_count=diagnosis_counts[1],
                misconception_count=diagnosis_counts[2],
            )
        )

    return items


def _diagnosis_response(
    db: Session,
    diagnosis: Diagnosis,
) -> DiagnosisResponse:
    primary_misconception = None

    if diagnosis.primary_misconception_id is not None:
        misconception = (
            db.query(Misconception)
            .filter(
                Misconception.id
                == diagnosis.primary_misconception_id
            )
            .first()
        )

        if misconception is not None:
            primary_misconception = _misconception_summary(
                misconception
            )

    evidence_rows = (
        db.query(DiagnosisEvidence)
        .filter(DiagnosisEvidence.diagnosis_id == diagnosis.id)
        .order_by(
            DiagnosisEvidence.created_at.asc(),
            DiagnosisEvidence.id.asc(),
        )
        .all()
    )

    evidence = [
        DiagnosisEvidenceResponse(
            id=row.id,
            diagnosis_id=row.diagnosis_id,
            source=_evidence_source(row.evidence_type),
            strength=EvidenceStrength.MEDIUM,
            text=row.evidence_text,
            sort_order=index,
            metadata={
                "rule_id": row.rule_id,
                "persisted_evidence_type": row.evidence_type,
            },
        )
        for index, row in enumerate(evidence_rows)
    ]

    alternative_rows = (
        db.query(DiagnosisAlternative, Misconception)
        .join(
            Misconception,
            Misconception.id
            == DiagnosisAlternative.misconception_id,
        )
        .filter(
            DiagnosisAlternative.diagnosis_id == diagnosis.id
        )
        .order_by(
            DiagnosisAlternative.confidence.desc().nullslast(),
            DiagnosisAlternative.created_at.asc(),
        )
        .all()
    )

    alternatives = [
        DiagnosisAlternativeResponse(
            id=alternative.id,
            diagnosis_id=alternative.diagnosis_id,
            misconception=_misconception_summary(
                misconception
            ),
            confidence=alternative.confidence or 0.0,
            reason=alternative.reason,
        )
        for alternative, misconception in alternative_rows
    ]

    return DiagnosisResponse(
        id=diagnosis.id,
        attempt_id=diagnosis.attempt_id,
        state=_diagnosis_state(diagnosis.state),
        confidence=diagnosis.confidence or 0.0,
        primary_misconception=primary_misconception,
        evidence=evidence,
        alternatives=alternatives,
        model_version=diagnosis.model_version,
        decision_reason=diagnosis.decision_reason,
        next_action=_next_action(diagnosis.next_action),
        created_at=diagnosis.created_at,
    )


def _problem_detail(
    db: Session,
    problem: Problem,
) -> ProblemDetail:
    misconception_rows = (
        db.query(Misconception)
        .join(
            ProblemMisconception,
            ProblemMisconception.misconception_id
            == Misconception.id,
        )
        .filter(
            ProblemMisconception.problem_id == problem.id
        )
        .order_by(Misconception.code.asc())
        .all()
    )

    supported_misconceptions = [
        SupportedMisconception(
            id=misconception.id,
            code=misconception.code,
            name=misconception.name,
            description=misconception.description,
            topic=misconception.topic,
            active=misconception.active,
        )
        for misconception in misconception_rows
    ]

    return ProblemDetail(
        id=problem.id,
        code=problem.code,
        title=problem.title,
        topic=problem.topic,
        statement=problem.statement,
        difficulty=problem.difficulty,
        expected_language=problem.expected_language,
        rule_context=problem.rule_context,
        active=problem.active,
        supported_misconceptions=supported_misconceptions,
        created_at=problem.created_at,
    )


def _attempt_summary(attempt: Attempt) -> AttemptSummary:
    return AttemptSummary.model_validate(attempt)


def _student_summary(
    student: StudentAlias,
) -> StudentAliasSummary:
    return StudentAliasSummary.model_validate(student)


def _problem_list_item(problem: Problem) -> ProblemListItem:
    return ProblemListItem.model_validate(problem)


def _diagnosis_summary(
    diagnosis: Diagnosis,
) -> DiagnosisSummary:
    return DiagnosisSummary(
        id=diagnosis.id,
        attempt_id=diagnosis.attempt_id,
        state=_diagnosis_state(diagnosis.state),
        confidence=diagnosis.confidence or 0.0,
        primary_misconception_id=(
            diagnosis.primary_misconception_id
        ),
        model_version=diagnosis.model_version,
        next_action=_next_action(diagnosis.next_action),
        created_at=diagnosis.created_at,
    )


def _misconception_summary(
    misconception: Misconception,
) -> MisconceptionSummary:
    return MisconceptionSummary(
        id=misconception.id,
        code=misconception.code,
        name=misconception.name,
        topic=misconception.topic,
    )


def _diagnosis_state(value: str) -> DiagnosisState:
    try:
        return DiagnosisState(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unsupported diagnosis state stored in database: {value}",
        ) from exc


def _next_action(value: str | None) -> DiagnosisNextAction:
    normalized = value or DiagnosisNextAction.NO_ACTION.value

    try:
        return DiagnosisNextAction(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Unsupported diagnosis next action stored in database: "
                f"{normalized}"
            ),
        ) from exc


def _evidence_source(value: str) -> EvidenceSource:
    aliases = {
        "text": EvidenceSource.WRITTEN_REASONING,
        "code": EvidenceSource.SOURCE_CODE,
        "input": EvidenceSource.PROBLEM,
        "speech": EvidenceSource.SPEECH_TRANSCRIPT,
        "test": EvidenceSource.RULE_ENGINE,
    }

    normalized = value.strip().lower()

    if normalized in aliases:
        return aliases[normalized]

    try:
        return EvidenceSource(normalized)
    except ValueError:
        return EvidenceSource.RULE_ENGINE


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0

    return round(numerator / denominator, 4)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None

    return round(float(value), 4)


def _normalize_pagination(
    page: int,
    page_size: int,
) -> tuple[int, int]:
    normalized_page = max(page, 1)
    normalized_page_size = max(1, min(page_size, 100))
    return normalized_page, normalized_page_size