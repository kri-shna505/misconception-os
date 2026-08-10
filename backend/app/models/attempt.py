import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Attempt(Base):
    """
    Stores one pseudonymous student submission.

    Sprint 9 retry support:
    - An original attempt has parent_attempt_id=None and retry_number=0.
    - A retry points to the immediately previous attempt.
    - retry_number increases within the same student/problem attempt chain.

    The application service must additionally verify that a retry and its
    parent belong to the same student alias and problem. That rule cannot be
    reliably enforced through a simple database CHECK constraint because it
    requires reading values from another row.
    """

    __tablename__ = "attempts"

    __table_args__ = (
        Index(
            "ix_attempts_student_created_at",
            "student_alias_id",
            "created_at",
        ),
        Index(
            "ix_attempts_problem_created_at",
            "problem_id",
            "created_at",
        ),
        Index(
            "ix_attempts_language_created_at",
            "selected_language",
            "created_at",
        ),
        Index(
            "ix_attempts_student_problem_created_at",
            "student_alias_id",
            "problem_id",
            "created_at",
        ),
        Index(
            "ix_attempts_parent_created_at",
            "parent_attempt_id",
            "created_at",
        ),
        Index(
            "ix_attempts_student_problem_retry",
            "student_alias_id",
            "problem_id",
            "retry_number",
        ),
        CheckConstraint(
            (
                "response_time_seconds IS NULL "
                "OR response_time_seconds >= 0"
            ),
            name="ck_attempts_response_time_nonnegative",
        ),
        CheckConstraint(
            "retry_number >= 0",
            name="ck_attempts_retry_number_nonnegative",
        ),
        CheckConstraint(
            (
                "parent_attempt_id IS NULL "
                "OR parent_attempt_id <> id"
            ),
            name="ck_attempts_parent_not_self",
        ),
        CheckConstraint(
            (
                "(parent_attempt_id IS NULL AND retry_number = 0) "
                "OR "
                "(parent_attempt_id IS NOT NULL AND retry_number >= 1)"
            ),
            name="ck_attempts_parent_retry_consistency",
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

    problem_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "problems.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    parent_attempt_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "attempts.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    retry_number = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        index=True,
    )

    final_answer = Column(
        Text,
        nullable=True,
    )

    written_reasoning = Column(
        Text,
        nullable=False,
    )

    source_code = Column(
        Text,
        nullable=True,
    )

    speech_transcript = Column(
        Text,
        nullable=True,
    )

    selected_language = Column(
        String(30),
        nullable=False,
        default="python",
        index=True,
    )

    response_time_seconds = Column(
        Integer,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    @property
    def is_retry(self) -> bool:
        """
        Return True when this attempt belongs to a retry chain.
        """

        return (
            self.parent_attempt_id is not None
            and self.retry_number > 0
        )

    def link_to_parent(
        self,
        *,
        parent_attempt_id: uuid.UUID,
        retry_number: int,
    ) -> None:
        """
        Link this submission to its immediately previous attempt.

        Cross-row ownership validation—same student and same problem—must be
        performed by the service before calling this method.
        """

        if parent_attempt_id == self.id:
            raise ValueError(
                "An attempt cannot use itself as its parent."
            )

        if retry_number < 1:
            raise ValueError(
                "A linked retry must have retry_number >= 1."
            )

        self.parent_attempt_id = parent_attempt_id
        self.retry_number = retry_number

    def __repr__(self) -> str:
        return (
            f"<Attempt("
            f"id={self.id}, "
            f"student_alias_id={self.student_alias_id}, "
            f"problem_id={self.problem_id}, "
            f"parent_attempt_id={self.parent_attempt_id}, "
            f"retry_number={self.retry_number}, "
            f"selected_language={self.selected_language!r}, "
            f"response_time_seconds={self.response_time_seconds}"
            f")>"
        )