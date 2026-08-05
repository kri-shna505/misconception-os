from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentTeacher
from app.core.database import get_db
from app.schemas.auth import AuthenticationErrorResponse
from app.schemas.teacher_review import (
    TeacherReviewAcceptRequest,
    TeacherReviewDetailResponse,
    TeacherReviewDraftRequest,
    TeacherReviewFinalizeRequest,
    TeacherReviewMessageResponse,
    TeacherReviewOverrideRequest,
    TeacherReviewQueueResponse,
)
from app.services.teacher_review_service import (
    AttemptNotFoundError,
    DiagnosisNotFoundError,
    InvalidReviewStateError,
    MisconceptionNotFoundError,
    ReviewAlreadyFinalizedError,
    ReviewNotFoundError,
    TeacherReviewPersistenceError,
    accept_system_diagnosis,
    finalize_review,
    get_review_detail,
    list_review_queue,
    override_system_diagnosis,
    reopen_review,
    save_review_draft,
)


router = APIRouter(
    prefix="/teacher/reviews",
    tags=["Teacher Reviews"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]

ReviewStatusQuery = Literal[
    "pending",
    "in_review",
    "reviewed",
]


def _not_found_exception(
    detail: str,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=detail,
    )


def _conflict_exception(
    detail: str,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
    )


def _bad_request_exception(
    detail: str,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )


def _persistence_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Teacher review data could not be saved. "
            "Please try again."
        ),
    )


def _raise_service_exception(
    error: Exception,
) -> None:
    """
    Convert teacher-review service exceptions into API responses.
    """

    if isinstance(
        error,
        AttemptNotFoundError,
    ):
        raise _not_found_exception(
            str(error)
        ) from error

    if isinstance(
        error,
        DiagnosisNotFoundError,
    ):
        raise _not_found_exception(
            str(error)
        ) from error

    if isinstance(
        error,
        ReviewNotFoundError,
    ):
        raise _not_found_exception(
            str(error)
        ) from error

    if isinstance(
        error,
        MisconceptionNotFoundError,
    ):
        raise _not_found_exception(
            str(error)
        ) from error

    if isinstance(
        error,
        ReviewAlreadyFinalizedError,
    ):
        raise _conflict_exception(
            str(error)
        ) from error

    if isinstance(
        error,
        InvalidReviewStateError,
    ):
        raise _bad_request_exception(
            str(error)
        ) from error

    if isinstance(
        error,
        TeacherReviewPersistenceError,
    ):
        raise _persistence_exception() from error

    raise error


@router.get(
    "",
    response_model=TeacherReviewQueueResponse,
    status_code=status.HTTP_200_OK,
    summary="List teacher review queue",
    description=(
        "Return a paginated queue of student attempts for teacher review. "
        "Attempts without a saved teacher-review row are treated as pending."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": AuthenticationErrorResponse,
            "description": (
                "A valid teacher Bearer token is required."
            ),
        },
        status.HTTP_403_FORBIDDEN: {
            "model": AuthenticationErrorResponse,
            "description": (
                "Teacher or administrator access is required."
            ),
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": (
                "Pagination or review-status filters are invalid."
            ),
        },
    },
)
def get_review_queue(
    current_teacher: CurrentTeacher,
    db: DatabaseSession,
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    review_status: ReviewStatusQuery | None = Query(
        default=None,
        description=(
            "Filter by pending, in_review, or reviewed status."
        ),
    ),
) -> TeacherReviewQueueResponse:
    """
    Return the protected teacher-review queue.
    """

    del current_teacher

    try:
        return list_review_queue(
            db=db,
            page=page,
            page_size=page_size,
            review_status=review_status,
        )

    except Exception as error:
        _raise_service_exception(error)
        raise


@router.get(
    "/{attempt_id}",
    response_model=TeacherReviewDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get teacher review detail",
    description=(
        "Return the attempt context, pseudonymous student, problem, "
        "latest system diagnosis, and existing teacher review."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": AuthenticationErrorResponse,
            "description": (
                "A valid teacher Bearer token is required."
            ),
        },
        status.HTTP_403_FORBIDDEN: {
            "model": AuthenticationErrorResponse,
            "description": (
                "Teacher or administrator access is required."
            ),
        },
        status.HTTP_404_NOT_FOUND: {
            "description": (
                "The requested student attempt was not found."
            ),
        },
    },
)
def get_teacher_review_detail(
    attempt_id: uuid.UUID,
    current_teacher: CurrentTeacher,
    db: DatabaseSession,
) -> TeacherReviewDetailResponse:
    """
    Retrieve one reviewable attempt and its current review state.
    """

    del current_teacher

    try:
        return get_review_detail(
            db=db,
            attempt_id=attempt_id,
        )

    except Exception as error:
        _raise_service_exception(error)
        raise


@router.put(
    "/{attempt_id}/draft",
    response_model=TeacherReviewMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Save teacher review draft",
    description=(
        "Create or update a pending or in-review teacher-review draft "
        "without finalizing it."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": AuthenticationErrorResponse,
            "description": (
                "A valid teacher Bearer token is required."
            ),
        },
        status.HTTP_403_FORBIDDEN: {
            "model": AuthenticationErrorResponse,
            "description": (
                "Teacher or administrator access is required."
            ),
        },
        status.HTTP_404_NOT_FOUND: {
            "description": (
                "The attempt or selected misconception was not found."
            ),
        },
        status.HTTP_409_CONFLICT: {
            "description": (
                "The review has already been finalized."
            ),
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": (
                "The review draft could not be saved."
            ),
        },
    },
)
def save_teacher_review_draft(
    attempt_id: uuid.UUID,
    payload: TeacherReviewDraftRequest,
    current_teacher: CurrentTeacher,
    db: DatabaseSession,
) -> TeacherReviewMessageResponse:
    """
    Save editable teacher-review fields as a draft.
    """

    try:
        return save_review_draft(
            db=db,
            attempt_id=attempt_id,
            teacher=current_teacher,
            payload=payload,
        )

    except Exception as error:
        _raise_service_exception(error)
        raise


