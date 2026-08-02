import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    __table_args__ = (
        Index(
            "ix_diagnoses_state_created_at",
            "state",
            "created_at",
        ),
        Index(
            "ix_diagnoses_misconception_created_at",
            "primary_misconception_id",
            "created_at",
        ),
        Index(
            "ix_diagnoses_model_version_created_at",
            "model_version",
            "created_at",
        ),
        Index(
            "ix_diagnoses_next_action_created_at",
            "next_action",
            "created_at",
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

    # confident / possible / insufficient / no_misconception
    state = Column(
        String(30),
        nullable=False,
        index=True,
    )

    primary_misconception_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "misconceptions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    confidence = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    model_version = Column(
        String(80),
        nullable=False,
        default="rule-v1.3",
        index=True,
    )

    decision_reason = Column(
        Text,
        nullable=True,
    )

    next_action = Column(
        String(50),
        nullable=False,
        default="no_action",
        index=True,
    )

    rule_score = Column(
        Float,
        nullable=True,
    )

    llm_score = Column(
        Float,
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
            f"<Diagnosis("
            f"id={self.id}, "
            f"attempt_id={self.attempt_id}, "
            f"state={self.state!r}, "
            f"confidence={self.confidence}, "
            f"primary_misconception_id={self.primary_misconception_id}, "
            f"model_version={self.model_version!r}"
            f")>"
        )