from __future__ import annotations

import json
import logging
import re
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.ml_diagnosis_service import (
    diagnose_with_ml_from_mapping,
    diagnosis_model_fields,
    ml_diagnosis_available,
    rule_only_diagnosis_model_fields,
)
from app.schemas.diagnosis import (
    DiagnosisAlternativeResponse,
    DiagnosisEvidenceResponse,
    DiagnosisNextAction,
    DiagnosisResponse,
    DiagnosisState,
    MisconceptionSummary,
)
from app.services.evidence_extractor import extract_evidence
from app.services.rule_detector import detect_misconception


MODEL_VERSION = "rule-v1.9"

logger = logging.getLogger(__name__)


# Diagnosis must remain inside the misconception taxonomy configured for the
# selected problem. This prevents a detector signal from one topic (for example,
# recursion) being returned for an unrelated problem (for example, binary search).
PROBLEM_MISCONCEPTION_ALLOWLIST: dict[str, set[str]] = {
    "P1": {"M1"},
    "P2": {"M2", "M3"},
    "P3": {"M2", "M3"},
    "P4": {"M4"},
    "P5": {"M5"},
}


def create_diagnosis_from_attempt(
    db: Session,
    attempt_id: UUID,
) -> DiagnosisResponse:
    """
    Create an evidence-backed rule diagnosis from an existing saved attempt.

    Sprint 8 scope:
    - M1 Binary Search on Unsorted Data
    - M2 Missing or Incorrect Recursion Base Case
    - M3 Recursive Call Without Reducing Problem Size
    - M4 Pass-by-Value vs Pass-by-Reference Confusion
    - M5 Stack vs Heap Confusion

    Hardening:
    - If an attempt already has a diagnosis, return the latest existing diagnosis.
    - Do not create duplicate diagnosis rows for accidental repeated calls.

    This service is aligned with the current database schema:
    - diagnoses
    - diagnosis_evidence
    - diagnosis_alternatives

    Sprint 9 integration:
    - Restricts each problem to its configured misconception taxonomy.
    - Supports the P1-P5 evidence/rule pipeline across the source-language
      patterns handled by evidence_extractor.py (including Python and C/C++).
    - Preserves deterministic M4/M5 evidence-backed diagnosis behavior.

    Sprint 10 integration:
    - Loads normalized reasoning and multimodal/language metadata from attempts.
    - Delegates semantic evidence selection to evidence_extractor.py so
      normalized reasoning can be used without overwriting original student text.
    - Keeps source-code analysis bound to the selected programming submission.
    - Uses rule-v1.9 so Sprint 10 evidence semantics do not reuse stale
      rule-v1.8 diagnosis snapshots.
    """

    attempt = _get_attempt_or_404(db, attempt_id)

    # Preserve the original fast/idempotent rule-only path when ML is off.
    # When ML is enabled, the final model version is known only after fusion.
    if not settings.ML_DIAGNOSIS_ENABLED:
        existing_diagnosis = _get_existing_diagnosis_for_attempt(
            db=db,
            attempt_id=attempt.id,
            model_version=MODEL_VERSION,
        )

        if existing_diagnosis is not None:
            return _build_existing_diagnosis_response(
                db=db,
                diagnosis_id=existing_diagnosis.id,
            )

    problem = _get_problem_or_404(db, attempt.problem_id)
    allowed_codes = _get_allowed_misconception_codes(problem)

    # Keep detection inside the selected problem's misconception taxonomy.
    signals = extract_evidence(attempt=attempt, problem=problem)
    rule_result = detect_misconception(
        signals,
        allowed_rule_codes=allowed_codes,
    )

    # Sprint 9 verification hardening for P5 / M5.
    #
    # Evidence extraction is authoritative for observable student statements.
    # If the generic rule detector returns no misconception even though the
    # extractor produced explicit M5 stack/heap misconception signals, promote
    # the result through the same structured diagnosis contract. This is not a
    # free-form classifier: it is a narrow deterministic fallback bounded to
    # P5 -> M5.
    rule_result = _apply_m5_evidence_fallback(
        problem_code=_normalize_code(problem.code),
        allowed_codes=allowed_codes,
        signals=signals,
        rule_result=rule_result,
    )

    # Sprint 9 P1-P4 correction hardening.
    #
    # The rule detector remains the primary classifier. This narrow fallback is
    # used only when the detector returns INSUFFICIENT even though the extractor
    # has already produced a complete, internally consistent corrective pattern.
    # It prevents fully corrected retries from being stuck at INSUFFICIENT while
    # keeping the decision bounded to the approved problem taxonomy.
    rule_result = _apply_supported_correction_fallback(
        problem_code=_normalize_code(problem.code),
        allowed_codes=allowed_codes,
        signals=signals,
        rule_result=rule_result,
    )

    detected_code = _normalize_code(rule_result.misconception_code)
    detection_is_supported = bool(
        detected_code and detected_code in allowed_codes
    )

    if detection_is_supported:
        final_state = rule_result.state
        final_confidence = rule_result.confidence
        final_misconception_code = detected_code
        final_evidence = list(rule_result.evidence)
        final_alternative_codes = [
            code
            for code in (
                _normalize_code(item)
                for item in rule_result.alternative_misconception_codes
            )
            if code
            and code in allowed_codes
            and code != final_misconception_code
        ]
        final_decision_reason = rule_result.decision_reason
        final_next_action = rule_result.next_action

    elif detected_code is None:
        # Correct or non-diagnostic work can produce no misconception code.
        # Preserve positive evidence instead of erasing it.
        final_state = rule_result.state
        final_confidence = rule_result.confidence
        final_misconception_code = None
        final_evidence = list(rule_result.evidence)
        final_alternative_codes = []
        final_decision_reason = rule_result.decision_reason
        final_next_action = rule_result.next_action

    else:
        # Reject cross-topic output while preserving observable evidence.
        final_state = DiagnosisState.INSUFFICIENT
        final_confidence = 0.0
        final_misconception_code = None
        final_evidence = list(rule_result.evidence)
        final_alternative_codes = []
        final_decision_reason = _unsupported_detection_reason(
            problem_code=problem.code,
            detected_code=detected_code,
            allowed_codes=allowed_codes,
        )
        final_next_action = DiagnosisNextAction.ASK_CLARIFICATION

    _validate_final_diagnosis_contract(
        state=final_state,
        misconception_code=final_misconception_code,
        confidence=final_confidence,
        evidence=final_evidence,
    )

    primary_misconception = None
    primary_misconception_id = None

    if final_misconception_code:
        primary_misconception = _get_misconception_by_code_or_404(
            db=db,
            code=final_misconception_code,
        )
        primary_misconception_id = primary_misconception.id

    diagnosis_fields = _resolve_initial_diagnosis_model_fields(
        attempt=attempt,
        problem=problem,
        state=final_state,
        confidence=final_confidence,
        primary_misconception_id=primary_misconception_id,
        decision_reason=final_decision_reason,
        next_action=final_next_action,
    )

    final_state = DiagnosisState(diagnosis_fields["state"])
    final_confidence = float(diagnosis_fields["confidence"])
    final_decision_reason = diagnosis_fields["decision_reason"]
    final_next_action = DiagnosisNextAction(
        diagnosis_fields["next_action"]
    )

    resolved_primary_id = diagnosis_fields["primary_misconception_id"]
    if resolved_primary_id is None:
        primary_misconception = None
        primary_misconception_id = None
        final_misconception_code = None
        final_alternative_codes = []
    else:
        primary_misconception_id = UUID(str(resolved_primary_id))

    _validate_final_diagnosis_contract(
        state=final_state,
        misconception_code=final_misconception_code,
        confidence=final_confidence,
        evidence=final_evidence,
    )

    selected_model_version = str(diagnosis_fields["model_version"])

    existing_diagnosis = _get_existing_diagnosis_for_attempt(
        db=db,
        attempt_id=attempt.id,
        model_version=selected_model_version,
    )

    if existing_diagnosis is not None:
        return _build_existing_diagnosis_response(
            db=db,
            diagnosis_id=existing_diagnosis.id,
        )

    diagnosis_id = uuid4()

    db.execute(
        text(
            """
            INSERT INTO diagnoses (
                id,
                attempt_id,
                state,
                primary_misconception_id,
                confidence,
                model_version,
                decision_reason,
                next_action,
                rule_score,
                llm_score,
                ml_score,
                hybrid_score,
                prediction_source,
                feature_version,
                calibration_version,
                created_at,
                updated_at
            )
            VALUES (
                :id,
                :attempt_id,
                :state,
                :primary_misconception_id,
                :confidence,
                :model_version,
                :decision_reason,
                :next_action,
                :rule_score,
                :llm_score,
                :ml_score,
                :hybrid_score,
                :prediction_source,
                :feature_version,
                :calibration_version,
                NOW(),
                NOW()
            )
            """
        ),
        {
            "id": diagnosis_id,
            "attempt_id": attempt.id,
            "state": _state_value(final_state),
            "primary_misconception_id": primary_misconception_id,
            "confidence": final_confidence,
            "model_version": selected_model_version,
            "decision_reason": final_decision_reason,
            "next_action": _next_action_value(final_next_action),
            "rule_score": diagnosis_fields["rule_score"],
            "llm_score": None,
            "ml_score": diagnosis_fields["ml_score"],
            "hybrid_score": diagnosis_fields["hybrid_score"],
            "prediction_source": diagnosis_fields["prediction_source"],
            "feature_version": diagnosis_fields["feature_version"],
            "calibration_version": diagnosis_fields["calibration_version"],
        },
    )

    evidence_responses: list[DiagnosisEvidenceResponse] = []

    for index, evidence in enumerate(final_evidence):
        evidence_id = uuid4()

        db.execute(
            text(
                """
                INSERT INTO diagnosis_evidence (
                    id,
                    diagnosis_id,
                    evidence_type,
                    rule_id,
                    evidence_text,
                    created_at
                )
                VALUES (
                    :id,
                    :diagnosis_id,
                    :evidence_type,
                    :rule_id,
                    :evidence_text,
                    NOW()
                )
                """
            ),
            {
                "id": evidence_id,
                "diagnosis_id": diagnosis_id,
                "evidence_type": evidence.source.value,
                "rule_id": (
                    final_misconception_code
                    or _state_value(final_state).upper()
                ),
                "evidence_text": evidence.text,
            },
        )

        evidence_responses.append(
            DiagnosisEvidenceResponse(
                id=evidence_id,
                diagnosis_id=diagnosis_id,
                source=evidence.source,
                strength=evidence.strength,
                text=evidence.text,
                sort_order=index,
                metadata=evidence.metadata or {},
            )
        )

    alternative_responses: list[DiagnosisAlternativeResponse] = []

    for alternative_code in final_alternative_codes:
        alternative_misconception = _get_misconception_by_code_or_404(
            db=db,
            code=alternative_code,
        )
        alternative_id = uuid4()
        alternative_confidence = _alternative_confidence(final_confidence)

        db.execute(
            text(
                """
                INSERT INTO diagnosis_alternatives (
                    id,
                    diagnosis_id,
                    misconception_id,
                    confidence,
                    created_at
                )
                VALUES (
                    :id,
                    :diagnosis_id,
                    :misconception_id,
                    :confidence,
                    NOW()
                )
                """
            ),
            {
                "id": alternative_id,
                "diagnosis_id": diagnosis_id,
                "misconception_id": alternative_misconception.id,
                "confidence": alternative_confidence,
            },
        )

        alternative_responses.append(
            DiagnosisAlternativeResponse(
                id=alternative_id,
                diagnosis_id=diagnosis_id,
                misconception=MisconceptionSummary(
                    id=alternative_misconception.id,
                    code=alternative_misconception.code,
                    name=alternative_misconception.name,
                    topic=alternative_misconception.topic,
                ),
                confidence=alternative_confidence,
                reason="Alternative misconception triggered by overlapping rule evidence.",
            )
        )

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to persist diagnosis result.",
        ) from exc

    created_at = _get_diagnosis_created_at(db, diagnosis_id)

    return DiagnosisResponse(
        id=diagnosis_id,
        attempt_id=attempt.id,
        state=final_state,
        confidence=final_confidence,
        primary_misconception=(
            MisconceptionSummary(
                id=primary_misconception.id,
                code=primary_misconception.code,
                name=primary_misconception.name,
                topic=primary_misconception.topic,
            )
            if primary_misconception
            else None
        ),
        evidence=evidence_responses,
        alternatives=alternative_responses,
        model_version=selected_model_version,
        decision_reason=final_decision_reason,
        next_action=final_next_action,
        created_at=created_at,
    )


