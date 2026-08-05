from __future__ import annotations

import uuid
from datetime import datetime
from typing import Final

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_and_update_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    AuthenticatedUserResponse,
)


ALLOWED_TEACHER_ROLES: Final[frozenset[str]] = frozenset(
    {
        "teacher",
        "admin",
    }
)

# Used only to reduce timing differences when the submitted email
# does not belong to an existing account.
_DUMMY_PASSWORD_HASH: Final[str] = hash_password(
    "MisconceptionOS-Dummy-Password-2026!"
)


class AuthenticationServiceError(RuntimeError):
    """
    Base exception for authentication-service failures.
    """


class InvalidCredentialsError(AuthenticationServiceError):
    """
    Raised when the submitted email, password, or token is invalid.
    """


class InactiveUserError(AuthenticationServiceError):
    """
    Raised when authentication is attempted for an inactive user.
    """


class UnauthorizedRoleError(AuthenticationServiceError):
    """
    Raised when a user cannot access teacher functionality.
    """


class UserNotFoundError(AuthenticationServiceError):
    """
    Raised when a requested user no longer exists.
    """


class PasswordChangeError(AuthenticationServiceError):
    """
    Raised when a password-change request is invalid.
    """


class AuthPersistenceError(AuthenticationServiceError):
    """
    Raised when authentication data cannot be persisted.
    """


def normalize_email(email: str) -> str:
    """
    Normalize an email address before database lookup.
    """

    if not isinstance(email, str):
        raise InvalidCredentialsError(
            "Invalid email or password."
        )

    normalized_email = email.strip().lower()

    if not normalized_email:
        raise InvalidCredentialsError(
            "Invalid email or password."
        )

    return normalized_email


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    """
    Find a user using a case-insensitive email lookup.
    """

    normalized_email = normalize_email(email)

    statement = select(User).where(
        func.lower(User.email) == normalized_email
    )

    return db.scalar(statement)


def get_user_by_id(
    db: Session,
    user_id: uuid.UUID,
) -> User | None:
    """
    Find a user by primary-key UUID.
    """

    return db.get(User, user_id)


def require_user_by_id(
    db: Session,
    user_id: uuid.UUID,
) -> User:
    """
    Return an existing user or raise a service exception.
    """

    user = get_user_by_id(
        db=db,
        user_id=user_id,
    )

    if user is None:
        raise UserNotFoundError(
            "Authenticated user no longer exists."
        )

    return user


def validate_teacher_access(
    user: User,
) -> None:
    """
    Ensure the user can access teacher functionality.
    """

    if not user.is_active:
        raise InactiveUserError(
            "This account is inactive."
        )

    normalized_role = (
        user.role.strip().lower()
        if isinstance(user.role, str)
        else ""
    )

    if normalized_role not in ALLOWED_TEACHER_ROLES:
        raise UnauthorizedRoleError(
            "This account cannot access the teacher console."
        )


def _commit_user(
    db: Session,
    user: User,
) -> None:
    """
    Persist and refresh a changed user safely.
    """

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except SQLAlchemyError as error:
        db.rollback()

        raise AuthPersistenceError(
            "Authentication data could not be saved."
        ) from error


def _record_failed_login(
    db: Session,
    user: User,
) -> None:
    """
    Increment the failed-login counter.
    """

    current_attempts = (
        user.failed_login_attempts
        if user.failed_login_attempts is not None
        else 0
    )

    user.failed_login_attempts = current_attempts + 1

    _commit_user(
        db=db,
        user=user,
    )


def _record_successful_login(
    db: Session,
    user: User,
    *,
    updated_password_hash: str | None,
) -> None:
    """
    Store successful-login metadata and apply an upgraded password
    hash when pwdlib reports that the current hash policy is outdated.
    """

    now = datetime.utcnow()

    user.failed_login_attempts = 0
    user.last_login_at = now

    if updated_password_hash is not None:
        user.password_hash = updated_password_hash
        user.password_changed_at = now

        # A changed password hash rotates token_version so tokens
        # issued before the upgrade cannot remain valid.
        user.token_version = (
            (user.token_version or 0) + 1
        )

    _commit_user(
        db=db,
        user=user,
    )


