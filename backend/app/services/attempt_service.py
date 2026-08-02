from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.models.problem import Problem
from app.models.student_alias import StudentAlias
from app.schemas.attempt import AttemptCreate


def _clean_optional_text(value: str | None) -> str | None:
    """
    Trim optional text while preserving internal whitespace and line breaks.

    Empty strings are stored as NULL instead of meaningless blank text.
    """

    if value is None:
        return None

    cleaned = value.strip()

    return cleaned or None


def _clean_required_text(value: str) -> str:
    """
    Trim required text and reject an empty result.
    """

    cleaned = value.strip()

    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Written reasoning cannot be empty.",
        )

    return cleaned


def _normalize_language(value: str | None) -> str:
    """
    Normalize programming-language values before persistence.
    """

    if not value:
        return "python"

    normalized = value.strip().lower()

    language_aliases = {
        "py": "python",
        "python3": "python",
        "python 3": "python",
        "c language": "c",
        "text / no code": "text",
        "text/no code": "text",
        "no code": "text",
    }

    return language_aliases.get(normalized, normalized) or "python"


def _get_student_alias(
    db: Session,
    student_alias_id: UUID,
) -> StudentAlias:
    student_alias = (
        db.query(StudentAlias)
        .filter(StudentAlias.id == student_alias_id)
        .first()
    )

    if student_alias is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student alias session not found.",
        )

    if not student_alias.consent_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student consent is required before submitting an attempt.",
        )

    return student_alias


def _get_active_problem(
    db: Session,
    problem_id: UUID,
) -> Problem:
    problem = (
        db.query(Problem)
        .filter(Problem.id == problem_id)
        .first()
    )

    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found.",
        )

    if not problem.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit an attempt for an inactive problem.",
        )

    return problem


def create_attempt(
    db: Session,
    payload: AttemptCreate,
) -> Attempt:
    """
    Validate and persist a student attempt.

    The attempt's answer, reasoning, source code, transcript, language, and
    response time are stored exactly once in a single transaction.
    """

    _get_student_alias(
        db=db,
        student_alias_id=payload.student_alias_id,
    )

    _get_active_problem(
        db=db,
        problem_id=payload.problem_id,
    )

    written_reasoning = _clean_required_text(
        payload.written_reasoning
    )

    final_answer = _clean_optional_text(
        payload.final_answer
    )

    source_code = _clean_optional_text(
        payload.source_code
    )

    speech_transcript = _clean_optional_text(
        payload.speech_transcript
    )

    selected_language = _normalize_language(
        payload.selected_language
    )

    if (
        final_answer is None
        and source_code is None
        and speech_transcript is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Attempt must include a final answer, source code, or speech "
                "transcript in addition to written reasoning."
            ),
        )

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

    try:
        db.add(attempt)

        # Send the INSERT to the database so generated values such as the UUID
        # become available before the final commit.
        db.flush()

        db.commit()
        db.refresh(attempt)

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save the student attempt.",
        ) from exc

    # Defensive integrity checks. A successful request must not silently lose
    # required reasoning or submitted source code.
    if not attempt.written_reasoning:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Attempt was saved without written reasoning.",
        )

    if source_code is not None and attempt.source_code != source_code:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Attempt source code was not persisted correctly.",
        )

    return attempt


def get_attempt_by_id(
    db: Session,
    attempt_id: UUID,
) -> Attempt:
    """
    Return a saved attempt with all answer fields available to diagnosis.
    """

    attempt = (
        db.query(Attempt)
        .filter(Attempt.id == attempt_id)
        .first()
    )

    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attempt not found.",
        )

    return attempt