def _resolve_initial_diagnosis_model_fields(
    *,
    attempt: SimpleNamespace,
    problem: SimpleNamespace,
    state: DiagnosisState | str,
    confidence: float,
    primary_misconception_id: UUID | None,
    decision_reason: str | None,
    next_action: DiagnosisNextAction | str,
) -> dict[str, Any]:
    """
    Select hybrid diagnosis fields when ML is usable.

    Every ML-specific failure is isolated here and falls back to the exact
    deterministic rule result. Database errors are deliberately not handled
    here; persistence failures must continue to fail and roll back normally.
    """

    rule_fields = rule_only_diagnosis_model_fields(
        state=_state_value(state),
        confidence=confidence,
        primary_misconception_id=(
            str(primary_misconception_id)
            if primary_misconception_id is not None
            else None
        ),
        decision_reason=decision_reason,
        rule_score=confidence,
        model_version=MODEL_VERSION,
    )
    # Preserve the existing rule detector's intervention choice exactly.
    rule_fields["next_action"] = _next_action_value(next_action)

    if not settings.ML_DIAGNOSIS_ENABLED:
        return rule_fields

    model_path = settings.ML_MODEL_PATH

    try:
        availability = ml_diagnosis_available(model_path)
    except Exception:
        logger.warning(
            "Unable to check ML diagnosis availability; using rule-only diagnosis.",
            exc_info=True,
        )
        return rule_fields

    if not availability.available:
        logger.info(
            "ML diagnosis artifact is unavailable; using rule-only diagnosis."
        )
        return rule_fields

    attempt_payload = dict(vars(attempt))
    attempt_payload.update(
        {
            "attempt_id": str(attempt.id),
            "problem_id": str(problem.id),
            "problem_code": problem.code,
            "problem_title": problem.title,
            "problem_topic": problem.topic,
            "problem_difficulty": problem.difficulty,
            "expected_language": problem.expected_language,
        }
    )

    rule_mapping = {
        "state": _state_value(state),
        "confidence": float(confidence),
        "primary_misconception_id": (
            str(primary_misconception_id)
            if primary_misconception_id is not None
            else None
        ),
        "rule_score": float(confidence),
        "model_version": MODEL_VERSION,
        "decision_reason": decision_reason,
    }

    try:
        hybrid_result = diagnose_with_ml_from_mapping(
            attempt=attempt_payload,
            rule_result=rule_mapping,
            model_path=model_path,
            use_model_cache=settings.ML_MODEL_CACHE_ENABLED,
        )
        return diagnosis_model_fields(hybrid_result)
    except Exception:
        logger.warning(
            "ML diagnosis failed; using rule-only diagnosis.",
            exc_info=True,
        )
        return rule_fields


