from uuid import UUID

from sqlalchemy.orm import Session

from app.models.misconception import Misconception
from app.models.problem import Problem
from app.models.problem_misconception import ProblemMisconception


class ProblemService:
    @staticmethod
    def list_active_problems(db: Session) -> list[Problem]:
        return (
            db.query(Problem)
            .filter(Problem.active.is_(True))
            .order_by(Problem.code.asc())
            .all()
        )

    @staticmethod
    def get_problem_detail(db: Session, problem_id: UUID) -> dict | None:
        problem = (
            db.query(Problem)
            .filter(
                Problem.id == problem_id,
                Problem.active.is_(True),
            )
            .first()
        )

        if not problem:
            return None

        misconceptions = (
            db.query(Misconception)
            .join(
                ProblemMisconception,
                ProblemMisconception.misconception_id == Misconception.id,
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
            "supported_misconceptions": misconceptions,
            "created_at": problem.created_at,
        }