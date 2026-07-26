import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class DiagnosisAlternative(Base):
    __tablename__ = "diagnosis_alternatives"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    diagnosis_id = Column(UUID(as_uuid=True), ForeignKey("diagnoses.id", ondelete="CASCADE"), nullable=False, index=True)
    misconception_id = Column(UUID(as_uuid=True), ForeignKey("misconceptions.id", ondelete="CASCADE"), nullable=False, index=True)

    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)