import { useEffect, useMemo, useState } from "react";

import { getProblemAnalytics } from "../services/teacherApi";
import type {
  DiagnosisStateAnalyticsItem,
  ProblemAnalyticsResponse,
} from "../types/teacher";


type TeacherProblemAnalyticsPageProps = {
  problemId: string;
  onBack: () => void;
  onOpenAttempts?: (problemId: string) => void;
};


function formatPercent(value: number): string {
  return `${Math.round(value)}%`;
}


function formatDuration(value: number | null): string {
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


function formatDiagnosisState(value: string): string {
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
  state: DiagnosisStateAnalyticsItem["state"]
): string {
  switch (state) {
    case "confident":
      return "teacher-status-pill teacher-status-confident";

    case "possible":
      return "teacher-status-pill teacher-status-possible";

    case "insufficient":
      return "teacher-status-pill teacher-status-insufficient";

    case "no_misconception":
      return "teacher-status-pill teacher-status-verified";

    default:
      return "teacher-status-pill teacher-status-undiagnosed";
  }
}


function diagnosisBarClassName(
  state: DiagnosisStateAnalyticsItem["state"]
): string {
  switch (state) {
    case "confident":
      return "teacher-problem-state-bar-fill teacher-problem-state-confident";

    case "possible":
      return "teacher-problem-state-bar-fill teacher-problem-state-possible";

    case "insufficient":
      return "teacher-problem-state-bar-fill teacher-problem-state-insufficient";

    case "no_misconception":
      return "teacher-problem-state-bar-fill teacher-problem-state-verified";

    default:
      return "teacher-problem-state-bar-fill";
  }
}


export function TeacherProblemAnalyticsPage({
  problemId,
  onBack,
  onOpenAttempts,
}: TeacherProblemAnalyticsPageProps) {
  const [analytics, setAnalytics] =
    useState<ProblemAnalyticsResponse | null>(
      null
    );

  const [isLoading, setIsLoading] =
    useState(true);

  const [errorMessage, setErrorMessage] =
    useState<string | null>(null);

  const [refreshKey, setRefreshKey] =
    useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function loadProblemAnalytics() {
      setIsLoading(true);
      setErrorMessage(null);

      try {
        const payload =
          await getProblemAnalytics(
            problemId,
            controller.signal
          );

        setAnalytics(payload);
      } catch (error) {
        if (
          controller.signal.aborted ||
          (
            error instanceof DOMException &&
            error.name === "AbortError"
          )
        ) {
          return;
        }

        setErrorMessage(
          error instanceof Error
            ? error.message
            : "Unable to load problem analytics."
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadProblemAnalytics();

    return () => {
      controller.abort();
    };
  }, [problemId, refreshKey]);

  const diagnosisCoverageRate = useMemo(() => {
    if (
      !analytics ||
      analytics.total_attempts === 0
    ) {
      return 0;
    }

    return (
      analytics.diagnosed_attempts /
      analytics.total_attempts
    ) * 100;
  }, [analytics]);

  const verifiedRate = useMemo(() => {
    if (
      !analytics ||
      analytics.diagnosed_attempts === 0
    ) {
      return 0;
    }

    return (
      analytics.verified_attempts /
      analytics.diagnosed_attempts
    ) * 100;
  }, [analytics]);

  const misconceptionRate = useMemo(() => {
    if (
      !analytics ||
      analytics.diagnosed_attempts === 0
    ) {
      return 0;
    }

    return (
      analytics.misconception_attempts /
      analytics.diagnosed_attempts
    ) * 100;
  }, [analytics]);

  const insufficientRate = useMemo(() => {
    if (
      !analytics ||
      analytics.diagnosed_attempts === 0
    ) {
      return 0;
    }

    return (
      analytics.insufficient_attempts /
      analytics.diagnosed_attempts
    ) * 100;
  }, [analytics]);

  const sortedDiagnosisStates = useMemo(
    () =>
      [...(analytics?.diagnosis_states ?? [])].sort(
        (left, right) =>
          right.count - left.count
      ),
    [analytics]
  );

  function handleRetry(): void {
    setRefreshKey(
      (current) => current + 1
    );
  }

  return (
    <main className="teacher-problem-analytics-shell">
      <header className="teacher-dashboard-header">
        <div className="brand-lockup">
          <div className="brand-mark">M/OS</div>

          <div>
            <strong>MisconceptionOS</strong>
            <span>Teacher Problem Analytics</span>
          </div>
        </div>

        <button
          type="button"
          className="ghost-button"
          onClick={onBack}
        >
          Back
        </button>
      </header>

      {isLoading ? (
        <section className="state-card">
          Loading problem analytics...
        </section>
      ) : null}

      {!isLoading && errorMessage ? (
        <section className="state-card error-state-card">
          <h2>Unable to load problem analytics</h2>
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
      analytics ? (
        <>
          <section className="teacher-problem-analytics-intro">
            <div>
              <p className="eyebrow">
                Problem performance review
              </p>

              <h1>{analytics.problem.title}</h1>

              <p>
                {analytics.problem.code} ·{" "}
                {analytics.problem.topic}
              </p>
            </div>

            <div className="teacher-problem-analytics-actions">
              <button
                type="button"
                className="primary-button"
                onClick={() =>
                  onOpenAttempts?.(
                    analytics.problem.id
                  )
                }
                disabled={!onOpenAttempts}
              >
                View related attempts
              </button>
            </div>
          </section>

          <section className="teacher-problem-analytics-summary-grid">
            <article className="teacher-summary-card">
              <p className="eyebrow">
                Total attempts
              </p>
              <strong>
                {analytics.total_attempts}
              </strong>
              <span>Recorded submissions</span>
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
                {analytics.diagnosed_attempts} diagnosed
              </span>
            </article>

            <article className="teacher-summary-card">
              <p className="eyebrow">
                Verified outcomes
              </p>
              <strong>
                {analytics.verified_attempts}
              </strong>
              <span>
                {formatPercent(verifiedRate)} of diagnoses
              </span>
            </article>

            <article className="teacher-summary-card">
              <p className="eyebrow">
                Misconception signals
              </p>
              <strong>
                {analytics.misconception_attempts}
              </strong>
              <span>
                {formatPercent(
                  misconceptionRate
                )}{" "}
                of diagnoses
              </span>
            </article>

            <article className="teacher-summary-card">
              <p className="eyebrow">
                Insufficient evidence
              </p>
              <strong>
                {analytics.insufficient_attempts}
              </strong>
              <span>
                {formatPercent(
                  insufficientRate
                )}{" "}
                of diagnoses
              </span>
            </article>

            <article className="teacher-summary-card">
              <p className="eyebrow">
                Average response time
              </p>
              <strong>
                {formatDuration(
                  analytics.average_response_time_seconds
                )}
              </strong>
              <span>Across recorded attempts</span>
            </article>
          </section>

          <section className="teacher-problem-analytics-grid">
            <article className="teacher-panel">
              <div className="teacher-panel-heading">
                <div>
                  <p className="eyebrow">
                    Diagnosis distribution
                  </p>
                  <h2>Outcome states</h2>
                </div>

                <span>
                  {analytics.diagnosed_attempts} diagnoses
                </span>
              </div>

              {sortedDiagnosisStates.length === 0 ? (
                <div className="teacher-empty-state">
                  No diagnosis-state analytics are available.
                </div>
              ) : (
                <div className="teacher-problem-state-list">
                  {sortedDiagnosisStates.map(
                    (item) => (
                      <article
                        className="teacher-problem-state-item"
                        key={item.state}
                      >
                        <div className="teacher-problem-state-heading">
                          <span
                            className={diagnosisClassName(
                              item.state
                            )}
                          >
                            {formatDiagnosisState(
                              item.state
                            )}
                          </span>

                          <strong>
                            {item.count}
                          </strong>
                        </div>

                        <div className="teacher-problem-state-bar">
                          <span
                            className={diagnosisBarClassName(
                              item.state
                            )}
                            style={{
                              width: `${Math.max(
                                0,
                                Math.min(
                                  100,
                                  item.percentage
                                )
                              )}%`,
                            }}
                          />
                        </div>

                        <small>
                          {formatPercent(
                            item.percentage
                          )}{" "}
                          of diagnosed attempts
                        </small>
                      </article>
                    )
                  )}
                </div>
              )}
            </article>

            <article className="teacher-panel">
              <div className="teacher-panel-heading">
                <div>
                  <p className="eyebrow">
                    Review interpretation
                  </p>
                  <h2>Teacher signals</h2>
                </div>
              </div>

              <div className="teacher-problem-signal-list">
                <article className="teacher-problem-signal-card">
                  <span>Coverage</span>
                  <strong>
                    {formatPercent(
                      diagnosisCoverageRate
                    )}
                  </strong>
                  <p>
                    Percentage of submitted attempts with a saved diagnosis.
                  </p>
                </article>

                <article className="teacher-problem-signal-card">
                  <span>Misconception rate</span>
                  <strong>
                    {formatPercent(
                      misconceptionRate
                    )}
                  </strong>
                  <p>
                    Share of diagnosed attempts that contain a supported misconception.
                  </p>
                </article>

                <article className="teacher-problem-signal-card">
                  <span>Clarification load</span>
                  <strong>
                    {analytics.insufficient_attempts}
                  </strong>
                  <p>
                    Attempts that require more evidence, clarification, or a diagnostic question.
                  </p>
                </article>
              </div>
            </article>
          </section>

          <section className="teacher-panel">
            <div className="teacher-panel-heading">
              <div>
                <p className="eyebrow">
                  Problem context
                </p>
                <h2>{analytics.problem.title}</h2>
              </div>

              <span>
                {analytics.problem.difficulty ??
                  "Unspecified difficulty"}
              </span>
            </div>

            <div className="teacher-detail-text-block">
              {analytics.problem.statement}
            </div>

            <div className="teacher-problem-meta-grid">
              <div>
                <span>Problem code</span>
                <strong>
                  {analytics.problem.code}
                </strong>
              </div>

              <div>
                <span>Topic</span>
                <strong>
                  {analytics.problem.topic}
                </strong>
              </div>

              <div>
                <span>Expected language</span>
                <strong>
                  {analytics.problem.expected_language ??
                    "Not specified"}
                </strong>
              </div>

              <div>
                <span>Status</span>
                <strong>
                  {analytics.problem.active
                    ? "Active"
                    : "Inactive"}
                </strong>
              </div>
            </div>
          </section>
        </>
      ) : null}
    </main>
  );
}