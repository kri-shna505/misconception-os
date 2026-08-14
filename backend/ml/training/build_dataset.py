from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.ml.label_mapper import (
    SupervisedDiagnosisLabel,
    try_map_teacher_review_to_label,
)
from app.models.attempt import Attempt
from app.models.diagnosis import Diagnosis
from app.models.teacher_review import TeacherReview


EXPORT_DIR = Path(__file__).resolve().parents[1] / "data" / "exports"

DEFAULT_CSV_PATH = EXPORT_DIR / "teacher_reviewed_dataset.csv"
DEFAULT_JSONL_PATH = EXPORT_DIR / "teacher_reviewed_dataset.jsonl"


@dataclass(slots=True)
class DatasetRow:
    attempt_id: str
    student_alias_id: str
    problem_id: str

    parent_attempt_id: str | None
    retry_number: int

    final_answer: str | None
    written_reasoning: str
    normalized_reasoning: str | None
    source_code: str | None
    speech_transcript: str | None

    selected_language: str
    input_language: str | None
    input_modality: str | None

    response_time_seconds: float | None

    speech_processing_status: str | None
    speech_audio_retained: bool | None

    rule_state: str | None
    rule_misconception_id: str | None
    rule_confidence: float | None
    rule_score: float | None

    prediction_source: str | None
    ml_score: float | None
    hybrid_score: float | None

    model_version: str | None
    feature_version: str | None
    calibration_version: str | None

    teacher_review_id: str
    teacher_decision: str

    target_state: str
    target_misconception_id: str | None

    created_at: str


def _stringify_uuid(value: Any) -> str | None:
    if value is None:
        return None

    return str(value)


def _stringify_datetime(value: Any) -> str:
    if value is None:
        return ""

    isoformat = getattr(value, "isoformat", None)

    if callable(isoformat):
        return isoformat()

    return str(value)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip()

    return normalized or None


def _get_retry_number(attempt: Attempt) -> int:
    value = getattr(
        attempt,
        "retry_number",
        0,
    )

    if value is None:
        return 0

    return int(value)


def _get_latest_diagnosis(
    session: Session,
    attempt_id: Any,
) -> Diagnosis | None:
    statement = (
        select(Diagnosis)
        .where(
            Diagnosis.attempt_id == attempt_id
        )
        .order_by(
            Diagnosis.created_at.desc(),
            Diagnosis.id.desc(),
        )
        .limit(1)
    )

    return session.scalar(statement)


def _build_dataset_row(
    *,
    attempt: Attempt,
    review: TeacherReview,
    diagnosis: Diagnosis | None,
    label: SupervisedDiagnosisLabel,
) -> DatasetRow:
    return DatasetRow(
        attempt_id=str(attempt.id),
        student_alias_id=str(
            attempt.student_alias_id
        ),
        problem_id=str(
            attempt.problem_id
        ),
        parent_attempt_id=_stringify_uuid(
            getattr(
                attempt,
                "parent_attempt_id",
                None,
            )
        ),
        retry_number=_get_retry_number(
            attempt
        ),
        final_answer=_optional_text(
            getattr(
                attempt,
                "final_answer",
                None,
            )
        ),
        written_reasoning=(
            getattr(
                attempt,
                "written_reasoning",
                "",
            )
            or ""
        ).strip(),
        normalized_reasoning=_optional_text(
            getattr(
                attempt,
                "normalized_reasoning",
                None,
            )
        ),
        source_code=_optional_text(
            getattr(
                attempt,
                "source_code",
                None,
            )
        ),
        speech_transcript=_optional_text(
            getattr(
                attempt,
                "speech_transcript",
                None,
            )
        ),
        selected_language=(
            getattr(
                attempt,
                "selected_language",
                "",
            )
            or ""
        ).strip(),
        input_language=_optional_text(
            getattr(
                attempt,
                "input_language",
                None,
            )
        ),
        input_modality=_optional_text(
            getattr(
                attempt,
                "input_modality",
                None,
            )
        ),
        response_time_seconds=getattr(
            attempt,
            "response_time_seconds",
            None,
        ),
        speech_processing_status=_optional_text(
            getattr(
                attempt,
                "speech_processing_status",
                None,
            )
        ),
        speech_audio_retained=getattr(
            attempt,
            "speech_audio_retained",
            None,
        ),
        rule_state=(
            diagnosis.state
            if diagnosis is not None
            else None
        ),
        rule_misconception_id=(
            _stringify_uuid(
                diagnosis.primary_misconception_id
            )
            if diagnosis is not None
            else None
        ),
        rule_confidence=(
            diagnosis.confidence
            if diagnosis is not None
            else None
        ),
        rule_score=(
            diagnosis.rule_score
            if diagnosis is not None
            else None
        ),
        prediction_source=(
            getattr(
                diagnosis,
                "prediction_source",
                None,
            )
            if diagnosis is not None
            else None
        ),
        ml_score=(
            getattr(
                diagnosis,
                "ml_score",
                None,
            )
            if diagnosis is not None
            else None
        ),
        hybrid_score=(
            getattr(
                diagnosis,
                "hybrid_score",
                None,
            )
            if diagnosis is not None
            else None
        ),
        model_version=(
            diagnosis.model_version
            if diagnosis is not None
            else None
        ),
        feature_version=(
            getattr(
                diagnosis,
                "feature_version",
                None,
            )
            if diagnosis is not None
            else None
        ),
        calibration_version=(
            getattr(
                diagnosis,
                "calibration_version",
                None,
            )
            if diagnosis is not None
            else None
        ),
        teacher_review_id=(
            label.teacher_review_id
        ),
        teacher_decision=(
            label.review_decision
        ),
        target_state=(
            label.state
        ),
        target_misconception_id=(
            label.misconception_id
        ),
        created_at=_stringify_datetime(
            attempt.created_at
        ),
    )


