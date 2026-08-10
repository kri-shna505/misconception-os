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
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class DiagnosticQuestion(Base):
    """
    Stores a faculty-approved diagnostic question for a misconception.

    A diagnostic question is used when the diagnosis state is ``possible`` or
    when the system needs additional evidence before confirming a
    misconception.

    ``competing_misconception_id`` is optional. When present, the question is
    intended to distinguish the primary misconception from a specific competing
    misconception.
    """

    __tablename__ = "diagnostic_questions"

    __table_args__ = (
        Index(
            "ix_diagnostic_questions_misconception_active",
            "misconception_id",
            "active",
        ),
        Index(
            "ix_diagnostic_questions_competing_active",
            "competing_misconception_id",
            "active",
        ),
        Index(
            "ix_diagnostic_questions_created_at",
            "created_at",
        ),
        CheckConstraint(
            "char_length(trim(question_text)) >= 10",
            name="ck_diagnostic_questions_text_min_length",
        ),
        CheckConstraint(
            (
                "competing_misconception_id IS NULL "
                "OR competing_misconception_id <> misconception_id"
            ),
            name="ck_diagnostic_questions_competing_not_self",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    misconception_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "misconceptions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    competing_misconception_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "misconceptions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    question_text = Column(
        Text,
        nullable=False,
    )

    approved_by = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def activate(self) -> None:
        """
        Make this diagnostic question available for student interventions.
        """

        self.active = True

    def deactivate(self) -> None:
        """
        Prevent this diagnostic question from being selected for new
        interventions while preserving historical references.
        """

        self.active = False

    def __repr__(self) -> str:
        return (
            f"<DiagnosticQuestion("
            f"id={self.id}, "
            f"misconception_id={self.misconception_id}, "
            f"competing_misconception_id={self.competing_misconception_id}, "
            f"active={self.active}"
            f")>"
        )