import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class HintTemplate(Base):
    __tablename__ = "hint_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    misconception_id = Column(
        UUID(as_uuid=True),
        ForeignKey("misconceptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    level = Column(Integer, nullable=False)  # 1 / 2 / 3
    hint_text = Column(Text, nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("misconception_id", "level", name="uq_hint_misconception_level"),
    )