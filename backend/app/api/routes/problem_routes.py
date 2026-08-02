from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.problem_schema import ProblemDetail, ProblemListItem
from app.services.problem_service import ProblemService


router = APIRouter(
    prefix="/problems",
    tags=["Problems"],
)


@router.get(
    "",
    response_model=list[ProblemListItem],
    status_code=status.HTTP_200_OK,
    summary="List active problems",
    description=(
        "Return all active problems available in the student problem bank."
    ),
    response_description="Collection of active problem summaries.",
)
def list_problems(
    db: Session = Depends(get_db),
) -> list[ProblemListItem]:
    return ProblemService.list_active_problems(db)


@router.get(
    "/{problem_id}",
    response_model=ProblemDetail,
    status_code=status.HTTP_200_OK,
    summary="Get problem details",
    description=(
        "Return one problem with its statement, rule context, active status, "
        "expected language, and supported misconception mappings."
    ),
    response_description="Complete problem details.",
)
def get_problem_detail(
    problem_id: UUID,
    db: Session = Depends(get_db),
) -> ProblemDetail:
    problem = ProblemService.get_problem_detail(
        db,
        problem_id,
    )

    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found.",
        )

    return problem