def create_followup_diagnosis_from_response(
    db: Session,
    diagnostic_response_id: UUID,
) -> DiagnosisResponse:
    """
    Re-evaluate a diagnostic answer and create an immutable follow-up diagnosis.

    The original diagnosis is never updated. The new diagnosis uses a unique
    model version derived from the diagnostic-response ID, allowing multiple
    diagnosis snapshots for the same attempt without violating the
    ``attempt_id + model_version`` uniqueness constraint.

    This deterministic Sprint 9 evaluator uses the approved diagnostic
    question and the student's answer as additional evidence. It classifies
    the response as:

    - ``confident`` when the answer reinforces the misconception;
    - ``no_misconception`` when the answer clearly states the correct concept;
    - ``insufficient`` when the answer is blank, evasive, or ambiguous.
    """

    context = _get_diagnostic_response_context_or_404(
        db=db,
        diagnostic_response_id=diagnostic_response_id,
    )

    if context.resulting_diagnosis_id is not None:
        return _build_existing_diagnosis_response(
            db=db,
            diagnosis_id=context.resulting_diagnosis_id,
        )

    original_state = _state_value(context.original_state)

    if original_state not in {
        DiagnosisState.POSSIBLE.value,
        DiagnosisState.INSUFFICIENT.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only possible or insufficient diagnoses can be "
                "re-evaluated from a diagnostic response."
            ),
        )

    if context.primary_misconception_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The original diagnosis has no primary misconception "
                "to re-evaluate."
            ),
        )

    model_version = _diagnostic_followup_model_version(
        diagnostic_response_id
    )

    existing = _get_existing_diagnosis_for_attempt(
        db=db,
        attempt_id=context.attempt_id,
        model_version=model_version,
    )

    if existing is not None:
        _link_response_to_resulting_diagnosis(
            db=db,
            diagnostic_response_id=diagnostic_response_id,
            resulting_diagnosis_id=existing.id,
        )
        return _build_existing_diagnosis_response(
            db=db,
            diagnosis_id=existing.id,
        )

    evaluation = _evaluate_diagnostic_answer(
        misconception_code=context.misconception_code,
        question_text=context.question_text,
        response_text=context.response_text,
    )

    final_state = evaluation.state
    final_confidence = evaluation.confidence
    final_next_action = evaluation.next_action
    final_decision_reason = evaluation.decision_reason

    if final_state in {
        DiagnosisState.CONFIDENT,
        DiagnosisState.POSSIBLE,
    }:
        primary_misconception_id = context.primary_misconception_id
        primary_misconception = SimpleNamespace(
            id=context.primary_misconception_id,
            code=context.misconception_code,
            name=context.misconception_name,
            topic=context.misconception_topic,
        )
    else:
        primary_misconception_id = None
        primary_misconception = None

    evidence_text = (
        f"Diagnostic question: {context.question_text} "
        f"Student response: {context.response_text}"
    )

    _validate_final_diagnosis_contract(
        state=final_state,
        misconception_code=(
            context.misconception_code
            if primary_misconception_id is not None
            else None
        ),
        confidence=final_confidence,
        evidence=[evidence_text],
    )

    diagnosis_id = uuid4()
    evidence_id = uuid4()

    try:
        db.execute(
            text(
                """
                INSERT INTO diagnoses (
                    id,
                    attempt_id,
                    state,
                    primary_misconception_id,
                    confidence,
                    model_version,
                    decision_reason,
                    next_action,
                    rule_score,
                    llm_score,
                    created_at,
                    updated_at
                )
                VALUES (
                    :id,
                    :attempt_id,
                    :state,
                    :primary_misconception_id,
                    :confidence,
                    :model_version,
                    :decision_reason,
                    :next_action,
                    :rule_score,
                    :llm_score,
                    NOW(),
                    NOW()
                )
                """
            ),
            {
                "id": diagnosis_id,
                "attempt_id": context.attempt_id,
                "state": _state_value(final_state),
                "primary_misconception_id": primary_misconception_id,
                "confidence": final_confidence,
                "model_version": model_version,
                "decision_reason": final_decision_reason,
                "next_action": _next_action_value(final_next_action),
                "rule_score": final_confidence,
                "llm_score": None,
            },
        )

        db.execute(
            text(
                """
                INSERT INTO diagnosis_evidence (
                    id,
                    diagnosis_id,
                    evidence_type,
                    rule_id,
                    evidence_text,
                    created_at
                )
                VALUES (
                    :id,
                    :diagnosis_id,
                    :evidence_type,
                    :rule_id,
                    :evidence_text,
                    NOW()
                )
                """
            ),
            {
                "id": evidence_id,
                "diagnosis_id": diagnosis_id,
                "evidence_type": "written_reasoning",
                "rule_id": (
                    context.misconception_code
                    or "DIAGNOSTIC_RESPONSE"
                ),
                "evidence_text": evidence_text,
            },
        )

        db.execute(
            text(
                """
                UPDATE diagnostic_responses
                SET
                    evaluated = TRUE,
                    evaluated_at = NOW(),
                    resulting_diagnosis_id = :resulting_diagnosis_id,
                    updated_at = NOW()
                WHERE id = :diagnostic_response_id
                  AND resulting_diagnosis_id IS NULL
                """
            ),
            {
                "resulting_diagnosis_id": diagnosis_id,
                "diagnostic_response_id": diagnostic_response_id,
            },
        )

        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Unable to create the follow-up diagnosis from the "
                "diagnostic response."
            ),
        ) from exc

    created_at = _get_diagnosis_created_at(
        db,
        diagnosis_id,
    )

    return DiagnosisResponse(
        id=diagnosis_id,
        attempt_id=context.attempt_id,
        state=final_state,
        confidence=final_confidence,
        primary_misconception=(
            MisconceptionSummary(
                id=primary_misconception.id,
                code=primary_misconception.code,
                name=primary_misconception.name,
                topic=primary_misconception.topic,
            )
            if primary_misconception is not None
            else None
        ),
        evidence=[
            DiagnosisEvidenceResponse(
                id=evidence_id,
                diagnosis_id=diagnosis_id,
                source="written_reasoning",
                strength="strong",
                text=evidence_text,
                sort_order=0,
                metadata={
                    "diagnostic_response_id": str(
                        diagnostic_response_id
                    ),
                    "diagnostic_question_id": str(
                        context.diagnostic_question_id
                    ),
                    "reevaluation": True,
                },
            )
        ],
        alternatives=[],
        model_version=model_version,
        decision_reason=final_decision_reason,
        next_action=final_next_action,
        created_at=created_at,
    )


