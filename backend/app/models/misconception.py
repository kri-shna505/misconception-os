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
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Misconception(Base):
    __tablename__ = "misconceptions"

    __table_args__ = (
        Index(
            "ix_misconceptions_active_topic",
            "active",
            "topic",
        ),
        Index(
            "ix_misconceptions_active_created_at",
            "active",
            "created_at",
        ),
        Index(
            "ix_misconceptions_topic_created_at",
            "topic",
            "created_at",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    code = Column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    name = Column(
        String(255),
        nullable=False,
        index=True,
    )

    description = Column(
        Text,
        nullable=True,
    )

    topic = Column(
        String(100),
        nullable=True,
        index=True,
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
            f"<Misconception("
            f"id={self.id}, "
            f"code={self.code!r}, "
            f"name={self.name!r}, "
            f"topic={self.topic!r}, "
            f"active={self.active}"
            f")>"
        )