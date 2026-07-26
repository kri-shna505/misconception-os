from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.problem_schema import ProblemDetail, ProblemListItem
from app.services.problem_service import ProblemService

router = APIRouter(prefix="/problems", tags=["Problems"])


@router.get("", response_model=list[ProblemListItem])
def list_problems(db: Session = Depends(get_db)):
    return ProblemService.list_active_problems(db)


@router.get("/{problem_id}", response_model=ProblemDetail)
def get_problem_detail(
    problem_id: UUID,
    db: Session = Depends(get_db),
):
    problem = ProblemService.get_problem_detail(db, problem_id)

    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found.",
        )

    return problem