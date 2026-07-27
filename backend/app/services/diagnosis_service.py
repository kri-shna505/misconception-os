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
    DiagnosisResponse,
    MisconceptionSummary,
)
from app.services.evidence_extractor import extract_evidence
from app.services.rule_detector import detect_misconception


MODEL_VERSION = "rule-v1"


def create_diagnosis_from_attempt(
    db: Session,
    attempt_id: UUID,
) -> DiagnosisResponse:
    """
    Create an evidence-backed rule diagnosis from an existing saved attempt.

    Sprint 4 scope:
    - M1 Binary Search on Unsorted Data
    - M2 Missing or Incorrect Recursion Base Case
    - M3 Recursive Call Without Reducing Problem Size

    Sprint 4.1 hardening:
    - If an attempt already has a diagnosis, return the latest existing diagnosis.
    - Do not create duplicate diagnosis rows for accidental repeated calls.

    This service is aligned with the current database schema:
    - diagnoses
    - diagnosis_evidence
    - diagnosis_alternatives
    """

    attempt = _get_attempt_or_404(db, attempt_id)

    existing_diagnosis = _get_existing_diagnosis_for_attempt(
        db=db,
        attempt_id=attempt.id,
    )

    if existing_diagnosis is not None:
        return _build_existing_diagnosis_response(
            db=db,
            diagnosis_id=existing_diagnosis.id,
        )

    problem = _get_problem_or_404(db, attempt.problem_id)

    signals = extract_evidence(attempt, problem)
    rule_result = detect_misconception(signals)

    primary_misconception = None
    primary_misconception_id = None

    if rule_result.misconception_code:
        primary_misconception = _get_misconception_by_code_or_404(
            db=db,
            code=rule_result.misconception_code,
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
            "state": rule_result.state.value,
            "primary_misconception_id": primary_misconception_id,
            "confidence": rule_result.confidence,
            "model_version": MODEL_VERSION,
            "rule_score": rule_result.confidence,
            "llm_score": None,
        },
    )

    evidence_responses: list[DiagnosisEvidenceResponse] = []

    for index, evidence in enumerate(rule_result.evidence):
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
                "rule_id": rule_result.misconception_code or "INSUFFICIENT",
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

    for alternative_code in rule_result.alternative_misconception_codes:
        alternative_misconception = _get_misconception_by_code_or_404(
            db=db,
            code=alternative_code,
        )
        alternative_id = uuid4()
        alternative_confidence = _alternative_confidence(rule_result.confidence)

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

    db.commit()

    created_at = _get_diagnosis_created_at(db, diagnosis_id)

    return DiagnosisResponse(
        id=diagnosis_id,
        attempt_id=attempt.id,
        state=rule_result.state,
        confidence=rule_result.confidence,
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
        decision_reason=rule_result.decision_reason,
        next_action=rule_result.next_action,
        created_at=created_at,
    )


def _get_existing_diagnosis_for_attempt(
    db: Session,
    attempt_id: UUID,
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
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"attempt_id": attempt_id},
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
        decision_reason="Existing diagnosis returned. Duplicate diagnosis creation was skipped for this attempt.",
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


def _next_action_for_existing_diagnosis(
    state: str,
    confidence: float | None,
    has_primary_misconception: bool,
) -> str:
    if state == "confident" and has_primary_misconception:
        return "show_hint"

    if confidence is not None and confidence >= 0.45:
        return "ask_diagnostic_question"

    return "request_more_evidence"


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