from app.core.database import SessionLocal

from app.models.user import User
from app.models.misconception import Misconception
from app.models.problem import Problem
from app.models.problem_misconception import ProblemMisconception
from app.models.diagnostic_question import DiagnosticQuestion
from app.models.hint_template import HintTemplate


def get_or_create_misconception(db, code, name, topic, description):
    existing = db.query(Misconception).filter(Misconception.code == code).first()
    if existing:
        return existing

    item = Misconception(
        code=code,
        name=name,
        topic=topic,
        description=description,
        active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_or_create_problem(
    db,
    code,
    title,
    topic,
    statement,
    difficulty,
    expected_language,
    rule_context,
):
    existing = db.query(Problem).filter(Problem.code == code).first()
    if existing:
        return existing

    item = Problem(
        code=code,
        title=title,
        topic=topic,
        statement=statement,
        difficulty=difficulty,
        expected_language=expected_language,
        rule_context=rule_context,
        active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_or_create_mapping(db, problem_id, misconception_id):
    existing = (
        db.query(ProblemMisconception)
        .filter(
            ProblemMisconception.problem_id == problem_id,
            ProblemMisconception.misconception_id == misconception_id,
        )
        .first()
    )

    if existing:
        return existing

    item = ProblemMisconception(
        problem_id=problem_id,
        misconception_id=misconception_id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_or_create_question(
    db,
    misconception_id,
    question_text,
    competing_misconception_id=None,
):
    existing = (
        db.query(DiagnosticQuestion)
        .filter(
            DiagnosticQuestion.misconception_id == misconception_id,
            DiagnosticQuestion.question_text == question_text,
        )
        .first()
    )

    if existing:
        return existing

    item = DiagnosticQuestion(
        misconception_id=misconception_id,
        competing_misconception_id=competing_misconception_id,
        question_text=question_text,
        active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_or_create_hint(db, misconception_id, level, hint_text):
    existing = (
        db.query(HintTemplate)
        .filter(
            HintTemplate.misconception_id == misconception_id,
            HintTemplate.level == level,
        )
        .first()
    )

    if existing:
        return existing

    item = HintTemplate(
        misconception_id=misconception_id,
        level=level,
        hint_text=hint_text,
        active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_or_create_teacher(db):
    email = "teacher@misconceptionos.local"

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return existing

    teacher = User(
        email=email,
        password_hash="TEMP_HASH_CHANGE_IN_AUTH_SPRINT",
        role="admin",
        is_active=True,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


def seed():
    db = SessionLocal()

    try:
        print("Seeding MisconceptionOS database...")

        teacher = get_or_create_teacher(db)

        # 1. Misconceptions
        m1 = get_or_create_misconception(
            db,
            code="M1",
            name="Binary Search on Unsorted Data",
            topic="Binary Search",
            description="Student applies binary search without recognizing that binary search requires sorted input.",
        )

        m2 = get_or_create_misconception(
            db,
            code="M2",
            name="Missing or Incorrect Recursion Base Case",
            topic="Recursion",
            description="Student writes recursive logic without a valid stopping condition.",
        )

        m3 = get_or_create_misconception(
            db,
            code="M3",
            name="Recursive Call Without Reducing Problem Size",
            topic="Recursion",
            description="Student writes a recursive call that does not move toward the base case.",
        )

        m4 = get_or_create_misconception(
            db,
            code="M4",
            name="Pass-by-Value vs Pass-by-Reference Confusion",
            topic="Function Parameters",
            description="Student expects local parameter changes to modify caller variables without return, pointer, or reference semantics.",
        )

        m5 = get_or_create_misconception(
            db,
            code="M5",
            name="Stack vs Heap Confusion",
            topic="Memory Model",
            description="Student confuses stack frames, heap allocation, local variable lifetime, or dynamic memory behavior.",
        )

        # 2. Problems
        p1 = get_or_create_problem(
            db,
            code="P1",
            title="Search Target in Array",
            topic="Binary Search",
            difficulty="easy",
            expected_language="python",
            statement=(
                "Given an array and a target value, explain how you would search for the target "
                "and write code for your approach.\n\n"
                "Array: [4, 1, 7, 3, 9]\n"
                "Target: 7"
            ),
            rule_context={
                "requires_sorted_input": True,
                "input_array": [4, 1, 7, 3, 9],
                "target": 7,
            },
        )

        p2 = get_or_create_problem(
            db,
            code="P2",
            title="Recursive Factorial",
            topic="Recursion",
            difficulty="easy",
            expected_language="python",
            statement=(
                "Write a recursive function factorial(n) that returns n!. "
                "Explain when the recursion stops and how each recursive call moves toward that stopping condition."
            ),
            rule_context={
                "expected_recursive_variable": "n",
                "expected_progress": "decrease",
                "valid_base_cases": ["n == 0", "n == 1", "n <= 1"],
            },
        )

        p3 = get_or_create_problem(
            db,
            code="P3",
            title="Recursive Sum of N Numbers",
            topic="Recursion",
            difficulty="easy",
            expected_language="python",
            statement=(
                "Write a recursive function sum_n(n) that returns 1 + 2 + ... + n. "
                "Explain the base case and recursive step."
            ),
            rule_context={
                "expected_recursive_variable": "n",
                "expected_progress": "decrease",
                "valid_base_cases": ["n == 0", "n == 1", "n <= 1"],
            },
        )

        p4 = get_or_create_problem(
            db,
            code="P4",
            title="Swap Two Numbers",
            topic="Function Parameters",
            difficulty="medium",
            expected_language="c",
            statement=(
                "Write a C function to swap two integer variables x and y. "
                "Explain whether the original variables in the caller will change."
            ),
            rule_context={
                "language": "c",
                "requires_caller_variable_mutation": True,
                "valid_methods": ["return_values", "pointers", "references"],
            },
        )

        p5 = get_or_create_problem(
            db,
            code="P5",
            title="Recursion Memory Explanation",
            topic="Memory Model",
            difficulty="medium",
            expected_language="text",
            statement=(
                "Explain where local variables of recursive function calls are stored, "
                "and what happens to them when each function call returns."
            ),
            rule_context={
                "focus": "stack_heap_memory",
                "requires_code": False,
            },
        )

        # 3. Problem-misconception mappings
        get_or_create_mapping(db, p1.id, m1.id)

        get_or_create_mapping(db, p2.id, m2.id)
        get_or_create_mapping(db, p2.id, m3.id)

        get_or_create_mapping(db, p3.id, m2.id)
        get_or_create_mapping(db, p3.id, m3.id)

        get_or_create_mapping(db, p4.id, m4.id)

        get_or_create_mapping(db, p5.id, m5.id)

        # 4. Diagnostic questions
        get_or_create_question(
            db,
            misconception_id=m1.id,
            question_text="What condition must an array satisfy before binary search can be used correctly?",
        )

        get_or_create_question(
            db,
            misconception_id=m2.id,
            competing_misconception_id=m3.id,
            question_text="When should your recursive function stop calling itself?",
        )

        get_or_create_question(
            db,
            misconception_id=m3.id,
            competing_misconception_id=m2.id,
            question_text="What value is passed to the next recursive call, and is it closer to the stopping case?",
        )

        get_or_create_question(
            db,
            misconception_id=m4.id,
            question_text="In this language, does changing a function parameter automatically change the original variable in the caller?",
        )

        get_or_create_question(
            db,
            misconception_id=m5.id,
            question_text="Where are local variables of a function call usually stored, and what happens to them when the function returns?",
        )

        # 5. Hint templates
        get_or_create_hint(
            db,
            m1.id,
            1,
            "Binary search depends on an ordering assumption.",
        )
        get_or_create_hint(
            db,
            m1.id,
            2,
            "Before using low, high, and mid, check whether the array is sorted.",
        )
        get_or_create_hint(
            db,
            m1.id,
            3,
            "For an unsorted array, either sort it first or use a search method that does not require ordering.",
        )

        get_or_create_hint(
            db,
            m2.id,
            1,
            "Every recursive function needs a stopping condition.",
        )
        get_or_create_hint(
            db,
            m2.id,
            2,
            "Look for the smallest input where the answer is already known.",
        )
        get_or_create_hint(
            db,
            m2.id,
            3,
            "For factorial, n == 0 or n == 1 can return 1 without another recursive call.",
        )

        get_or_create_hint(
            db,
            m3.id,
            1,
            "A recursive call must move closer to the stopping condition.",
        )
        get_or_create_hint(
            db,
            m3.id,
            2,
            "Check whether the argument passed to the recursive call is smaller, shorter, or otherwise closer to completion.",
        )
        get_or_create_hint(
            db,
            m3.id,
            3,
            "For factorial, calling factorial(n) repeats the same problem; calling factorial(n - 1) reduces the problem size.",
        )

        get_or_create_hint(
            db,
            m4.id,
            1,
            "Changing a local parameter does not always change the original variable.",
        )
        get_or_create_hint(
            db,
            m4.id,
            2,
            "Check whether your language passes a copy, a pointer, a reference, or an object reference.",
        )
        get_or_create_hint(
            db,
            m4.id,
            3,
            "In C, swapping two caller variables usually requires pointers or returning the new values.",
        )

        get_or_create_hint(
            db,
            m5.id,
            1,
            "Stack and heap store different kinds of runtime data.",
        )
        get_or_create_hint(
            db,
            m5.id,
            2,
            "Function calls usually create stack frames; dynamic allocation usually uses heap memory.",
        )
        get_or_create_hint(
            db,
            m5.id,
            3,
            "Local variables in a function call usually disappear when that call returns, while heap-allocated memory follows different lifetime rules.",
        )

        print("Seed completed successfully.")
        print(f"Teacher/admin account seeded: {teacher.email}")

    finally:
        db.close()


if __name__ == "__main__":
    seed()