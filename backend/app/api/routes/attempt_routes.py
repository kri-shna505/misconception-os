from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.attempt import AttemptCreate, AttemptResponse
from app.services.attempt_service import (
    create_attempt,
    get_attempt_by_id,
)


router = APIRouter(
    prefix="/attempts",
    tags=["Attempts"],
)


@router.post(
    "",
    response_model=AttemptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit student attempt",
    description=(
        "Create and persist a student attempt containing the final answer, "
        "written reasoning, optional source code, optional speech transcript, "
        "selected language, and response time."
    ),
    response_description="The saved student attempt.",
)
def submit_attempt(
    payload: AttemptCreate,
    db: Session = Depends(get_db),
) -> AttemptResponse:
    """
    Save a new student attempt.

    Validation of the student alias, consent status, problem availability,
    and attempt contents is handled by the attempt service.
    """

    return create_attempt(
        db=db,
        payload=payload,
    )


@router.get(
    "/{attempt_id}",
    response_model=AttemptResponse,
    status_code=status.HTTP_200_OK,
    summary="Get attempt by ID",
    description=(
        "Retrieve one saved student attempt by its UUID. "
        "A 404 response is returned when the attempt does not exist."
    ),
    response_description="The requested student attempt.",
)
def get_attempt(
    attempt_id: UUID,
    db: Session = Depends(get_db),
) -> AttemptResponse:
    """
    Retrieve a single saved attempt.

    This endpoint supports the existing student workflow and may also be
    reused internally by teacher-facing review services.
    """

    return get_attempt_by_id(
        db=db,
        attempt_id=attempt_id,
    )