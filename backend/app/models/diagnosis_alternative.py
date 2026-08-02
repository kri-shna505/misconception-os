import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class DiagnosisAlternative(Base):
    __tablename__ = "diagnosis_alternatives"

    __table_args__ = (
        Index(
            "ix_diagnosis_alternatives_diagnosis_confidence",
            "diagnosis_id",
            "confidence",
        ),
        Index(
            "ix_diagnosis_alternatives_misconception_created_at",
            "misconception_id",
            "created_at",
        ),
        Index(
            "ix_diagnosis_alternatives_created_at",
            "created_at",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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

    misconception_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "misconceptions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    confidence = Column(
        Float,
        nullable=True,
    )

    reason = Column(
        Text,
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
            f"<DiagnosisAlternative("
            f"id={self.id}, "
            f"diagnosis_id={self.diagnosis_id}, "
            f"misconception_id={self.misconception_id}, "
            f"confidence={self.confidence}"
            f")>"
        )