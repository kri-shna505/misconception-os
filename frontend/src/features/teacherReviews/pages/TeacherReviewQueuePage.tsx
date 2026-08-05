import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getTeacherReviewQueue,
  TeacherReviewApiError,
} from "../api";
import { ReviewStatusBadge } from "../components/ReviewStatusBadge";
import type {
  TeacherReviewQueueItem,
  TeacherReviewQueueResponse,
  TeacherReviewStatus,
} from "../types";


type TeacherReviewQueuePageProps = {
  onBack: () => void;
  onOpenReview: (
    attemptId: string,
  ) => void;
  onAuthenticationRequired?: () => void;
};


type ReviewStatusFilter =
  | "all"
  | TeacherReviewStatus;


const DEFAULT_PAGE_SIZE = 20;


function formatDateTime(
  value: string,
): string {
  const parsedDate = new Date(value);

  if (
    Number.isNaN(
      parsedDate.getTime(),
    )
  ) {
    return value;
  }

  return new Intl.DateTimeFormat(
    "en",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(parsedDate);
}


function formatDuration(
  value: number | null,
): string {
  if (value === null) {
    return "Not recorded";
  }

  if (value < 60) {
    return `${Math.round(value)} sec`;
  }

  const minutes = Math.floor(
    value / 60,
  );

  const seconds = Math.round(
    value % 60,
  );

  return `${minutes}m ${seconds}s`;
}


function formatDiagnosisState(
  state: string | undefined,
): string {
  if (!state) {
    return "Undiagnosed";
  }

  return state
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase() +
        part.slice(1),
    )
    .join(" ");
}


function formatConfidence(
  value: number | undefined,
): string {
  if (value === undefined) {
    return "—";
  }

  return `${Math.round(
    value * 100,
  )}%`;
}


function getReviewStatus(
  item: TeacherReviewQueueItem,
): TeacherReviewStatus {
  return (
    item.review?.status ??
    "pending"
  );
}


function getReviewDecisionLabel(
  item: TeacherReviewQueueItem,
): string {
  if (!item.review?.decision) {
    return "No teacher decision";
  }

  return item.review.decision ===
    "accepted"
    ? "Accepted"
    : "Overridden";
}


function getDisplayedDiagnosisState(
  item: TeacherReviewQueueItem,
): string | undefined {
  if (
    item.review?.status === "reviewed" &&
    item.review.final_state
  ) {
    return item.review.final_state;
  }

  return item.system_diagnosis?.state;
}


function getDisplayedDiagnosisLabel(
  item: TeacherReviewQueueItem,
): string {
  return item.review?.status === "reviewed"
    ? "Teacher final diagnosis"
    : "System diagnosis";
}


function getDisplayedConfidence(
  item: TeacherReviewQueueItem,
): number | undefined {
  if (item.review?.status === "reviewed") {
    return undefined;
  }

  return item.system_diagnosis?.confidence;
}


function getDisplayedDiagnosisNote(
  item: TeacherReviewQueueItem,
): string {
  if (item.review?.status === "reviewed") {
    return item.review.decision === "accepted"
      ? "Accepted by teacher"
      : "Overridden by teacher";
  }

  return (
    "Confidence: " +
    formatConfidence(
      getDisplayedConfidence(item),
    )
  );
}


function getErrorMessage(
  error: unknown,
): string {
  if (
    error instanceof
    TeacherReviewApiError
  ) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return (
    "Unable to load the teacher " +
    "review queue."
  );
}


