from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.models.diagnosis import Diagnosis
from app.models.diagnostic_question import DiagnosticQuestion
from app.models.diagnostic_response import DiagnosticResponse
from app.models.hint_event import HintEvent
from app.models.misconception_evolution import MisconceptionEvolution
from app.schemas.diagnosis import DiagnosisState
from app.services.diagnosis_service import (
    create_followup_diagnosis_from_response,
)
from app.schemas.intervention import (
    DiagnosticQuestionResponse,
    DiagnosticReevaluationResponse,
    DiagnosticResponseCreate,
    DiagnosticResponseResult,
    LearningHistoryItem,
    LearningHistoryResponse,
    MisconceptionEvolutionResponse,
    MisconceptionEvolutionState,
    RetryAttemptCreate,
    RetryAttemptResponse,
)


QUESTION_ELIGIBLE_NEXT_ACTIONS = {
    "ask_diagnostic_question",
}

QUESTION_ELIGIBLE_STATES = {
    "possible",
    "insufficient",
}


def get_next_diagnostic_question(
    *,
    db: Session,
    diagnosis_id: UUID,
    student_alias_id: UUID,
) -> DiagnosticQuestionResponse:
    """
    Return the next active, unanswered diagnostic question.

    The diagnosis must belong to the supplied student alias and must currently
    require a diagnostic question. Questions are selected deterministically by
    creation time and ID so repeated requests behave consistently.
    """

    diagnosis, attempt = _get_owned_diagnosis_context(
        db=db,
        diagnosis_id=diagnosis_id,
        student_alias_id=student_alias_id,
    )

    misconception_id = _require_question_eligible_diagnosis(
        diagnosis=diagnosis,
    )

    answered_question_ids = (
        select(DiagnosticResponse.diagnostic_question_id)
        .where(
            DiagnosticResponse.diagnosis_id == diagnosis.id,
            DiagnosticResponse.student_alias_id == student_alias_id,
        )
    )

    question = db.execute(
        select(DiagnosticQuestion)
        .where(
            DiagnosticQuestion.misconception_id == misconception_id,
            DiagnosticQuestion.active.is_(True),
            DiagnosticQuestion.id.not_in(answered_question_ids),
        )
        .order_by(
            DiagnosticQuestion.created_at.asc(),
            DiagnosticQuestion.id.asc(),
        )
        .limit(1)
    ).scalar_one_or_none()

    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No active unanswered diagnostic question is configured "
                "for this diagnosis."
            ),
        )

    return DiagnosticQuestionResponse(
        id=question.id,
        diagnosis_id=diagnosis.id,
        attempt_id=attempt.id,
        student_alias_id=student_alias_id,
        misconception_id=question.misconception_id,
        competing_misconception_id=(
            question.competing_misconception_id
        ),
        question_text=question.question_text,
        created_at=question.created_at,
    )


def submit_diagnostic_response(
    *,
    db: Session,
    diagnosis_id: UUID,
    diagnostic_question_id: UUID,
    student_alias_id: UUID,
    request: DiagnosticResponseCreate,
) -> DiagnosticReevaluationResponse:
    """
    Persist and immediately re-evaluate one diagnostic answer.

    The original diagnosis remains immutable. The response is saved first,
    then the approved follow-up diagnosis pipeline creates a new diagnosis
    snapshot and links it through ``resulting_diagnosis_id``.

    If follow-up diagnosis creation fails, the stored response remains pending
    and can be safely retried through ``evaluate_diagnostic_response``.
    """

    diagnosis, attempt = _get_owned_diagnosis_context(
        db=db,
        diagnosis_id=diagnosis_id,
        student_alias_id=student_alias_id,
    )

    misconception_id = _require_question_eligible_diagnosis(
        diagnosis=diagnosis,
    )

    question = db.execute(
        select(DiagnosticQuestion).where(
            DiagnosticQuestion.id == diagnostic_question_id,
            DiagnosticQuestion.active.is_(True),
        )
    ).scalar_one_or_none()

    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic question was not found or is inactive.",
        )

    if question.misconception_id != misconception_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The diagnostic question does not target the diagnosis "
                "misconception."
            ),
        )

    response = DiagnosticResponse(
        student_alias_id=student_alias_id,
        attempt_id=attempt.id,
        diagnosis_id=diagnosis.id,
        diagnostic_question_id=question.id,
        response_text=request.response_text,
        evaluated=False,
        evaluated_at=None,
    )

    db.add(response)

    try:
        db.commit()
        db.refresh(response)
    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This diagnostic question has already been answered "
                "for the diagnosis."
            ),
        ) from exc
    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save the diagnostic response.",
        ) from exc

    resulting_diagnosis = (
        create_followup_diagnosis_from_response(
            db=db,
            diagnostic_response_id=response.id,
        )
    )

    db.refresh(response)

    return DiagnosticReevaluationResponse(
        diagnostic_response=(
            _build_diagnostic_response_result(
                response=response,
            )
        ),
        original_diagnosis_id=diagnosis.id,
        resulting_diagnosis_id=(
            resulting_diagnosis.id
        ),
        previous_state=DiagnosisState(
            _diagnosis_state_value(
                diagnosis.state
            )
        ),
        resulting_state=(
            resulting_diagnosis.state
        ),
        resulting_diagnosis=(
            resulting_diagnosis
        ),
        reevaluated=True,
        message=(
            "Diagnostic response saved and re-evaluated successfully."
        ),
    )


