import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class TeacherReview(Base):
    """
    Stores the teacher's review decision for one student attempt.

    The original system diagnosis remains unchanged. Any teacher
    acceptance, correction, or override is stored separately here so
    that the automated result and the human-reviewed result remain
    independently traceable.
    """

    __tablename__ = "teacher_reviews"

    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            name="uq_teacher_reviews_attempt_id",
        ),
        CheckConstraint(
            (
                "status IN ("
                "'pending', "
                "'in_review', "
                "'reviewed'"
                ")"
            ),
            name="ck_teacher_reviews_valid_status",
        ),
        CheckConstraint(
            (
                "decision IS NULL OR decision IN ("
                "'accepted', "
                "'overridden'"
                ")"
            ),
            name="ck_teacher_reviews_valid_decision",
        ),
        CheckConstraint(
            (
                "final_state IS NULL OR final_state IN ("
                "'confident', "
                "'possible', "
                "'insufficient', "
                "'no_misconception'"
                ")"
            ),
            name="ck_teacher_reviews_valid_final_state",
        ),
        Index(
            "ix_teacher_reviews_status_created_at",
            "status",
            "created_at",
        ),
        Index(
            "ix_teacher_reviews_teacher_status",
            "teacher_id",
            "status",
        ),
        Index(
            "ix_teacher_reviews_reviewed_at",
            "reviewed_at",
        ),
        Index(
            "ix_teacher_reviews_final_misconception",
            "final_misconception_id",
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

    teacher_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    system_diagnosis_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "diagnoses.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    status = Column(
        String(30),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )

    decision = Column(
        String(30),
        nullable=True,
    )

    final_state = Column(
        String(30),
        nullable=True,
        index=True,
    )

    final_misconception_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "misconceptions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    override_reason = Column(
        Text,
        nullable=True,
    )

    teacher_note = Column(
        Text,
        nullable=True,
    )

    reviewed_at = Column(
        DateTime,
        nullable=True,
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
        index=True,
    )

    def mark_in_review(self) -> None:
        """
        Move a pending review into draft/in-review state.
        """

        self.status = "in_review"
        self.reviewed_at = None

    def finalize(self) -> None:
        """
        Mark the review as completed.
        """

        self.status = "reviewed"
        self.reviewed_at = datetime.utcnow()

    def reopen(self) -> None:
        """
        Reopen a finalized review for editing.
        """

        self.status = "in_review"
        self.reviewed_at = None

    def __repr__(self) -> str:
        return (
            f"<TeacherReview("
            f"id={self.id}, "
            f"attempt_id={self.attempt_id}, "
            f"teacher_id={self.teacher_id}, "
            f"status={self.status!r}, "
            f"decision={self.decision!r}"
            f")>"
        )