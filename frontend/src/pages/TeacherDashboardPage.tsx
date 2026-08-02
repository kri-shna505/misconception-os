import { useEffect, useMemo, useState } from "react";

import { API_BASE_URL } from "../api/client";
import { getTeacherDashboard } from "../services/teacherApi";
import type {
  AttemptsOverTimeItem,
  TeacherDashboardResponse,
} from "../types/teacher";


type TeacherDashboardPageProps = {
  onBack: () => void;
  onOpenAttempts: () => void;
};


function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}


function formatSeconds(value: number | null): string {
  if (value === null) {
    return "—";
  }

  if (value < 60) {
    return `${Math.round(value)}s`;
  }

  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);

  return `${minutes}m ${seconds}s`;
}


function formatDate(value: string): string {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(parsed);
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


function getMaximumTrendValue(
  items: AttemptsOverTimeItem[]
): number {
  return Math.max(
    1,
    ...items.flatMap((item) => [
      item.attempt_count,
      item.diagnosis_count,
      item.verified_count,
      item.misconception_count,
    ])
  );
}


export function TeacherDashboardPage({
  onBack,
  onOpenAttempts,
}: TeacherDashboardPageProps) {
  const [dashboard, setDashboard] =
    useState<TeacherDashboardResponse | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] =
    useState<string | null>(null);

  const [days, setDays] = useState(30);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function loadDashboard() {
      setIsLoading(true);
      setErrorMessage(null);

      try {
        const payload = await getTeacherDashboard(
          {
            days,
            top_misconceptions: 5,
          },
          controller.signal
        );

        setDashboard(payload);
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
            : "Unable to load teacher dashboard."
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadDashboard();

    return () => {
      controller.abort();
    };
  }, [days, refreshKey]);

  const maximumTrendValue = useMemo(
    () =>
      getMaximumTrendValue(
        dashboard?.attempts_over_time ?? []
      ),
    [dashboard]
  );

  const summary = dashboard?.summary;

  function handleRetry() {
    setRefreshKey((current) => current + 1);
  }

  return (
    <main className="teacher-dashboard-shell">
      <header className="teacher-dashboard-header">
        <div className="brand-lockup">
          <div className="brand-mark">M/OS</div>

          <div>
            <strong>MisconceptionOS</strong>
            <span>Teacher Review Console</span>
          </div>
        </div>

        <div className="teacher-dashboard-actions">
          <button
            type="button"
            className="primary-button"
            onClick={onOpenAttempts}
          >
            View all attempts
          </button>

          <label className="teacher-range-control">
            <span>Timeline</span>

            <select
              value={days}
              onChange={(event) =>
                setDays(Number(event.target.value))
              }
              disabled={isLoading}
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </label>

          <button
            type="button"
            className="ghost-button"
            onClick={onBack}
          >
            Back to landing
          </button>
        </div>
      </header>

      <section className="teacher-dashboard-intro">
        <div>
          <p className="eyebrow">Teacher workflow</p>
          <h1>Classroom diagnosis overview</h1>
          <p>
            Review diagnosis coverage, student activity, and the most
            frequently detected misconception patterns.
          </p>
        </div>

        <div className="teacher-intro-actions">
          <button
            type="button"
            className="primary-button"
            onClick={onOpenAttempts}
          >
            Open attempt review
          </button>

          {dashboard ? (
            <p className="teacher-generated-at">
              Updated {formatDateTime(dashboard.generated_at)}
            </p>
          ) : null}
        </div>
      </section>

      {isLoading ? (
        <section className="state-card">
          Loading teacher analytics...
        </section>
      ) : null}

      {!isLoading && errorMessage ? (
        <section className="state-card error-state-card">
          <h2>Unable to load the teacher dashboard</h2>
          <p>{errorMessage}</p>
          <p>
            Confirm that the backend is running at{" "}
            <code>{API_BASE_URL}</code>.
          </p>

          <button
            type="button"
            className="primary-button"
            onClick={handleRetry}
          >
            Retry dashboard
          </button>
        </section>
      ) : null}

      {!isLoading && !errorMessage && dashboard && summary ? (
        <>
          <section className="teacher-metric-grid">
            <article className="teacher-metric-card">
              <span>Students</span>
              <strong>{summary.total_students}</strong>
              <small>Pseudonymous learners</small>
            </article>

            <article className="teacher-metric-card">
              <span>Attempts</span>
              <strong>{summary.total_attempts}</strong>
              <small>
                {formatPercent(summary.diagnosis_coverage_rate)} diagnosed
              </small>
            </article>

            <article className="teacher-metric-card">
              <span>Verified</span>
              <strong>{summary.verified_attempts}</strong>
              <small>
                {formatPercent(summary.verified_rate)} of diagnoses
              </small>
            </article>

            <article className="teacher-metric-card">
              <span>Misconception signals</span>
              <strong>{summary.misconception_attempts}</strong>
              <small>
                {formatPercent(summary.misconception_rate)} of diagnoses
              </small>
            </article>

            <article className="teacher-metric-card">
              <span>Insufficient evidence</span>
              <strong>{summary.insufficient_attempts}</strong>
              <small>Needs clarification</small>
            </article>

            <article className="teacher-metric-card">
              <span>Average response time</span>
              <strong>
                {formatSeconds(
                  summary.average_response_time_seconds
                )}
              </strong>
              <small>Across recorded attempts</small>
            </article>
          </section>

          <section className="teacher-dashboard-grid">
            <article className="teacher-panel">
              <div className="teacher-panel-heading">
                <div>
                  <p className="eyebrow">Activity</p>
                  <h2>Attempts over time</h2>
                </div>

                <span>
                  {summary.undiagnosed_attempts} undiagnosed
                </span>
              </div>

              {dashboard.attempts_over_time.length === 0 ? (
                <div className="teacher-empty-state">
                  No attempt activity is available for this period.
                </div>
              ) : (
                <div className="teacher-trend-list">
                  {dashboard.attempts_over_time.map((item) => (
                    <div
                      className="teacher-trend-row"
                      key={item.date}
                    >
                      <span className="teacher-trend-date">
                        {formatDate(item.date)}
                      </span>

                      <div className="teacher-trend-bars">
                        <div
                          className="teacher-trend-bar attempts"
                          style={{
                            width: `${
                              (item.attempt_count /
                                maximumTrendValue) *
                              100
                            }%`,
                          }}
                          title={`${item.attempt_count} attempts`}
                        />

                        <div
                          className="teacher-trend-bar diagnoses"
                          style={{
                            width: `${
                              (item.diagnosis_count /
                                maximumTrendValue) *
                              100
                            }%`,
                          }}
                          title={`${item.diagnosis_count} diagnoses`}
                        />
                      </div>

                      <span className="teacher-trend-total">
                        {item.attempt_count}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              <div className="teacher-chart-legend">
                <span>
                  <i className="legend-swatch attempts" />
                  Attempts
                </span>

                <span>
                  <i className="legend-swatch diagnoses" />
                  Diagnoses
                </span>
              </div>
            </article>

            <article className="teacher-panel">
              <div className="teacher-panel-heading">
                <div>
                  <p className="eyebrow">Priority review</p>
                  <h2>Top misconception patterns</h2>
                </div>
              </div>

              {dashboard.misconception_analytics.length === 0 ? (
                <div className="teacher-empty-state">
                  No supported misconceptions were detected.
                </div>
              ) : (
                <div className="teacher-misconception-list">
                  {dashboard.misconception_analytics.map(
                    (item) => (
                      <article
                        className="teacher-misconception-item"
                        key={item.misconception_id}
                      >
                        <div className="teacher-misconception-code">
                          {item.code}
                        </div>

                        <div className="teacher-misconception-copy">
                          <strong>{item.name}</strong>
                          <span>
                            {item.topic ?? "Uncategorized"} ·{" "}
                            {item.affected_student_count} students ·{" "}
                            {item.affected_problem_count} problems
                          </span>
                        </div>

                        <div className="teacher-misconception-metric">
                          <strong>{item.detection_count}</strong>
                          <span>detections</span>
                        </div>
                      </article>
                    )
                  )}
                </div>
              )}
            </article>
          </section>

          <section className="teacher-dashboard-footer-grid">
            <article className="teacher-summary-card">
              <p className="eyebrow">Diagnosis coverage</p>
              <strong>
                {formatPercent(summary.diagnosis_coverage_rate)}
              </strong>
              <span>
                {summary.total_diagnoses} diagnoses from{" "}
                {summary.total_attempts} attempts
              </span>
            </article>

            <article className="teacher-summary-card">
              <p className="eyebrow">Verified outcomes</p>
              <strong>{summary.verified_attempts}</strong>
              <span>
                Attempts with no supported misconception detected
              </span>
            </article>

            <article className="teacher-summary-card">
              <p className="eyebrow">Review queue</p>
              <strong>
                {summary.insufficient_attempts +
                  summary.undiagnosed_attempts}
              </strong>
              <span>
                Insufficient or currently undiagnosed attempts
              </span>
            </article>
          </section>
        </>
      ) : null}
    </main>
  );
}