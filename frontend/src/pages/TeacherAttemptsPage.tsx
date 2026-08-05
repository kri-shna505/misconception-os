import {
  type FormEvent,
  useEffect,
  useMemo,
  useState,
} from "react";

import { getTeacherAttempts } from "../services/teacherApi";
import type {
  TeacherAttemptFilters,
  TeacherAttemptListItem,
  TeacherAttemptListResponse,
} from "../types/teacher";

type TeacherAttemptsPageProps = {
  onBack: () => void;
  onOpenAttempt?: (attemptId: string) => void;
  onOpenStudentHistory?: (
    studentAliasId: string
  ) => void;
  onOpenProblemAnalytics?: (
    problemId: string
  ) => void;

  /*
   * When supplied, the page initially loads only
   * attempts belonging to this problem.
   */
  initialProblemId?: string;
};

type AttemptFilterFormState = {
  search: string;
  diagnosisState: string;
  misconceptionCode: string;
  createdFrom: string;
  createdTo: string;
  problemId: string;
};

const DEFAULT_PAGE_SIZE = 20;

function createInitialFilters(
  problemId?: string
): AttemptFilterFormState {
  return {
    search: "",
    diagnosisState: "",
    misconceptionCode: "",
    createdFrom: "",
    createdTo: "",
    problemId: problemId ?? "",
  };
}

function formatDateTime(value: string): string {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

function formatDuration(
  value: number | null
): string {
  if (value === null) {
    return "Not recorded";
  }

  if (value < 60) {
    return `${Math.round(value)} sec`;
  }

  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);

  return `${minutes}m ${seconds}s`;
}

function formatDiagnosisState(
  state: string | undefined
): string {
  if (!state) {
    return "Undiagnosed";
  }

  return state
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase() +
        part.slice(1)
    )
    .join(" ");
}

function diagnosisClassName(
  state: string | undefined
): string {
  switch (state) {
    case "confident":
      return (
        "teacher-status-pill " +
        "teacher-status-confident"
      );

    case "possible":
      return (
        "teacher-status-pill " +
        "teacher-status-possible"
      );

    case "insufficient":
      return (
        "teacher-status-pill " +
        "teacher-status-insufficient"
      );

    case "no_misconception":
      return (
        "teacher-status-pill " +
        "teacher-status-verified"
      );

    default:
      return (
        "teacher-status-pill " +
        "teacher-status-undiagnosed"
      );
  }
}

function formatConfidence(
  value: number | undefined
): string {
  if (value === undefined) {
    return "—";
  }

  return `${Math.round(value * 100)}%`;
}


function getDisplayedDiagnosisState(
  item: TeacherAttemptListItem
): string | undefined {
  if (
    item.review?.status === "reviewed" &&
    item.review.final_state
  ) {
    return item.review.final_state;
  }

  return (
    item.system_diagnosis?.state ??
    item.diagnosis?.state
  );
}


function getDisplayedConfidence(
  item: TeacherAttemptListItem
): string {
  if (
    item.review?.status === "reviewed" &&
    item.review.final_state
  ) {
    return "Reviewed";
  }

  return formatConfidence(
    (
      item.system_diagnosis ??
      item.diagnosis
    )?.confidence
  );
}

function buildApiFilters({
  page,
  pageSize,
  filters,
}: {
  page: number;
  pageSize: number;
  filters: AttemptFilterFormState;
}): TeacherAttemptFilters {
  return {
    page,
    page_size: pageSize,

    /*
     * This is the key connection required by the
     * problem analytics "View related attempts"
     * navigation.
     */
    problem_id:
      filters.problemId || undefined,

    search:
      filters.search.trim() || undefined,

    diagnosis_state:
      filters.diagnosisState === ""
        ? undefined
        : (filters.diagnosisState as TeacherAttemptFilters["diagnosis_state"]),

    misconception_code:
      filters.misconceptionCode.trim() ||
      undefined,

    created_from: filters.createdFrom
      ? new Date(
          `${filters.createdFrom}T00:00:00`
        ).toISOString()
      : undefined,

    created_to: filters.createdTo
      ? new Date(
          `${filters.createdTo}T23:59:59`
        ).toISOString()
      : undefined,
  };
}