def _get_diagnostic_response_context_or_404(
    *,
    db: Session,
    diagnostic_response_id: UUID,
) -> SimpleNamespace:
    row = db.execute(
        text(
            """
            SELECT
                dr.id AS diagnostic_response_id,
                dr.attempt_id,
                dr.diagnosis_id AS original_diagnosis_id,
                dr.diagnostic_question_id,
                dr.response_text,
                dr.resulting_diagnosis_id,
                d.state AS original_state,
                d.primary_misconception_id,
                q.question_text,
                m.code AS misconception_code,
                m.name AS misconception_name,
                m.topic AS misconception_topic
            FROM diagnostic_responses dr
            JOIN diagnoses d
                ON d.id = dr.diagnosis_id
            JOIN diagnostic_questions q
                ON q.id = dr.diagnostic_question_id
            LEFT JOIN misconceptions m
                ON m.id = d.primary_misconception_id
            WHERE dr.id = :diagnostic_response_id
            """
        ),
        {
            "diagnostic_response_id": diagnostic_response_id,
        },
    ).mappings().first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic response was not found.",
        )

    return _namespace_from_row(row)


def _diagnostic_followup_model_version(
    diagnostic_response_id: UUID,
) -> str:
    return (
        f"{MODEL_VERSION}-dq-"
        f"{str(diagnostic_response_id).replace('-', '')[:12]}"
    )


def _link_response_to_resulting_diagnosis(
    *,
    db: Session,
    diagnostic_response_id: UUID,
    resulting_diagnosis_id: UUID,
) -> None:
    try:
        db.execute(
            text(
                """
                UPDATE diagnostic_responses
                SET
                    evaluated = TRUE,
                    evaluated_at = COALESCE(evaluated_at, NOW()),
                    resulting_diagnosis_id = :resulting_diagnosis_id,
                    updated_at = NOW()
                WHERE id = :diagnostic_response_id
                """
            ),
            {
                "resulting_diagnosis_id": resulting_diagnosis_id,
                "diagnostic_response_id": diagnostic_response_id,
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "The follow-up diagnosis exists, but the diagnostic "
                "response could not be linked to it."
            ),
        ) from exc


def _evaluate_diagnostic_answer(
    *,
    misconception_code: str | None,
    question_text: str,
    response_text: str,
) -> SimpleNamespace:
    """
    Deterministically evaluate one diagnostic-question response.

    This is intentionally rule-based and bounded to the approved misconception
    taxonomy. The evaluator does not generate free-form labels.

    Matching is normalized so harmless wording differences such as
    "each recursive invocation has a separate stack frame" and
    "every active recursive call gets its own frame" are treated as the same
    conceptual evidence.
    """

    normalized_code = _normalize_code(
        misconception_code
    )
    normalized_answer = _normalize_answer_text(
        response_text
    )

    if len(normalized_answer) < 3:
        return SimpleNamespace(
            state=DiagnosisState.INSUFFICIENT,
            confidence=0.20,
            next_action=DiagnosisNextAction.ASK_CLARIFICATION,
            decision_reason=(
                "The diagnostic response was too short to provide "
                "reliable additional evidence."
            ),
        )

    correct_phrases, misconception_phrases = (
        _diagnostic_phrase_bank(
            normalized_code
        )
    )

    correct_score = _phrase_score(
        normalized_answer,
        correct_phrases,
    )
    misconception_score = _phrase_score(
        normalized_answer,
        misconception_phrases,
    )

    if (
        _answer_is_ambiguous(
            normalized_answer
        )
        and correct_score == 0
        and misconception_score == 0
    ):
        return SimpleNamespace(
            state=DiagnosisState.INSUFFICIENT,
            confidence=0.30,
            next_action=DiagnosisNextAction.ASK_CLARIFICATION,
            decision_reason=(
                "The diagnostic response remained ambiguous and did "
                "not clearly support or reject the suspected misconception."
            ),
        )

    if (
        correct_score > misconception_score
        and correct_score > 0
    ):
        return SimpleNamespace(
            state=DiagnosisState.NO_MISCONCEPTION,
            confidence=min(
                0.95,
                0.82
                + (
                    0.04
                    * correct_score
                ),
            ),
            next_action=DiagnosisNextAction.NO_ACTION,
            decision_reason=(
                "The diagnostic response clearly states the correct "
                f"concept for {normalized_code or 'the suspected misconception'}."
            ),
        )

    if (
        misconception_score > correct_score
        and misconception_score > 0
    ):
        return SimpleNamespace(
            state=DiagnosisState.CONFIDENT,
            confidence=min(
                0.95,
                0.82
                + (
                    0.04
                    * misconception_score
                ),
            ),
            next_action=DiagnosisNextAction.SHOW_HINT,
            decision_reason=(
                "The diagnostic response reinforces the suspected "
                f"{normalized_code or 'misconception'}."
            ),
        )

    if (
        correct_score > 0
        and misconception_score > 0
    ):
        return SimpleNamespace(
            state=DiagnosisState.INSUFFICIENT,
            confidence=0.40,
            next_action=DiagnosisNextAction.ASK_CLARIFICATION,
            decision_reason=(
                "The diagnostic response contains conflicting conceptual "
                "signals and cannot be resolved reliably."
            ),
        )

    return SimpleNamespace(
        state=DiagnosisState.INSUFFICIENT,
        confidence=0.35,
        next_action=DiagnosisNextAction.ASK_CLARIFICATION,
        decision_reason=(
            "The diagnostic response did not contain enough targeted "
            "evidence to resolve the possible diagnosis."
        ),
    )


def _normalize_answer_text(
    value: str,
) -> str:
    normalized = value.strip().lower()

    normalized = re.sub(
        r"[^a-z0-9_+\-<>=*]+",
        " ",
        normalized,
    )

    return re.sub(
        r"\s+",
        " ",
        normalized,
    ).strip()


