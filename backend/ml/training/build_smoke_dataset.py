from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final


EXPORT_DIR: Final[Path] = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "exports"
)

DEFAULT_CSV_PATH: Final[Path] = (
    EXPORT_DIR
    / "smoke_training_dataset.csv"
)

DEFAULT_JSONL_PATH: Final[Path] = (
    EXPORT_DIR
    / "smoke_training_dataset.jsonl"
)

SMOKE_DATASET_VERSION: Final[str] = (
    "smoke-v1.0"
)


@dataclass(slots=True)
class SmokeDatasetRow:
    """
    Synthetic engineering-only training row.

    IMPORTANT:
    These rows are NOT research ground truth.
    They exist only to validate the Sprint 11 ML pipeline.
    """

    attempt_id: str
    problem_id: str

    written_reasoning: str
    normalized_reasoning: str | None

    source_code: str | None
    speech_transcript: str | None

    selected_language: str
    input_language: str
    input_modality: str

    response_time_seconds: float

    rule_state: str
    rule_misconception_id: str | None
    rule_confidence: float
    rule_score: float

    target_state: str
    target_misconception_id: str | None

    synthetic: bool
    dataset_version: str


def _row(
    *,
    index: int,
    written_reasoning: str,
    source_code: str | None,
    speech_transcript: str | None,
    input_language: str,
    input_modality: str,
    rule_state: str,
    rule_misconception_id: str | None,
    rule_confidence: float,
    rule_score: float,
    target_state: str,
    target_misconception_id: str | None,
    response_time_seconds: float,
) -> SmokeDatasetRow:
    return SmokeDatasetRow(
        attempt_id=(
            f"smoke-attempt-{index:03d}"
        ),
        problem_id="smoke-problem-p1",
        written_reasoning=(
            written_reasoning
        ),
        normalized_reasoning=None,
        source_code=source_code,
        speech_transcript=(
            speech_transcript
        ),
        selected_language="python",
        input_language=(
            input_language
        ),
        input_modality=(
            input_modality
        ),
        response_time_seconds=(
            response_time_seconds
        ),
        rule_state=rule_state,
        rule_misconception_id=(
            rule_misconception_id
        ),
        rule_confidence=(
            rule_confidence
        ),
        rule_score=rule_score,
        target_state=target_state,
        target_misconception_id=(
            target_misconception_id
        ),
        synthetic=True,
        dataset_version=(
            SMOKE_DATASET_VERSION
        ),
    )


