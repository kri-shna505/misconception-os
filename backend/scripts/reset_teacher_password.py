from __future__ import annotations

import getpass
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User


def normalize_email(value: str) -> str:
    email = value.strip().lower()

    if not email:
        raise ValueError("Email cannot be empty.")

    return email


def read_new_password() -> str:
    password = getpass.getpass(
        "New password: "
    )

    confirmation = getpass.getpass(
        "Confirm new password: "
    )

    if password != confirmation:
        raise ValueError(
            "Passwords do not match."
        )

    if len(password) < 8:
        raise ValueError(
            "Password must contain at least 8 characters."
        )

    if len(password.encode("utf-8")) > 128:
        raise ValueError(
            "Password is too long."
        )

    return password


def reset_teacher_password() -> None:
    print()
    print("Reset MisconceptionOS teacher password")
    print("---------------------------------------")

    try:
        email = normalize_email(
            input("Teacher email: ")
        )
        new_password = read_new_password()

    except (EOFError, KeyboardInterrupt):
        print()
        print("Password reset cancelled.")
        raise SystemExit(1)

    except ValueError as error:
        print()
        print(f"Input error: {error}")
        raise SystemExit(1)

    db = SessionLocal()

    try:
        statement = select(User).where(
            func.lower(User.email) == email
        )

        user = db.scalar(statement)

        if user is None:
            print()
            print("Teacher account was not found.")
            raise SystemExit(1)

        user.password_hash = hash_password(
            new_password
        )
        user.password_changed_at = (
            datetime.utcnow()
        )
        user.failed_login_attempts = 0
        user.token_version = (
            (user.token_version or 0) + 1
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    except SQLAlchemyError as error:
        db.rollback()

        print()
        print(
            "Database error: password could "
            "not be reset."
        )
        print(str(error))

        raise SystemExit(1)

    finally:
        db.close()

    print()
    print("Password reset successfully.")
    print(f"Email: {user.email}")
    print(
        "The password hash is now compatible "
        "with the current Argon2 configuration."
    )


if __name__ == "__main__":
    reset_teacher_password()