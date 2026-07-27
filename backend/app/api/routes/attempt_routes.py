from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.attempt import AttemptCreate, AttemptResponse
from app.services.attempt_service import create_attempt, get_attempt_by_id

router = APIRouter(prefix="/attempts", tags=["Attempts"])


@router.post(
    "",
    response_model=AttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_attempt(payload: AttemptCreate, db: Session = Depends(get_db)):
    return create_attempt(db=db, payload=payload)


@router.get("/{attempt_id}", response_model=AttemptResponse)
def get_attempt(attempt_id: UUID, db: Session = Depends(get_db)):
    return get_attempt_by_id(db=db, attempt_id=attempt_id)