def _phrase_score(
    answer: str,
    phrases: set[str],
) -> int:
    """
    Count distinct approved phrase matches after applying the same text
    normalization to both the answer and phrase bank.

    Sprint 9 hardening:
    misconception phrases are not counted when the matched concept is
    immediately negated by the student. This avoids false positives such as:

    - "recursive calls do not share one stack frame"
    - "local variables are not stored on the heap"
    - "the caller variables do not change automatically"
    """

    score = 0

    for phrase in phrases:
        normalized_phrase = (
            _normalize_answer_text(
                phrase
            )
        )

        if not normalized_phrase:
            continue

        start = 0

        while True:
            index = answer.find(
                normalized_phrase,
                start,
            )

            if index < 0:
                break

            if not _match_is_locally_negated(
                answer=answer,
                match_start=index,
            ):
                score += 1
                break

            start = (
                index
                + len(normalized_phrase)
            )

    return score


def _match_is_locally_negated(
    *,
    answer: str,
    match_start: int,
) -> bool:
    """
    Return True when an approved phrase match is preceded by a nearby
    negation token.

    The window is intentionally small so unrelated earlier words such as
    "not sure" do not suppress later affirmative evidence.
    """

    window_start = max(
        0,
        match_start - 48,
    )

    prefix = answer[
        window_start:match_start
    ]

    negation_patterns = [
        r"\\bnot\\b",
        r"\\bnever\\b",
        r"\\bno\\b",
        r"\\bcannot\\b",
        r"\\bcan t\\b",
        r"\\bdo not\\b",
        r"\\bdon t\\b",
        r"\\bdoes not\\b",
        r"\\bdoesn t\\b",
        r"\\bare not\\b",
        r"\\baren t\\b",
        r"\\bis not\\b",
        r"\\bisn t\\b",
        r"\\bwill not\\b",
        r"\\bwon t\\b",
    ]

    return any(
        re.search(
            pattern,
            prefix,
        )
        for pattern in negation_patterns
    )


def _answer_is_ambiguous(answer: str) -> bool:
    ambiguous_phrases = {
        "i don't know",
        "i do not know",
        "not sure",
        "maybe",
        "probably",
        "it depends",
        "unsure",
        "no idea",
    }

    return any(
        phrase in answer
        for phrase in ambiguous_phrases
    )


def _diagnostic_phrase_bank(
    misconception_code: str | None,
) -> tuple[set[str], set[str]]:
    """
    Return approved deterministic phrase banks for diagnostic re-evaluation.

    The phrases intentionally include common paraphrases observed in student
    explanations while remaining narrow enough to avoid free-form semantic
    guessing.
    """

    banks: dict[
        str,
        tuple[
            set[str],
            set[str],
        ],
    ] = {
        "M1": (
            {
                "must be sorted",
                "array must be sorted",
                "input must be sorted",
                "binary search requires sorted",
                "binary search requires a sorted array",
                "sort the array first",
                "cannot use binary search directly on unsorted data",
                "use linear search on the unsorted array",
                "use linear search for unsorted input",
                "linear search is appropriate for unsorted data",
                "binary search depends on sorted order",
                "binary search only works on sorted data",
            },
            {
                "works on unsorted",
                "binary search works on unsorted data",
                "does not need to be sorted",
                "binary search any array",
                "sorting is not required for binary search",
            },
        ),
        "M2": (
            {
                "base case",
                "stopping condition",
                "returns without another call",
                "must stop before another recursive call",
                "n <= 1",
                "n == 0",
                "n == 1",
                "return directly",
                "return without another recursive call",
                "explicit base case",
            },
            {
                "does not need a base case",
                "recursion stops automatically",
                "will stop by itself",
                "recursive calls stop automatically",
            },
        ),
        "M3": (
            {
                "reduce the problem",
                "smaller argument",
                "smaller input",
                "n - 1",
                "decreasing argument",
                "moves toward the base case",
                "recursive call must make progress",
                "recursive call uses n - 1",
                "recursive call uses a smaller value",
                "problem size decreases on each recursive call",
            },
            {
                "same argument",
                "same value recursively",
                "does not need to decrease",
                "recursive call can use the same argument",
                "problem size does not need to change",
            },
        ),
        "M4": (
            {
                "local parameters",
                "local copies",
                "caller variables do not change",
                "original variables do not change",
                "does not change the caller",
                "pass by value",
                "use pointers",
                "uses pointers",
                "pass addresses",
                "passes addresses",
                "dereference",
                "dereferences",
                "return the swapped values",
                "returns the swapped values",
                "local parameter changes do not change the caller variables",
                "changing local parameters does not change the original variables",
                "caller variables remain unchanged",
                "use addresses",
                "modify through pointers",
            },
            {
                "caller variables change automatically",
                "original variables change automatically",
                "changing local parameters changes the caller",
                "changing parameters changes the caller",
                "x and y change the originals",
                "local reassignment changes the original variables",
            },
        ),
        "M5": (
            {
                "each call has its own stack frame",
                "each recursive call has its own stack frame",
                "each recursive call has its own frame",
                "each invocation has its own stack frame",
                "each recursive invocation has its own stack frame",
                "every active recursive call has its own stack frame",
                "every recursive call gets its own stack frame",
                "recursive calls have separate stack frames",
                "recursive calls do not share one stack frame",
                "recursive calls do not reuse the same stack frame",
                "separate stack frame",
                "separate stack frames",
                "locals are removed when the call returns",
                "local variables are removed when the call returns",
                "locals are destroyed when the call returns",
                "local variables do not remain alive after return",
                "local variables do not remain alive on the heap",
                "ordinary local variables are not stored on the heap",
                "stack frame is removed",
                "stack frame is popped",
                "frame is removed when the call returns",
                "frames are removed in reverse order",
                "local variables belong to that call",
                "parameters and local variables are stored in that stack frame",
            },
            {
                "reuse the same stack frame",
                "reuses the same stack frame",
                "recursive calls reuse the same stack frame",
                "recursive calls reuse one stack frame",
                "recursive calls share the same stack frame",
                "all recursive calls share one stack frame",
                "only one stack frame",
                "single stack frame",
                "locals stay after return",
                "locals remain after return",
                "local variables remain after the function returns",
                "stack variables survive after return",
                "recursive locals are on the heap",
                "recursive local variables are on the heap",
                "recursive locals are stored on the heap",
                "all recursive local variables are stored on the heap",
                "all locals are stored on the heap",
                "local variables are stored on the heap",
                "local variables remain alive on the heap",
                "locals remain alive on the heap",
            },
        ),
    }

    return banks.get(
        misconception_code or "",
        (
            set(),
            set(),
        ),
    )




