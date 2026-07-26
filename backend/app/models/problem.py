import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class Problem(Base):
    __tablename__ = "problems"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(30), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    topic = Column(String(100), nullable=False)
    statement = Column(Text, nullable=False)
    difficulty = Column(String(50), nullable=True)
    expected_language = Column(String(50), nullable=True)
    rule_context = Column(JSONB, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)