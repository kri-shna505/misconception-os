from __future__ import annotations

import math
import uuid
from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.models.diagnosis import Diagnosis
from app.models.misconception import Misconception
from app.models.problem import Problem
from app.models.student_alias import StudentAlias
from app.models.teacher_review import TeacherReview
from app.models.user import User
from app.schemas.teacher_review import (
    TeacherReviewAcceptRequest,
    TeacherReviewAttemptDetail,
    TeacherReviewAttemptSummary,
    TeacherReviewDetailResponse,
    TeacherReviewDiagnosisSummary,
    TeacherReviewDraftRequest,
    TeacherReviewFinalizeRequest,
    TeacherReviewMessageResponse,
    TeacherReviewOverrideRequest,
    TeacherReviewPaginationMeta,
    TeacherReviewProblemSummary,
    TeacherReviewQueueItem,
    TeacherReviewQueueResponse,
    TeacherReviewResponse,
    TeacherReviewStudentSummary,
)


ReviewStatusFilter = Literal[
    "pending",
    "in_review",
    "reviewed",
]


class TeacherReviewServiceError(RuntimeError):
    """
    Base exception for teacher-review workflow failures.
    """


class AttemptNotFoundError(
    TeacherReviewServiceError
):
    """
    Raised when the requested student attempt does not exist.
    """


class DiagnosisNotFoundError(
    TeacherReviewServiceError
):
    """
    Raised when an action requires a system diagnosis but none exists.
    """


class ReviewNotFoundError(
    TeacherReviewServiceError
):
    """
    Raised when a teacher review does not exist.
    """


class ReviewAlreadyFinalizedError(
    TeacherReviewServiceError
):
    """
    Raised when a finalized review is modified without reopening it.
    """


class InvalidReviewStateError(
    TeacherReviewServiceError
):
    """
    Raised when review fields contain an inconsistent decision.
    """


class MisconceptionNotFoundError(
    TeacherReviewServiceError
):
    """
    Raised when the selected misconception does not exist or is inactive.
    """


class TeacherReviewPersistenceError(
    TeacherReviewServiceError
):
    """
    Raised when a teacher-review database operation fails.
    """


def _normalize_optional_text(
    value: str | None,
) -> str | None:
    """
    Normalize optional teacher-entered text.

    Empty or whitespace-only text is persisted as NULL.
    """

    if value is None:
        return None

    normalized = value.strip()

    return normalized or None


def _get_attempt(
    db: Session,
    attempt_id: uuid.UUID,
) -> Attempt:
    """
    Return an attempt or raise a service exception.
    """

    attempt = db.get(
        Attempt,
        attempt_id,
    )

    if attempt is None:
        raise AttemptNotFoundError(
            "Student attempt was not found."
        )

    return attempt


