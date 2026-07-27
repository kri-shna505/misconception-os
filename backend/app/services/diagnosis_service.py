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

    This service is aligned with the current database schema:
    - diagnoses
    - diagnosis_evidence
    - diagnosis_alternatives
    """

    attempt = _get_attempt_or_404(db, attempt_id)
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