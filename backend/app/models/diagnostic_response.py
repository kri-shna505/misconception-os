from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class DiagnosticResponse(Base):
    """
    Stores a student's answer to one diagnostic question.

    Sprint 9 uses diagnostic responses to collect additional evidence when a
    diagnosis is marked as ``possible`` or otherwise requires clarification.

    Each response is linked to:

    - the student alias;
    - the original attempt;
    - the diagnosis that requested more evidence;
    - the selected diagnostic question;
    - the resulting follow-up diagnosis, after re-evaluation.

    Service-level validation must ensure that:

    - the diagnosis belongs to the attempt;
    - the attempt belongs to the student alias;
    - the question targets the diagnosis misconception;
    - the same question is not answered twice for the same diagnosis;
    - only eligible diagnoses can receive a diagnostic response;
    - a resulting diagnosis belongs to the same attempt;
    - an evaluated response has an evaluation timestamp.
    """

    __tablename__ = "diagnostic_responses"

    __table_args__ = (
        UniqueConstraint(
            "diagnosis_id",
            "diagnostic_question_id",
            name="uq_diagnostic_responses_diagnosis_question",
        ),
        UniqueConstraint(
            "resulting_diagnosis_id",
            name="uq_diagnostic_responses_resulting_diagnosis",
        ),
        Index(
            "ix_diagnostic_responses_student_created_at",
            "student_alias_id",
            "created_at",
        ),
        Index(
            "ix_diagnostic_responses_attempt_created_at",
            "attempt_id",
            "created_at",
        ),
        Index(
            "ix_diagnostic_responses_diagnosis_created_at",
            "diagnosis_id",
            "created_at",
        ),
        Index(
            "ix_diagnostic_responses_resulting_diagnosis_created_at",
            "resulting_diagnosis_id",
            "created_at",
        ),
        Index(
            "ix_diagnostic_responses_question_created_at",
            "diagnostic_question_id",
            "created_at",
        ),
        Index(
            "ix_diagnostic_responses_evaluated_created_at",
            "evaluated",
            "created_at",
        ),
        CheckConstraint(
            "char_length(trim(response_text)) >= 1",
            name="ck_diagnostic_responses_text_not_blank",
        ),
        CheckConstraint(
            (
                "("
                "evaluated = false "
                "AND evaluated_at IS NULL"
                ") "
                "OR "
                "("
                "evaluated = true "
                "AND evaluated_at IS NOT NULL"
                ")"
            ),
            name="ck_diagnostic_responses_evaluation_consistency",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    student_alias_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "student_aliases.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
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

    diagnosis_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "diagnoses.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    diagnostic_question_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "diagnostic_questions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    resulting_diagnosis_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "diagnoses.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    response_text = Column(
        Text,
        nullable=False,
    )

    evaluated = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )

    evaluated_at = Column(
        DateTime,
        nullable=True,
        index=True,
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

    def mark_evaluated(
        self,
        *,
        resulting_diagnosis_id: uuid.UUID | None = None,
    ) -> None:
        """
        Mark this response as consumed by the re-evaluation pipeline.

        When a follow-up diagnosis is created, its ID should be supplied so the
        response preserves an immutable audit link from the original diagnosis
        to the resulting diagnosis.
        """

        self.evaluated = True
        self.evaluated_at = datetime.utcnow()

        if resulting_diagnosis_id is not None:
            self.resulting_diagnosis_id = resulting_diagnosis_id

    def reopen_evaluation(self) -> None:
        """
        Mark the response as pending evaluation again.

        Reopening clears the previous resulting-diagnosis link because the
        response is no longer considered consumed by a completed evaluation.
        """

        self.evaluated = False
        self.evaluated_at = None
        self.resulting_diagnosis_id = None

    @property
    def is_pending_evaluation(self) -> bool:
        """
        Return True when this response has not yet been re-evaluated.
        """

        return not self.evaluated

    @property
    def has_resulting_diagnosis(self) -> bool:
        """
        Return True when re-evaluation created a follow-up diagnosis.
        """

        return self.resulting_diagnosis_id is not None

    def __repr__(self) -> str:
        return (
            f"<DiagnosticResponse("
            f"id={self.id}, "
            f"student_alias_id={self.student_alias_id}, "
            f"attempt_id={self.attempt_id}, "
            f"diagnosis_id={self.diagnosis_id}, "
            f"diagnostic_question_id={self.diagnostic_question_id}, "
            f"resulting_diagnosis_id={self.resulting_diagnosis_id}, "
            f"evaluated={self.evaluated}"
            f")>"
        )