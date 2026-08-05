from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    TokenDecodeError,
    TokenExpiredError,
    decode_access_token,
)
from app.models.user import User
from app.schemas.auth import TokenPayload
from app.services.auth_service import (
    AuthPersistenceError,
    InactiveUserError,
    InvalidCredentialsError,
    UnauthorizedRoleError,
    UserNotFoundError,
    validate_token_user,
)


bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="TeacherBearerAuth",
    description=(
        "Paste the JWT access token returned by "
        "POST /api/auth/login."
    ),
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]

BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


def _authentication_exception(
    detail: str = (
        "Could not validate authentication credentials."
    ),
) -> HTTPException:
    """
    Build a consistent HTTP 401 authentication response.
    """

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def _authorization_exception(
    detail: str = (
        "You do not have permission to access "
        "this resource."
    ),
) -> HTTPException:
    """
    Build a consistent HTTP 403 authorization response.
    """

    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


def _decode_token_payload(
    token: str,
) -> TokenPayload:
    """
    Decode a JWT and convert its claims into a validated schema.
    """

    try:
        claims = decode_access_token(token)

        return TokenPayload.from_jwt_claims(
            claims
        )

    except TokenExpiredError as error:
        raise _authentication_exception(
            "Authentication token has expired."
        ) from error

    except TokenDecodeError as error:
        raise _authentication_exception(
            "Authentication token is invalid."
        ) from error

    except (
        ValidationError,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        raise _authentication_exception(
            "Authentication token claims are invalid."
        ) from error


def get_current_user(
    db: DatabaseSession,
    credentials: BearerCredentials,
) -> User:
    """
    Return the authenticated user represented by the Bearer token.

    This dependency validates:

    - token presence
    - Bearer authentication scheme
    - JWT signature
    - token expiration
    - required JWT claims
    - user existence
    - active account status
    - token-version revocation
    - role consistency
    """

    if credentials is None:
        raise _authentication_exception(
            "Authentication credentials were not provided."
        )

    if credentials.scheme.lower() != "bearer":
        raise _authentication_exception(
            "Bearer authentication is required."
        )

    token = credentials.credentials.strip()

    if not token:
        raise _authentication_exception(
            "Authentication token was not provided."
        )

    token_payload = _decode_token_payload(
        token
    )

    try:
        return validate_token_user(
            db=db,
            user_id=token_payload.subject,
            token_version=(
                token_payload.token_version
            ),
            token_role=token_payload.role,
        )

    except UserNotFoundError as error:
        raise _authentication_exception(
            "Authenticated user no longer exists."
        ) from error

    except InactiveUserError as error:
        raise _authentication_exception(
            "This account is inactive."
        ) from error

    except InvalidCredentialsError as error:
        raise _authentication_exception(
            "Authentication token is no longer valid."
        ) from error

    except UnauthorizedRoleError as error:
        raise _authorization_exception(
            "This account cannot access protected "
            "teacher resources."
        ) from error

    except AuthPersistenceError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Authentication service is temporarily "
                "unavailable."
            ),
        ) from error


def get_current_teacher(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
) -> User:
    """
    Require an authenticated teacher or administrator.
    """

    normalized_role = (
        current_user.role.strip().lower()
        if isinstance(
            current_user.role,
            str,
        )
        else ""
    )

    if normalized_role not in {
        "teacher",
        "admin",
    }:
        raise _authorization_exception(
            "Teacher access is required."
        )

    return current_user


def get_current_admin(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
) -> User:
    """
    Require an authenticated administrator.
    """

    normalized_role = (
        current_user.role.strip().lower()
        if isinstance(
            current_user.role,
            str,
        )
        else ""
    )

    if normalized_role != "admin":
        raise _authorization_exception(
            "Administrator access is required."
        )

    return current_user


CurrentUser = Annotated[
    User,
    Depends(get_current_user),
]

CurrentTeacher = Annotated[
    User,
    Depends(get_current_teacher),
]

CurrentAdmin = Annotated[
    User,
    Depends(get_current_admin),
]