def _apply_supported_correction_fallback(
    *,
    problem_code: str | None,
    allowed_codes: set[str],
    signals: Any,
    rule_result: Any,
) -> Any:
    """
    Promote a fully corrected P1-P4 retry when the generic detector returns
    INSUFFICIENT despite complete structured corrective evidence.

    This is deliberately conservative:
    - it never overrides a supported misconception diagnosis;
    - it never overrides an existing NO_MISCONCEPTION result;
    - it only runs for the fixed MVP mappings P1-P4;
    - it relies on structured extractor booleans/evidence, not raw keywords.
    """

    detected_code = _normalize_code(
        getattr(
            rule_result,
            "misconception_code",
            None,
        )
    )
    state_value = _state_value(
        getattr(
            rule_result,
            "state",
            DiagnosisState.INSUFFICIENT,
        )
    )

    if detected_code is not None:
        return rule_result

    if state_value != DiagnosisState.INSUFFICIENT.value:
        return rule_result

    evidence = list(
        getattr(
            signals,
            "evidence",
            [],
        )
    )

    # P1 / M1:
    # Unsorted problem + explicit rejection of binary search + sequential
    # linear-search implementation.
    if problem_code == "P1" and "M1" in allowed_codes:
        explicitly_rejects_binary = any(
            (
                "binary search should not be used directly" in str(
                    getattr(item, "text", "")
                ).lower()
                or "binary search should not be used" in str(
                    getattr(item, "text", "")
                ).lower()
            )
            for item in evidence
        )

        if (
            bool(getattr(signals, "problem_array_is_unsorted", False))
            and bool(getattr(signals, "code_uses_linear_search", False))
            and not bool(getattr(signals, "code_uses_binary_search", False))
            and not bool(
                getattr(
                    signals,
                    "reasoning_mentions_binary_search",
                    False,
                )
            )
            and explicitly_rejects_binary
        ):
            return SimpleNamespace(
                misconception_code=None,
                state=DiagnosisState.NO_MISCONCEPTION,
                confidence=0.95,
                evidence=evidence,
                alternative_misconception_codes=[],
                decision_reason=(
                    "The corrected P1 retry recognizes that binary search "
                    "requires sorted order and uses a sequential linear search "
                    "for the unsorted input."
                ),
                next_action=DiagnosisNextAction.NO_ACTION,
            )

    # P2/P3 / M2-M3:
    # Correct recursion requires both a base case and verified progress toward
    # that base case.
    if (
        problem_code in {"P2", "P3"}
        and bool({"M2", "M3"} & allowed_codes)
        and bool(getattr(signals, "recursive_call_detected", False))
        and bool(getattr(signals, "base_case_detected", False))
        and bool(
            getattr(
                signals,
                "recursive_call_decreasing_argument",
                False,
            )
        )
        and not bool(getattr(signals, "missing_base_case", False))
        and not bool(
            getattr(
                signals,
                "recursive_call_same_argument",
                False,
            )
        )
        and not bool(
            getattr(
                signals,
                "recursive_call_increasing_argument",
                False,
            )
        )
    ):
        return SimpleNamespace(
            misconception_code=None,
            state=DiagnosisState.NO_MISCONCEPTION,
            confidence=0.95,
            evidence=evidence,
            alternative_misconception_codes=[],
            decision_reason=(
                "The corrected recursive implementation contains an explicit "
                "stopping condition and reduces the recursive argument toward "
                "termination."
            ),
            next_action=DiagnosisNextAction.NO_ACTION,
        )

    # P4 / M4:
    # Correct caller-visible mutation can be demonstrated by explicit
    # pass-by-value understanding plus a pointer/return mechanism.
    if problem_code == "P4" and "M4" in allowed_codes:
        correct_semantics = bool(
            getattr(
                signals,
                "correct_parameter_semantics_understood",
                False,
            )
        )
        correct_mechanism = any(
            (
                bool(
                    getattr(
                        signals,
                        "pointer_based_swap_detected",
                        False,
                    )
                ),
                bool(
                    getattr(
                        signals,
                        "return_based_swap_detected",
                        False,
                    )
                ),
            )
        )

        if (
            correct_semantics
            and correct_mechanism
            and not bool(
                getattr(
                    signals,
                    "parameter_reassignment_claims_caller_mutation",
                    False,
                )
            )
            and not bool(
                getattr(
                    signals,
                    "pass_by_value_confusion_detected",
                    False,
                )
            )
            and not bool(
                getattr(
                    signals,
                    "swap_uses_only_local_reassignment",
                    False,
                )
            )
        ):
            return SimpleNamespace(
                misconception_code=None,
                state=DiagnosisState.NO_MISCONCEPTION,
                confidence=0.95,
                evidence=evidence,
                alternative_misconception_codes=[],
                decision_reason=(
                    "The corrected P4 retry distinguishes local parameter "
                    "changes from caller-visible mutation and uses an approved "
                    "pointer/address or return-value mechanism."
                ),
                next_action=DiagnosisNextAction.NO_ACTION,
            )

    return rule_result

def _apply_m5_evidence_fallback(
    *,
    problem_code: str | None,
    allowed_codes: set[str],
    signals: Any,
    rule_result: Any,
) -> Any:
    """
    Promote explicit P5/M5 evidence when the generic detector under-classifies it.

    This fallback exists only for the approved P5 -> M5 taxonomy and only uses
    deterministic booleans emitted by ``extract_evidence``. The extractor is
    responsible for negation handling; this fallback must never infer M5 from
    raw keyword presence alone.

    Promotion rules:
    - two or more explicit M5 misconception signals -> confident / show_hint;
    - one explicit M5 misconception signal -> possible / diagnostic question;
    - otherwise preserve the detector result unchanged.

    Existing detector output for a supported misconception always wins.
    """

    detected_code = _normalize_code(
        getattr(
            rule_result,
            "misconception_code",
            None,
        )
    )

    if (
        problem_code != "P5"
        or "M5" not in allowed_codes
        or detected_code is not None
    ):
        return rule_result

    signal_names = [
        "stack_heap_confusion_detected",
        "single_stack_frame_claim_detected",
        "locals_survive_return_claim_detected",
        "recursive_locals_on_heap_claim_detected",
    ]

    matched_signal_names = [
        name
        for name in signal_names
        if bool(
            getattr(
                signals,
                name,
                False,
            )
        )
    ]

    # stack_heap_confusion_detected is an aggregate signal in the hardened
    # extractor, so do not double-count it when a more specific signal exists.
    specific_signal_names = [
        name
        for name in matched_signal_names
        if name != "stack_heap_confusion_detected"
    ]

    signal_count = len(
        specific_signal_names
        or matched_signal_names
    )

    if signal_count == 0:
        return rule_result

    m5_evidence = [
        item
        for item in list(
            getattr(
                signals,
                "evidence",
                [],
            )
        )
        if (
            "stack frame" in str(
                getattr(
                    item,
                    "text",
                    "",
                )
            ).lower()
            or "heap" in str(
                getattr(
                    item,
                    "text",
                    "",
                )
            ).lower()
            or "local variables survive" in str(
                getattr(
                    item,
                    "text",
                    "",
                )
            ).lower()
        )
    ]

    if signal_count >= 2:
        return SimpleNamespace(
            misconception_code="M5",
            state=DiagnosisState.CONFIDENT,
            confidence=0.92,
            evidence=(
                m5_evidence
                or list(
                    getattr(
                        signals,
                        "evidence",
                        [],
                    )
                )
            ),
            alternative_misconception_codes=[],
            decision_reason=(
                "Multiple explicit M5 memory-model signals were observed: "
                + ", ".join(
                    specific_signal_names
                    or matched_signal_names
                )
                + "."
            ),
            next_action=DiagnosisNextAction.SHOW_HINT,
        )

    return SimpleNamespace(
        misconception_code="M5",
        state=DiagnosisState.POSSIBLE,
        confidence=0.62,
        evidence=(
            m5_evidence
            or list(
                getattr(
                    signals,
                    "evidence",
                    [],
                )
            )
        ),
        alternative_misconception_codes=[],
        decision_reason=(
            "One explicit M5 memory-model signal was observed, but additional "
            "evidence is required before committing to a confident diagnosis."
        ),
        next_action=DiagnosisNextAction.ASK_DIAGNOSTIC_QUESTION,
    )