def build_smoke_rows() -> list[SmokeDatasetRow]:
    """
    Build a balanced synthetic dataset.

    We intentionally create multiple examples for each state so that
    train/test stratification works.

    Classes:

    - confident
    - possible
    - insufficient
    - no_misconception
    """

    m1 = "M1"

    rows: list[SmokeDatasetRow] = []

    index = 1

    confident_examples = [
        {
            "written_reasoning": (
                "I will use binary search directly "
                "because checking the middle element "
                "lets me discard half of the array."
            ),
            "source_code": (
                "def search(arr, target):\n"
                "    left = 0\n"
                "    right = len(arr) - 1\n"
                "    while left <= right:\n"
                "        mid = (left + right) // 2\n"
                "        if arr[mid] == target:\n"
                "            return mid\n"
                "        if arr[mid] < target:\n"
                "            left = mid + 1\n"
                "        else:\n"
                "            right = mid - 1\n"
                "    return -1"
            ),
            "speech_transcript": None,
            "input_language": "english",
            "input_modality": (
                "text + code"
            ),
            "response_time_seconds": 42,
        },
        {
            "written_reasoning": (
                "Binary search is O(log n), "
                "so I will use it on this array."
            ),
            "source_code": (
                "while low <= high:\n"
                "    mid = (low + high) // 2"
            ),
            "speech_transcript": (
                "The array does not need sorting "
                "because binary search still compares "
                "with the middle value."
            ),
            "input_language": "english",
            "input_modality": (
                "text + code + speech"
            ),
            "response_time_seconds": 51,
        },
        {
            "written_reasoning": (
                "ఈ array sorted కాకపోయినా "
                "binary search use చేయొచ్చు. "
                "Middle element చూసి half discard చేస్తాను."
            ),
            "source_code": (
                "mid = (left + right) // 2\n"
                "if arr[mid] < target:\n"
                "    left = mid + 1"
            ),
            "speech_transcript": None,
            "input_language": "telugu",
            "input_modality": (
                "text + code"
            ),
            "response_time_seconds": 47,
        },
        {
            "written_reasoning": (
                "I will repeatedly halve the "
                "search interval until I find 7."
            ),
            "source_code": (
                "if arr[mid] == target:\n"
                "    return mid\n"
                "elif arr[mid] < target:\n"
                "    left = mid + 1"
            ),
            "speech_transcript": (
                "Sorted order is not necessary "
                "for this approach."
            ),
            "input_language": "english",
            "input_modality": (
                "text + code + speech"
            ),
            "response_time_seconds": 39,
        },
        {
            "written_reasoning": (
                "Binary search should work because "
                "every comparison removes half "
                "of the remaining values."
            ),
            "source_code": (
                "low = 0\n"
                "high = len(arr) - 1\n"
                "while low <= high:\n"
                "    mid = (low + high) // 2"
            ),
            "speech_transcript": None,
            "input_language": "english",
            "input_modality": (
                "text + code"
            ),
            "response_time_seconds": 36,
        },
        {
            "written_reasoning": (
                "Array order గురించి check చేయాల్సిన "
                "అవసరం లేదు. Binary search faster."
            ),
            "source_code": (
                "mid = (low + high) // 2\n"
                "high = mid - 1"
            ),
            "speech_transcript": (
                "I can discard one half directly."
            ),
            "input_language": "telugu",
            "input_modality": (
                "text + code + speech"
            ),
            "response_time_seconds": 44,
        },
    ]

    for example in confident_examples:
        rows.append(
            _row(
                index=index,
                written_reasoning=(
                    example[
                        "written_reasoning"
                    ]
                ),
                source_code=(
                    example["source_code"]
                ),
                speech_transcript=(
                    example[
                        "speech_transcript"
                    ]
                ),
                input_language=(
                    example[
                        "input_language"
                    ]
                ),
                input_modality=(
                    example[
                        "input_modality"
                    ]
                ),
                rule_state="confident",
                rule_misconception_id=m1,
                rule_confidence=0.92,
                rule_score=0.95,
                target_state="confident",
                target_misconception_id=m1,
                response_time_seconds=(
                    example[
                        "response_time_seconds"
                    ]
                ),
            )
        )

        index += 1

    possible_examples = [
        {
            "written_reasoning": (
                "I think binary search may work "
                "because it is faster."
            ),
            "source_code": None,
            "speech_transcript": None,
            "input_language": "english",
            "input_modality": "text",
            "response_time_seconds": 29,
        },
        {
            "written_reasoning": (
                "I would probably compare with "
                "the middle element."
            ),
            "source_code": None,
            "speech_transcript": (
                "I am not sure whether the array "
                "needs to be sorted."
            ),
            "input_language": "english",
            "input_modality": (
                "text + speech"
            ),
            "response_time_seconds": 31,
        },
        {
            "written_reasoning": (
                "Binary search use చేయాలని అనుకుంటున్నాను, "
                "but sorted condition sure కాదు."
            ),
            "source_code": None,
            "speech_transcript": None,
            "input_language": "telugu",
            "input_modality": "text",
            "response_time_seconds": 34,
        },
        {
            "written_reasoning": (
                "Maybe I can divide the array "
                "into halves repeatedly."
            ),
            "source_code": (
                "mid = len(arr) // 2"
            ),
            "speech_transcript": None,
            "input_language": "english",
            "input_modality": (
                "text + code"
            ),
            "response_time_seconds": 27,
        },
        {
            "written_reasoning": (
                "I expect O(log n) search, "
                "but I am not fully sure about "
                "the precondition."
            ),
            "source_code": None,
            "speech_transcript": (
                "I think the middle element "
                "helps reduce the search space."
            ),
            "input_language": "english",
            "input_modality": (
                "text + speech"
            ),
            "response_time_seconds": 35,
        },
        {
            "written_reasoning": (
                "Middle element compare చేస్తే "
                "half remove చేయొచ్చేమో."
            ),
            "source_code": None,
            "speech_transcript": None,
            "input_language": "telugu",
            "input_modality": "text",
            "response_time_seconds": 33,
        },
    ]

    for example in possible_examples:
        rows.append(
            _row(
                index=index,
                written_reasoning=(
                    example[
                        "written_reasoning"
                    ]
                ),
                source_code=(
                    example["source_code"]
                ),
                speech_transcript=(
                    example[
                        "speech_transcript"
                    ]
                ),
                input_language=(
                    example[
                        "input_language"
                    ]
                ),
                input_modality=(
                    example[
                        "input_modality"
                    ]
                ),
                rule_state="possible",
                rule_misconception_id=m1,
                rule_confidence=0.63,
                rule_score=0.65,
                target_state="possible",
                target_misconception_id=m1,
                response_time_seconds=(
                    example[
                        "response_time_seconds"
                    ]
                ),
            )
        )

        index += 1

    insufficient_examples = [
        {
            "written_reasoning": "I don't know.",
            "source_code": None,
            "speech_transcript": None,
            "input_language": "english",
            "input_modality": "text",
            "response_time_seconds": 8,
        },
        {
            "written_reasoning": "Not sure.",
            "source_code": None,
            "speech_transcript": None,
            "input_language": "english",
            "input_modality": "text",
            "response_time_seconds": 11,
        },
        {
            "written_reasoning": "తెలియదు.",
            "source_code": None,
            "speech_transcript": None,
            "input_language": "telugu",
            "input_modality": "text",
            "response_time_seconds": 9,
        },
        {
            "written_reasoning": (
                "Maybe search somehow."
            ),
            "source_code": None,
            "speech_transcript": None,
            "input_language": "english",
            "input_modality": "text",
            "response_time_seconds": 10,
        },
        {
            "written_reasoning": "",
            "source_code": None,
            "speech_transcript": (
                "I am not sure what approach to use."
            ),
            "input_language": "english",
            "input_modality": "speech",
            "response_time_seconds": 13,
        },
        {
            "written_reasoning": (
                "ఏ algorithm use చేయాలో తెలియదు."
            ),
            "source_code": None,
            "speech_transcript": None,
            "input_language": "telugu",
            "input_modality": "text",
            "response_time_seconds": 12,
        },
    ]

    for example in insufficient_examples:
        rows.append(
            _row(
                index=index,
                written_reasoning=(
                    example[
                        "written_reasoning"
                    ]
                ),
                source_code=(
                    example["source_code"]
                ),
                speech_transcript=(
                    example[
                        "speech_transcript"
                    ]
                ),
                input_language=(
                    example[
                        "input_language"
                    ]
                ),
                input_modality=(
                    example[
                        "input_modality"
                    ]
                ),
                rule_state="insufficient",
                rule_misconception_id=None,
                rule_confidence=0.22,
                rule_score=0.18,
                target_state="insufficient",
                target_misconception_id=None,
                response_time_seconds=(
                    example[
                        "response_time_seconds"
                    ]
                ),
            )
        )

        index += 1

    correct_examples = [
        {
            "written_reasoning": (
                "Binary search requires sorted input. "
                "This array is unsorted, so I will use "
                "linear search."
            ),
            "source_code": (
                "def search(arr, target):\n"
                "    for index, value in enumerate(arr):\n"
                "        if value == target:\n"
                "            return index\n"
                "    return -1"
            ),
            "speech_transcript": None,
            "input_language": "english",
            "input_modality": (
                "text + code"
            ),
            "response_time_seconds": 38,
        },
        {
            "written_reasoning": (
                "The input is not sorted. "
                "I should scan each element instead "
                "of using binary search directly."
            ),
            "source_code": (
                "for i in range(len(arr)):\n"
                "    if arr[i] == target:\n"
                "        return i"
            ),
            "speech_transcript": (
                "Binary search depends on sorted order."
            ),
            "input_language": "english",
            "input_modality": (
                "text + code + speech"
            ),
            "response_time_seconds": 40,
        },
        {
            "written_reasoning": (
                "ఈ array sorted కాదు. "
                "కాబట్టి direct binary search correct కాదు. "
                "Linear search చేస్తాను."
            ),
            "source_code": (
                "for index, value in enumerate(arr):\n"
                "    if value == target:\n"
                "        return index"
            ),
            "speech_transcript": None,
            "input_language": "telugu",
            "input_modality": (
                "text + code"
            ),
            "response_time_seconds": 41,
        },
        {
            "written_reasoning": (
                "I can either sort the array first "
                "or use a search algorithm that does "
                "not require ordering. I will use "
                "linear search."
            ),
            "source_code": (
                "for value in arr:\n"
                "    if value == target:\n"
                "        return True"
            ),
            "speech_transcript": None,
            "input_language": "english",
            "input_modality": (
                "text + code"
            ),
            "response_time_seconds": 37,
        },
        {
            "written_reasoning": (
                "Binary search correct ga work అవ్వాలంటే "
                "array sorted ఉండాలి. ఈ input sorted కాదు."
            ),
            "source_code": (
                "for i, item in enumerate(arr):\n"
                "    if item == target:\n"
                "        return i"
            ),
            "speech_transcript": (
                "So I will use linear search."
            ),
            "input_language": "telugu",
            "input_modality": (
                "text + code + speech"
            ),
            "response_time_seconds": 43,
        },
        {
            "written_reasoning": (
                "The sorted-input precondition is missing, "
                "so binary search is inappropriate here."
            ),
            "source_code": (
                "return next(\n"
                "    (i for i, v in enumerate(arr) "
                "if v == target),\n"
                "    -1,\n"
                ")"
            ),
            "speech_transcript": None,
            "input_language": "english",
            "input_modality": (
                "text + code"
            ),
            "response_time_seconds": 36,
        },
    ]

    for example in correct_examples:
        rows.append(
            _row(
                index=index,
                written_reasoning=(
                    example[
                        "written_reasoning"
                    ]
                ),
                source_code=(
                    example["source_code"]
                ),
                speech_transcript=(
                    example[
                        "speech_transcript"
                    ]
                ),
                input_language=(
                    example[
                        "input_language"
                    ]
                ),
                input_modality=(
                    example[
                        "input_modality"
                    ]
                ),
                rule_state="no_misconception",
                rule_misconception_id=None,
                rule_confidence=0.95,
                rule_score=0.95,
                target_state=(
                    "no_misconception"
                ),
                target_misconception_id=None,
                response_time_seconds=(
                    example[
                        "response_time_seconds"
                    ]
                ),
            )
        )

        index += 1

    return rows