def get_diagnostic_response(
    *,
    db: Session,
    diagnostic_response_id: UUID,
    student_alias_id: UUID,
) -> DiagnosticResponseResult:
    """
    Return one diagnostic response owned by the supplied student alias.
    """

    response = db.execute(
        select(DiagnosticResponse).where(
            DiagnosticResponse.id == diagnostic_response_id,
        )
    ).scalar_one_or_none()

    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic response was not found.",
        )

    if response.student_alias_id != student_alias_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "The diagnostic response does not belong to the supplied "
                "student alias."
            ),
        )

    return _build_diagnostic_response_result(
        response=response,
    )


def evaluate_diagnostic_response(
    *,
    db: Session,
    diagnostic_response_id: UUID,
    student_alias_id: UUID,
) -> DiagnosticReevaluationResponse:
    """
    Create or return the follow-up diagnosis for one stored response.

    This endpoint is idempotent. If the response was already evaluated, the
    existing resulting diagnosis is returned instead of creating a duplicate.
    """

    response = db.execute(
        select(DiagnosticResponse).where(
            DiagnosticResponse.id == diagnostic_response_id,
        )
    ).scalar_one_or_none()

    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic response was not found.",
        )

    if response.student_alias_id != student_alias_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "The diagnostic response does not belong to the supplied "
                "student alias."
            ),
        )

    original_diagnosis = db.execute(
        select(Diagnosis).where(
            Diagnosis.id == response.diagnosis_id,
        )
    ).scalar_one_or_none()

    if original_diagnosis is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The diagnostic response references a missing "
                "original diagnosis."
            ),
        )

    resulting_diagnosis = (
        create_followup_diagnosis_from_response(
            db=db,
            diagnostic_response_id=response.id,
        )
    )

    db.refresh(response)

    return DiagnosticReevaluationResponse(
        diagnostic_response=(
            _build_diagnostic_response_result(
                response=response,
            )
        ),
        original_diagnosis_id=(
            original_diagnosis.id
        ),
        resulting_diagnosis_id=(
            resulting_diagnosis.id
        ),
        previous_state=DiagnosisState(
            _diagnosis_state_value(
                original_diagnosis.state
            )
        ),
        resulting_state=(
            resulting_diagnosis.state
        ),
        resulting_diagnosis=(
            resulting_diagnosis
        ),
        reevaluated=True,
        message=(
            "Diagnostic response re-evaluated successfully."
        ),
    )


def mark_diagnostic_response_evaluated(
    *,
    db: Session,
    diagnostic_response_id: UUID,
    student_alias_id: UUID,
) -> DiagnosticReevaluationResponse:
    """
    Backward-compatible alias for the Sprint 9A re-evaluation operation.
    """

    return evaluate_diagnostic_response(
        db=db,
        diagnostic_response_id=diagnostic_response_id,
        student_alias_id=student_alias_id,
    )


def create_retry_attempt(
    *,
    db: Session,
    parent_attempt_id: UUID,
    student_alias_id: UUID,
    request: RetryAttemptCreate,
) -> RetryAttemptResponse:
    """
    Create a retry linked to the immediately previous attempt.

    The parent must belong to the same student. The new attempt automatically
    inherits the original problem and increments the retry number.
    """

    parent_attempt = db.execute(
        select(Attempt).where(
            Attempt.id == parent_attempt_id,
        )
    ).scalar_one_or_none()

    if parent_attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent attempt was not found.",
        )

    if parent_attempt.student_alias_id != student_alias_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "The parent attempt does not belong to the supplied "
                "student alias."
            ),
        )

    if parent_attempt.problem_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The parent attempt is not linked to a problem and "
                "cannot be retried."
            ),
        )

    retry_number = int(parent_attempt.retry_number or 0) + 1

    retry_attempt = Attempt(
        student_alias_id=student_alias_id,
        problem_id=parent_attempt.problem_id,
        parent_attempt_id=parent_attempt.id,
        retry_number=retry_number,
        final_answer=request.final_answer,
        written_reasoning=request.written_reasoning,
        source_code=request.source_code,
        speech_transcript=request.speech_transcript,
        selected_language=request.selected_language,
        response_time_seconds=request.response_time_seconds,
    )

    db.add(retry_attempt)

    try:
        db.commit()
        db.refresh(retry_attempt)
    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create the retry attempt.",
        ) from exc

    return RetryAttemptResponse(
        id=retry_attempt.id,
        student_alias_id=retry_attempt.student_alias_id,
        problem_id=retry_attempt.problem_id,
        parent_attempt_id=retry_attempt.parent_attempt_id,
        retry_number=retry_attempt.retry_number,
        selected_language=retry_attempt.selected_language,
        response_time_seconds=retry_attempt.response_time_seconds,
        created_at=retry_attempt.created_at,
    )


def calculate_evolution_state(
    *,
    previous_state: DiagnosisState | str | None,
    previous_misconception_id: UUID | None,
    previous_confidence: float | None,
    current_state: DiagnosisState | str,
    current_misconception_id: UUID | None,
    current_confidence: float,
) -> MisconceptionEvolutionState:
    """
    Classify the conceptual transition between two diagnosis snapshots.

    The transition rules are misconception-agnostic and therefore apply
    consistently across the approved P1-P5 taxonomy.
    """

    previous_state_value = _diagnosis_state_value(
        previous_state,
    )
    current_state_value = _diagnosis_state_value(
        current_state,
    )

    if current_state_value == DiagnosisState.INSUFFICIENT.value:
        return MisconceptionEvolutionState.UNCERTAIN

    if previous_state_value is None:
        if current_misconception_id is not None:
            return MisconceptionEvolutionState.NEWLY_DETECTED

        return MisconceptionEvolutionState.UNCERTAIN

    if (
        previous_misconception_id is not None
        and current_state_value
        == DiagnosisState.NO_MISCONCEPTION.value
        and current_misconception_id is None
    ):
        return MisconceptionEvolutionState.CORRECTED

    if (
        previous_misconception_id is None
        and current_misconception_id is not None
    ):
        return MisconceptionEvolutionState.NEWLY_DETECTED

    if (
        previous_misconception_id is None
        and current_misconception_id is None
        and previous_state_value == DiagnosisState.NO_MISCONCEPTION.value
        and current_state_value == DiagnosisState.NO_MISCONCEPTION.value
    ):
        # Sprint 9 taxonomy has no separate "stable_correct" state. Keep the
        # transition UNCERTAIN rather than incorrectly calling it CORRECTED.
        return MisconceptionEvolutionState.UNCERTAIN

    if (
        previous_misconception_id is not None
        and current_misconception_id is not None
        and previous_misconception_id != current_misconception_id
    ):
        return MisconceptionEvolutionState.REPLACED

    if (
        previous_misconception_id is not None
        and previous_misconception_id == current_misconception_id
    ):
        previous_confidence_value = float(
            previous_confidence or 0.0
        )

        state_improved = (
            previous_state_value == DiagnosisState.CONFIDENT.value
            and current_state_value == DiagnosisState.POSSIBLE.value
        )

        confidence_improved = (
            previous_confidence is not None
            and current_confidence < previous_confidence_value
        )

        if state_improved or confidence_improved:
            return MisconceptionEvolutionState.IMPROVING

        return MisconceptionEvolutionState.REPEATED

    return MisconceptionEvolutionState.UNCERTAIN


def record_misconception_evolution(
    *,
    db: Session,
    diagnosis_id: UUID,
) -> MisconceptionEvolutionResponse:
    """
    Create or return the evolution record for one diagnosis.

    When the attempt has a parent, the latest diagnosis for that parent is used
    as the comparison point. An original attempt has no previous context.
    """

    existing = db.execute(
        select(MisconceptionEvolution).where(
            MisconceptionEvolution.diagnosis_id == diagnosis_id,
        )
    ).scalar_one_or_none()

    # Evolution is derived state. During Sprint 9 testing, an older persisted
    # row may reflect a previous transition rule (for example "repeated" before
    # the confident -> possible "improving" fix). Recalculate from immutable
    # diagnosis snapshots below and update the existing row when necessary.
    current_diagnosis = db.execute(
        select(Diagnosis).where(
            Diagnosis.id == diagnosis_id,
        )
    ).scalar_one_or_none()

    if current_diagnosis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnosis was not found.",
        )

    current_attempt = db.execute(
        select(Attempt).where(
            Attempt.id == current_diagnosis.attempt_id,
        )
    ).scalar_one_or_none()

    if current_attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attempt linked to the diagnosis was not found.",
        )

    previous_attempt: Attempt | None = None
    previous_diagnosis: Diagnosis | None = None

    if current_attempt.parent_attempt_id is not None:
        previous_attempt = db.execute(
            select(Attempt).where(
                Attempt.id == current_attempt.parent_attempt_id,
            )
        ).scalar_one_or_none()

        if previous_attempt is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Retry attempt references a missing parent attempt.",
            )

        if (
            previous_attempt.student_alias_id
            != current_attempt.student_alias_id
            or previous_attempt.problem_id
            != current_attempt.problem_id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Retry chain contains attempts from different students "
                    "or problems."
                ),
            )

        previous_diagnosis = _get_latest_diagnosis_for_attempt(
            db=db,
            attempt_id=previous_attempt.id,
        )

    evolution_state = calculate_evolution_state(
        previous_state=(
            previous_diagnosis.state
            if previous_diagnosis is not None
            else None
        ),
        previous_misconception_id=(
            previous_diagnosis.primary_misconception_id
            if previous_diagnosis is not None
            else None
        ),
        previous_confidence=(
            previous_diagnosis.confidence
            if previous_diagnosis is not None
            else None
        ),
        current_state=current_diagnosis.state,
        current_misconception_id=(
            current_diagnosis.primary_misconception_id
        ),
        current_confidence=float(
            current_diagnosis.confidence
        ),
    )

    evolution_values = {
        "student_alias_id": current_attempt.student_alias_id,
        "problem_id": current_attempt.problem_id,
        "attempt_id": current_attempt.id,
        "diagnosis_id": current_diagnosis.id,
        "previous_attempt_id": (
            previous_attempt.id
            if previous_attempt is not None
            else None
        ),
        "previous_diagnosis_id": (
            previous_diagnosis.id
            if previous_diagnosis is not None
            else None
        ),
        "previous_misconception_id": (
            previous_diagnosis.primary_misconception_id
            if previous_diagnosis is not None
            else None
        ),
        "current_misconception_id": (
            current_diagnosis.primary_misconception_id
        ),
        "previous_diagnosis_state": (
            _diagnosis_state_value(previous_diagnosis.state)
            if previous_diagnosis is not None
            else None
        ),
        "current_diagnosis_state": _diagnosis_state_value(
            current_diagnosis.state
        ),
        "evolution_state": evolution_state.value,
    }

    if existing is None:
        evolution = MisconceptionEvolution(
            **evolution_values,
        )
        db.add(evolution)
    else:
        evolution = existing

        # Re-sync all derived comparison fields so stale development/test rows
        # cannot preserve an obsolete transition result.
        for field_name, field_value in evolution_values.items():
            setattr(
                evolution,
                field_name,
                field_value,
            )

    try:
        db.commit()
        db.refresh(evolution)
    except IntegrityError as exc:
        db.rollback()

        existing_after_conflict = db.execute(
            select(MisconceptionEvolution).where(
                MisconceptionEvolution.diagnosis_id
                == diagnosis_id,
            )
        ).scalar_one_or_none()

        if existing_after_conflict is not None:
            return _build_evolution_response(
                evolution=existing_after_conflict,
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "An evolution record already exists for this diagnosis."
            ),
        ) from exc
    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to record misconception evolution.",
        ) from exc

    return _build_evolution_response(
        evolution=evolution,
    )


def get_learning_history(
    *,
    db: Session,
    student_alias_id: UUID,
    problem_id: UUID | None = None,
) -> LearningHistoryResponse:
    """
    Build the student's intervention and retry timeline.

    History is attempt-centric rather than diagnosis-centric. An attempt may
    have more than one diagnosis snapshot (for example, after a diagnostic
    question re-evaluation), so the service:

    - returns the latest diagnosis snapshot for display;
    - aggregates hint usage across every diagnosis for the attempt;
    - reports whether any diagnostic question was answered for the attempt;
    - returns the latest stored evolution record for the attempt.

    This keeps the learning-history UI correct even when an attempt contains
    an original diagnosis plus one or more immutable follow-up diagnoses.
    """

    attempt_query = select(Attempt).where(
        Attempt.student_alias_id == student_alias_id,
    )

    if problem_id is not None:
        attempt_query = attempt_query.where(
            Attempt.problem_id == problem_id,
        )

    attempts = (
        db.execute(
            attempt_query.order_by(
                Attempt.created_at.asc(),
                Attempt.id.asc(),
            )
        )
        .scalars()
        .all()
    )

    items: list[LearningHistoryItem] = []

    for attempt in attempts:
        diagnoses = _get_attempt_diagnoses(
            db=db,
            attempt_id=attempt.id,
        )

        latest_diagnosis = (
            diagnoses[-1]
            if diagnoses
            else None
        )

        diagnosis_ids = [
            diagnosis.id
            for diagnosis in diagnoses
        ]

        hint_levels: list[int] = []

        if diagnosis_ids:
            hint_levels = sorted(
                {
                    int(level)
                    for level in (
                        db.execute(
                            select(HintEvent.level).where(
                                HintEvent.diagnosis_id.in_(
                                    diagnosis_ids
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                }
            )

        diagnostic_question_answered = (
            int(
                db.execute(
                    select(
                        func.count(
                            DiagnosticResponse.id
                        )
                    ).where(
                        DiagnosticResponse.attempt_id
                        == attempt.id,
                    )
                ).scalar_one()
            )
            > 0
        )

        evolution = db.execute(
            select(MisconceptionEvolution)
            .where(
                MisconceptionEvolution.attempt_id
                == attempt.id,
            )
            .order_by(
                MisconceptionEvolution.created_at.desc(),
                MisconceptionEvolution.id.desc(),
            )
            .limit(1)
        ).scalar_one_or_none()

        evolution_state = (
            MisconceptionEvolutionState(
                evolution.evolution_state
            )
            if evolution is not None
            else None
        )

        items.append(
            LearningHistoryItem(
                attempt_id=attempt.id,
                problem_id=attempt.problem_id,
                parent_attempt_id=attempt.parent_attempt_id,
                retry_number=int(
                    attempt.retry_number or 0
                ),
                diagnosis_id=(
                    latest_diagnosis.id
                    if latest_diagnosis is not None
                    else None
                ),
                diagnosis_state=(
                    DiagnosisState(
                        _diagnosis_state_value(
                            latest_diagnosis.state
                        )
                    )
                    if latest_diagnosis is not None
                    else None
                ),
                misconception_id=(
                    latest_diagnosis.primary_misconception_id
                    if latest_diagnosis is not None
                    else None
                ),
                confidence=(
                    float(
                        latest_diagnosis.confidence
                    )
                    if latest_diagnosis is not None
                    else None
                ),
                hint_levels_used=hint_levels,
                diagnostic_question_answered=(
                    diagnostic_question_answered
                ),
                evolution_state=evolution_state,
                created_at=attempt.created_at,
            )
        )

    return LearningHistoryResponse(
        student_alias_id=student_alias_id,
        problem_id=problem_id,
        items=items,
        total_items=len(items),
    )


def _get_attempt_diagnoses(
    *,
    db: Session,
    attempt_id: UUID,
) -> list[Diagnosis]:
    """
    Return all immutable diagnosis snapshots for an attempt in chronological
    order.
    """

    return list(
        db.execute(
            select(Diagnosis)
            .where(
                Diagnosis.attempt_id == attempt_id,
            )
            .order_by(
                Diagnosis.created_at.asc(),
                Diagnosis.id.asc(),
            )
        )
        .scalars()
        .all()
    )


def _get_latest_diagnosis_for_attempt(
    *,
    db: Session,
    attempt_id: UUID,
) -> Diagnosis | None:
    """
    Return the newest diagnosis snapshot for one attempt.
    """

    return db.execute(
        select(Diagnosis)
        .where(
            Diagnosis.attempt_id == attempt_id,
        )
        .order_by(
            Diagnosis.created_at.desc(),
            Diagnosis.id.desc(),
        )
        .limit(1)
    ).scalar_one_or_none()


def _get_owned_diagnosis_context(
    *,
    db: Session,
    diagnosis_id: UUID,
    student_alias_id: UUID,
) -> tuple[Diagnosis, Attempt]:
    row = db.execute(
        select(
            Diagnosis,
            Attempt,
        )
        .join(
            Attempt,
            Attempt.id == Diagnosis.attempt_id,
        )
        .where(
            Diagnosis.id == diagnosis_id,
        )
    ).one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnosis was not found.",
        )

    diagnosis, attempt = row

    if attempt.student_alias_id != student_alias_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "The diagnosis does not belong to the supplied "
                "student alias."
            ),
        )

    return diagnosis, attempt


def _require_question_eligible_diagnosis(
    *,
    diagnosis: Diagnosis,
) -> UUID:
    normalized_state = _diagnosis_state_value(
        diagnosis.state
    )
    normalized_next_action = str(
        getattr(
            diagnosis.next_action,
            "value",
            diagnosis.next_action,
        )
    ).strip().lower()

    if normalized_state not in QUESTION_ELIGIBLE_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Diagnostic questions are available only for possible "
                "or insufficient diagnoses."
            ),
        )

    if normalized_next_action not in QUESTION_ELIGIBLE_NEXT_ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This diagnosis does not currently request a diagnostic "
                "question."
            ),
        )

    if diagnosis.primary_misconception_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A diagnostic question cannot be selected because the "
                "diagnosis has no primary misconception."
            ),
        )

    return diagnosis.primary_misconception_id


