from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentTeacher
from app.core.database import get_db
from app.schemas.auth import (
    AccessTokenResponse,
    AuthenticatedUserResponse,
    AuthenticationErrorResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    LogoutResponse,
    TeacherLoginRequest,
)
from app.services.auth_service import (
    AuthPersistenceError,
    InactiveUserError,
    InvalidCredentialsError,
    PasswordChangeError,
    UnauthorizedRoleError,
    change_user_password,
    login_teacher,
    logout_user,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


@router.post(
    "/login",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": AuthenticationErrorResponse,
            "description": (
                "The email or password is incorrect."
            ),
        },
        status.HTTP_403_FORBIDDEN: {
            "model": AuthenticationErrorResponse,
            "description": (
                "The account is inactive or cannot access "
                "the teacher console."
            ),
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": AuthenticationErrorResponse,
            "description": (
                "Authentication data could not be saved."
            ),
        },
    },
)
def login(
    payload: TeacherLoginRequest,
    db: DatabaseSession,
) -> AccessTokenResponse:
    """
    Authenticate a teacher or administrator and issue a JWT access
    token.
    """

    try:
        return login_teacher(
            db=db,
            email=payload.email,
            password=payload.password,
        )

    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        ) from error

    except InactiveUserError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        ) from error

    except UnauthorizedRoleError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This account cannot access the "
                "teacher console."
            ),
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


@router.get(
    "/me",
    response_model=AuthenticatedUserResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": AuthenticationErrorResponse,
            "description": (
                "A valid Bearer token is required."
            ),
        },
        status.HTTP_403_FORBIDDEN: {
            "model": AuthenticationErrorResponse,
            "description": (
                "Teacher access is required."
            ),
        },
    },
)
def get_authenticated_teacher(
    current_teacher: CurrentTeacher,
) -> AuthenticatedUserResponse:
    """
    Return the currently authenticated teacher or administrator.
    """

    return AuthenticatedUserResponse.model_validate(
        current_teacher
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": AuthenticationErrorResponse,
            "description": (
                "A valid Bearer token is required."
            ),
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": AuthenticationErrorResponse,
            "description": (
                "The logout operation could not be saved."
            ),
        },
    },
)
def logout(
    db: DatabaseSession,
    current_teacher: CurrentTeacher,
) -> LogoutResponse:
    """
    Invalidate all access tokens issued to the authenticated user.

    This increments the user's token version, causing previously
    issued JWTs to be rejected.
    """

    try:
        logout_user(
            db=db,
            user=current_teacher,
        )

    except AuthPersistenceError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Logout could not be completed. "
                "Please try again."
            ),
        ) from error

    return LogoutResponse()


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": AuthenticationErrorResponse,
            "description": (
                "The current password is incorrect or the "
                "new password is invalid."
            ),
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": AuthenticationErrorResponse,
            "description": (
                "A valid Bearer token is required."
            ),
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": AuthenticationErrorResponse,
            "description": (
                "The password change could not be saved."
            ),
        },
    },
)
def change_password(
    payload: ChangePasswordRequest,
    db: DatabaseSession,
    current_teacher: CurrentTeacher,
) -> ChangePasswordResponse:
    """
    Change the authenticated user's password.

    All previously issued access tokens are invalidated after the
    password is changed.
    """

    try:
        change_user_password(
            db=db,
            user=current_teacher,
            current_password=(
                payload.current_password
            ),
            new_password=payload.new_password,
        )

    except PasswordChangeError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    except AuthPersistenceError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Password change could not be saved. "
                "Please try again."
            ),
        ) from error

    return ChangePasswordResponse()