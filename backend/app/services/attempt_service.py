from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.models.problem import Problem
from app.models.student_alias import StudentAlias
from app.schemas.attempt import AttemptCreate


VALID_SPEECH_PROCESSING_STATUSES = {
    "not_provided",
    "pending",
    "processing",
    "completed",
    "failed",
}

VALID_INPUT_MODALITIES = {
    "text",
    "code",
    "speech",
    "text_code",
    "text_speech",
    "code_speech",
    "text_code_speech",
}


def _clean_optional_text(
    value: str | None,
) -> str | None:
    """
    Trim optional text while preserving internal whitespace and line breaks.

    Empty strings are stored as NULL instead of meaningless blank text.
    """

    if value is None:
        return None

    cleaned = value.strip()
    return cleaned or None


def _clean_required_text(
    value: str,
) -> str:
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


def _normalize_programming_language(
    value: str | None,
) -> str:
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

    return (
        language_aliases.get(
            normalized,
            normalized,
        )
        or "python"
    )


def _normalize_natural_language(
    value: str | None,
    *,
    default: str | None = None,
) -> str | None:
    """
    Normalize natural-language metadata.

    Sprint 10 currently recognizes English/Telugu aliases explicitly while
    preserving other normalized language names for future expansion.
    """

    if value is None:
        return default

    normalized = value.strip().lower()

    if not normalized:
        return default

    language_aliases = {
        "en": "english",
        "eng": "english",
        "te": "telugu",
        "tel": "telugu",
        "hi": "hindi",
        "hin": "hindi",
    }

    return language_aliases.get(
        normalized,
        normalized,
    )


def _normalize_input_modality(
    value: str | None,
) -> str:
    """
    Normalize and validate the attempt input modality.
    """

    if value is None:
        return "text"

    normalized = value.strip().lower().replace("-", "_")

    modality_aliases = {
        "text+code": "text_code",
        "text+speech": "text_speech",
        "code+speech": "code_speech",
        "text+code+speech": "text_code_speech",
    }

    normalized = modality_aliases.get(
        normalized,
        normalized,
    )

    if normalized not in VALID_INPUT_MODALITIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Invalid input modality. Expected one of: "
                + ", ".join(sorted(VALID_INPUT_MODALITIES))
                + "."
            ),
        )

    return normalized


def _normalize_speech_processing_status(
    value: str | None,
) -> str:
    """
    Normalize and validate speech-processing state.
    """

    if value is None:
        return "not_provided"

    normalized = value.strip().lower()

    if normalized not in VALID_SPEECH_PROCESSING_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Invalid speech processing status. Expected one of: "
                + ", ".join(sorted(VALID_SPEECH_PROCESSING_STATUSES))
                + "."
            ),
        )

    return normalized


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
            detail=(
                "Student consent is required before submitting an attempt."
            ),
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
            detail=(
                "Cannot submit an attempt for an inactive problem."
            ),
        )

    return problem


def _validate_multimodal_payload(
    *,
    final_answer: str | None,
    source_code: str | None,
    speech_transcript: str | None,
    speech_audio_reference: str | None,
    speech_audio_retained: bool,
    speech_processing_status: str,
    input_modality: str,
) -> None:
    """
    Apply defensive Sprint 10 multimodal integrity checks.

    Pydantic performs equivalent request validation, but service-level checks
    protect internal callers and future non-HTTP entry points.
    """

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

    if (
        speech_audio_retained
        and speech_audio_reference is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "speech_audio_reference is required when "
                "speech_audio_retained is true."
            ),
        )

    speech_present = (
        speech_transcript is not None
        or speech_audio_reference is not None
    )

    modality_has_speech = input_modality in {
        "speech",
        "text_speech",
        "code_speech",
        "text_code_speech",
    }

    if speech_present and not modality_has_speech:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "input_modality must include speech when speech input "
                "metadata is provided."
            ),
        )

    if (
        not speech_present
        and speech_processing_status
        in {
            "pending",
            "processing",
            "completed",
        }
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Active or completed speech processing requires speech input."
            ),
        )


def create_attempt(
    db: Session,
    payload: AttemptCreate,
) -> Attempt:
    """
    Validate and persist a student attempt.

    Sprint 10 persists multimodal/language metadata alongside the existing
    answer, reasoning, source-code, transcript, programming-language, and
    response-time fields in one transaction.
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

    normalized_reasoning = _clean_optional_text(
        payload.normalized_reasoning
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

    speech_audio_reference = _clean_optional_text(
        payload.speech_audio_reference
    )

    selected_language = _normalize_programming_language(
        payload.selected_language
    )

    input_language = (
        _normalize_natural_language(
            payload.input_language,
            default="english",
        )
        or "english"
    )

    detected_language = _normalize_natural_language(
        payload.detected_language,
        default=None,
    )

    input_modality = _normalize_input_modality(
        payload.input_modality
    )

    speech_processing_status = (
        _normalize_speech_processing_status(
            payload.speech_processing_status
        )
    )

    speech_audio_retained = bool(
        payload.speech_audio_retained
    )

    _validate_multimodal_payload(
        final_answer=final_answer,
        source_code=source_code,
        speech_transcript=speech_transcript,
        speech_audio_reference=speech_audio_reference,
        speech_audio_retained=speech_audio_retained,
        speech_processing_status=speech_processing_status,
        input_modality=input_modality,
    )

    attempt = Attempt(
        student_alias_id=payload.student_alias_id,
        problem_id=payload.problem_id,
        final_answer=final_answer,
        written_reasoning=written_reasoning,
        normalized_reasoning=normalized_reasoning,
        source_code=source_code,
        speech_transcript=speech_transcript,
        speech_audio_reference=speech_audio_reference,
        speech_audio_retained=speech_audio_retained,
        speech_processing_status=speech_processing_status,
        input_modality=input_modality,
        input_language=input_language,
        detected_language=detected_language,
        selected_language=selected_language,
        response_time_seconds=payload.response_time_seconds,
    )

    try:
        db.add(attempt)

        # Send the INSERT to the database so generated values such as the UUID
        # and timestamps become available before the final commit.
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
    # required reasoning, submitted source code, or Sprint 10 metadata.
    if not attempt.written_reasoning:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Attempt was saved without written reasoning.",
        )

    if (
        source_code is not None
        and attempt.source_code != source_code
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Attempt source code was not persisted correctly."
            ),
        )

    if attempt.input_modality != input_modality:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Attempt input modality was not persisted correctly."
            ),
        )

    if attempt.input_language != input_language:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Attempt input language was not persisted correctly."
            ),
        )

    if (
        speech_transcript is not None
        and attempt.speech_transcript != speech_transcript
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Attempt speech transcript was not persisted correctly."
            ),
        )

    return attempt


def get_attempt_by_id(
    db: Session,
    attempt_id: UUID,
) -> Attempt:
    """
    Return a saved attempt with all answer and Sprint 10 fields available
    to diagnosis and intervention services.
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