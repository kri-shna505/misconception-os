import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getStudentHistory,
} from "../services/teacherApi";

import type {
  StudentHistoryItem,
  StudentHistoryResponse,
} from "../types/teacher";


type TeacherStudentHistoryPageProps = {
  studentAliasId: string;
  onBack: () => void;
  onOpenAttempt?: (
    attemptId: string
  ) => void;
  onOpenProblemAnalytics?: (
    problemId: string
  ) => void;
};


type EvolutionState =
  | "newly_detected"
  | "repeated"
  | "improving"
  | "corrected"
  | "replaced"
  | "uncertain";


type InterventionHistoryShape = {
  parent_attempt_id?: string | null;
  retry_number?: number | null;
  hint_levels_used?: number[];
  diagnostic_question_answered?: boolean;
  evolution_state?: EvolutionState | null;
};


const DEFAULT_PAGE_SIZE = 20;


function formatDateTime(
  value: string
): string {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(
    "en",
    {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }
  ).format(parsed);
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

  const minutes = Math.floor(
    value / 60
  );

  const seconds = Math.round(
    value % 60
  );

  return `${minutes}m ${seconds}s`;
}


function formatPercent(
  value: number
): string {
  return `${Math.round(
    value * 100
  )}%`;
}


function formatDiagnosisState(
  value: string | undefined
): string {
  if (!value) {
    return "Undiagnosed";
  }

  return value
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase() +
        part.slice(1)
    )
    .join(" ");
}


