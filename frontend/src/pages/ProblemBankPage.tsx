import { useEffect, useMemo, useState } from "react";
import { apiRequest } from "../api/client";
import type { ProblemListItem } from "../types/problem";
import type { StudentSessionResponse } from "../types/student";

interface ProblemBankPageProps {
  session: StudentSessionResponse;
  onProblemSelected: (problemId: string) => void;
  onResetSession: () => void;
}

type ProblemMeta = {
  misconceptionCode: string;
  focus: string;
  summary: string;
  status: "Ready" | "Preview";
};

function getProblemMeta(problem: ProblemListItem): ProblemMeta {
  const code = problem.code?.toUpperCase();

  if (code === "P1") {
    return {
      misconceptionCode: "M1",
      focus: "Binary search precondition",
      summary: "Checks whether binary search is incorrectly used on unsorted input.",
      status: "Ready",
    };
  }

  if (code === "P2") {
    return {
      misconceptionCode: "M2",
      focus: "Recursion base case",
      summary: "Checks whether the recursive solution has a valid stopping condition.",
      status: "Ready",
    };
  }

  if (code === "P3") {
    return {
      misconceptionCode: "M3",
      focus: "Recursive progress",
      summary: "Checks whether the recursive call reduces the problem size.",
      status: "Ready",
    };
  }

  if (code === "P4") {
    return {
      misconceptionCode: "M4",
      focus: "Pass-by-value vs reference",
      summary: "Checks confusion between local variable changes and caller-visible changes.",
      status: "Preview",
    };
  }

  if (code === "P5") {
    return {
      misconceptionCode: "M5",
      focus: "Stack vs heap reasoning",
      summary: "Checks misunderstanding of stack frames, heap objects, and memory behavior.",
      status: "Preview",
    };
  }

  return {
    misconceptionCode: "M?",
    focus: "Diagnostic focus not configured",
    summary: "This seeded problem is available for student attempt collection.",
    status: "Preview",
  };
}

function formatTopic(topic?: string) {
  if (!topic) return "DSA";
  return topic;
}

function formatDifficulty(difficulty?: string | null) {
  if (!difficulty) return "not set";
  return difficulty.charAt(0).toUpperCase() + difficulty.slice(1);
}

export function ProblemBankPage({
  session,
  onProblemSelected,
  onResetSession,
}: ProblemBankPageProps) {
  const [problems, setProblems] = useState<ProblemListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadProblems() {
      try {
        const data = await apiRequest<ProblemListItem[]>("/problems");
        setProblems(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load problems");
      } finally {
        setLoading(false);
      }
    }

    loadProblems();
  }, []);

  const readyCount = useMemo(
    () => problems.filter((problem) => getProblemMeta(problem).status === "Ready").length,
    [problems]
  );

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
            <span>Alias: <strong>{session.alias}</strong></span>
            <span>ID: <strong>{session.pseudonymous_id}</strong></span>
          </div>

          <button className="outline-button compact" onClick={onResetSession}>
            Reset
          </button>
        </div>
      </header>

      <section className="workspace-summary-card">
        <div>
          <p className="section-kicker">Student workspace</p>
          <h1>Available DSA Problems</h1>
          <p className="workspace-copy">
            Select a seeded problem. Save the attempt first, then generate diagnosis separately.
          </p>
        </div>

        <div className="workspace-stats">
          <div className="stat-tile">
            <span>Total</span>
            <strong>{problems.length}</strong>
          </div>

          <div className="stat-tile">
            <span>Ready</span>
            <strong>{readyCount}</strong>
          </div>
        </div>
      </section>

      {loading && (
        <section className="state-card">
          Loading problems...
        </section>
      )}

      {error && (
        <section className="state-card error-state">
          {error}
        </section>
      )}

      {!loading && !error && (
        <section className="problem-list-clean">
          {problems.map((problem) => {
            const meta = getProblemMeta(problem);

            return (
              <article key={problem.id} className="problem-row-card">
                <div className="problem-code-column">
                  <span className="problem-code-pill">{problem.code}</span>
                  <span className={`status-pill ${meta.status === "Ready" ? "ready" : "preview"}`}>
                    {meta.status}
                  </span>
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
                    className="primary-button compact-action"
                    onClick={() => onProblemSelected(problem.id)}
                  >
                    Attempt
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