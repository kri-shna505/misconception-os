from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
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
    summary="Create diagnosis from saved attempt",
    description=(
        "Generate a rule-based diagnosis for a previously saved student "
        "attempt. The service extracts observable evidence, evaluates the "
        "misconception rules configured for the problem, persists the "
        "diagnosis, and returns the complete diagnosis result."
    ),
    response_description=(
        "The generated diagnosis, including state, confidence, evidence, "
        "primary misconception, alternatives, decision reason, and next action."
    ),
)
def create_diagnosis_from_saved_attempt(
    attempt_id: UUID,
    db: Session = Depends(get_db),
) -> DiagnosisResponse:
    """
    Generate a diagnosis from an existing attempt.

    The diagnosis service is responsible for:

    - validating that the attempt exists;
    - loading the problem and supported misconception rules;
    - extracting evidence from the problem, reasoning, and source code;
    - detecting a supported misconception or a verified no-misconception state;
    - persisting diagnosis evidence and alternatives;
    - avoiding duplicate diagnosis records for the same attempt.
    """

    return create_diagnosis_from_attempt(
        db=db,
        attempt_id=attempt_id,
    )