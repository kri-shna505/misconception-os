import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class User(Base):
    """
    Authenticated platform user.

    Sprint 7A currently uses this model for teacher authentication,
    protected teacher routes, password lifecycle tracking, and token
    invalidation.

    Passwords must never be stored directly. Only a secure password
    hash is persisted in ``password_hash``.
    """

    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "role IN ('teacher', 'admin')",
            name="ck_users_valid_role",
        ),
        CheckConstraint(
            "failed_login_attempts >= 0",
            name="ck_users_failed_login_attempts_non_negative",
        ),
        CheckConstraint(
            "token_version >= 0",
            name="ck_users_token_version_non_negative",
        ),
        Index(
            "ix_users_role_active",
            "role",
            "is_active",
        ),
        Index(
            "ix_users_active_created_at",
            "is_active",
            "created_at",
        ),
        Index(
            "ix_users_role_created_at",
            "role",
            "created_at",
        ),
        Index(
            "ix_users_email_active",
            "email",
            "is_active",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    display_name = Column(
        String(120),
        nullable=True,
    )

    password_hash = Column(
        String(255),
        nullable=False,
    )

    role = Column(
        String(50),
        nullable=False,
        default="teacher",
        server_default="teacher",
        index=True,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )

    failed_login_attempts = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    last_login_at = Column(
        DateTime,
        nullable=True,
        index=True,
    )

    password_changed_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    token_version = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        index=True,
    )

    def record_successful_login(self) -> None:
        """
        Update authentication metadata after a valid login.
        """

        self.last_login_at = datetime.utcnow()
        self.failed_login_attempts = 0

    def record_failed_login(self) -> None:
        """
        Increment the failed-login counter.

        Account lockout rules should be enforced by the authentication
        service rather than directly inside the ORM model.
        """

        self.failed_login_attempts += 1

    def invalidate_existing_tokens(self) -> None:
        """
        Increment token version so previously issued access tokens can
        be rejected by the authentication dependency.
        """

        self.token_version += 1

    def mark_password_changed(self) -> None:
        """
        Record password modification and invalidate older tokens.
        """

        self.password_changed_at = datetime.utcnow()
        self.invalidate_existing_tokens()

    def __repr__(self) -> str:
        return (
            f"<User("
            f"id={self.id}, "
            f"email={self.email!r}, "
            f"display_name={self.display_name!r}, "
            f"role={self.role!r}, "
            f"is_active={self.is_active}"
            f")>"
        )