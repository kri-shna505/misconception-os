from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.models.problem import Problem
from app.models.student_alias import StudentAlias
from app.schemas.attempt import AttemptCreate


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()
    return cleaned if cleaned else None


def _clean_required_text(value: str) -> str:
    return value.strip()


def create_attempt(db: Session, payload: AttemptCreate) -> Attempt:
    student_alias = (
        db.query(StudentAlias)
        .filter(StudentAlias.id == payload.student_alias_id)
        .first()
    )

    if not student_alias:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student alias session not found.",
        )

    if not student_alias.consent_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student consent is required before submitting an attempt.",
        )

    problem = db.query(Problem).filter(Problem.id == payload.problem_id).first()

    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found.",
        )

    if not problem.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit an attempt for an inactive problem.",
        )

    written_reasoning = _clean_required_text(payload.written_reasoning)
    final_answer = _clean_optional_text(payload.final_answer)
    source_code = _clean_optional_text(payload.source_code)
    speech_transcript = _clean_optional_text(payload.speech_transcript)
    selected_language = payload.selected_language.strip().lower()

    if not selected_language:
        selected_language = "python"

    attempt = Attempt(
        student_alias_id=payload.student_alias_id,
        problem_id=payload.problem_id,
        final_answer=final_answer,
        written_reasoning=written_reasoning,
        source_code=source_code,
        speech_transcript=speech_transcript,
        selected_language=selected_language,
        response_time_seconds=payload.response_time_seconds,
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return attempt


def get_attempt_by_id(db: Session, attempt_id: UUID) -> Attempt:
    attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()

    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attempt not found.",
        )

    return attempt