import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class DiagnosisEvidence(Base):
    __tablename__ = "diagnosis_evidence"

    __table_args__ = (
        Index(
            "ix_diagnosis_evidence_diagnosis_created_at",
            "diagnosis_id",
            "created_at",
        ),
        Index(
            "ix_diagnosis_evidence_type_created_at",
            "evidence_type",
            "created_at",
        ),
        Index(
            "ix_diagnosis_evidence_rule_created_at",
            "rule_id",
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

    # Examples: problem, written_reasoning, source_code,
    # speech_transcript, rule_engine.
    evidence_type = Column(
        String(50),
        nullable=False,
        index=True,
    )

    # Stores the activated misconception rule code, such as M1, M2, or M3.
    # For non-diagnostic outcomes it may store a state label such as
    # NO_MISCONCEPTION or INSUFFICIENT.
    rule_id = Column(
        String(100),
        nullable=True,
        index=True,
    )

    evidence_text = Column(
        Text,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<DiagnosisEvidence("
            f"id={self.id}, "
            f"diagnosis_id={self.diagnosis_id}, "
            f"evidence_type={self.evidence_type!r}, "
            f"rule_id={self.rule_id!r}"
            f")>"
        )