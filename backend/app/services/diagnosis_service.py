from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

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


MODEL_VERSION = "rule-v1.4"


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

    Sprint 8 integration:
    - Restricts each problem to its configured misconception taxonomy.
    - Persists M4/M5 rule results using the same evidence-backed contract.
    - Uses rule-v1.4 so new Sprint 8 diagnoses do not collide with prior
      rule-v1.3 results for the same attempt.
    """

    attempt = _get_attempt_or_404(db, attempt_id)

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
                rule_score,
                llm_score,
                created_at
            )
            VALUES (
                :id,
                :attempt_id,
                :state,
                :primary_misconception_id,
                :confidence,
                :model_version,
                :rule_score,
                :llm_score,
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
            "model_version": MODEL_VERSION,
            "rule_score": final_confidence,
            "llm_score": None,
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
        model_version=MODEL_VERSION,
        decision_reason=final_decision_reason,
        next_action=final_next_action,
        created_at=created_at,
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
        decision_reason=_existing_diagnosis_reason(
            state=diagnosis.state,
            has_primary_misconception=primary_misconception is not None,
        ),
        next_action=_next_action_for_existing_diagnosis(
            state=diagnosis.state,
            confidence=diagnosis.confidence,
            has_primary_misconception=primary_misconception is not None,
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
    row = db.execute(
        text(
            """
            SELECT
                id,
                student_alias_id,
                problem_id,
                final_answer,
                written_reasoning,
                source_code,
                speech_transcript,
                selected_language,
                response_time_seconds,
                created_at
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