export function TeacherReviewQueuePage({
  onBack,
  onOpenReview,
  onAuthenticationRequired,
}: TeacherReviewQueuePageProps) {
  const [
    response,
    setResponse,
  ] =
    useState<TeacherReviewQueueResponse | null>(
      null,
    );

  const [
    statusFilter,
    setStatusFilter,
  ] =
    useState<ReviewStatusFilter>(
      "all",
    );

  const [
    page,
    setPage,
  ] = useState(1);

  const [
    pageSize,
    setPageSize,
  ] = useState(
    DEFAULT_PAGE_SIZE,
  );

  const [
    isLoading,
    setIsLoading,
  ] = useState(true);

  const [
    errorMessage,
    setErrorMessage,
  ] =
    useState<string | null>(
      null,
    );

  const [
    refreshKey,
    setRefreshKey,
  ] = useState(0);

  useEffect(() => {
    let isCancelled = false;

    async function loadQueue() {
      setIsLoading(true);
      setErrorMessage(null);

      try {
        const payload =
          await getTeacherReviewQueue({
            page,
            page_size: pageSize,
            review_status:
              statusFilter === "all"
                ? undefined
                : statusFilter,
          });

        if (isCancelled) {
          return;
        }

        setResponse(payload);
      } catch (error) {
        if (isCancelled) {
          return;
        }

        if (
          error instanceof
            TeacherReviewApiError &&
          error.status === 401
        ) {
          onAuthenticationRequired?.();
        }

        setErrorMessage(
          getErrorMessage(error),
        );
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadQueue();

    return () => {
      isCancelled = true;
    };
  }, [
    onAuthenticationRequired,
    page,
    pageSize,
    refreshKey,
    statusFilter,
  ]);

  const items =
    response?.items ?? [];

  const pagination =
    response?.pagination;

  const statusCounts =
    useMemo(() => {
      return items.reduce(
        (
          counts,
          item,
        ) => {
          const status =
            getReviewStatus(item);

          counts[status] += 1;

          return counts;
        },
        {
          pending: 0,
          in_review: 0,
          reviewed: 0,
        } satisfies Record<
          TeacherReviewStatus,
          number
        >,
      );
    }, [items]);

  function handleStatusFilterChange(
    nextStatus:
      ReviewStatusFilter,
  ): void {
    setStatusFilter(
      nextStatus,
    );

    setPage(1);
  }

  function handleRetry(): void {
    setRefreshKey(
      (current) =>
        current + 1,
    );
  }

  function handlePageSizeChange(
    value: string,
  ): void {
    const nextPageSize =
      Number(value);

    if (
      !Number.isFinite(
        nextPageSize,
      ) ||
      nextPageSize < 1
    ) {
      return;
    }

    setPageSize(
      nextPageSize,
    );

    setPage(1);
  }

  return (
    <main className="teacher-review-queue-shell">
      <header className="teacher-dashboard-header">
        <div className="brand-lockup">
          <div className="brand-mark">
            M/OS
          </div>

          <div>
            <strong>
              MisconceptionOS
            </strong>

            <span>
              Teacher Review Queue
            </span>
          </div>
        </div>

        <button
          type="button"
          className="ghost-button"
          onClick={onBack}
        >
          Back to dashboard
        </button>
      </header>

      <section className="teacher-review-queue-intro">
        <div>
          <p className="eyebrow">
            Human review workflow
          </p>

          <h1>
            Review student diagnoses
          </h1>

          <p>
            Inspect system diagnoses,
            save review drafts,
            accept or override outcomes,
            and finalize teacher decisions.
          </p>
        </div>

        <div className="teacher-review-queue-total">
          <span>
            Total records
          </span>

          <strong>
            {pagination?.total_items ??
              0}
          </strong>
        </div>
      </section>

      <section className="teacher-review-filter-panel">
        <div className="teacher-review-filter-heading">
          <div>
            <p className="eyebrow">
              Queue filters
            </p>

            <h2>
              Review status
            </h2>
          </div>

          <button
            type="button"
            className="ghost-button"
            onClick={handleRetry}
            disabled={isLoading}
          >
            Refresh
          </button>
        </div>

        <div className="teacher-review-filter-buttons">
          <button
            type="button"
            className={
              statusFilter === "all"
                ? "teacher-review-filter-button teacher-review-filter-button-active"
                : "teacher-review-filter-button"
            }
            onClick={() =>
              handleStatusFilterChange(
                "all",
              )
            }
          >
            All
          </button>

          <button
            type="button"
            className={
              statusFilter === "pending"
                ? "teacher-review-filter-button teacher-review-filter-button-active"
                : "teacher-review-filter-button"
            }
            onClick={() =>
              handleStatusFilterChange(
                "pending",
              )
            }
          >
            Pending
          </button>

          <button
            type="button"
            className={
              statusFilter === "in_review"
                ? "teacher-review-filter-button teacher-review-filter-button-active"
                : "teacher-review-filter-button"
            }
            onClick={() =>
              handleStatusFilterChange(
                "in_review",
              )
            }
          >
            In review
          </button>

          <button
            type="button"
            className={
              statusFilter === "reviewed"
                ? "teacher-review-filter-button teacher-review-filter-button-active"
                : "teacher-review-filter-button"
            }
            onClick={() =>
              handleStatusFilterChange(
                "reviewed",
              )
            }
          >
            Reviewed
          </button>
        </div>

        <div className="teacher-review-visible-summary">
          <span>
            Visible page:
          </span>

          <strong>
            {statusCounts.pending}
          </strong>
          <span>
            pending
          </span>

          <strong>
            {statusCounts.in_review}
          </strong>
          <span>
            in review
          </span>

          <strong>
            {statusCounts.reviewed}
          </strong>
          <span>
            reviewed
          </span>
        </div>
      </section>

      {isLoading ? (
        <section className="state-card">
          Loading teacher review queue...
        </section>
      ) : null}

      {!isLoading &&
      errorMessage ? (
        <section className="state-card error-state-card">
          <h2>
            Unable to load review queue
          </h2>

          <p>
            {errorMessage}
          </p>

          <button
            type="button"
            className="primary-button"
            onClick={handleRetry}
          >
            Retry
          </button>
        </section>
      ) : null}

      {!isLoading &&
      !errorMessage &&
      items.length === 0 ? (
        <section className="teacher-empty-state">
          <h2>
            No review records found
          </h2>

          <p>
            There are no attempts matching
            the selected review status.
          </p>
        </section>
      ) : null}

      {!isLoading &&
      !errorMessage &&
      items.length > 0 ? (
        <>
          <section className="teacher-review-queue-list">
            {items.map(
              (item) => (
                <article
                  className="teacher-review-queue-card"
                  key={
                    item.attempt.id
                  }
                >
                  <div className="teacher-review-card-main">
                    <div className="teacher-review-card-heading">
                      <div>
                        <span className="teacher-review-problem-code">
                          {
                            item.problem
                              .code
                          }
                        </span>

                        <h2>
                          {
                            item.problem
                              .title
                          }
                        </h2>

                        <p>
                          {
                            item.problem
                              .topic
                          }
                        </p>
                      </div>

                      <ReviewStatusBadge
                        review={
                          item.review
                        }
                      />
                    </div>

                    <div className="teacher-review-card-grid">
                      <div>
                        <span>
                          Student
                        </span>

                        <strong>
                          {
                            item.student
                              .alias
                          }
                        </strong>

                        <small>
                          {
                            item.student
                              .pseudonymous_id
                          }
                        </small>
                      </div>

                      <div>
                        <span>
                          {getDisplayedDiagnosisLabel(
                            item,
                          )}
                        </span>

                        <strong>
                          {formatDiagnosisState(
                            getDisplayedDiagnosisState(
                              item,
                            ),
                          )}
                        </strong>

                        <small>
                          {getDisplayedDiagnosisNote(
                            item,
                          )}
                        </small>
                      </div>

                      <div>
                        <span>
                          Teacher decision
                        </span>

                        <strong>
                          {getReviewDecisionLabel(
                            item,
                          )}
                        </strong>

                        <small>
                          {item.review
                            ?.final_state
                            ? formatDiagnosisState(
                                item
                                  .review
                                  .final_state,
                              )
                            : "No final state"}
                        </small>
                      </div>

                      <div>
                        <span>
                          Submission
                        </span>

                        <strong>
                          {
                            item.attempt
                              .selected_language
                          }
                        </strong>

                        <small>
                          {formatDuration(
                            item.attempt
                              .response_time_seconds,
                          )}
                        </small>
                      </div>
                    </div>

                    <div className="teacher-review-card-footer">
                      <span>
                        Submitted{" "}
                        {formatDateTime(
                          item.attempt
                            .created_at,
                        )}
                      </span>

                      {item.review
                        ?.updated_at ? (
                        <span>
                          Review updated{" "}
                          {formatDateTime(
                            item.review
                              .updated_at,
                          )}
                        </span>
                      ) : null}
                    </div>
                  </div>

                  <div className="teacher-review-card-actions">
                    <button
                      type="button"
                      className="primary-button"
                      onClick={() =>
                        onOpenReview(
                          item.attempt
                            .id,
                        )
                      }
                    >
                      {item.review
                        ?.status ===
                      "reviewed"
                        ? "View review"
                        : "Open review"}
                    </button>
                  </div>
                </article>
              ),
            )}
          </section>

          <section className="teacher-pagination">
            <div>
              <span>
                Page{" "}
                {pagination?.page ??
                  page}{" "}
                of{" "}
                {pagination?.total_pages ??
                  1}
              </span>

              <label>
                Rows

                <select
                  value={pageSize}
                  onChange={(
                    event,
                  ) =>
                    handlePageSizeChange(
                      event.target
                        .value,
                    )
                  }
                >
                  <option value={10}>
                    10
                  </option>

                  <option value={20}>
                    20
                  </option>

                  <option value={50}>
                    50
                  </option>
                </select>
              </label>
            </div>

            <div className="teacher-pagination-actions">
              <button
                type="button"
                className="ghost-button"
                disabled={
                  isLoading ||
                  !pagination
                    ?.has_previous
                }
                onClick={() =>
                  setPage(
                    (current) =>
                      Math.max(
                        1,
                        current - 1,
                      ),
                  )
                }
              >
                Previous
              </button>

              <button
                type="button"
                className="primary-button"
                disabled={
                  isLoading ||
                  !pagination
                    ?.has_next
                }
                onClick={() =>
                  setPage(
                    (current) =>
                      current + 1,
                  )
                }
              >
                Next
              </button>
            </div>
          </section>
        </>
      ) : null}
    </main>
  );
}