def write_csv(
    rows: list[SmokeDatasetRow],
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
    rows: list[SmokeDatasetRow],
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


def print_summary(
    rows: list[SmokeDatasetRow],
) -> None:
    counts: dict[str, int] = {}

    language_counts: dict[str, int] = {}
    modality_counts: dict[str, int] = {}

    for row in rows:
        counts[row.target_state] = (
            counts.get(
                row.target_state,
                0,
            )
            + 1
        )

        language_counts[
            row.input_language
        ] = (
            language_counts.get(
                row.input_language,
                0,
            )
            + 1
        )

        modality_counts[
            row.input_modality
        ] = (
            modality_counts.get(
                row.input_modality,
                0,
            )
            + 1
        )

    print()
    print("=" * 72)
    print("SPRINT 11 SMOKE DATASET")
    print("=" * 72)

    print(
        f"Dataset version: "
        f"{SMOKE_DATASET_VERSION}"
    )

    print(
        f"Total synthetic rows: "
        f"{len(rows)}"
    )

    print()
    print("Target-state distribution")
    print("-------------------------")

    for state in sorted(counts):
        print(
            f"  {state}: "
            f"{counts[state]}"
        )

    print()
    print("Input-language distribution")
    print("---------------------------")

    for language in sorted(
        language_counts
    ):
        print(
            f"  {language}: "
            f"{language_counts[language]}"
        )

    print()
    print("Input-modality distribution")
    print("---------------------------")

    for modality in sorted(
        modality_counts
    ):
        print(
            f"  {modality}: "
            f"{modality_counts[modality]}"
        )

    print()
    print("WARNING")
    print("-------")

    print(
        "This dataset is SYNTHETIC and exists only "
        "for engineering smoke tests."
    )

    print(
        "Do not merge it into the real "
        "teacher-reviewed dataset."
    )

    print(
        "Do not report metrics from this dataset "
        "as research/model performance."
    )


def build_smoke_dataset(
    *,
    csv_path: Path,
    jsonl_path: Path,
) -> list[SmokeDatasetRow]:
    rows = build_smoke_rows()

    write_csv(
        rows,
        csv_path,
    )

    write_jsonl(
        rows,
        jsonl_path,
    )

    print_summary(
        rows
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a synthetic Sprint 11 "
            "engineering smoke dataset."
        )
    )

    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV_PATH,
    )

    parser.add_argument(
        "--jsonl",
        type=Path,
        default=DEFAULT_JSONL_PATH,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    build_smoke_dataset(
        csv_path=args.csv,
        jsonl_path=args.jsonl,
    )


if __name__ == "__main__":
    main()