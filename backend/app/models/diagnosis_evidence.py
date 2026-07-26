import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class DiagnosisEvidence(Base):
    __tablename__ = "diagnosis_evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    diagnosis_id = Column(UUID(as_uuid=True), ForeignKey("diagnoses.id", ondelete="CASCADE"), nullable=False, index=True)

    evidence_type = Column(String(50), nullable=False)  # text / code / input / speech / test
    rule_id = Column(String(100), nullable=True)
    evidence_text = Column(Text, nullable=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)