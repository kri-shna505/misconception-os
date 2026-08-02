from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.misconception import Misconception
from app.models.problem import Problem
from app.models.problem_misconception import ProblemMisconception


class ProblemService:
    @staticmethod
    def list_active_problems(
        db: Session,
    ) -> list[Problem]:
        """
        Return all active problems for the student problem bank.

        Results are ordered by problem code to keep the frontend display
        deterministic.
        """

        return (
            db.query(Problem)
            .filter(Problem.active.is_(True))
            .order_by(Problem.code.asc())
            .all()
        )

    @staticmethod
    def get_problem_detail(
        db: Session,
        problem_id: UUID,
    ) -> dict[str, Any] | None:
        """
        Return one active problem together with its supported active
        misconception mappings.

        The returned dictionary matches the ProblemDetail response schema.
        """

        problem = (
            db.query(Problem)
            .filter(
                Problem.id == problem_id,
                Problem.active.is_(True),
            )
            .first()
        )

        if problem is None:
            return None

        misconceptions = (
            db.query(Misconception)
            .join(
                ProblemMisconception,
                ProblemMisconception.misconception_id
                == Misconception.id,
            )
            .filter(
                ProblemMisconception.problem_id == problem.id,
                Misconception.active.is_(True),
            )
            .order_by(Misconception.code.asc())
            .all()
        )

        return {
            "id": problem.id,
            "code": problem.code,
            "title": problem.title,
            "topic": problem.topic,
            "statement": problem.statement,
            "difficulty": problem.difficulty,
            "expected_language": problem.expected_language,
            "rule_context": problem.rule_context,
            "active": problem.active,
            "supported_misconceptions": misconceptions,
            "created_at": problem.created_at,
        }