import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class StudentAlias(Base):
    __tablename__ = "student_aliases"

    __table_args__ = (
        Index(
            "ix_student_aliases_consent_created_at",
            "consent_status",
            "created_at",
        ),
        Index(
            "ix_student_aliases_alias_created_at",
            "alias",
            "created_at",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    alias = Column(
        String(80),
        nullable=False,
        index=True,
    )

    pseudonymous_id = Column(
        String(40),
        unique=True,
        nullable=False,
        index=True,
    )

    consent_status = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<StudentAlias("
            f"id={self.id}, "
            f"alias={self.alias!r}, "
            f"pseudonymous_id={self.pseudonymous_id!r}, "
            f"consent_status={self.consent_status}"
            f")>"
        )