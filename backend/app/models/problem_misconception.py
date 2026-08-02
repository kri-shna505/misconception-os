import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class ProblemMisconception(Base):
    __tablename__ = "problem_misconceptions"

    __table_args__ = (
        UniqueConstraint(
            "problem_id",
            "misconception_id",
            name="uq_problem_misconception",
        ),
        Index(
            "ix_problem_misconceptions_problem_created_at",
            "problem_id",
            "created_at",
        ),
        Index(
            "ix_problem_misconceptions_misconception_created_at",
            "misconception_id",
            "created_at",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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

    misconception_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "misconceptions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
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
            f"<ProblemMisconception("
            f"id={self.id}, "
            f"problem_id={self.problem_id}, "
            f"misconception_id={self.misconception_id}"
            f")>"
        )