def _validate_final_diagnosis_contract(
    *,
    state: DiagnosisState,
    misconception_code: str | None,
    confidence: float,
    evidence: list[Any],
) -> None:
    """
    Enforce the structured diagnosis contract before writing to the database.

    A confident or possible diagnosis must identify a misconception. A
    no-misconception or insufficient result must not carry one. Confident
    diagnoses must include observable evidence.
    """

    normalized_state = _state_value(state)

    if not 0.0 <= float(confidence) <= 1.0:
        raise HTTPException(
            status_code=500,
            detail="Diagnosis confidence must be between 0 and 1.",
        )

    if normalized_state in {
        DiagnosisState.CONFIDENT.value,
        DiagnosisState.POSSIBLE.value,
    } and not misconception_code:
        raise HTTPException(
            status_code=500,
            detail=(
                "Confident or possible diagnosis requires a "
                "misconception code."
            ),
        )

    if normalized_state in {
        DiagnosisState.NO_MISCONCEPTION.value,
        DiagnosisState.INSUFFICIENT.value,
    } and misconception_code:
        raise HTTPException(
            status_code=500,
            detail=(
                "No-misconception or insufficient diagnosis must not "
                "carry a misconception code."
            ),
        )

    if (
        normalized_state == DiagnosisState.CONFIDENT.value
        and not evidence
    ):
        raise HTTPException(
            status_code=500,
            detail=(
                "Confident diagnosis requires at least one observable "
                "evidence item."
            ),
        )


def _get_allowed_misconception_codes(problem: SimpleNamespace) -> set[str]:
    """
    Return the misconception codes that are valid for the selected problem.

    The current MVP uses a seeded problem bank. Keeping this allowlist in the
    service layer provides a final safety boundary even when an extractor or
    detector emits a cross-topic false positive.
    """
    problem_code = _normalize_code(getattr(problem, "code", None))

    if problem_code and problem_code in PROBLEM_MISCONCEPTION_ALLOWLIST:
        return set(PROBLEM_MISCONCEPTION_ALLOWLIST[problem_code])

    rule_context = getattr(problem, "rule_context", {}) or {}
    configured_codes = rule_context.get("misconception_codes", [])

    if isinstance(configured_codes, str):
        configured_codes = [configured_codes]

    if isinstance(configured_codes, list):
        normalized_codes = {
            code
            for code in (_normalize_code(item) for item in configured_codes)
            if code
        }
        if normalized_codes:
            return normalized_codes

    return set()


def _unsupported_detection_reason(
    problem_code: str,
    detected_code: str | None,
    allowed_codes: set[str],
) -> str:
    normalized_problem_code = _normalize_code(problem_code) or "UNKNOWN"
    allowed_label = ", ".join(sorted(allowed_codes)) or "none"

    if detected_code:
        return (
            f"Detector produced {detected_code}, but problem "
            f"{normalized_problem_code} only supports: {allowed_label}. "
            "The cross-topic result was rejected."
        )

    return (
        f"No supported misconception signal was detected for problem "
        f"{normalized_problem_code}. Allowed codes: {allowed_label}."
    )


def _normalize_code(value: Any) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip().upper()
    return normalized or None


def _state_value(state: Any) -> str:
    value = getattr(state, "value", state)
    return str(value).strip().lower()


def _next_action_value(next_action: Any) -> str:
    value = getattr(next_action, "value", next_action)
    return str(value).strip().lower()


