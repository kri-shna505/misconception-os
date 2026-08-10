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
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class HintTemplate(Base):
    """
    Faculty-approved intervention hints.

    Each misconception may have one hint per level:

        Level 1 -> Conceptual hint
        Level 2 -> Guided hint
        Level 3 -> Strong guidance

    The system progressively reveals hints instead of exposing the complete
    solution immediately.
    """

    __tablename__ = "hint_templates"

    __table_args__ = (
        UniqueConstraint(
            "misconception_id",
            "level",
            name="uq_hint_misconception_level",
        ),
        Index(
            "ix_hint_templates_misconception_active",
            "misconception_id",
            "active",
        ),
        Index(
            "ix_hint_templates_level",
            "level",
        ),
        Index(
            "ix_hint_templates_created_at",
            "created_at",
        ),
        CheckConstraint(
            "level BETWEEN 1 AND 3",
            name="ck_hint_templates_level_range",
        ),
        CheckConstraint(
            "char_length(trim(hint_text)) >= 10",
            name="ck_hint_templates_text_min_length",
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

    level = Column(
        Integer,
        nullable=False,
    )

    hint_text = Column(
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
        Make this hint available.
        """

        self.active = True

    def deactivate(self) -> None:
        """
        Disable this hint without deleting historical records.
        """

        self.active = False

    @property
    def is_level_one(self) -> bool:
        return self.level == 1

    @property
    def is_level_two(self) -> bool:
        return self.level == 2

    @property
    def is_level_three(self) -> bool:
        return self.level == 3

    def __repr__(self) -> str:
        return (
            f"<HintTemplate("
            f"id={self.id}, "
            f"misconception_id={self.misconception_id}, "
            f"level={self.level}, "
            f"active={self.active}"
            f")>"
        )