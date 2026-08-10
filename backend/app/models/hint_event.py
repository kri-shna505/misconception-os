from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class HintEvent(Base):
    """
    Records one hint revealed to a student for a specific diagnosis.

    Sprint 9 uses these records to enforce progressive hint delivery:

        First request  -> level 1
        Second request -> level 2
        Third request  -> level 3

    Historical hint events are preserved even if a hint template is later
    deactivated or deleted.

    Service-level validation must ensure that:

    - the attempt belongs to the student alias;
    - the diagnosis belongs to the attempt;
    - the hint template matches the diagnosed misconception;
    - hint levels are revealed in sequence;
    - no level greater than 3 is issued.
    """

    __tablename__ = "hint_events"

    __table_args__ = (
        UniqueConstraint(
            "diagnosis_id",
            "level",
            name="uq_hint_events_diagnosis_level",
        ),
        Index(
            "ix_hint_events_attempt_created_at",
            "attempt_id",
            "created_at",
        ),
        Index(
            "ix_hint_events_student_created_at",
            "student_alias_id",
            "created_at",
        ),
        Index(
            "ix_hint_events_diagnosis_created_at",
            "diagnosis_id",
            "created_at",
        ),
        Index(
            "ix_hint_events_template_created_at",
            "hint_template_id",
            "created_at",
        ),
        CheckConstraint(
            "level BETWEEN 1 AND 3",
            name="ck_hint_events_level_range",
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

    hint_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "hint_templates.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    level = Column(
        Integer,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    @property
    def is_final_level(self) -> bool:
        """
        Return True when this event revealed the strongest approved hint.
        """

        return self.level == 3

    def __repr__(self) -> str:
        return (
            f"<HintEvent("
            f"id={self.id}, "
            f"student_alias_id={self.student_alias_id}, "
            f"attempt_id={self.attempt_id}, "
            f"diagnosis_id={self.diagnosis_id}, "
            f"hint_template_id={self.hint_template_id}, "
            f"level={self.level}"
            f")>"
        )