def authenticate_teacher(
    db: Session,
    *,
    email: str,
    password: str,
) -> User:
    """
    Authenticate a teacher or administrator.

    Unknown emails and incorrect passwords intentionally produce the
    same response to reduce account-enumeration risk.
    """

    normalized_email = normalize_email(email)

    user = get_user_by_email(
        db=db,
        email=normalized_email,
    )

    if user is None:
        # Perform a real password verification even when no account
        # exists so unknown-email requests follow a similar code path.
        verify_password(
            password,
            _DUMMY_PASSWORD_HASH,
        )

        raise InvalidCredentialsError(
            "Invalid email or password."
        )

    password_is_valid, updated_password_hash = (
        verify_and_update_password(
            password,
            user.password_hash,
        )
    )

    if not password_is_valid:
        _record_failed_login(
            db=db,
            user=user,
        )

        raise InvalidCredentialsError(
            "Invalid email or password."
        )

    validate_teacher_access(user)

    _record_successful_login(
        db=db,
        user=user,
        updated_password_hash=updated_password_hash,
    )

    return user


def create_login_response(
    user: User,
) -> AccessTokenResponse:
    """
    Issue a JWT and construct the public login response.
    """

    validate_teacher_access(user)

    token_version = user.token_version or 0

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        token_version=token_version,
    )

    return AccessTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=(
            settings.ACCESS_TOKEN_EXPIRE_MINUTES
            * 60
        ),
        user=AuthenticatedUserResponse.model_validate(
            user
        ),
    )


def login_teacher(
    db: Session,
    *,
    email: str,
    password: str,
) -> AccessTokenResponse:
    """
    Authenticate a teacher and return a signed access token.
    """

    user = authenticate_teacher(
        db=db,
        email=email,
        password=password,
    )

    return create_login_response(user)


def invalidate_user_tokens(
    db: Session,
    *,
    user: User,
) -> User:
    """
    Invalidate every access token previously issued to a user.

    JWTs are stateless, so token_version provides account-wide token
    revocation without maintaining a separate token blacklist.
    """

    user.token_version = (
        (user.token_version or 0) + 1
    )

    _commit_user(
        db=db,
        user=user,
    )

    return user


def logout_user(
    db: Session,
    *,
    user: User,
) -> None:
    """
    Log a user out from all sessions.
    """

    invalidate_user_tokens(
        db=db,
        user=user,
    )


def change_user_password(
    db: Session,
    *,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """
    Replace an authenticated user's password and revoke old tokens.
    """

    current_password_is_valid = verify_password(
        current_password,
        user.password_hash,
    )

    if not current_password_is_valid:
        raise PasswordChangeError(
            "Current password is incorrect."
        )

    if current_password == new_password:
        raise PasswordChangeError(
            "New password must be different "
            "from the current password."
        )

    new_password_hash = hash_password(
        new_password
    )

    now = datetime.utcnow()

    user.password_hash = new_password_hash
    user.password_changed_at = now
    user.failed_login_attempts = 0
    user.token_version = (
        (user.token_version or 0) + 1
    )

    _commit_user(
        db=db,
        user=user,
    )


def validate_token_user(
    db: Session,
    *,
    user_id: uuid.UUID,
    token_version: int,
    token_role: str,
) -> User:
    """
    Validate database-dependent JWT claims.

    Signature, token type, and expiration checks are handled by
    security.py. This function verifies that the account still
    exists, remains active, retains its role, and has not revoked the
    submitted token.
    """

    user = require_user_by_id(
        db=db,
        user_id=user_id,
    )

    validate_teacher_access(user)

    stored_token_version = (
        user.token_version or 0
    )

    if stored_token_version != token_version:
        raise InvalidCredentialsError(
            "Authentication token has been revoked."
        )

    stored_role = (
        user.role.strip().lower()
        if isinstance(user.role, str)
        else ""
    )

    normalized_token_role = (
        token_role.strip().lower()
        if isinstance(token_role, str)
        else ""
    )

    if stored_role != normalized_token_role:
        raise InvalidCredentialsError(
            "Authentication token role is no longer valid."
        )

    return user