import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class DiagnosticQuestion(Base):
    __tablename__ = "diagnostic_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    misconception_id = Column(
        UUID(as_uuid=True),
        ForeignKey("misconceptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    competing_misconception_id = Column(
        UUID(as_uuid=True),
        ForeignKey("misconceptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    question_text = Column(Text, nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)