from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Diagnosis(Base):
    """
    Stores one structured diagnosis generated for a student attempt.

    The diagnosis records:

    - the diagnostic state;
    - the selected misconception, when applicable;
    - the evidence-derived confidence score;
    - the model or rule-engine version;
    - the recommended next intervention;
    - optional rule and LLM component scores.

    Sprint 9 intervention support:

    - ``possible`` diagnoses may lead to a diagnostic question;
    - ``confident`` diagnoses may lead to progressive hints;
    - ``insufficient`` diagnoses require clarification;
    - ``no_misconception`` diagnoses require no intervention.

    Only one diagnosis may exist for the same attempt and model version.
    A newer model version may create a separate diagnosis for the same attempt.
    """

    __tablename__ = "diagnoses"

    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "model_version",
            name="uq_diagnoses_attempt_model_version",
        ),
        Index(
            "ix_diagnoses_state_created_at",
            "state",
            "created_at",
        ),
        Index(
            "ix_diagnoses_misconception_created_at",
            "primary_misconception_id",
            "created_at",
        ),
        Index(
            "ix_diagnoses_model_version_created_at",
            "model_version",
            "created_at",
        ),
        Index(
            "ix_diagnoses_next_action_created_at",
            "next_action",
            "created_at",
        ),
        Index(
            "ix_diagnoses_attempt_created_at",
            "attempt_id",
            "created_at",
        ),
        Index(
            "ix_diagnoses_attempt_state",
            "attempt_id",
            "state",
        ),
        Index(
            "ix_diagnoses_state_next_action",
            "state",
            "next_action",
        ),
        CheckConstraint(
            (
                "state IN ("
                "'confident', "
                "'possible', "
                "'insufficient', "
                "'no_misconception'"
                ")"
            ),
            name="ck_diagnoses_valid_state",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_diagnoses_confidence_range",
        ),
        CheckConstraint(
            (
                "rule_score IS NULL "
                "OR (rule_score >= 0.0 AND rule_score <= 1.0)"
            ),
            name="ck_diagnoses_rule_score_range",
        ),
        CheckConstraint(
            (
                "llm_score IS NULL "
                "OR (llm_score >= 0.0 AND llm_score <= 1.0)"
            ),
            name="ck_diagnoses_llm_score_range",
        ),
        CheckConstraint(
            (
                "next_action IN ("
                "'show_hint', "
                "'ask_diagnostic_question', "
                "'ask_clarification', "
                "'no_action'"
                ")"
            ),
            name="ck_diagnoses_valid_next_action",
        ),
        CheckConstraint(
            (
                "("
                "state IN ('confident', 'possible') "
                "AND primary_misconception_id IS NOT NULL"
                ") "
                "OR "
                "("
                "state IN ('insufficient', 'no_misconception') "
                "AND primary_misconception_id IS NULL"
                ")"
            ),
            name="ck_diagnoses_state_misconception_consistency",
        ),
        CheckConstraint(
            (
                "("
                "state = 'confident' "
                "AND confidence >= 0.75"
                ") "
                "OR "
                "("
                "state = 'possible' "
                "AND confidence >= 0.45 "
                "AND confidence < 0.75"
                ") "
                "OR "
                "("
                "state = 'insufficient' "
                "AND confidence < 0.45"
                ") "
                "OR "
                "("
                "state = 'no_misconception' "
                "AND confidence >= 0.75"
                ")"
            ),
            name="ck_diagnoses_state_confidence_consistency",
        ),
        CheckConstraint(
            (
                "("
                "state = 'confident' "
                "AND next_action = 'show_hint'"
                ") "
                "OR "
                "("
                "state = 'possible' "
                "AND next_action = 'ask_diagnostic_question'"
                ") "
                "OR "
                "("
                "state = 'insufficient' "
                "AND next_action IN ("
                "'ask_clarification', "
                "'ask_diagnostic_question'"
                ")"
                ") "
                "OR "
                "("
                "state = 'no_misconception' "
                "AND next_action = 'no_action'"
                ")"
            ),
            name="ck_diagnoses_state_next_action_consistency",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    attempt_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "attempts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    state = Column(
        String(30),
        nullable=False,
        index=True,
    )

    primary_misconception_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "misconceptions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    confidence = Column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0",
    )

    model_version = Column(
        String(80),
        nullable=False,
        default="rule-v1.4",
        server_default="rule-v1.4",
        index=True,
    )

    decision_reason = Column(
        Text,
        nullable=True,
    )

    next_action = Column(
        String(50),
        nullable=False,
        default="no_action",
        server_default="no_action",
        index=True,
    )

    rule_score = Column(
        Float,
        nullable=True,
    )

    llm_score = Column(
        Float,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        index=True,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
        index=True,
    )

    @property
    def requires_hint(self) -> bool:
        """
        Return True when the diagnosis recommends progressive hints.
        """

        return (
            self.state == "confident"
            and self.next_action == "show_hint"
            and self.primary_misconception_id is not None
        )

    @property
    def requires_diagnostic_question(self) -> bool:
        """
        Return True when more targeted evidence should be collected.
        """

        return (
            self.state == "possible"
            and self.next_action == "ask_diagnostic_question"
            and self.primary_misconception_id is not None
        )

    @property
    def requires_clarification(self) -> bool:
        """
        Return True when the submission lacks sufficient evidence.
        """

        return (
            self.state == "insufficient"
            and self.next_action
            in {
                "ask_clarification",
                "ask_diagnostic_question",
            }
        )

    @property
    def is_final_without_intervention(self) -> bool:
        """
        Return True when no further student intervention is required.
        """

        return (
            self.state == "no_misconception"
            and self.next_action == "no_action"
        )

    def __repr__(self) -> str:
        return (
            f"<Diagnosis("
            f"id={self.id}, "
            f"attempt_id={self.attempt_id}, "
            f"state={self.state!r}, "
            f"confidence={self.confidence}, "
            f"primary_misconception_id={self.primary_misconception_id}, "
            f"model_version={self.model_version!r}, "
            f"next_action={self.next_action!r}"
            f")>"
        )