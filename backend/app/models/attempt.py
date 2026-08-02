import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Attempt(Base):
    __tablename__ = "attempts"

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

    def __repr__(self) -> str:
        return (
            f"<Attempt("
            f"id={self.id}, "
            f"student_alias_id={self.student_alias_id}, "
            f"problem_id={self.problem_id}, "
            f"selected_language={self.selected_language!r}"
            f")>"
        )