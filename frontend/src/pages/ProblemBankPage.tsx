import { useEffect, useMemo, useState } from "react";
import { apiRequest } from "../api/client";
import type { ProblemListItem } from "../types/problem";
import type { StudentSessionResponse } from "../types/student";

export type ProblemProgressState =
  | "not_started"
  | "in_progress"
  | "attempt_saved"
  | "diagnosed";

interface ProblemBankPageProps {
  session: StudentSessionResponse;
  onProblemSelected: (problemId: string) => void;
  onResetSession: () => void;

  /**
   * Current attempt and diagnosis progress keyed by problem ID.
   */
  progressByProblemId?: Record<string, ProblemProgressState>;
}

type ProblemAvailability = "Available" | "Preview";

type ProblemMeta = {
  misconceptionCode: string;
  focus: string;
  summary: string;
  availability: ProblemAvailability;
};

function getProblemMeta(problem: ProblemListItem): ProblemMeta {
  const code = problem.code?.toUpperCase();

  if (code === "P1") {
    return {
      misconceptionCode: "M1",
      focus: "Binary search precondition",
      summary:
        "Checks whether binary search is incorrectly used on unsorted input.",
      availability: "Available",
    };
  }

  if (code === "P2") {
    return {
      misconceptionCode: "M2",
      focus: "Recursion base case",
      summary:
        "Checks whether the recursive solution has a valid stopping condition.",
      availability: "Available",
    };
  }

  if (code === "P3") {
    return {
      misconceptionCode: "M3",
      focus: "Recursive progress",
      summary:
        "Checks whether the recursive call reduces the problem size.",
      availability: "Available",
    };
  }

  if (code === "P4") {
    return {
      misconceptionCode: "M4",
      focus: "Pass-by-value vs reference",
      summary:
        "Checks confusion between local variable changes and caller-visible changes.",
      availability: "Available",
    };
  }

  if (code === "P5") {
    return {
      misconceptionCode: "M5",
      focus: "Stack vs heap reasoning",
      summary:
        "Checks misunderstanding of stack frames, heap objects, and memory behavior.",
      availability: "Available",
    };
  }

  return {
    misconceptionCode: "M?",
    focus: "Diagnostic focus not configured",
    summary:
      "This seeded problem is available for student attempt collection.",
    availability:
      problem.active === false
        ? "Preview"
        : "Available",
  };
}

function formatTopic(topic?: string | null) {
  if (!topic) {
    return "DSA";
  }

  return topic;
}

function formatDifficulty(difficulty?: string | null) {
  if (!difficulty) {
    return "Not set";
  }

  return difficulty.charAt(0).toUpperCase() + difficulty.slice(1);
}

function getProgressLabel(progress: ProblemProgressState) {
  switch (progress) {
    case "in_progress":
      return "Continue";

    case "attempt_saved":
      return "Submitted";

    case "diagnosed":
      return "View diagnosis";

    case "not_started":
    default:
      return "Attempt";
  }
}

function getProgressStatusLabel(progress: ProblemProgressState) {
  switch (progress) {
    case "in_progress":
      return "In progress";

    case "attempt_saved":
      return "Attempt saved";

    case "diagnosed":
      return "Diagnosed";

    case "not_started":
    default:
      return null;
  }
}

function getProgressClassName(progress: ProblemProgressState) {
  switch (progress) {
    case "in_progress":
      return "in-progress";

    case "attempt_saved":
      return "submitted";

    case "diagnosed":
      return "diagnosed";

    case "not_started":
    default:
      return "not-started";
  }
}