def _get_attempt_context(
    db: Session,
    attempt_id: uuid.UUID,
) -> tuple[
    Attempt,
    StudentAlias,
    Problem,
]:
    """
    Load the attempt, pseudonymous student, and problem.
    """

    statement = (
        select(
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
        .where(
            Attempt.id == attempt_id
        )
    )

    row = db.execute(
        statement
    ).first()

    if row is None:
        raise AttemptNotFoundError(
            "Student attempt was not found."
        )

    attempt, student, problem = row

    return (
        attempt,
        student,
        problem,
    )


def _get_latest_diagnosis(
    db: Session,
    attempt_id: uuid.UUID,
) -> Diagnosis | None:
    """
    Return the latest saved diagnosis for an attempt.

    The diagnoses table does not enforce one diagnosis per attempt,
    so the service deliberately selects the newest record.
    """

    statement = (
        select(Diagnosis)
        .where(
            Diagnosis.attempt_id
            == attempt_id
        )
        .order_by(
            Diagnosis.created_at.desc(),
            Diagnosis.id.desc(),
        )
        .limit(1)
    )

    return db.scalar(statement)


def _get_review(
    db: Session,
    attempt_id: uuid.UUID,
) -> TeacherReview | None:
    """
    Return the review associated with an attempt.
    """

    statement = select(
        TeacherReview
    ).where(
        TeacherReview.attempt_id
        == attempt_id
    )

    return db.scalar(statement)


def _require_review(
    db: Session,
    attempt_id: uuid.UUID,
) -> TeacherReview:
    """
    Return an existing review or raise an exception.
    """

    review = _get_review(
        db=db,
        attempt_id=attempt_id,
    )

    if review is None:
        raise ReviewNotFoundError(
            "Teacher review was not found."
        )

    return review


def _get_or_create_review(
    db: Session,
    *,
    attempt: Attempt,
    teacher: User,
    diagnosis: Diagnosis | None,
) -> TeacherReview:
    """
    Return the attempt review, creating a pending review if necessary.
    """

    existing_review = _get_review(
        db=db,
        attempt_id=attempt.id,
    )

    if existing_review is not None:
        return existing_review

    review = TeacherReview(
        attempt_id=attempt.id,
        teacher_id=teacher.id,
        system_diagnosis_id=(
            diagnosis.id
            if diagnosis is not None
            else None
        ),
        status="pending",
    )

    try:
        db.add(review)
        db.flush()

        return review

    except IntegrityError:
        db.rollback()

        concurrent_review = _get_review(
            db=db,
            attempt_id=attempt.id,
        )

        if concurrent_review is not None:
            return concurrent_review

        raise TeacherReviewPersistenceError(
            "Teacher review could not be created."
        )

    except SQLAlchemyError as error:
        db.rollback()

        raise TeacherReviewPersistenceError(
            "Teacher review could not be created."
        ) from error


def _require_editable_review(
    review: TeacherReview,
) -> None:
    """
    Reject modifications to finalized reviews.
    """

    if review.status == "reviewed":
        raise ReviewAlreadyFinalizedError(
            "This teacher review has already been finalized."
        )


def _get_active_misconception(
    db: Session,
    misconception_id: uuid.UUID,
) -> Misconception:
    """
    Return an active misconception selected by the teacher.
    """

    statement = select(
        Misconception
    ).where(
        Misconception.id
        == misconception_id,
        Misconception.active.is_(True),
    )

    misconception = db.scalar(
        statement
    )

    if misconception is None:
        raise MisconceptionNotFoundError(
            "Selected misconception was not found or is inactive."
        )

    return misconception


def _validate_final_outcome(
    db: Session,
    *,
    final_state: str,
    final_misconception_id: (
        uuid.UUID | None
    ),
) -> None:
    """
    Validate final-state and misconception consistency.
    """

    misconception_states = {
        "confident",
        "possible",
    }

    non_misconception_states = {
        "insufficient",
        "no_misconception",
    }

    if (
        final_state
        in misconception_states
        and final_misconception_id
        is None
    ):
        raise InvalidReviewStateError(
            "A final misconception is required for "
            "confident or possible outcomes."
        )

    if (
        final_state
        in non_misconception_states
        and final_misconception_id
        is not None
    ):
        raise InvalidReviewStateError(
            "A final misconception must not be selected for "
            "insufficient or no-misconception outcomes."
        )

    if final_misconception_id is not None:
        _get_active_misconception(
            db=db,
            misconception_id=(
                final_misconception_id
            ),
        )


def _commit_review(
    db: Session,
    review: TeacherReview,
) -> TeacherReview:
    """
    Persist and refresh a review safely.
    """

    try:
        db.add(review)
        db.commit()
        db.refresh(review)

        return review

    except SQLAlchemyError as error:
        db.rollback()

        raise TeacherReviewPersistenceError(
            "Teacher review could not be saved."
        ) from error


def _review_response(
    review: TeacherReview,
) -> TeacherReviewResponse:
    """
    Convert a persisted review into its API schema.
    """

    return TeacherReviewResponse.model_validate(
        review
    )


def _student_summary(
    student: StudentAlias,
) -> TeacherReviewStudentSummary:
    return TeacherReviewStudentSummary(
        id=student.id,
        alias=student.alias,
        pseudonymous_id=(
            student.pseudonymous_id
        ),
    )


def _problem_summary(
    problem: Problem,
) -> TeacherReviewProblemSummary:
    return TeacherReviewProblemSummary(
        id=problem.id,
        code=problem.code,
        title=problem.title,
        topic=problem.topic,
    )


def _attempt_summary(
    attempt: Attempt,
) -> TeacherReviewAttemptSummary:
    return TeacherReviewAttemptSummary(
        id=attempt.id,
        selected_language=(
            attempt.selected_language
        ),
        response_time_seconds=(
            attempt.response_time_seconds
        ),
        created_at=attempt.created_at,
    )


def _attempt_detail(
    attempt: Attempt,
) -> TeacherReviewAttemptDetail:
    """
    Convert a student attempt into the full detail schema.
    """

    return TeacherReviewAttemptDetail(
        id=attempt.id,
        final_answer=attempt.final_answer,
        written_reasoning=(
            attempt.written_reasoning
        ),
        source_code=attempt.source_code,
        speech_transcript=(
            attempt.speech_transcript
        ),
        selected_language=(
            attempt.selected_language
        ),
        response_time_seconds=(
            attempt.response_time_seconds
        ),
        created_at=attempt.created_at,
    )


def _diagnosis_summary(
    diagnosis: Diagnosis | None,
) -> TeacherReviewDiagnosisSummary | None:
    if diagnosis is None:
        return None

    return TeacherReviewDiagnosisSummary(
        id=diagnosis.id,
        state=diagnosis.state,
        confidence=diagnosis.confidence,
        primary_misconception_id=(
            diagnosis.primary_misconception_id
        ),
        model_version=(
            diagnosis.model_version
        ),
        next_action=diagnosis.next_action,
        created_at=diagnosis.created_at,
    )


def get_review_detail(
    db: Session,
    *,
    attempt_id: uuid.UUID,
) -> TeacherReviewDetailResponse:
    """
    Return the complete teacher-review context for one attempt.
    """

    (
        attempt,
        student,
        problem,
    ) = _get_attempt_context(
        db=db,
        attempt_id=attempt_id,
    )

    diagnosis = _get_latest_diagnosis(
        db=db,
        attempt_id=attempt.id,
    )

    review = _get_review(
        db=db,
        attempt_id=attempt.id,
    )

    return TeacherReviewDetailResponse(
        attempt_id=attempt.id,
        attempt=_attempt_detail(
            attempt
        ),
        student=_student_summary(
            student
        ),
        problem=_problem_summary(
            problem
        ),
        system_diagnosis=(
            _diagnosis_summary(
                diagnosis
            )
        ),
        review=(
            _review_response(review)
            if review is not None
            else None
        ),
    )


def list_review_queue(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    review_status: (
        ReviewStatusFilter | None
    ) = None,
) -> TeacherReviewQueueResponse:
    """
    Return a paginated teacher-review queue.

    Attempts with no TeacherReview row are treated as pending.
    """

    if page < 1:
        raise InvalidReviewStateError(
            "Page must be greater than or equal to 1."
        )

    if page_size < 1 or page_size > 100:
        raise InvalidReviewStateError(
            "Page size must be between 1 and 100."
        )

    filters = []

    if review_status == "pending":
        filters.append(
            or_(
                TeacherReview.id.is_(None),
                TeacherReview.status
                == "pending",
            )
        )

    elif review_status in {
        "in_review",
        "reviewed",
    }:
        filters.append(
            TeacherReview.status
            == review_status
        )

    base_statement = (
        select(
            Attempt,
            StudentAlias,
            Problem,
            TeacherReview,
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
        .outerjoin(
            TeacherReview,
            TeacherReview.attempt_id
            == Attempt.id,
        )
    )

    count_statement = (
        select(
            func.count(Attempt.id)
        )
        .outerjoin(
            TeacherReview,
            TeacherReview.attempt_id
            == Attempt.id,
        )
    )

    if filters:
        base_statement = (
            base_statement.where(
                *filters
            )
        )

        count_statement = (
            count_statement.where(
                *filters
            )
        )

    total_items = (
        db.scalar(count_statement)
        or 0
    )

    total_pages = (
        math.ceil(
            total_items / page_size
        )
        if total_items > 0
        else 0
    )

    offset = (
        page - 1
    ) * page_size

    rows = db.execute(
        base_statement
        .order_by(
            Attempt.created_at.desc(),
            Attempt.id.desc(),
        )
        .offset(offset)
        .limit(page_size)
    ).all()

    items: list[
        TeacherReviewQueueItem
    ] = []

    for (
        attempt,
        student,
        problem,
        review,
    ) in rows:
        diagnosis = _get_latest_diagnosis(
            db=db,
            attempt_id=attempt.id,
        )

        items.append(
            TeacherReviewQueueItem(
                attempt=_attempt_summary(
                    attempt
                ),
                student=_student_summary(
                    student
                ),
                problem=_problem_summary(
                    problem
                ),
                system_diagnosis=(
                    _diagnosis_summary(
                        diagnosis
                    )
                ),
                review=(
                    _review_response(
                        review
                    )
                    if review is not None
                    else None
                ),
            )
        )

    return TeacherReviewQueueResponse(
        items=items,
        pagination=(
            TeacherReviewPaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=total_pages,
                has_previous=page > 1,
                has_next=(
                    total_pages > 0
                    and page < total_pages
                ),
            )
        ),
    )


def save_review_draft(
    db: Session,
    *,
    attempt_id: uuid.UUID,
    teacher: User,
    payload: TeacherReviewDraftRequest,
) -> TeacherReviewMessageResponse:
    """
    Create or update a non-finalized teacher-review draft.
    """

    attempt = _get_attempt(
        db=db,
        attempt_id=attempt_id,
    )

    diagnosis = _get_latest_diagnosis(
        db=db,
        attempt_id=attempt.id,
    )

    review = _get_or_create_review(
        db=db,
        attempt=attempt,
        teacher=teacher,
        diagnosis=diagnosis,
    )

    _require_editable_review(
        review
    )

    if (
        payload.final_state
        is not None
    ):
        _validate_final_outcome(
            db=db,
            final_state=(
                payload.final_state
            ),
            final_misconception_id=(
                payload.final_misconception_id
            ),
        )

    review.teacher_id = teacher.id
    review.system_diagnosis_id = (
        diagnosis.id
        if diagnosis is not None
        else None
    )
    review.status = payload.status
    review.decision = payload.decision
    review.final_state = (
        payload.final_state
    )
    review.final_misconception_id = (
        payload.final_misconception_id
    )
    review.override_reason = (
        _normalize_optional_text(
            payload.override_reason
        )
    )
    review.teacher_note = (
        _normalize_optional_text(
            payload.teacher_note
        )
    )
    review.reviewed_at = None

    saved_review = _commit_review(
        db=db,
        review=review,
    )

    return TeacherReviewMessageResponse(
        message="Teacher review draft saved.",
        review=_review_response(
            saved_review
        ),
    )


def accept_system_diagnosis(
    db: Session,
    *,
    attempt_id: uuid.UUID,
    teacher: User,
    payload: TeacherReviewAcceptRequest,
) -> TeacherReviewMessageResponse:
    """
    Save a draft that accepts the latest system diagnosis.
    """

    attempt = _get_attempt(
        db=db,
        attempt_id=attempt_id,
    )

    diagnosis = _get_latest_diagnosis(
        db=db,
        attempt_id=attempt.id,
    )

    if diagnosis is None:
        raise DiagnosisNotFoundError(
            "This attempt does not have a system diagnosis to accept."
        )

    _validate_final_outcome(
        db=db,
        final_state=diagnosis.state,
        final_misconception_id=(
            diagnosis.primary_misconception_id
        ),
    )

    review = _get_or_create_review(
        db=db,
        attempt=attempt,
        teacher=teacher,
        diagnosis=diagnosis,
    )

    _require_editable_review(
        review
    )

    review.teacher_id = teacher.id
    review.system_diagnosis_id = (
        diagnosis.id
    )
    review.status = "in_review"
    review.decision = "accepted"
    review.final_state = (
        diagnosis.state
    )
    review.final_misconception_id = (
        diagnosis.primary_misconception_id
    )
    review.override_reason = None
    review.teacher_note = (
        _normalize_optional_text(
            payload.teacher_note
        )
    )
    review.reviewed_at = None

    saved_review = _commit_review(
        db=db,
        review=review,
    )

    return TeacherReviewMessageResponse(
        message=(
            "System diagnosis accepted as a review draft."
        ),
        review=_review_response(
            saved_review
        ),
    )


def override_system_diagnosis(
    db: Session,
    *,
    attempt_id: uuid.UUID,
    teacher: User,
    payload: TeacherReviewOverrideRequest,
) -> TeacherReviewMessageResponse:
    """
    Save a teacher-selected diagnosis override as a draft.
    """

    attempt = _get_attempt(
        db=db,
        attempt_id=attempt_id,
    )

    diagnosis = _get_latest_diagnosis(
        db=db,
        attempt_id=attempt.id,
    )

    _validate_final_outcome(
        db=db,
        final_state=payload.final_state,
        final_misconception_id=(
            payload.final_misconception_id
        ),
    )

    review = _get_or_create_review(
        db=db,
        attempt=attempt,
        teacher=teacher,
        diagnosis=diagnosis,
    )

    _require_editable_review(
        review
    )

    review.teacher_id = teacher.id
    review.system_diagnosis_id = (
        diagnosis.id
        if diagnosis is not None
        else None
    )
    review.status = "in_review"
    review.decision = "overridden"
    review.final_state = (
        payload.final_state
    )
    review.final_misconception_id = (
        payload.final_misconception_id
    )
    review.override_reason = (
        _normalize_optional_text(
            payload.override_reason
        )
    )
    review.teacher_note = (
        _normalize_optional_text(
            payload.teacher_note
        )
    )
    review.reviewed_at = None

    saved_review = _commit_review(
        db=db,
        review=review,
    )

    return TeacherReviewMessageResponse(
        message=(
            "Teacher diagnosis override saved as a draft."
        ),
        review=_review_response(
            saved_review
        ),
    )


def finalize_review(
    db: Session,
    *,
    attempt_id: uuid.UUID,
    teacher: User,
    payload: TeacherReviewFinalizeRequest,
) -> TeacherReviewMessageResponse:
    """
    Finalize a teacher review.

    Accepted decisions must exactly match the latest system diagnosis.
    Overridden decisions must contain a valid teacher-selected result.
    """

    attempt = _get_attempt(
        db=db,
        attempt_id=attempt_id,
    )

    diagnosis = _get_latest_diagnosis(
        db=db,
        attempt_id=attempt.id,
    )

    if payload.decision == "accepted":
        if diagnosis is None:
            raise DiagnosisNotFoundError(
                "This attempt does not have a system diagnosis to accept."
            )

        if (
            payload.final_state
            != diagnosis.state
            or payload.final_misconception_id
            != diagnosis.primary_misconception_id
        ):
            raise InvalidReviewStateError(
                "An accepted review must match the latest system diagnosis."
            )

    _validate_final_outcome(
        db=db,
        final_state=payload.final_state,
        final_misconception_id=(
            payload.final_misconception_id
        ),
    )

    review = _get_or_create_review(
        db=db,
        attempt=attempt,
        teacher=teacher,
        diagnosis=diagnosis,
    )

    _require_editable_review(
        review
    )

    review.teacher_id = teacher.id
    review.system_diagnosis_id = (
        diagnosis.id
        if diagnosis is not None
        else None
    )
    review.decision = (
        payload.decision
    )
    review.final_state = (
        payload.final_state
    )
    review.final_misconception_id = (
        payload.final_misconception_id
    )
    review.override_reason = (
        _normalize_optional_text(
            payload.override_reason
        )
    )
    review.teacher_note = (
        _normalize_optional_text(
            payload.teacher_note
        )
    )

    review.finalize()

    saved_review = _commit_review(
        db=db,
        review=review,
    )

    return TeacherReviewMessageResponse(
        message="Teacher review finalized.",
        review=_review_response(
            saved_review
        ),
    )


def reopen_review(
    db: Session,
    *,
    attempt_id: uuid.UUID,
    teacher: User,
) -> TeacherReviewMessageResponse:
    """
    Reopen a finalized review for additional editing.
    """

    review = _require_review(
        db=db,
        attempt_id=attempt_id,
    )

    if review.status != "reviewed":
        raise InvalidReviewStateError(
            "Only a finalized review can be reopened."
        )

    review.teacher_id = teacher.id
    review.reopen()

    saved_review = _commit_review(
        db=db,
        review=review,
    )

    return TeacherReviewMessageResponse(
        message="Teacher review reopened.",
        review=_review_response(
            saved_review
        ),
    )