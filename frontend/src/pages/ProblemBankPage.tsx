import { useEffect, useState } from "react";
import { apiRequest } from "../api/client";
import type { ProblemListItem } from "../types/problem";
import type { StudentSessionResponse } from "../types/student";

interface ProblemBankPageProps {
  session: StudentSessionResponse;
  onProblemSelected: (problemId: string) => void;
  onResetSession: () => void;
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

  return (
    <main className="page-shell">
      <section className="top-bar">
        <div>
          <p className="eyebrow">Student</p>
          <h1>Problem Bank</h1>
          <p className="muted">
            Alias: <strong>{session.alias}</strong> | ID:{" "}
            <strong>{session.pseudonymous_id}</strong>
          </p>
        </div>

        <button className="secondary-button" onClick={onResetSession}>
          Reset session
        </button>
      </section>

      {loading && <section className="panel">Loading problems...</section>}

      {error && <section className="error-box">{error}</section>}

      {!loading && !error && (
        <section className="problem-grid">
          {problems.map((problem) => (
            <article key={problem.id} className="problem-card">
              <div className="problem-meta">
                <span>{problem.code}</span>
                <span>{problem.topic}</span>
                <span>{problem.difficulty || "not set"}</span>
              </div>

              <h2>{problem.title}</h2>

              <button onClick={() => onProblemSelected(problem.id)}>
                View problem
              </button>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}