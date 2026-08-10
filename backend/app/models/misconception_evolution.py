from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class MisconceptionEvolution(Base):
    """
    Stores the conceptual change detected between related student attempts.

    Sprint 9 evolution states:

    - newly_detected:
      A misconception was detected for the first time.

    - repeated:
      The same misconception appeared again with no clear improvement.

    - improving:
      The same misconception remains, but diagnosis confidence or severity
      decreased.

    - corrected:
      A previously detected misconception changed to no_misconception.

    - replaced:
      A previous misconception changed into a different misconception.

    - uncertain:
      The current diagnosis is insufficient or cannot be compared reliably.

    One evolution record is associated with one diagnosis. The record may
    reference the previous attempt and previous diagnosis when the current
    attempt is part of a retry chain.

    Service-level validation must ensure that:

    - current and previous attempts belong to the same student;
    - current and previous attempts belong to the same problem;
    - diagnosis_id belongs to attempt_id;
    - previous_diagnosis_id belongs to previous_attempt_id;
    - misconception IDs agree with their corresponding diagnoses;
    - evolution_state is calculated using the approved transition rules.
    """

    __tablename__ = "misconception_evolutions"

    __table_args__ = (
        UniqueConstraint(
            "diagnosis_id",
            name="uq_misconception_evolutions_diagnosis",
        ),
        Index(
            "ix_misconception_evolutions_student_created_at",
            "student_alias_id",
            "created_at",
        ),
        Index(
            "ix_misconception_evolutions_problem_created_at",
            "problem_id",
            "created_at",
        ),
        Index(
            "ix_misconception_evolutions_attempt_created_at",
            "attempt_id",
            "created_at",
        ),
        Index(
            "ix_misconception_evolutions_previous_attempt",
            "previous_attempt_id",
        ),
        Index(
            "ix_misconception_evolutions_state_created_at",
            "evolution_state",
            "created_at",
        ),
        Index(
            "ix_misconception_evolutions_current_misconception",
            "current_misconception_id",
            "created_at",
        ),
        Index(
            "ix_misconception_evolutions_previous_misconception",
            "previous_misconception_id",
            "created_at",
        ),
        CheckConstraint(
            (
                "evolution_state IN ("
                "'newly_detected', "
                "'repeated', "
                "'improving', "
                "'corrected', "
                "'replaced', "
                "'uncertain'"
                ")"
            ),
            name="ck_misconception_evolutions_valid_state",
        ),
        CheckConstraint(
            (
                "previous_diagnosis_state IS NULL "
                "OR previous_diagnosis_state IN ("
                "'confident', "
                "'possible', "
                "'insufficient', "
                "'no_misconception'"
                ")"
            ),
            name=(
                "ck_misconception_evolutions_valid_previous_diagnosis_state"
            ),
        ),
        CheckConstraint(
            (
                "current_diagnosis_state IN ("
                "'confident', "
                "'possible', "
                "'insufficient', "
                "'no_misconception'"
                ")"
            ),
            name=(
                "ck_misconception_evolutions_valid_current_diagnosis_state"
            ),
        ),
        CheckConstraint(
            (
                "previous_attempt_id IS NULL "
                "OR previous_attempt_id <> attempt_id"
            ),
            name="ck_misconception_evolutions_attempt_not_self",
        ),
        CheckConstraint(
            (
                "previous_diagnosis_id IS NULL "
                "OR previous_diagnosis_id <> diagnosis_id"
            ),
            name="ck_misconception_evolutions_diagnosis_not_self",
        ),
        CheckConstraint(
            (
                "(previous_attempt_id IS NULL "
                "AND previous_diagnosis_id IS NULL) "
                "OR "
                "(previous_attempt_id IS NOT NULL "
                "AND previous_diagnosis_id IS NOT NULL)"
            ),
            name=(
                "ck_misconception_evolutions_previous_reference_consistency"
            ),
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

    previous_attempt_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "attempts.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    previous_diagnosis_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "diagnoses.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    previous_misconception_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "misconceptions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    current_misconception_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "misconceptions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    previous_diagnosis_state = Column(
        String(30),
        nullable=True,
    )

    current_diagnosis_state = Column(
        String(30),
        nullable=False,
    )

    evolution_state = Column(
        String(30),
        nullable=False,
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

    @property
    def is_first_detection(self) -> bool:
        return self.evolution_state == "newly_detected"

    @property
    def is_repeated(self) -> bool:
        return self.evolution_state == "repeated"

    @property
    def is_improving(self) -> bool:
        return self.evolution_state == "improving"

    @property
    def is_corrected(self) -> bool:
        return self.evolution_state == "corrected"

    @property
    def is_replaced(self) -> bool:
        return self.evolution_state == "replaced"

    @property
    def is_uncertain(self) -> bool:
        return self.evolution_state == "uncertain"

    @property
    def has_previous_attempt(self) -> bool:
        return (
            self.previous_attempt_id is not None
            and self.previous_diagnosis_id is not None
        )

    def __repr__(self) -> str:
        return (
            f"<MisconceptionEvolution("
            f"id={self.id}, "
            f"student_alias_id={self.student_alias_id}, "
            f"problem_id={self.problem_id}, "
            f"attempt_id={self.attempt_id}, "
            f"diagnosis_id={self.diagnosis_id}, "
            f"previous_attempt_id={self.previous_attempt_id}, "
            f"previous_diagnosis_id={self.previous_diagnosis_id}, "
            f"evolution_state={self.evolution_state!r}"
            f")>"
        )