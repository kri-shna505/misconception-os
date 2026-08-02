import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class Problem(Base):
    __tablename__ = "problems"

    __table_args__ = (
        Index(
            "ix_problems_active_topic",
            "active",
            "topic",
        ),
        Index(
            "ix_problems_active_difficulty",
            "active",
            "difficulty",
        ),
        Index(
            "ix_problems_active_created_at",
            "active",
            "created_at",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    code = Column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
    )

    title = Column(
        String(255),
        nullable=False,
    )

    topic = Column(
        String(100),
        nullable=False,
        index=True,
    )

    statement = Column(
        Text,
        nullable=False,
    )

    difficulty = Column(
        String(50),
        nullable=True,
        index=True,
    )

    expected_language = Column(
        String(50),
        nullable=True,
    )

    rule_context = Column(
        JSONB,
        nullable=True,
    )

    active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Problem("
            f"id={self.id}, "
            f"code={self.code!r}, "
            f"title={self.title!r}, "
            f"topic={self.topic!r}, "
            f"active={self.active}"
            f")>"
        )