def _get_existing_diagnosis_for_attempt(
    db: Session,
    attempt_id: UUID,
    model_version: str,
) -> SimpleNamespace | None:
    row = db.execute(
        text(
            """
            SELECT
                id,
                attempt_id,
                state,
                primary_misconception_id,
                confidence,
                model_version,
                decision_reason,
                next_action,
                rule_score,
                llm_score,
                created_at
            FROM diagnoses
            WHERE attempt_id = :attempt_id
              AND model_version = :model_version
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {
            "attempt_id": attempt_id,
            "model_version": model_version,
        },
    ).mappings().first()

    if row is None:
        return None

    return _namespace_from_row(row)


def _build_existing_diagnosis_response(
    db: Session,
    diagnosis_id: UUID,
) -> DiagnosisResponse:
    diagnosis = _get_diagnosis_or_404(db=db, diagnosis_id=diagnosis_id)

    evidence = _get_existing_evidence_for_diagnosis(
        db=db,
        diagnosis_id=diagnosis.id,
    )

    alternatives = _get_existing_alternatives_for_diagnosis(
        db=db,
        diagnosis_id=diagnosis.id,
    )

    primary_misconception = None

    if diagnosis.primary_misconception_id is not None:
        primary_misconception = MisconceptionSummary(
            id=diagnosis.primary_misconception_id,
            code=diagnosis.misconception_code,
            name=diagnosis.misconception_name,
            topic=diagnosis.misconception_topic,
        )

    return DiagnosisResponse(
        id=diagnosis.id,
        attempt_id=diagnosis.attempt_id,
        state=diagnosis.state,
        confidence=diagnosis.confidence or 0.0,
        primary_misconception=primary_misconception,
        evidence=evidence,
        alternatives=alternatives,
        model_version=diagnosis.model_version or MODEL_VERSION,
        decision_reason=(
            diagnosis.decision_reason
            or _existing_diagnosis_reason(
                state=diagnosis.state,
                has_primary_misconception=primary_misconception is not None,
            )
        ),
        next_action=(
            diagnosis.next_action
            or _next_action_for_existing_diagnosis(
                state=diagnosis.state,
                confidence=diagnosis.confidence,
                has_primary_misconception=primary_misconception is not None,
            )
        ),
        created_at=diagnosis.created_at,
    )


def _get_diagnosis_or_404(
    db: Session,
    diagnosis_id: UUID,
) -> SimpleNamespace:
    row = db.execute(
        text(
            """
            SELECT
                d.id,
                d.attempt_id,
                d.state,
                d.primary_misconception_id,
                d.confidence,
                d.model_version,
                d.decision_reason,
                d.next_action,
                d.rule_score,
                d.llm_score,
                d.created_at,
                m.code AS misconception_code,
                m.name AS misconception_name,
                m.topic AS misconception_topic
            FROM diagnoses d
            LEFT JOIN misconceptions m
                ON d.primary_misconception_id = m.id
            WHERE d.id = :diagnosis_id
            """
        ),
        {"diagnosis_id": diagnosis_id},
    ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Diagnosis not found.")

    return _namespace_from_row(row)


def _get_existing_evidence_for_diagnosis(
    db: Session,
    diagnosis_id: UUID,
) -> list[DiagnosisEvidenceResponse]:
    rows = db.execute(
        text(
            """
            SELECT
                id,
                diagnosis_id,
                evidence_type,
                rule_id,
                evidence_text,
                created_at
            FROM diagnosis_evidence
            WHERE diagnosis_id = :diagnosis_id
            ORDER BY created_at ASC, id ASC
            """
        ),
        {"diagnosis_id": diagnosis_id},
    ).mappings().all()

    evidence_responses: list[DiagnosisEvidenceResponse] = []

    for index, row in enumerate(rows):
        evidence_responses.append(
            DiagnosisEvidenceResponse(
                id=row["id"],
                diagnosis_id=row["diagnosis_id"],
                source=row["evidence_type"],
                strength="strong",
                text=row["evidence_text"],
                sort_order=index,
                metadata={
                    "rule_id": row["rule_id"],
                    "returned_from_existing_diagnosis": True,
                },
            )
        )

    return evidence_responses


def _get_existing_alternatives_for_diagnosis(
    db: Session,
    diagnosis_id: UUID,
) -> list[DiagnosisAlternativeResponse]:
    rows = db.execute(
        text(
            """
            SELECT
                da.id,
                da.diagnosis_id,
                da.misconception_id,
                da.confidence,
                da.created_at,
                m.code,
                m.name,
                m.topic
            FROM diagnosis_alternatives da
            JOIN misconceptions m
                ON da.misconception_id = m.id
            WHERE da.diagnosis_id = :diagnosis_id
            ORDER BY da.created_at ASC, da.id ASC
            """
        ),
        {"diagnosis_id": diagnosis_id},
    ).mappings().all()

    alternative_responses: list[DiagnosisAlternativeResponse] = []

    for row in rows:
        alternative_responses.append(
            DiagnosisAlternativeResponse(
                id=row["id"],
                diagnosis_id=row["diagnosis_id"],
                misconception=MisconceptionSummary(
                    id=row["misconception_id"],
                    code=row["code"],
                    name=row["name"],
                    topic=row["topic"],
                ),
                confidence=row["confidence"],
                reason="Existing alternative misconception returned from saved diagnosis.",
            )
        )

    return alternative_responses



def _existing_diagnosis_reason(
    state: str,
    has_primary_misconception: bool,
) -> str:
    normalized_state = str(state).strip().lower()

    if normalized_state == DiagnosisState.NO_MISCONCEPTION.value:
        return (
            "Existing no-misconception diagnosis returned. Duplicate diagnosis "
            "creation was skipped for this attempt."
        )

    if has_primary_misconception:
        return (
            "Existing misconception diagnosis returned. Duplicate diagnosis "
            "creation was skipped for this attempt."
        )

    return (
        "Existing diagnosis returned. Duplicate diagnosis creation was skipped "
        "for this attempt."
    )

def _next_action_for_existing_diagnosis(
    state: str,
    confidence: float | None,
    has_primary_misconception: bool,
) -> DiagnosisNextAction:
    normalized_state = str(state).strip().lower()

    if normalized_state == DiagnosisState.NO_MISCONCEPTION.value:
        return DiagnosisNextAction.NO_ACTION

    if (
        normalized_state == DiagnosisState.CONFIDENT.value
        and has_primary_misconception
    ):
        return DiagnosisNextAction.SHOW_HINT

    if normalized_state == DiagnosisState.POSSIBLE.value:
        return DiagnosisNextAction.ASK_DIAGNOSTIC_QUESTION

    if normalized_state == DiagnosisState.INSUFFICIENT.value:
        return DiagnosisNextAction.ASK_CLARIFICATION

    if confidence is not None and confidence >= 0.45:
        return DiagnosisNextAction.ASK_DIAGNOSTIC_QUESTION

    return DiagnosisNextAction.NO_ACTION


def _get_attempt_or_404(db: Session, attempt_id: UUID) -> SimpleNamespace:
    """
    Load the complete attempt contract required by the diagnosis pipeline.

    Sprint 10 includes normalized reasoning plus multimodal/language metadata.
    The evidence extractor decides which reasoning representation contributes
    to deterministic misconception signals; this service keeps the original
    attempt data intact.
    """

    row = db.execute(
        text(
            """
            SELECT
                id,
                student_alias_id,
                problem_id,
                parent_attempt_id,
                retry_number,
                final_answer,
                written_reasoning,
                normalized_reasoning,
                source_code,
                speech_transcript,
                speech_audio_reference,
                speech_audio_retained,
                speech_processing_status,
                input_modality,
                input_language,
                detected_language,
                selected_language,
                response_time_seconds,
                created_at,
                updated_at
            FROM attempts
            WHERE id = :attempt_id
            """
        ),
        {"attempt_id": attempt_id},
    ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Attempt not found.")

    return _namespace_from_row(row)


def _get_problem_or_404(db: Session, problem_id: UUID) -> SimpleNamespace:
    row = db.execute(
        text(
            """
            SELECT
                id,
                code,
                title,
                topic,
                statement,
                difficulty,
                expected_language,
                rule_context,
                created_at
            FROM problems
            WHERE id = :problem_id
            """
        ),
        {"problem_id": problem_id},
    ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Problem not found.")

    return _namespace_from_row(row)


def _get_misconception_by_code_or_404(
    db: Session,
    code: str,
) -> SimpleNamespace:
    row = db.execute(
        text(
            """
            SELECT
                id,
                code,
                name,
                topic
            FROM misconceptions
            WHERE code = :code
            """
        ),
        {"code": code},
    ).mappings().first()

    if row is None:
        raise HTTPException(
            status_code=500,
            detail=f"Misconception code {code} is not seeded in database.",
        )

    return _namespace_from_row(row)


def _get_diagnosis_created_at(db: Session, diagnosis_id: UUID) -> Any:
    row = db.execute(
        text(
            """
            SELECT created_at
            FROM diagnoses
            WHERE id = :diagnosis_id
            """
        ),
        {"diagnosis_id": diagnosis_id},
    ).mappings().first()

    if row is None:
        raise HTTPException(
            status_code=500,
            detail="Diagnosis was not saved correctly.",
        )

    return row["created_at"]


def _alternative_confidence(primary_confidence: float) -> float:
    if primary_confidence >= 0.90:
        return 0.55

    if primary_confidence >= 0.75:
        return 0.50

    return 0.45


def _namespace_from_row(row: Any) -> SimpleNamespace:
    data = dict(row)

    if "rule_context" in data:
        data["rule_context"] = _normalize_rule_context(data["rule_context"])

    return SimpleNamespace(**data)


def _normalize_rule_context(value: Any) -> dict[str, Any]:
    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}

        if isinstance(parsed, dict):
            return parsed

    return {}

__all__ = [
    "MODEL_VERSION",
    "PROBLEM_MISCONCEPTION_ALLOWLIST",
    "create_diagnosis_from_attempt",
    "create_followup_diagnosis_from_response",
]