@router.post(
    "/{attempt_id}/accept",
    response_model=TeacherReviewMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept system diagnosis",
    description=(
        "Copy the latest system diagnosis into an editable teacher-review "
        "draft and mark the decision as accepted."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": AuthenticationErrorResponse,
            "description": (
                "A valid teacher Bearer token is required."
            ),
        },
        status.HTTP_403_FORBIDDEN: {
            "model": AuthenticationErrorResponse,
            "description": (
                "Teacher or administrator access is required."
            ),
        },
        status.HTTP_404_NOT_FOUND: {
            "description": (
                "The attempt or latest system diagnosis was not found."
            ),
        },
        status.HTTP_409_CONFLICT: {
            "description": (
                "The review has already been finalized."
            ),
        },
    },
)
def accept_teacher_system_diagnosis(
    attempt_id: uuid.UUID,
    payload: TeacherReviewAcceptRequest,
    current_teacher: CurrentTeacher,
    db: DatabaseSession,
) -> TeacherReviewMessageResponse:
    """
    Accept the latest system diagnosis as a teacher-review draft.
    """

    try:
        return accept_system_diagnosis(
            db=db,
            attempt_id=attempt_id,
            teacher=current_teacher,
            payload=payload,
        )

    except Exception as error:
        _raise_service_exception(error)
        raise


@router.post(
    "/{attempt_id}/override",
    response_model=TeacherReviewMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Override system diagnosis",
    description=(
        "Save a teacher-selected diagnosis state and misconception as "
        "an editable override draft."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": AuthenticationErrorResponse,
            "description": (
                "A valid teacher Bearer token is required."
            ),
        },
        status.HTTP_403_FORBIDDEN: {
            "model": AuthenticationErrorResponse,
            "description": (
                "Teacher or administrator access is required."
            ),
        },
        status.HTTP_404_NOT_FOUND: {
            "description": (
                "The attempt or selected misconception was not found."
            ),
        },
        status.HTTP_409_CONFLICT: {
            "description": (
                "The review has already been finalized."
            ),
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": (
                "The override decision is inconsistent."
            ),
        },
    },
)
def override_teacher_system_diagnosis(
    attempt_id: uuid.UUID,
    payload: TeacherReviewOverrideRequest,
    current_teacher: CurrentTeacher,
    db: DatabaseSession,
) -> TeacherReviewMessageResponse:
    """
    Save an editable teacher-selected diagnosis override.
    """

    try:
        return override_system_diagnosis(
            db=db,
            attempt_id=attempt_id,
            teacher=current_teacher,
            payload=payload,
        )

    except Exception as error:
        _raise_service_exception(error)
        raise


@router.post(
    "/{attempt_id}/finalize",
    response_model=TeacherReviewMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Finalize teacher review",
    description=(
        "Finalize an accepted or overridden teacher review and store "
        "the reviewed timestamp."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": AuthenticationErrorResponse,
            "description": (
                "A valid teacher Bearer token is required."
            ),
        },
        status.HTTP_403_FORBIDDEN: {
            "model": AuthenticationErrorResponse,
            "description": (
                "Teacher or administrator access is required."
            ),
        },
        status.HTTP_404_NOT_FOUND: {
            "description": (
                "The attempt, diagnosis, or selected misconception "
                "was not found."
            ),
        },
        status.HTTP_409_CONFLICT: {
            "description": (
                "The review has already been finalized."
            ),
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": (
                "The final review decision is inconsistent."
            ),
        },
    },
)
def finalize_teacher_review(
    attempt_id: uuid.UUID,
    payload: TeacherReviewFinalizeRequest,
    current_teacher: CurrentTeacher,
    db: DatabaseSession,
) -> TeacherReviewMessageResponse:
    """
    Finalize a teacher-reviewed diagnosis.
    """

    try:
        return finalize_review(
            db=db,
            attempt_id=attempt_id,
            teacher=current_teacher,
            payload=payload,
        )

    except Exception as error:
        _raise_service_exception(error)
        raise


@router.post(
    "/{attempt_id}/reopen",
    response_model=TeacherReviewMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reopen finalized review",
    description=(
        "Move a finalized teacher review back to in-review status."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": AuthenticationErrorResponse,
            "description": (
                "A valid teacher Bearer token is required."
            ),
        },
        status.HTTP_403_FORBIDDEN: {
            "model": AuthenticationErrorResponse,
            "description": (
                "Teacher or administrator access is required."
            ),
        },
        status.HTTP_404_NOT_FOUND: {
            "description": (
                "The teacher review was not found."
            ),
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": (
                "Only finalized reviews can be reopened."
            ),
        },
    },
)
def reopen_teacher_review(
    attempt_id: uuid.UUID,
    current_teacher: CurrentTeacher,
    db: DatabaseSession,
) -> TeacherReviewMessageResponse:
    """
    Reopen a finalized review for editing.
    """

    try:
        return reopen_review(
            db=db,
            attempt_id=attempt_id,
            teacher=current_teacher,
        )

    except Exception as error:
        _raise_service_exception(error)
        raise