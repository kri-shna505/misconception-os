from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.student_schema import StudentSessionCreate, StudentSessionResponse
from app.services.student_service import StudentService

router = APIRouter(prefix="/student", tags=["Student"])


@router.post(
    "/session",
    response_model=StudentSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_student_session(
    payload: StudentSessionCreate,
    db: Session = Depends(get_db),
):
    try:
        student = StudentService.create_session(db, payload)
        return {
            "student_alias_id": student.id,
            "alias": student.alias,
            "pseudonymous_id": student.pseudonymous_id,
            "consent_status": student.consent_status,
            "created_at": student.created_at,
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc