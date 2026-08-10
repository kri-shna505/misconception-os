from __future__ import annotations

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.intervention import (
    DiagnosticQuestionResponse,
    DiagnosticReevaluationResponse,
    DiagnosticResponseCreate,
    DiagnosticResponseResult,
    HintDeliveryResponse,
    HintProgressResponse,
    LearningHistoryResponse,
    MisconceptionEvolutionResponse,
    RetryAttemptCreate,
    RetryAttemptResponse,
    RevealedHintListResponse,
)
from app.services.hint_service import (
    get_hint_progress,
    list_revealed_hints,
    reveal_next_hint,
)
from app.services.intervention_service import (
    create_retry_attempt,
    evaluate_diagnostic_response,
    get_diagnostic_response,
    get_learning_history,
    get_next_diagnostic_question,
    record_misconception_evolution,
    submit_diagnostic_response,
)


router = APIRouter(
    prefix="/interventions",
    tags=["Interventions"],
)


@router.get(
    "/diagnoses/{diagnosis_id}/hints/progress",
    response_model=HintProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Get progressive hint status",
    description=(
        "Return the hint levels already revealed for a diagnosis and the "
        "next level available to the student."
    ),
    response_description="Current progressive hint status.",
)
def read_hint_progress(
    diagnosis_id: UUID,
    student_alias_id: UUID = Query(
        ...,
        description="Student alias that owns the diagnosed attempt.",
    ),
    db: Session = Depends(get_db),
) -> HintProgressResponse:
    result = get_hint_progress(
        db=db,
        diagnosis_id=diagnosis_id,
        student_alias_id=student_alias_id,
    )

    return HintProgressResponse.model_validate(
        result,
    )


@router.post(
    "/diagnoses/{diagnosis_id}/hints/next",
    response_model=HintDeliveryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reveal the next progressive hint",
    description=(
        "Reveal and persist the next approved hint in the L1-L3 progression "
        "for an eligible confident misconception diagnosis."
    ),
    response_description="Newly revealed hint and remaining progression.",
)
def create_next_hint(
    diagnosis_id: UUID,
    student_alias_id: UUID = Query(
        ...,
        description="Student alias that owns the diagnosed attempt.",
    ),
    db: Session = Depends(get_db),
) -> HintDeliveryResponse:
    result = reveal_next_hint(
        db=db,
        diagnosis_id=diagnosis_id,
        student_alias_id=student_alias_id,
    )

    return HintDeliveryResponse.model_validate(
        result,
    )


@router.get(
    "/diagnoses/{diagnosis_id}/hints",
    response_model=RevealedHintListResponse,
    status_code=status.HTTP_200_OK,
    summary="List revealed hints",
    description=(
        "Return all progressive hints already revealed for one diagnosis "
        "without creating a new hint event."
    ),
    response_description="Previously revealed hints for the diagnosis.",
)
def read_revealed_hints(
    diagnosis_id: UUID,
    student_alias_id: UUID = Query(
        ...,
        description="Student alias that owns the diagnosed attempt.",
    ),
    db: Session = Depends(get_db),
) -> RevealedHintListResponse:
    results = list_revealed_hints(
        db=db,
        diagnosis_id=diagnosis_id,
        student_alias_id=student_alias_id,
    )

    items = [
        HintDeliveryResponse.model_validate(
            item,
        )
        for item in results
    ]

    return RevealedHintListResponse(
        diagnosis_id=diagnosis_id,
        items=items,
        total_items=len(items),
    )


@router.get(
    "/diagnoses/{diagnosis_id}/question",
    response_model=DiagnosticQuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the next diagnostic question",
    description=(
        "Return the next active unanswered diagnostic question for an "
        "eligible possible or insufficient diagnosis."
    ),
    response_description="Selected diagnostic question.",
)
def read_next_diagnostic_question(
    diagnosis_id: UUID,
    student_alias_id: UUID = Query(
        ...,
        description="Student alias that owns the diagnosed attempt.",
    ),
    db: Session = Depends(get_db),
) -> DiagnosticQuestionResponse:
    return get_next_diagnostic_question(
        db=db,
        diagnosis_id=diagnosis_id,
        student_alias_id=student_alias_id,
    )


@router.post(
    "/diagnoses/{diagnosis_id}/questions/{diagnostic_question_id}/responses",
    response_model=DiagnosticReevaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit and re-evaluate a diagnostic response",
    description=(
        "Persist the student's answer to one diagnostic question, create an "
        "immutable follow-up diagnosis, and link the response to that result."
    ),
    response_description=(
        "Saved diagnostic response together with the resulting diagnosis."
    ),
)
def create_diagnostic_response(
    diagnosis_id: UUID,
    diagnostic_question_id: UUID,
    request: DiagnosticResponseCreate,
    student_alias_id: UUID = Query(
        ...,
        description="Student alias that owns the diagnosed attempt.",
    ),
    db: Session = Depends(get_db),
) -> DiagnosticReevaluationResponse:
    return submit_diagnostic_response(
        db=db,
        diagnosis_id=diagnosis_id,
        diagnostic_question_id=diagnostic_question_id,
        student_alias_id=student_alias_id,
        request=request,
    )


@router.get(
    "/diagnostic-responses/{diagnostic_response_id}",
    response_model=DiagnosticResponseResult,
    status_code=status.HTTP_200_OK,
    summary="Get a diagnostic response",
    description=(
        "Return one stored diagnostic response after validating student "
        "ownership."
    ),
    response_description="Stored diagnostic response.",
)
def read_diagnostic_response(
    diagnostic_response_id: UUID,
    student_alias_id: UUID = Query(
        ...,
        description="Student alias that owns the diagnostic response.",
    ),
    db: Session = Depends(get_db),
) -> DiagnosticResponseResult:
    return get_diagnostic_response(
        db=db,
        diagnostic_response_id=diagnostic_response_id,
        student_alias_id=student_alias_id,
    )


@router.post(
    "/diagnostic-responses/{diagnostic_response_id}/evaluated",
    response_model=DiagnosticReevaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate a diagnostic response",
    description=(
        "Create or return the immutable follow-up diagnosis for one stored "
        "diagnostic response. Repeated calls are idempotent."
    ),
    response_description=(
        "Diagnostic response together with its resulting diagnosis."
    ),
)
def update_diagnostic_response_as_evaluated(
    diagnostic_response_id: UUID,
    student_alias_id: UUID = Query(
        ...,
        description="Student alias that owns the diagnostic response.",
    ),
    db: Session = Depends(get_db),
) -> DiagnosticReevaluationResponse:
    return evaluate_diagnostic_response(
        db=db,
        diagnostic_response_id=diagnostic_response_id,
        student_alias_id=student_alias_id,
    )


@router.post(
    "/attempts/{parent_attempt_id}/retry",
    response_model=RetryAttemptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a retry attempt",
    description=(
        "Create a new attempt linked to the supplied parent attempt. The "
        "student and problem are inherited from the parent and retry_number "
        "is incremented automatically."
    ),
    response_description="Newly created retry attempt.",
)
def create_attempt_retry(
    parent_attempt_id: UUID,
    request: RetryAttemptCreate,
    student_alias_id: UUID = Query(
        ...,
        description="Student alias that owns the parent attempt.",
    ),
    db: Session = Depends(get_db),
) -> RetryAttemptResponse:
    return create_retry_attempt(
        db=db,
        parent_attempt_id=parent_attempt_id,
        student_alias_id=student_alias_id,
        request=request,
    )


@router.post(
    "/diagnoses/{diagnosis_id}/evolution",
    response_model=MisconceptionEvolutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Record misconception evolution",
    description=(
        "Create or return the conceptual transition associated with one "
        "diagnosis by comparing it with the parent attempt diagnosis."
    ),
    response_description="Stored misconception evolution record.",
)
def create_or_read_misconception_evolution(
    diagnosis_id: UUID,
    db: Session = Depends(get_db),
) -> MisconceptionEvolutionResponse:
    return record_misconception_evolution(
        db=db,
        diagnosis_id=diagnosis_id,
    )


@router.get(
    "/students/{student_alias_id}/learning-history",
    response_model=LearningHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get student learning history",
    description=(
        "Return the student's retry, diagnosis, hint, diagnostic-question, "
        "and misconception-evolution timeline. Optionally filter by problem."
    ),
    response_description="Student intervention and retry history.",
)
def read_learning_history(
    student_alias_id: UUID,
    problem_id: UUID | None = Query(
        default=None,
        description="Optional problem filter.",
    ),
    db: Session = Depends(get_db),
) -> LearningHistoryResponse:
    return get_learning_history(
        db=db,
        student_alias_id=student_alias_id,
        problem_id=problem_id,
    )


__all__ = [
    "router",
]