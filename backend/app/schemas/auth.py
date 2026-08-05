from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


UserRole = Literal["teacher", "admin"]
BearerTokenType = Literal["bearer"]
AccessTokenType = Literal["access"]


class TeacherLoginRequest(BaseModel):
    """
    Credentials submitted to the teacher login endpoint.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=False,
    )

    email: str = Field(
        min_length=3,
        max_length=255,
        examples=[
            "teacher@misconceptionos.local",
        ],
    )

    password: str = Field(
        min_length=8,
        max_length=128,
        examples=[
            "StrongTeacherPassword123!",
        ],
    )

    @field_validator("email")
    @classmethod
    def normalize_email(
        cls,
        value: str,
    ) -> str:
        normalized_value = value.strip().lower()

        if not normalized_value:
            raise ValueError(
                "Email cannot be empty."
            )

        if normalized_value.count("@") != 1:
            raise ValueError(
                "Email must contain exactly one @ symbol."
            )

        local_part, domain_part = normalized_value.split(
            "@",
            maxsplit=1,
        )

        if not local_part or not domain_part:
            raise ValueError(
                "Email must contain a valid local part "
                "and domain."
            )

        if "." not in domain_part:
            raise ValueError(
                "Email domain must contain a dot."
            )

        if (
            domain_part.startswith(".")
            or domain_part.endswith(".")
        ):
            raise ValueError(
                "Email domain is invalid."
            )

        return normalized_value

    @field_validator("password")
    @classmethod
    def validate_password(
        cls,
        value: str,
    ) -> str:
        if not value:
            raise ValueError(
                "Password cannot be empty."
            )

        # Passwords are intentionally not stripped or normalized.
        # Leading and trailing spaces may be part of a valid password.
        if len(value) > 128:
            raise ValueError(
                "Password must not exceed 128 characters."
            )

        return value


class AuthenticatedUserResponse(BaseModel):
    """
    Public authenticated-user information returned by the API.

    Sensitive fields such as password_hash, token_version, and failed
    login counters are intentionally excluded.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )

    id: uuid.UUID
    email: str
    display_name: str | None
    role: UserRole
    is_active: bool
    last_login_at: datetime | None
    password_changed_at: datetime
    created_at: datetime
    updated_at: datetime


class AccessTokenResponse(BaseModel):
    """
    Successful authentication response.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    access_token: str = Field(
        min_length=1,
    )

    token_type: BearerTokenType = "bearer"

    expires_in: int = Field(
        gt=0,
        description=(
            "Number of seconds until the access token expires."
        ),
    )

    user: AuthenticatedUserResponse


class TokenPayload(BaseModel):
    """
    Strongly typed representation of validated JWT claims.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    subject: uuid.UUID
    email: str
    role: UserRole

    token_version: int = Field(
        ge=0,
    )

    token_type: AccessTokenType
    token_id: uuid.UUID

    issued_at: datetime
    not_before: datetime
    expires_at: datetime

    @classmethod
    def from_jwt_claims(
        cls,
        claims: dict[str, Any],
    ) -> "TokenPayload":
        """
        Convert decoded JWT claims into a validated TokenPayload.
        """

        required_claims = {
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

        missing_claims = required_claims.difference(
            claims
        )

        if missing_claims:
            missing_names = ", ".join(
                sorted(missing_claims)
            )

            raise ValueError(
                "Token is missing required claims: "
                f"{missing_names}."
            )

        return cls(
            subject=claims["sub"],
            email=claims["email"],
            role=claims["role"],
            token_version=claims["token_version"],
            token_type=claims["type"],
            token_id=claims["jti"],
            issued_at=cls._timestamp_to_datetime(
                claims["iat"],
                claim_name="iat",
            ),
            not_before=cls._timestamp_to_datetime(
                claims["nbf"],
                claim_name="nbf",
            ),
            expires_at=cls._timestamp_to_datetime(
                claims["exp"],
                claim_name="exp",
            ),
        )

    @staticmethod
    def _timestamp_to_datetime(
        value: Any,
        *,
        claim_name: str,
    ) -> datetime:
        """
        Convert a numeric JWT timestamp into a UTC-aware datetime.
        """

        if isinstance(value, bool):
            raise ValueError(
                f"Token claim {claim_name!r} is invalid."
            )

        try:
            timestamp = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Token claim {claim_name!r} must be "
                "a numeric timestamp."
            ) from error

        return datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc,
        )


class AuthenticationErrorResponse(BaseModel):
    """
    Standard response body for authentication failures.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    detail: str


class LogoutResponse(BaseModel):
    """
    Response returned after the user's tokens are invalidated.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    message: str = "Logged out successfully."


class ChangePasswordRequest(BaseModel):
    """
    Request used to change an authenticated user's password.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=False,
    )

    current_password: str = Field(
        min_length=8,
        max_length=128,
    )

    new_password: str = Field(
        min_length=8,
        max_length=128,
    )

    @field_validator(
        "current_password",
        "new_password",
    )
    @classmethod
    def validate_password(
        cls,
        value: str,
    ) -> str:
        if not value:
            raise ValueError(
                "Password cannot be empty."
            )

        # Do not call strip(). Password whitespace may be intentional.
        if len(value) > 128:
            raise ValueError(
                "Password must not exceed 128 characters."
            )

        return value


class ChangePasswordResponse(BaseModel):
    """
    Response returned after a password is changed.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    message: str = (
        "Password changed successfully. "
        "Existing access tokens have been invalidated."
    )