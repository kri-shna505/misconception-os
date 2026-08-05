from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import ExpiredSignatureError, JWTError, jwt
from pwdlib import PasswordHash

from app.core.config import settings


ACCESS_TOKEN_TYPE = "access"
DEFAULT_JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 30

_password_hash = PasswordHash.recommended()


class TokenDecodeError(ValueError):
    """Raised when an authentication token cannot be trusted."""


class TokenExpiredError(TokenDecodeError):
    """Raised when an authentication token has expired."""


def _get_secret_key() -> str:
    secret_key = getattr(
        settings,
        "JWT_SECRET_KEY",
        None,
    ) or getattr(
        settings,
        "SECRET_KEY",
        None,
    )

    if not isinstance(secret_key, str) or not secret_key.strip():
        raise RuntimeError(
            "JWT signing secret is not configured. "
            "Set JWT_SECRET_KEY or SECRET_KEY."
        )

    return secret_key.strip()


def _get_jwt_algorithm() -> str:
    configured_algorithm = getattr(
        settings,
        "JWT_ALGORITHM",
        None,
    ) or getattr(
        settings,
        "ALGORITHM",
        None,
    )

    if (
        isinstance(configured_algorithm, str)
        and configured_algorithm.strip()
    ):
        return configured_algorithm.strip()

    return DEFAULT_JWT_ALGORITHM


def _get_access_token_expire_minutes() -> int:
    configured_value = getattr(
        settings,
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    try:
        expire_minutes = int(configured_value)
    except (TypeError, ValueError) as error:
        raise RuntimeError(
            "ACCESS_TOKEN_EXPIRE_MINUTES must be an integer."
        ) from error

    if expire_minutes <= 0:
        raise RuntimeError(
            "ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero."
        )

    return expire_minutes


def hash_password(password: str) -> str:
    """Create a secure Argon2 password hash."""

    if not isinstance(password, str) or not password:
        raise ValueError("Password cannot be empty.")

    if len(password) < 8:
        raise ValueError(
            "Password must contain at least 8 characters."
        )

    if len(password) > 128:
        raise ValueError(
            "Password must not exceed 128 characters."
        )

    return _password_hash.hash(password)


def verify_password(
    plain_password: str,
    password_hash: str,
) -> bool:
    """Verify a submitted password against a stored hash."""

    if not plain_password or not password_hash:
        return False

    try:
        return _password_hash.verify(
            plain_password,
            password_hash,
        )
    except (TypeError, ValueError):
        return False


def verify_and_update_password(
    plain_password: str,
    password_hash: str,
) -> tuple[bool, str | None]:
    """
    Verify a password and return an upgraded hash when needed.
    """

    if not plain_password or not password_hash:
        return False, None

    try:
        return _password_hash.verify_and_update(
            plain_password,
            password_hash,
        )
    except (TypeError, ValueError):
        return False, None


def create_access_token(
    *,
    user_id: uuid.UUID | str,
    email: str,
    role: str,
    token_version: int,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    normalized_email = email.strip().lower()
    normalized_role = role.strip().lower()

    if not normalized_email:
        raise ValueError("Token email cannot be empty.")

    if not normalized_role:
        raise ValueError("Token role cannot be empty.")

    if token_version < 0:
        raise ValueError(
            "Token version cannot be negative."
        )

    now = datetime.now(timezone.utc)

    expiry = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(
            minutes=_get_access_token_expire_minutes()
        )
    )

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": normalized_email,
        "role": normalized_role,
        "token_version": token_version,
        "type": ACCESS_TOKEN_TYPE,
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expiry.timestamp()),
    }

    if additional_claims:
        protected_claims = {
            "sub",
            "email",
            "role",
            "token_version",
            "type",
            "jti",
            "iat",
            "nbf",
            "exp",
        }

        conflicting_claims = (
            protected_claims
            & additional_claims.keys()
        )

        if conflicting_claims:
            names = ", ".join(
                sorted(conflicting_claims)
            )

            raise ValueError(
                "Additional claims cannot override "
                f"protected claims: {names}."
            )

        payload.update(additional_claims)

    return jwt.encode(
        payload,
        _get_secret_key(),
        algorithm=_get_jwt_algorithm(),
    )


def decode_access_token(
    token: str,
) -> dict[str, Any]:
    if not isinstance(token, str) or not token.strip():
        raise TokenDecodeError(
            "Authentication token is missing."
        )

    try:
        payload = jwt.decode(
            token.strip(),
            _get_secret_key(),
            algorithms=[_get_jwt_algorithm()],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "require_exp": True,
                "require_iat": True,
                "require_sub": True,
            },
        )
    except ExpiredSignatureError as error:
        raise TokenExpiredError(
            "Authentication token has expired."
        ) from error
    except JWTError as error:
        raise TokenDecodeError(
            "Authentication token is invalid."
        ) from error

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise TokenDecodeError(
            "Token is not an access token."
        )

    subject = payload.get("sub")
    email = payload.get("email")
    role = payload.get("role")
    token_version = payload.get("token_version")
    token_id = payload.get("jti")

    if not isinstance(subject, str) or not subject:
        raise TokenDecodeError(
            "Token subject is invalid."
        )

    try:
        uuid.UUID(subject)
    except ValueError as error:
        raise TokenDecodeError(
            "Token subject is not a valid UUID."
        ) from error

    if not isinstance(email, str) or not email:
        raise TokenDecodeError(
            "Token email is invalid."
        )

    if not isinstance(role, str) or not role:
        raise TokenDecodeError(
            "Token role is invalid."
        )

    if (
        not isinstance(token_version, int)
        or isinstance(token_version, bool)
        or token_version < 0
    ):
        raise TokenDecodeError(
            "Token version is invalid."
        )

    if not isinstance(token_id, str) or not token_id:
        raise TokenDecodeError(
            "Token identifier is invalid."
        )

    return payload


def get_token_subject(
    payload: dict[str, Any],
) -> uuid.UUID:
    subject = payload.get("sub")

    if not isinstance(subject, str):
        raise TokenDecodeError(
            "Token subject is invalid."
        )

    try:
        return uuid.UUID(subject)
    except ValueError as error:
        raise TokenDecodeError(
            "Token subject is not a valid UUID."
        ) 