function formatEvolutionState(
  value: EvolutionState | null
): string {
  if (!value) {
    return "Not recorded";
  }

  return value
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


function evolutionClassName(
  state: EvolutionState | null
): string {
  switch (state) {
    case "corrected":
      return (
        "teacher-status-pill " +
        "teacher-status-verified"
      );

    case "improving":
      return (
        "teacher-status-pill " +
        "teacher-status-possible"
      );

    case "repeated":
      return (
        "teacher-status-pill " +
        "teacher-status-confident"
      );

    case "newly_detected":
      return (
        "teacher-status-pill " +
        "teacher-status-possible"
      );

    case "replaced":
      return (
        "teacher-status-pill " +
        "teacher-status-insufficient"
      );

    case "uncertain":
      return (
        "teacher-status-pill " +
        "teacher-status-insufficient"
      );

    default:
      return (
        "teacher-status-pill " +
        "teacher-status-undiagnosed"
      );
  }
}


function buildHistoryLabel(
  item: StudentHistoryItem
): string {
  const diagnosis = item.diagnosis;

  if (!diagnosis) {
    return "No diagnosis";
  }

  return `${formatDiagnosisState(
    diagnosis.state
  )} · ${formatPercent(
    diagnosis.confidence
  )}`;
}


function readInterventionHistory(
  item: StudentHistoryItem
): InterventionHistoryShape {
  const source =
    item as StudentHistoryItem &
      Partial<InterventionHistoryShape>;

  const attemptSource =
    item.attempt as typeof item.attempt &
      Partial<InterventionHistoryShape>;

  return {
    parent_attempt_id:
      source.parent_attempt_id ??
      attemptSource.parent_attempt_id ??
      null,

    retry_number:
      source.retry_number ??
      attemptSource.retry_number ??
      0,

    hint_levels_used:
      source.hint_levels_used ?? [],

    diagnostic_question_answered:
      source.diagnostic_question_answered ??
      false,

    evolution_state:
      source.evolution_state ?? null,
  };
}


function buildHintLabel(
  levels: number[]
): string {
  if (levels.length === 0) {
    return "No hints used";
  }

  return `L${levels.join(" · L")}`;
}


function getRetryLabel(
  retryNumber: number
): string {
  if (retryNumber <= 0) {
    return "Original attempt";
  }

  return `Retry ${retryNumber}`;
}


export function TeacherStudentHistoryPage({
  studentAliasId,
  onBack,
  onOpenAttempt,
  onOpenProblemAnalytics,
}: TeacherStudentHistoryPageProps) {
  const [
    response,
    setResponse,
  ] = useState<
    StudentHistoryResponse | null
  >(null);

  const [
    page,
    setPage,
  ] = useState(1);

  const [
    pageSize,
    setPageSize,
  ] = useState(
    DEFAULT_PAGE_SIZE
  );

  const [
    isLoading,
    setIsLoading,
  ] = useState(true);

  const [
    errorMessage,
    setErrorMessage,
  ] = useState<
    string | null
  >(null);

  const [
    refreshKey,
    setRefreshKey,
  ] = useState(0);

  useEffect(() => {
    const controller =
      new AbortController();

    async function loadHistory() {
      setIsLoading(true);
      setErrorMessage(null);

      try {
        const payload =
          await getStudentHistory(
            studentAliasId,
            {
              page,
              page_size: pageSize,
            },
            controller.signal
          );

        setResponse(payload);
      } catch (error) {
        if (
          controller.signal.aborted ||
          (
            error instanceof DOMException &&
            error.name ===
              "AbortError"
          )
        ) {
          return;
        }

        setErrorMessage(
          error instanceof Error
            ? error.message
            : (
                "Unable to load " +
                "student history."
              )
        );
      } finally {
        if (
          !controller.signal.aborted
        ) {
          setIsLoading(false);
        }
      }
    }

    void loadHistory();

    return () => {
      controller.abort();
    };
  }, [
    studentAliasId,
    page,
    pageSize,
    refreshKey,
  ]);

  const items =
    response?.items ?? [];

  const pagination =
    response?.pagination;

  const summary =
    response?.summary;

  const diagnosisCoverageRate =
    useMemo(() => {
      if (
        !summary ||
        summary.total_attempts === 0
      ) {
        return 0;
      }

      return (
        summary.diagnosed_attempts /
        summary.total_attempts
      );
    }, [summary]);

  const misconceptionRate =
    useMemo(() => {
      if (
        !summary ||
        summary.diagnosed_attempts ===
          0
      ) {
        return 0;
      }

      return (
        summary.misconception_attempts /
        summary.diagnosed_attempts
      );
    }, [summary]);

  const learningProgress =
    useMemo(() => {
      let retries = 0;
      let corrected = 0;
      let improving = 0;
      let repeated = 0;
      let hintsUsed = 0;
      let questionsAnswered = 0;

      for (const item of items) {
        const intervention =
          readInterventionHistory(
            item
          );

        const retryNumber =
          Number(
            intervention.retry_number ??
              0
          );

        if (retryNumber > 0) {
          retries += 1;
        }

        hintsUsed +=
          intervention
            .hint_levels_used
            ?.length ?? 0;

        if (
          intervention
            .diagnostic_question_answered
        ) {
          questionsAnswered += 1;
        }

        switch (
          intervention.evolution_state
        ) {
          case "corrected":
            corrected += 1;
            break;

          case "improving":
            improving += 1;
            break;

          case "repeated":
            repeated += 1;
            break;

          default:
            break;
        }
      }

      return {
        retries,
        corrected,
        improving,
        repeated,
        hintsUsed,
        questionsAnswered,
      };
    }, [items]);

  function handleRetry() {
    setRefreshKey(
      (current) =>
        current + 1
    );
  }

  return (
    <main className="teacher-student-history-shell">
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
              Teacher Student History
            </span>
          </div>
        </div>

        <button
          type="button"
          className="ghost-button"
          onClick={onBack}
        >
          Back to attempt
        </button>
      </header>

      {isLoading ? (
        <section className="state-card">
          Loading student history...
        </section>
      ) : null}

      {!isLoading &&
      errorMessage ? (
        <section className="state-card error-state-card">
          <h2>
            Unable to load student history
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
      response &&
      summary ? (
        <>
          <section className="teacher-student-history-intro">
            <div>
              <p className="eyebrow">
                Pseudonymous student
                record
              </p>

              <h1>
                {response.student.alias}
              </h1>

              <p>
                {
                  response.student
                    .pseudonymous_id
                }
              </p>
            </div>

            <div className="teacher-history-consent-card">
              <span>
                Consent status
              </span>

              <strong>
                {
                  response.student
                    .consent_status
                    ? "Granted"
                    : "Not granted"
                }
              </strong>

              <small>
                Created{" "}
                {formatDateTime(
                  response.student
                    .created_at
                )}
              </small>
            </div>
          </section>

          <section className="teacher-student-history-summary-grid">
            <article className="teacher-summary-card">
              <p className="eyebrow">
                Total attempts
              </p>

              <strong>
                {summary.total_attempts}
              </strong>

              <span>
                Recorded submissions
              </span>
            </article>

            <article className="teacher-summary-card">
              <p className="eyebrow">
                Diagnosis coverage
              </p>

              <strong>
                {formatPercent(
                  diagnosisCoverageRate
                )}
              </strong>

              <span>
                {
                  summary.diagnosed_attempts
                }{" "}
                diagnosed
              </span>
            </article>

            <article className="teacher-summary-card">
              <p className="eyebrow">
                Verified outcomes
              </p>

              <strong>
                {
                  summary.verified_attempts
                }
              </strong>

              <span>
                No supported
                misconception
              </span>
            </article>

            <article className="teacher-summary-card">
              <p className="eyebrow">
                Misconception rate
              </p>

              <strong>
                {formatPercent(
                  misconceptionRate
                )}
              </strong>

              <span>
                {
                  summary
                    .misconception_attempts
                }{" "}
                misconception attempts
              </span>
            </article>

            <article className="teacher-summary-card">
              <p className="eyebrow">
                Insufficient evidence
              </p>

              <strong>
                {
                  summary
                    .insufficient_attempts
                }
              </strong>

              <span>
                Needs clarification
              </span>
            </article>

            <article className="teacher-summary-card">
              <p className="eyebrow">
                Average response time
              </p>

              <strong>
                {formatDuration(
                  summary
                    .average_response_time_seconds
                )}
              </strong>

              <span>
                Across recorded attempts
              </span>
            </article>
          </section>

          <section className="teacher-panel teacher-history-panel">
            <div className="teacher-panel-heading">
              <div>
                <p className="eyebrow">
                  Learning progress
                </p>

                <h2>
                  Intervention and
                  evolution summary
                </h2>
              </div>

              <span>
                Sprint 9 learning loop
              </span>
            </div>

            <div className="teacher-student-history-summary-grid">
              <article className="teacher-summary-card">
                <p className="eyebrow">
                  Linked retries
                </p>

                <strong>
                  {
                    learningProgress
                      .retries
                  }
                </strong>

                <span>
                  Follow-up attempts
                </span>
              </article>

              <article className="teacher-summary-card">
                <p className="eyebrow">
                  Corrected
                </p>

                <strong>
                  {
                    learningProgress
                      .corrected
                  }
                </strong>

                <span>
                  Misconceptions resolved
                </span>
              </article>

              <article className="teacher-summary-card">
                <p className="eyebrow">
                  Improving
                </p>

                <strong>
                  {
                    learningProgress
                      .improving
                  }
                </strong>

                <span>
                  Weaker misconception
                  evidence
                </span>
              </article>

              <article className="teacher-summary-card">
                <p className="eyebrow">
                  Repeated
                </p>

                <strong>
                  {
                    learningProgress
                      .repeated
                  }
                </strong>

                <span>
                  Same misconception
                  persists
                </span>
              </article>

              <article className="teacher-summary-card">
                <p className="eyebrow">
                  Hints revealed
                </p>

                <strong>
                  {
                    learningProgress
                      .hintsUsed
                  }
                </strong>

                <span>
                  Approved hint levels
                  used
                </span>
              </article>

              <article className="teacher-summary-card">
                <p className="eyebrow">
                  Questions answered
                </p>

                <strong>
                  {
                    learningProgress
                      .questionsAnswered
                  }
                </strong>

                <span>
                  Diagnostic follow-ups
                </span>
              </article>
            </div>
          </section>

          <section className="teacher-panel teacher-history-panel">
            <div className="teacher-panel-heading">
              <div>
                <p className="eyebrow">
                  Attempt timeline
                </p>

                <h2>
                  Student learning history
                </h2>
              </div>

              <span>
                {
                  pagination?.total_items ??
                  0
                }{" "}
                records
              </span>
            </div>

            {items.length === 0 ? (
              <div className="teacher-empty-state">
                No attempts are available
                for this student.
              </div>
            ) : (
              <div className="teacher-history-list">
                {items.map(
                  (
                    item,
                    index
                  ) => {
                    const intervention =
                      readInterventionHistory(
                        item
                      );

                    const retryNumber =
                      Number(
                        intervention
                          .retry_number ??
                          0
                      );

                    const hintLevels =
                      intervention
                        .hint_levels_used ??
                      [];

                    return (
                      <article
                        className="teacher-history-item"
                        key={
                          item.attempt.id
                        }
                      >
                        <div className="teacher-history-index">
                          {String(
                            (
                              (page - 1) *
                                pageSize
                            ) +
                              index +
                              1
                          ).padStart(
                            2,
                            "0"
                          )}
                        </div>

                        <div className="teacher-history-main">
                          <div className="teacher-history-heading">
                            <div>
                              <strong>
                                {
                                  item
                                    .problem
                                    .code
                                }{" "}
                                ·{" "}
                                {
                                  item
                                    .problem
                                    .title
                                }
                              </strong>

                              <span>
                                {
                                  item
                                    .problem
                                    .topic
                                }{" "}
                                ·{" "}
                                {formatDateTime(
                                  item
                                    .attempt
                                    .created_at
                                )}
                              </span>
                            </div>

                            <div
                              style={{
                                display:
                                  "flex",
                                gap:
                                  "0.5rem",
                                flexWrap:
                                  "wrap",
                                justifyContent:
                                  "flex-end",
                              }}
                            >
                              <span
                                className={
                                  diagnosisClassName(
                                    item
                                      .diagnosis
                                      ?.state
                                  )
                                }
                              >
                                {formatDiagnosisState(
                                  item
                                    .diagnosis
                                    ?.state
                                )}
                              </span>

                              <span
                                className={
                                  evolutionClassName(
                                    intervention
                                      .evolution_state ??
                                      null
                                  )
                                }
                              >
                                {formatEvolutionState(
                                  intervention
                                    .evolution_state ??
                                    null
                                )}
                              </span>
                            </div>
                          </div>

                          <div className="teacher-history-metadata">
                            <div>
                              <span>
                                Diagnosis
                              </span>

                              <strong>
                                {buildHistoryLabel(
                                  item
                                )}
                              </strong>
                            </div>

                            <div>
                              <span>
                                Retry
                              </span>

                              <strong>
                                {getRetryLabel(
                                  retryNumber
                                )}
                              </strong>
                            </div>

                            <div>
                              <span>
                                Hint usage
                              </span>

                              <strong>
                                {buildHintLabel(
                                  hintLevels
                                )}
                              </strong>
                            </div>

                            <div>
                              <span>
                                Diagnostic
                                question
                              </span>

                              <strong>
                                {
                                  intervention
                                    .diagnostic_question_answered
                                    ? "Answered"
                                    : "Not used"
                                }
                              </strong>
                            </div>

                            <div>
                              <span>
                                Language
                              </span>

                              <strong>
                                {
                                  item
                                    .attempt
                                    .selected_language
                                }
                              </strong>
                            </div>

                            <div>
                              <span>
                                Response time
                              </span>

                              <strong>
                                {formatDuration(
                                  item
                                    .attempt
                                    .response_time_seconds
                                )}
                              </strong>
                            </div>
                          </div>

                          {intervention
                            .parent_attempt_id ? (
                            <div
                              className="teacher-history-linkage"
                              style={{
                                marginTop:
                                  "0.75rem",
                              }}
                            >
                              <span>
                                Linked to
                                previous attempt
                              </span>

                              <strong>
                                {
                                  intervention
                                    .parent_attempt_id
                                }
                              </strong>
                            </div>
                          ) : null}
                        </div>

                        <div className="teacher-history-actions">
                          <button
                            type="button"
                            className="primary-button"
                            onClick={() =>
                              onOpenAttempt?.(
                                item
                                  .attempt
                                  .id
                              )
                            }
                            disabled={
                              !onOpenAttempt
                            }
                          >
                            Review attempt
                          </button>

                          <button
                            type="button"
                            className="ghost-button"
                            onClick={() =>
                              onOpenProblemAnalytics?.(
                                item
                                  .problem
                                  .id
                              )
                            }
                            disabled={
                              !onOpenProblemAnalytics
                            }
                          >
                            Problem analytics
                          </button>
                        </div>
                      </article>
                    );
                  }
                )}
              </div>
            )}
          </section>

          <section className="teacher-pagination">
            <div>
              <span>
                Page{" "}
                {
                  pagination?.page ??
                  page
                }{" "}
                of{" "}
                {
                  pagination
                    ?.total_pages ??
                  1
                }
              </span>

              <label>
                Rows

                <select
                  value={pageSize}
                  onChange={(
                    event
                  ) => {
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
                  !pagination
                    ?.has_previous
                }
                onClick={() =>
                  setPage(
                    (current) =>
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
                  !pagination
                    ?.has_next
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