def _build_diagnostic_response_result(
    *,
    response: DiagnosticResponse,
) -> DiagnosticResponseResult:
    return DiagnosticResponseResult(
        id=response.id,
        student_alias_id=response.student_alias_id,
        attempt_id=response.attempt_id,
        diagnosis_id=response.diagnosis_id,
        diagnostic_question_id=(
            response.diagnostic_question_id
        ),
        resulting_diagnosis_id=(
            response.resulting_diagnosis_id
        ),
        response_text=response.response_text,
        evaluated=response.evaluated,
        evaluated_at=response.evaluated_at,
        created_at=response.created_at,
        updated_at=response.updated_at,
    )


def _build_evolution_response(
    *,
    evolution: MisconceptionEvolution,
) -> MisconceptionEvolutionResponse:
    return MisconceptionEvolutionResponse(
        id=evolution.id,
        student_alias_id=evolution.student_alias_id,
        problem_id=evolution.problem_id,
        attempt_id=evolution.attempt_id,
        diagnosis_id=evolution.diagnosis_id,
        previous_attempt_id=evolution.previous_attempt_id,
        previous_diagnosis_id=evolution.previous_diagnosis_id,
        previous_misconception_id=(
            evolution.previous_misconception_id
        ),
        current_misconception_id=(
            evolution.current_misconception_id
        ),
        previous_diagnosis_state=(
            DiagnosisState(
                evolution.previous_diagnosis_state
            )
            if evolution.previous_diagnosis_state
            is not None
            else None
        ),
        current_diagnosis_state=DiagnosisState(
            evolution.current_diagnosis_state
        ),
        evolution_state=MisconceptionEvolutionState(
            evolution.evolution_state
        ),
        created_at=evolution.created_at,
        updated_at=evolution.updated_at,
    )


def _diagnosis_state_value(
    state_value: DiagnosisState | str | None,
) -> str | None:
    if state_value is None:
        return None

    if isinstance(
        state_value,
        DiagnosisState,
    ):
        return state_value.value

    raw_value = getattr(
        state_value,
        "value",
        state_value,
    )

    return str(raw_value).strip().lower()


__all__ = [
    "QUESTION_ELIGIBLE_NEXT_ACTIONS",
    "QUESTION_ELIGIBLE_STATES",
    "calculate_evolution_state",
    "create_retry_attempt",
    "evaluate_diagnostic_response",
    "get_diagnostic_response",
    "get_learning_history",
    "get_next_diagnostic_question",
    "mark_diagnostic_response_evaluated",
    "record_misconception_evolution",
    "submit_diagnostic_response",
]