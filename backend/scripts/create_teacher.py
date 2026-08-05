from __future__ import annotations

import getpass
import sys
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# Allow running the script directly from backend/scripts/.
BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User


ALLOWED_ROLES = {
    "teacher",
    "admin",
}


def normalize_email(value: str) -> str:
    email = value.strip().lower()

    if not email:
        raise ValueError("Email cannot be empty.")

    if email.count("@") != 1:
        raise ValueError(
            "Email must contain exactly one @ symbol."
        )

    local_part, domain_part = email.split(
        "@",
        maxsplit=1,
    )

    if not local_part or not domain_part:
        raise ValueError(
            "Email must contain a valid local part and domain."
        )

    if "." not in domain_part:
        raise ValueError(
            "Email domain must contain a dot."
        )

    return email


def normalize_display_name(
    value: str,
) -> str | None:
    display_name = value.strip()

    if not display_name:
        return None

    if len(display_name) > 120:
        raise ValueError(
            "Display name must not exceed 120 characters."
        )

    return display_name


def normalize_role(value: str) -> str:
    role = value.strip().lower() or "teacher"

    if role not in ALLOWED_ROLES:
        allowed_values = ", ".join(
            sorted(ALLOWED_ROLES)
        )

        raise ValueError(
            f"Role must be one of: {allowed_values}."
        )

    return role


def read_password() -> str:
    password = getpass.getpass(
        "Password: "
    )

    password_confirmation = getpass.getpass(
        "Confirm password: "
    )

    if password != password_confirmation:
        raise ValueError(
            "Passwords do not match."
        )

    if len(password) < 8:
        raise ValueError(
            "Password must contain at least 8 characters."
        )

    if len(password) > 128:
        raise ValueError(
            "Password must not exceed 128 characters."
        )

    return password


def find_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    statement = select(User).where(
        func.lower(User.email) == email
    )

    return db.scalar(statement)


def create_teacher() -> None:
    print()
    print("Create MisconceptionOS teacher account")
    print("---------------------------------------")

    try:
        email = normalize_email(
            input("Email: ")
        )

        display_name = normalize_display_name(
            input("Display name (optional): ")
        )

        role = normalize_role(
            input(
                "Role [teacher/admin] "
                "(default: teacher): "
            )
        )

        password = read_password()

    except (EOFError, KeyboardInterrupt):
        print()
        print("Account creation cancelled.")
        raise SystemExit(1)

    except ValueError as error:
        print()
        print(f"Input error: {error}")
        raise SystemExit(1)

    db = SessionLocal()

    try:
        existing_user = find_user_by_email(
            db=db,
            email=email,
        )

        if existing_user is not None:
            print()
            print(
                "A user with this email already exists."
            )
            raise SystemExit(1)

        user = User(
            email=email,
            display_name=display_name,
            password_hash=hash_password(
                password
            ),
            role=role,
            is_active=True,
            failed_login_attempts=0,
            token_version=0,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    except SQLAlchemyError as error:
        db.rollback()

        print()
        print(
            "Database error: teacher account "
            "could not be created."
        )
        print(str(error))

        raise SystemExit(1)

    except ValueError as error:
        db.rollback()

        print()
        print(f"Password error: {error}")

        raise SystemExit(1)

    finally:
        db.close()

    print()
    print("Teacher account created successfully.")
    print(f"User ID: {user.id}")
    print(f"Email: {user.email}")
    print(
        f"Display name: "
        f"{user.display_name or 'Not provided'}"
    )
    print(f"Role: {user.role}")
    print(f"Active: {user.is_active}")


if __name__ == "__main__":
    create_teacher()