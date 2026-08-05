import type {
  TeacherReviewRecord,
  TeacherReviewStatus,
} from "../types";


export type ReviewStatusBadgeProps = {
  status?: TeacherReviewStatus | null;
  review?: TeacherReviewRecord | null;
  compact?: boolean;
};


const STATUS_LABELS: Record<
  TeacherReviewStatus,
  string
> = {
  pending: "Pending",
  in_review: "In review",
  reviewed: "Reviewed",
};


const STATUS_CLASS_NAMES: Record<
  TeacherReviewStatus,
  string
> = {
  pending: "teacher-review-status-pending",
  in_review: "teacher-review-status-in-review",
  reviewed: "teacher-review-status-reviewed",
};


function isTeacherReviewStatus(
  value: unknown,
): value is TeacherReviewStatus {
  return (
    value === "pending" ||
    value === "in_review" ||
    value === "reviewed"
  );
}


function resolveStatus({
  status,
  review,
}: Pick<
  ReviewStatusBadgeProps,
  "status" | "review"
>): TeacherReviewStatus {
  const candidate =
    status ??
    review?.status;

  if (
    isTeacherReviewStatus(
      candidate,
    )
  ) {
    return candidate;
  }

  return "pending";
}


export function ReviewStatusBadge({
  status,
  review,
  compact = false,
}: ReviewStatusBadgeProps) {
  const resolvedStatus =
    resolveStatus({
      status,
      review,
    });

  const label =
    STATUS_LABELS[
      resolvedStatus
    ];

  const className = [
    "teacher-review-status-badge",
    STATUS_CLASS_NAMES[
      resolvedStatus
    ],
    compact
      ? "teacher-review-status-badge-compact"
      : null,
  ]
    .filter(
      (
        value,
      ): value is string =>
        Boolean(value),
    )
    .join(" ");

  return (
    <span
      className={className}
      aria-label={`Review status: ${label}`}
      title={`Review status: ${label}`}
      data-review-status={
        resolvedStatus
      }
    >
      <span
        className="teacher-review-status-dot"
        aria-hidden="true"
      />

      <span className="teacher-review-status-label">
        {label}
      </span>
    </span>
  );
}