export function TeacherAttemptsPage({
  onBack,
  onOpenAttempt,
  onOpenStudentHistory,
  onOpenProblemAnalytics,
  initialProblemId,
}: TeacherAttemptsPageProps) {
  const [response, setResponse] =
    useState<TeacherAttemptListResponse | null>(
      null
    );

  const [draftFilters, setDraftFilters] =
    useState<AttemptFilterFormState>(() =>
      createInitialFilters(initialProblemId)
    );

  const [appliedFilters, setAppliedFilters] =
    useState<AttemptFilterFormState>(() =>
      createInitialFilters(initialProblemId)
    );

  const [page, setPage] = useState(1);

  const [pageSize, setPageSize] =
    useState(DEFAULT_PAGE_SIZE);

  const [isLoading, setIsLoading] =
    useState(true);

  const [errorMessage, setErrorMessage] =
    useState<string | null>(null);

  const [refreshKey, setRefreshKey] =
    useState(0);

  /*
   * Synchronize the page when App.tsx supplies a
   * different problem filter while this component
   * remains mounted.
   */
  useEffect(() => {
    const nextProblemId =
      initialProblemId ?? "";

    setDraftFilters((current) => {
      if (
        current.problemId === nextProblemId
      ) {
        return current;
      }

      return {
        ...current,
        problemId: nextProblemId,
      };
    });

    setAppliedFilters((current) => {
      if (
        current.problemId === nextProblemId
      ) {
        return current;
      }

      return {
        ...current,
        problemId: nextProblemId,
      };
    });

    setPage(1);
  }, [initialProblemId]);

  useEffect(() => {
    const controller =
      new AbortController();

    async function loadAttempts() {
      setIsLoading(true);
      setErrorMessage(null);

      try {
        const payload =
          await getTeacherAttempts(
            buildApiFilters({
              page,
              pageSize,
              filters: appliedFilters,
            }),
            controller.signal
          );

        setResponse(payload);
      } catch (error) {
        if (
          controller.signal.aborted ||
          (error instanceof DOMException &&
            error.name === "AbortError")
        ) {
          return;
        }

        setErrorMessage(
          error instanceof Error
            ? error.message
            : "Unable to load teacher attempts."
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadAttempts();

    return () => {
      controller.abort();
    };
  }, [
    appliedFilters,
    page,
    pageSize,
    refreshKey,
  ]);

  const items = response?.items ?? [];
  const pagination =
    response?.pagination;

  const activeFilterCount = useMemo(
    () =>
      Object.values(
        appliedFilters
      ).filter(
        (value) => value.trim() !== ""
      ).length,
    [appliedFilters]
  );

  const isProblemFiltered =
    appliedFilters.problemId !== "";

  const filteredProblem =
    isProblemFiltered &&
    items.length > 0
      ? items[0].problem
      : null;

  function handleSubmitFilters(
    event: FormEvent<HTMLFormElement>
  ): void {
    event.preventDefault();
    setPage(1);
    setAppliedFilters(draftFilters);
  }

  function handleClearFilters(): void {
    /*
     * Clear only the filters entered on this page.
     * Preserve the contextual problem filter that
     * was supplied by Problem Analytics.
     */
    const preservedProblemId =
      appliedFilters.problemId ||
      draftFilters.problemId;

    const clearedFilters =
      createInitialFilters(
        preservedProblemId || undefined
      );

    setDraftFilters(clearedFilters);
    setAppliedFilters(clearedFilters);
    setPage(1);
  }

  function handleRemoveProblemFilter(): void {
    setDraftFilters((current) => ({
      ...current,
      problemId: "",
    }));

    setAppliedFilters((current) => ({
      ...current,
      problemId: "",
    }));

    setPage(1);
  }

  function handleRetry(): void {
    setRefreshKey(
      (current) => current + 1
    );
  }

  function renderAttemptActions(
    item: TeacherAttemptListItem
  ) {
    return (
      <div className="teacher-attempt-actions">
        <button
          type="button"
          className="primary-button"
          onClick={() =>
            onOpenAttempt?.(
              item.attempt.id
            )
          }
          disabled={!onOpenAttempt}
          title={
            onOpenAttempt
              ? "Open full attempt review"
              : "Attempt detail navigation is unavailable"
          }
        >
          Review
        </button>

        <button
          type="button"
          className="ghost-button"
          onClick={() =>
            onOpenStudentHistory?.(
              item.student.id
            )
          }
          disabled={
            !onOpenStudentHistory
          }
          title={
            onOpenStudentHistory
              ? "Open student history"
              : "Student history navigation is unavailable"
          }
        >
          Student
        </button>

        <button
          type="button"
          className="ghost-button"
          onClick={() =>
            onOpenProblemAnalytics?.(
              item.problem.id
            )
          }
          disabled={
            !onOpenProblemAnalytics
          }
          title={
            onOpenProblemAnalytics
              ? "Open problem analytics"
              : "Problem analytics navigation is unavailable"
          }
        >
          Problem
        </button>
      </div>
    );
  }

  return (
    <main className="teacher-attempts-shell">
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
              Teacher Attempt Review
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

      <section className="teacher-attempts-intro">
        <div>
          <p className="eyebrow">
            Teacher review queue
          </p>

          <h1>
            {filteredProblem
              ? `${filteredProblem.code} · ${filteredProblem.title}`
              : "Student attempts"}
          </h1>

          <p>
            {isProblemFiltered
              ? "Showing attempts related only to the selected problem."
              : "Search, filter, and inspect pseudonymous student submissions together with their latest diagnosis state."}
          </p>

          {isProblemFiltered ? (
            <div className="teacher-problem-filter-row">
              <div className="teacher-active-filter-note">
                Problem filter active
                {filteredProblem
                  ? `: ${filteredProblem.code} · ${filteredProblem.title}`
                  : ""}
              </div>

              <button
                type="button"
                className="ghost-button teacher-remove-problem-filter"
                onClick={handleRemoveProblemFilter}
                disabled={isLoading}
              >
                Remove problem filter
              </button>
            </div>
          ) : null}
        </div>

        <div className="teacher-attempts-count">
          <span>Total records</span>

          <strong>
            {pagination?.total_items ?? 0}
          </strong>
        </div>
      </section>

      <form
        className="teacher-attempt-filters"
        onSubmit={handleSubmitFilters}
      >
        <label className="teacher-filter-field teacher-filter-search">
          <span>Search</span>

          <input
            type="search"
            value={draftFilters.search}
            placeholder="Student, problem, or misconception"
            onChange={(event) =>
              setDraftFilters(
                (current) => ({
                  ...current,
                  search:
                    event.target.value,
                })
              )
            }
          />
        </label>

        <label className="teacher-filter-field">
          <span>Diagnosis state</span>

          <select
            value={
              draftFilters.diagnosisState
            }
            onChange={(event) =>
              setDraftFilters(
                (current) => ({
                  ...current,
                  diagnosisState:
                    event.target.value,
                })
              )
            }
          >
            <option value="">
              All states
            </option>

            <option value="confident">
              Confident
            </option>

            <option value="possible">
              Possible
            </option>

            <option value="insufficient">
              Insufficient
            </option>

            <option value="no_misconception">
              No misconception
            </option>
          </select>
        </label>

        <label className="teacher-filter-field">
          <span>
            Misconception code
          </span>

          <input
            type="text"
            value={
              draftFilters.misconceptionCode
            }
            placeholder="Example: M1"
            onChange={(event) =>
              setDraftFilters(
                (current) => ({
                  ...current,
                  misconceptionCode:
                    event.target.value.toUpperCase(),
                })
              )
            }
          />
        </label>

        <label className="teacher-filter-field">
          <span>From date</span>

          <input
            type="date"
            value={
              draftFilters.createdFrom
            }
            onChange={(event) =>
              setDraftFilters(
                (current) => ({
                  ...current,
                  createdFrom:
                    event.target.value,
                })
              )
            }
          />
        </label>

        <label className="teacher-filter-field">
          <span>To date</span>

          <input
            type="date"
            value={draftFilters.createdTo}
            onChange={(event) =>
              setDraftFilters(
                (current) => ({
                  ...current,
                  createdTo:
                    event.target.value,
                })
              )
            }
          />
        </label>

        <div className="teacher-filter-actions">
          <button
            type="submit"
            className="primary-button"
            disabled={isLoading}
          >
            Apply filters
          </button>

          <button
            type="button"
            className="ghost-button"
            onClick={
              handleClearFilters
            }
            disabled={
              isLoading &&
              activeFilterCount === 0
            }
          >
            Clear
          </button>
        </div>
      </form>

      {activeFilterCount > 0 ? (
        <div className="teacher-active-filter-note">
          {activeFilterCount} active{" "}
          {activeFilterCount === 1
            ? "filter"
            : "filters"}
        </div>
      ) : null}

      {isLoading ? (
        <section className="state-card">
          Loading student attempts...
        </section>
      ) : null}

      {!isLoading &&
      errorMessage ? (
        <section className="state-card error-state-card">
          <h2>
            Unable to load attempts
          </h2>

          <p>{errorMessage}</p>

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
          No attempts match the
          selected filters.
        </section>
      ) : null}

      {!isLoading &&
      !errorMessage &&
      items.length > 0 ? (
        <>
          <section className="teacher-attempt-table-card">
            <div className="teacher-attempt-table-wrap">
              <table className="teacher-attempt-table">
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Problem</th>
                    <th>Diagnosis</th>
                    <th>Confidence</th>
                    <th>Language</th>
                    <th>
                      Response time
                    </th>
                    <th>Submitted</th>
                    <th>Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {items.map((item) => (
                    <tr
                      key={
                        item.attempt.id
                      }
                    >
                      <td>
                        <div className="teacher-table-primary">
                          <strong>
                            {
                              item.student
                                .alias
                            }
                          </strong>

                          <span>
                            {
                              item.student
                                .pseudonymous_id
                            }
                          </span>
                        </div>
                      </td>

                      <td>
                        <div className="teacher-table-primary">
                          <strong>
                            {
                              item.problem
                                .code
                            }{" "}
                            ·{" "}
                            {
                              item.problem
                                .title
                            }
                          </strong>

                          <span>
                            {
                              item.problem
                                .topic
                            }
                          </span>
                        </div>
                      </td>

                      <td>
                        <span
                          className={diagnosisClassName(
                            getDisplayedDiagnosisState(
                              item
                            )
                          )}
                        >
                          {formatDiagnosisState(
                            getDisplayedDiagnosisState(
                              item
                            )
                          )}
                        </span>
                      </td>

                      <td>
                        <strong>
                          {getDisplayedConfidence(
                            item
                          )}
                        </strong>
                      </td>

                      <td>
                        <span className="teacher-language-pill">
                          {
                            item.attempt
                              .selected_language
                          }
                        </span>
                      </td>

                      <td>
                        {formatDuration(
                          item.attempt
                            .response_time_seconds
                        )}
                      </td>

                      <td>
                        {formatDateTime(
                          item.attempt
                            .created_at
                        )}
                      </td>

                      <td>
                        {renderAttemptActions(
                          item
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
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
                  onChange={(event) => {
                    setPageSize(
                      Number(
                        event.target
                          .value
                      )
                    );

                    setPage(1);
                  }}
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
                  !pagination?.has_previous
                }
                onClick={() =>
                  setPage((current) =>
                    Math.max(
                      1,
                      current - 1
                    )
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
                  !pagination?.has_next
                }
                onClick={() =>
                  setPage(
                    (current) =>
                      current + 1
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