export function ProblemBankPage({
  session,
  onProblemSelected,
  onResetSession,
  progressByProblemId = {},
}: ProblemBankPageProps) {
  const [problems, setProblems] = useState<ProblemListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadProblems() {
      try {
        setLoading(true);
        setError("");

        const data = await apiRequest<ProblemListItem[]>("/problems");

        if (isMounted) {
          setProblems(data);
        }
      } catch (err) {
        if (isMounted) {
          setError(
            err instanceof Error ? err.message : "Unable to load problems"
          );
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    void loadProblems();

    return () => {
      isMounted = false;
    };
  }, []);

  const summary = useMemo(() => {
    const available = problems.filter(
      (problem) => getProblemMeta(problem).availability === "Available"
    ).length;

    const saved = problems.filter((problem) => {
      const progress = progressByProblemId[problem.id];

      return progress === "attempt_saved" || progress === "diagnosed";
    }).length;

    const diagnosed = problems.filter(
      (problem) => progressByProblemId[problem.id] === "diagnosed"
    ).length;

    return {
      total: problems.length,
      available,
      saved,
      diagnosed,
    };
  }, [problems, progressByProblemId]);

  return (
    <main className="student-bank-page">
      <header className="student-bank-header">
        <div className="brand-block">
          <div className="brand-logo">M/OS</div>

          <div>
            <div className="brand-title">MisconceptionOS</div>
            <div className="brand-subtitle">DSA Diagnostic Tutor</div>
          </div>
        </div>

        <div className="session-block">
          <div className="session-meta">
            <span>
              Alias: <strong>{session.alias}</strong>
            </span>

            <span>
              ID: <strong>{session.pseudonymous_id}</strong>
            </span>
          </div>

          <button
            className="outline-button compact"
            type="button"
            onClick={onResetSession}
          >
            Reset
          </button>
        </div>
      </header>

      <section className="workspace-summary-card">
        <div className="workspace-summary-content">
          <p className="section-kicker">Student workspace</p>

          <h1>Available DSA Problems</h1>

          <p className="workspace-copy">
            Select a seeded problem. Save the attempt first, then generate
            diagnosis separately.
          </p>
        </div>

        <div className="workspace-stats">
          <div className="stat-tile">
            <span>Total</span>
            <strong>{summary.total}</strong>
          </div>

          <div className="stat-tile">
            <span>Available</span>
            <strong>{summary.available}</strong>
          </div>

          <div className="stat-tile">
            <span>Saved</span>
            <strong>{summary.saved}</strong>
          </div>

          <div className="stat-tile">
            <span>Diagnosed</span>
            <strong>{summary.diagnosed}</strong>
          </div>
        </div>
      </section>

      {loading && (
        <section className="state-card" aria-live="polite">
          Loading problems...
        </section>
      )}

      {error && (
        <section className="state-card error-state" role="alert">
          {error}
        </section>
      )}

      {!loading && !error && problems.length === 0 && (
        <section className="state-card">
          No seeded problems are currently available.
        </section>
      )}

      {!loading && !error && problems.length > 0 && (
        <section className="problem-list-clean">
          {problems.map((problem) => {
            const meta = getProblemMeta(problem);

            const progress =
              progressByProblemId[problem.id] ?? "not_started";

            const progressLabel = getProgressStatusLabel(progress);
            const progressClassName = getProgressClassName(progress);

            const actionLabel =
              meta.availability === "Preview" &&
              progress === "not_started"
                ? "View preview"
                : getProgressLabel(progress);

            return (
              <article
                key={problem.id}
                className={`problem-row-card problem-progress-${progressClassName}`}
              >
                <div className="problem-code-column">
                  <span className="problem-code-pill">
                    {problem.code}
                  </span>

                  <span
                    className={`status-pill ${
                      meta.availability === "Available"
                        ? "ready"
                        : "preview"
                    }`}
                  >
                    {meta.availability}
                  </span>

                  {progressLabel && (
                    <span
                      className={`progress-status-pill ${progressClassName}`}
                    >
                      {progressLabel}
                    </span>
                  )}
                </div>

                <div className="problem-content-column">
                  <div className="problem-tags">
                    <span>{formatTopic(problem.topic)}</span>
                    <span>{formatDifficulty(problem.difficulty)}</span>
                    <span>{meta.misconceptionCode}</span>
                  </div>

                  <h2>{problem.title}</h2>

                  <p>{meta.summary}</p>

                  <div className="diagnostic-focus-line">
                    <span>Diagnostic focus</span>
                    <strong>{meta.focus}</strong>
                  </div>
                </div>

                <div className="problem-action-column">
                  <button
                    className={`primary-button compact-action action-${progressClassName}`}
                    type="button"
                    onClick={() => onProblemSelected(problem.id)}
                  >
                    {actionLabel}
                  </button>
                </div>
              </article>
            );
          })}
        </section>
      )}
    </main>
  );
}