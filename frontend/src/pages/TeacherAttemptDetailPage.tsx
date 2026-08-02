import { useEffect, useMemo, useState } from "react";

import { getTeacherAttemptDetail } from "../services/teacherApi";
import type {
  TeacherAttemptDetailResponse,
} from "../types/teacher";


type TeacherAttemptDetailPageProps = {
  attemptId: string;
  onBack: () => void;
  onOpenStudentHistory?: (studentAliasId: string) => void;
  onOpenProblemAnalytics?: (problemId: string) => void;
};


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


function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
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


function diagnosisClassName(state: string): string {
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


function formatEvidenceSource(value: string): string {
  return value
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase() +
        part.slice(1)
    )
    .join(" ");
}


function formatMetadataValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  if (
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }

  try {
    return JSON.stringify(value);
  } catch {
    return "Unsupported value";
  }
}


export function TeacherAttemptDetailPage({
  attemptId,
  onBack,
  onOpenStudentHistory,
  onOpenProblemAnalytics,
}: TeacherAttemptDetailPageProps) {
  const [record, setRecord] =
    useState<TeacherAttemptDetailResponse | null>(
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

    async function loadAttemptDetail() {
      setIsLoading(true);
      setErrorMessage(null);

      try {
        const payload =
          await getTeacherAttemptDetail(
            attemptId,
            controller.signal
          );

        setRecord(payload);
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
            : "Unable to load attempt details."
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadAttemptDetail();

    return () => {
      controller.abort();
    };
  }, [attemptId, refreshKey]);

  const sortedEvidence = useMemo(
    () =>
      [...(record?.diagnosis?.evidence ?? [])].sort(
        (left, right) =>
          left.sort_order - right.sort_order
      ),
    [record]
  );

  function handleRetry() {
    setRefreshKey((current) => current + 1);
  }

  return (
    <main className="teacher-attempt-detail-shell">
      <header className="teacher-dashboard-header">
        <div className="brand-lockup">
          <div className="brand-mark">M/OS</div>

          <div>
            <strong>MisconceptionOS</strong>
            <span>Teacher Attempt Review</span>
          </div>
        </div>

        <button
          type="button"
          className="ghost-button"
          onClick={onBack}
        >
          Back to attempts
        </button>
      </header>

      {isLoading ? (
        <section className="state-card">
          Loading attempt review...
        </section>
      ) : null}

      {!isLoading && errorMessage ? (
        <section className="state-card error-state-card">
          <h2>Unable to load this attempt</h2>
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

      {!isLoading && !errorMessage && record ? (
        <>
          <section className="teacher-attempt-detail-intro">
            <div>
              <p className="eyebrow">
                Complete attempt review
              </p>

              <h1>{record.problem.title}</h1>

              <p>
                {record.problem.code} ·{" "}
                {record.problem.topic}
              </p>
            </div>

            <div className="teacher-attempt-detail-actions">
              <button
                type="button"
                className="ghost-button"
                onClick={() =>
                  onOpenStudentHistory?.(
                    record.student.id
                  )
                }
                disabled={!onOpenStudentHistory}
              >
                Student history
              </button>

              <button
                type="button"
                className="ghost-button"
                onClick={() =>
                  onOpenProblemAnalytics?.(
                    record.problem.id
                  )
                }
                disabled={!onOpenProblemAnalytics}
              >
                Problem analytics
              </button>
            </div>
          </section>

          <section className="teacher-attempt-detail-summary-grid">
            <article className="teacher-summary-card">
              <p className="eyebrow">Student</p>
              <strong>{record.student.alias}</strong>
              <span>
                {record.student.pseudonymous_id}
              </span>
            </article>

            <article className="teacher-summary-card">
              <p className="eyebrow">Submitted</p>
              <strong className="teacher-detail-small-value">
                {formatDateTime(
                  record.attempt.created_at
                )}
              </strong>
              <span>
                {record.attempt.selected_language}
              </span>
            </article>

            <article className="teacher-summary-card">
              <p className="eyebrow">Response time</p>
              <strong>
                {formatDuration(
                  record.attempt
                    .response_time_seconds
                )}
              </strong>
              <span>Recorded attempt duration</span>
            </article>

            <article className="teacher-summary-card">
              <p className="eyebrow">Diagnosis</p>

              {record.diagnosis ? (
                <>
                  <span
                    className={diagnosisClassName(
                      record.diagnosis.state
                    )}
                  >
                    {formatDiagnosisState(
                      record.diagnosis.state
                    )}
                  </span>

                  <strong>
                    {formatPercent(
                      record.diagnosis.confidence
                    )}
                  </strong>
                </>
              ) : (
                <>
                  <span className="teacher-status-pill teacher-status-undiagnosed">
                    Undiagnosed
                  </span>
                  <strong>—</strong>
                </>
              )}
            </article>
          </section>

          <section className="teacher-attempt-detail-grid">
            <article className="teacher-panel">
              <div className="teacher-panel-heading">
                <div>
                  <p className="eyebrow">
                    Student submission
                  </p>
                  <h2>Attempt content</h2>
                </div>
              </div>

              <div className="teacher-detail-section">
                <h3>Final answer</h3>
                <div className="teacher-detail-text-block">
                  {record.attempt.final_answer ??
                    "No final answer was provided."}
                </div>
              </div>

              <div className="teacher-detail-section">
                <h3>Written reasoning</h3>
                <div className="teacher-detail-text-block">
                  {record.attempt.written_reasoning}
                </div>
              </div>

              <div className="teacher-detail-section">
                <h3>Source code</h3>

                {record.attempt.source_code ? (
                  <pre className="teacher-code-block">
                    <code>
                      {record.attempt.source_code}
                    </code>
                  </pre>
                ) : (
                  <div className="teacher-detail-empty">
                    No source code was submitted.
                  </div>
                )}
              </div>

              <div className="teacher-detail-section">
                <h3>Speech transcript</h3>
                <div className="teacher-detail-text-block">
                  {record.attempt.speech_transcript ??
                    "No speech transcript was submitted."}
                </div>
              </div>
            </article>

            <article className="teacher-panel">
              <div className="teacher-panel-heading">
                <div>
                  <p className="eyebrow">
                    Diagnostic result
                  </p>
                  <h2>Evidence-backed diagnosis</h2>
                </div>
              </div>

              {!record.diagnosis ? (
                <div className="teacher-empty-state">
                  This attempt has not been diagnosed yet.
                </div>
              ) : (
                <>
                  <div className="teacher-diagnosis-overview">
                    <div>
                      <span
                        className={diagnosisClassName(
                          record.diagnosis.state
                        )}
                      >
                        {formatDiagnosisState(
                          record.diagnosis.state
                        )}
                      </span>

                      <strong>
                        {formatPercent(
                          record.diagnosis.confidence
                        )}
                      </strong>
                    </div>

                    <dl>
                      <div>
                        <dt>Model version</dt>
                        <dd>
                          {record.diagnosis.model_version}
                        </dd>
                      </div>

                      <div>
                        <dt>Next action</dt>
                        <dd>
                          {formatDiagnosisState(
                            record.diagnosis.next_action
                          )}
                        </dd>
                      </div>

                      <div>
                        <dt>Created</dt>
                        <dd>
                          {formatDateTime(
                            record.diagnosis.created_at
                          )}
                        </dd>
                      </div>
                    </dl>
                  </div>

                  <div className="teacher-detail-section">
                    <h3>Primary misconception</h3>

                    {record.diagnosis
                      .primary_misconception ? (
                      <article className="teacher-primary-misconception">
                        <span>
                          {
                            record.diagnosis
                              .primary_misconception.code
                          }
                        </span>

                        <div>
                          <strong>
                            {
                              record.diagnosis
                                .primary_misconception.name
                            }
                          </strong>

                          <small>
                            {record.diagnosis
                              .primary_misconception
                              .topic ??
                              "Uncategorized"}
                          </small>
                        </div>
                      </article>
                    ) : (
                      <div className="teacher-detail-empty">
                        No primary misconception was assigned.
                      </div>
                    )}
                  </div>

                  <div className="teacher-detail-section">
                    <h3>Decision reason</h3>
                    <div className="teacher-detail-text-block">
                      {record.diagnosis
                        .decision_reason ??
                        "No decision reason was recorded."}
                    </div>
                  </div>
                </>
              )}
            </article>
          </section>

          <section className="teacher-attempt-detail-grid">
            <article className="teacher-panel">
              <div className="teacher-panel-heading">
                <div>
                  <p className="eyebrow">
                    Evidence review
                  </p>
                  <h2>Diagnosis evidence</h2>
                </div>

                <span>
                  {sortedEvidence.length} items
                </span>
              </div>

              {sortedEvidence.length === 0 ? (
                <div className="teacher-empty-state">
                  No diagnosis evidence is available.
                </div>
              ) : (
                <div className="teacher-evidence-list">
                  {sortedEvidence.map(
                    (evidence, index) => (
                      <article
                        className="teacher-evidence-card"
                        key={
                          evidence.id ??
                          `${evidence.source}-${index}`
                        }
                      >
                        <div className="teacher-evidence-card-header">
                          <span>
                            {formatEvidenceSource(
                              evidence.source
                            )}
                          </span>

                          <strong>
                            {formatDiagnosisState(
                              evidence.strength
                            )}
                          </strong>
                        </div>

                        <p>{evidence.text}</p>

                        {Object.keys(
                          evidence.metadata
                        ).length > 0 ? (
                          <dl className="teacher-evidence-metadata">
                            {Object.entries(
                              evidence.metadata
                            ).map(
                              ([key, value]) => (
                                <div key={key}>
                                  <dt>
                                    {formatDiagnosisState(
                                      key
                                    )}
                                  </dt>
                                  <dd>
                                    {formatMetadataValue(
                                      value
                                    )}
                                  </dd>
                                </div>
                              )
                            )}
                          </dl>
                        ) : null}
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
                    Alternative hypotheses
                  </p>
                  <h2>Diagnosis alternatives</h2>
                </div>

                <span>
                  {record.diagnosis?.alternatives
                    .length ?? 0}{" "}
                  items
                </span>
              </div>

              {!record.diagnosis ||
              record.diagnosis.alternatives.length ===
                0 ? (
                <div className="teacher-empty-state">
                  No alternative misconceptions were recorded.
                </div>
              ) : (
                <div className="teacher-alternative-list">
                  {record.diagnosis.alternatives.map(
                    (alternative, index) => (
                      <article
                        className="teacher-alternative-card"
                        key={
                          alternative.id ??
                          `${alternative.misconception.id}-${index}`
                        }
                      >
                        <div>
                          <span>
                            {
                              alternative
                                .misconception.code
                            }
                          </span>

                          <strong>
                            {
                              alternative
                                .misconception.name
                            }
                          </strong>
                        </div>

                        <em>
                          {formatPercent(
                            alternative.confidence
                          )}
                        </em>

                        <p>
                          {alternative.reason ??
                            "No alternative reason was recorded."}
                        </p>
                      </article>
                    )
                  )}
                </div>
              )}
            </article>
          </section>

          <section className="teacher-panel">
            <div className="teacher-panel-heading">
              <div>
                <p className="eyebrow">
                  Problem context
                </p>
                <h2>{record.problem.title}</h2>
              </div>

              <span>
                {record.problem.difficulty ??
                  "Unspecified difficulty"}
              </span>
            </div>

            <div className="teacher-detail-text-block">
              {record.problem.statement}
            </div>

            <div className="teacher-problem-meta-grid">
              <div>
                <span>Expected language</span>
                <strong>
                  {record.problem.expected_language ??
                    "Not specified"}
                </strong>
              </div>

              <div>
                <span>Supported misconceptions</span>
                <strong>
                  {
                    record.problem
                      .supported_misconceptions.length
                  }
                </strong>
              </div>

              <div>
                <span>Problem status</span>
                <strong>
                  {record.problem.active
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