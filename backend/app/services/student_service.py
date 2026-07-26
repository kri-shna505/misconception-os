import re
import uuid

from sqlalchemy.orm import Session

from app.models.student_alias import StudentAlias
from app.schemas.student_schema import StudentSessionCreate


class StudentService:
    EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
    PHONE_PATTERN = re.compile(r"\b\d{10}\b")

    @staticmethod
    def _is_pii_like(alias: str) -> bool:
        cleaned = alias.strip().lower()

        if StudentService.EMAIL_PATTERN.search(cleaned):
            return True

        if StudentService.PHONE_PATTERN.search(cleaned):
            return True

        return False

    @staticmethod
    def _generate_pseudonymous_id() -> str:
        return f"STU-{uuid.uuid4().hex[:8].upper()}"

    @staticmethod
    def create_session(db: Session, payload: StudentSessionCreate) -> StudentAlias:
        alias = payload.alias.strip()

        if not payload.consent_status:
            raise ValueError("Consent is required to create a student session.")

        if StudentService._is_pii_like(alias):
            raise ValueError("Alias must not contain email address or phone number.")

        student = StudentAlias(
            alias=alias,
            pseudonymous_id=StudentService._generate_pseudonymous_id(),
            consent_status=True,
        )

        db.add(student)
        db.commit()
        db.refresh(student)

        return student