def load_dataset_rows(
    session: Session,
) -> tuple[list[DatasetRow], int]:
    statement = (
        select(
            Attempt,
            TeacherReview,
        )
        .join(
            TeacherReview,
            TeacherReview.attempt_id
            == Attempt.id,
        )
        .where(
            TeacherReview.status
            == "reviewed"
        )
        .order_by(
            Attempt.created_at.asc(),
            Attempt.id.asc(),
        )
    )

    rows: list[DatasetRow] = []
    rejected_reviews = 0

    for attempt, review in session.execute(
        statement
    ).all():
        label = (
            try_map_teacher_review_to_label(
                review
            )
        )

        if label is None:
            rejected_reviews += 1
            continue

        diagnosis = _get_latest_diagnosis(
            session,
            attempt.id,
        )

        rows.append(
            _build_dataset_row(
                attempt=attempt,
                review=review,
                diagnosis=diagnosis,
                label=label,
            )
        )

    return rows, rejected_reviews


def write_csv(
    rows: list[DatasetRow],
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not rows:
        path.write_text(
            "",
            encoding="utf-8",
        )
        return

    fieldnames = list(
        asdict(rows[0]).keys()
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(
                asdict(row)
            )


def write_jsonl(
    rows: list[DatasetRow],
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        for row in rows:
            file.write(
                json.dumps(
                    asdict(row),
                    ensure_ascii=False,
                )
            )

            file.write("\n")


def _normalized_bucket(
    value: str | None,
    *,
    fallback: str = "missing",
) -> str:
    if value is None:
        return fallback

    normalized = value.strip()

    return (
        normalized.lower()
        if normalized
        else fallback
    )


def print_distribution(
    title: str,
    counter: Counter[str],
) -> None:
    print()
    print(title)
    print("-" * len(title))

    if not counter:
        print("  none")
        return

    total = sum(
        counter.values()
    )

    for name, count in counter.most_common():
        percentage = (
            count / total * 100
            if total
            else 0.0
        )

        print(
            f"  {name}: "
            f"{count} "
            f"({percentage:.1f}%)"
        )


def audit_dataset(
    rows: list[DatasetRow],
    *,
    rejected_reviews: int,
) -> None:
    print()
    print("=" * 72)
    print("SPRINT 11 DATASET AUDIT")
    print("=" * 72)

    print(
        f"Usable supervised rows: "
        f"{len(rows)}"
    )

    print(
        f"Rejected finalized reviews: "
        f"{rejected_reviews}"
    )

    if not rows:
        print()
        print(
            "No teacher-reviewed training rows "
            "are currently available."
        )

        print(
            "Do not train a model until usable "
            "human-reviewed labels exist."
        )

        return

    state_counts = Counter(
        row.target_state
        for row in rows
    )

    misconception_counts = Counter(
        (
            row.target_misconception_id
            or "none"
        )
        for row in rows
    )

    decision_counts = Counter(
        row.teacher_decision
        for row in rows
    )

    input_language_counts = Counter(
        _normalized_bucket(
            row.input_language
        )
        for row in rows
    )

    modality_counts = Counter(
        _normalized_bucket(
            row.input_modality
        )
        for row in rows
    )

    programming_language_counts = Counter(
        _normalized_bucket(
            row.selected_language
        )
        for row in rows
    )

    retry_counts = Counter(
        (
            "retry"
            if row.retry_number > 0
            else "initial"
        )
        for row in rows
    )

    prediction_source_counts = Counter(
        _normalized_bucket(
            row.prediction_source
        )
        for row in rows
    )

    speech_counts = Counter(
        (
            "speech_present"
            if row.speech_transcript
            else "speech_missing"
        )
        for row in rows
    )

    code_counts = Counter(
        (
            "code_present"
            if row.source_code
            else "code_missing"
        )
        for row in rows
    )

    print_distribution(
        "Target state distribution",
        state_counts,
    )

    print_distribution(
        "Target misconception distribution",
        misconception_counts,
    )

    print_distribution(
        "Teacher decision distribution",
        decision_counts,
    )

    print_distribution(
        "Input language distribution",
        input_language_counts,
    )

    print_distribution(
        "Input modality distribution",
        modality_counts,
    )

    print_distribution(
        "Programming language distribution",
        programming_language_counts,
    )

    print_distribution(
        "Initial vs retry distribution",
        retry_counts,
    )

    print_distribution(
        "Prediction source distribution",
        prediction_source_counts,
    )

    print_distribution(
        "Speech availability",
        speech_counts,
    )

    print_distribution(
        "Source-code availability",
        code_counts,
    )

    unique_attempts = len(
        {
            row.attempt_id
            for row in rows
        }
    )

    unique_students = len(
        {
            row.student_alias_id
            for row in rows
        }
    )

    unique_problems = len(
        {
            row.problem_id
            for row in rows
        }
    )

    print()
    print("Coverage")
    print("--------")
    print(
        f"  Unique attempts: "
        f"{unique_attempts}"
    )
    print(
        f"  Unique students: "
        f"{unique_students}"
    )
    print(
        f"  Unique problems: "
        f"{unique_problems}"
    )

    minimum_class_count = min(
        state_counts.values()
    )

    print()
    print("Training readiness")
    print("------------------")

    if len(rows) < 50:
        print(
            "  NOT READY for serious supervised "
            "training: fewer than 50 usable rows."
        )
        print(
            "  Use this dataset only for pipeline "
            "validation and smoke experiments."
        )

    elif len(rows) < 200:
        print(
            "  LIMITED: enough for baseline pipeline "
            "experiments, but conclusions will be weak."
        )

    else:
        print(
            "  Dataset size is reasonable for baseline "
            "experiments."
        )

    if minimum_class_count < 5:
        print(
            "  WARNING: at least one target state has "
            "fewer than 5 examples."
        )

    elif minimum_class_count < 20:
        print(
            "  WARNING: class support is still thin for "
            "stable per-class evaluation."
        )

    else:
        print(
            "  State-level class support is sufficient "
            "for an initial evaluation split."
        )

    if unique_students < 2:
        print(
            "  WARNING: fewer than two students are "
            "represented."
        )

    if unique_problems < 2:
        print(
            "  WARNING: fewer than two problems are "
            "represented."
        )

    print()
    print(
        "Important: automated diagnosis columns are "
        "features/context only."
    )
    print(
        "TeacherReview final fields remain the "
        "supervised ground truth."
    )


def build_dataset(
    *,
    csv_path: Path,
    jsonl_path: Path,
) -> list[DatasetRow]:
    session = SessionLocal()

    try:
        rows, rejected_reviews = (
            load_dataset_rows(
                session
            )
        )

        write_csv(
            rows,
            csv_path,
        )

        write_jsonl(
            rows,
            jsonl_path,
        )

        audit_dataset(
            rows,
            rejected_reviews=rejected_reviews,
        )

        print()
        print("Exports")
        print("-------")
        print(
            f"  CSV:   "
            f"{csv_path}"
        )
        print(
            f"  JSONL: "
            f"{jsonl_path}"
        )

        return rows

    finally:
        session.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the Sprint 11 teacher-reviewed "
            "supervised-learning dataset."
        )
    )

    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help=(
            "Output CSV path. "
            f"Default: {DEFAULT_CSV_PATH}"
        ),
    )

    parser.add_argument(
        "--jsonl",
        type=Path,
        default=DEFAULT_JSONL_PATH,
        help=(
            "Output JSONL path. "
            f"Default: {DEFAULT_JSONL_PATH}"
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    build_dataset(
        csv_path=args.csv,
        jsonl_path=args.jsonl,
    )


if __name__ == "__main__":
    main()