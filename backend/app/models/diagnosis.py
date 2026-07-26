import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False, index=True)

    state = Column(String(30), nullable=False, index=True)  # confident / possible / insufficient
    primary_misconception_id = Column(
        UUID(as_uuid=True),
        ForeignKey("misconceptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    confidence = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=False, default="rules-v1")
    rule_score = Column(Float, nullable=True)
    llm_score = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)