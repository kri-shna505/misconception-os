from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.diagnosis import DiagnosisResponse
from app.services.diagnosis_service import create_diagnosis_from_attempt


router = APIRouter(
    prefix="/diagnoses",
    tags=["Diagnoses"],
)


@router.post(
    "/from-attempt/{attempt_id}",
    response_model=DiagnosisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Diagnosis From Attempt",
)
def create_diagnosis_from_saved_attempt(
    attempt_id: UUID,
    db: Session = Depends(get_db),
) -> DiagnosisResponse:
    """
    Create an evidence-backed rule diagnosis from an already saved attempt.

    Sprint 4 scope:
    - M1 Binary Search on Unsorted Data
    - M2 Missing or Incorrect Recursion Base Case
    - M3 Recursive Call Without Reducing Problem Size

    Important:
    This endpoint does not create an attempt.
    It only diagnoses an existing attempt.
    """
    return create_diagnosis_from_attempt(db=db, attempt_id=attempt_id)