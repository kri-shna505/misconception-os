import { useEffect, useState } from "react";
import { apiRequest } from "../api/client";
import type { ProblemDetail } from "../types/problem";

interface ProblemDetailPageProps {
  problemId: string;
  onBack: () => void;
}

export function ProblemDetailPage({ problemId, onBack }: ProblemDetailPageProps) {
  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadProblemDetail() {
      try {
        const data = await apiRequest<ProblemDetail>(`/problems/${problemId}`);
        setProblem(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load problem");
      } finally {
        setLoading(false);
      }
    }

    loadProblemDetail();
  }, [problemId]);

  if (loading) {
    return <main className="page-shell">Loading problem detail...</main>;
  }

  if (error || !problem) {
    return (
      <main className="page-shell">
        <section className="error-box">{error || "Problem not found"}</section>
        <button onClick={onBack}>Back to problem bank</button>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <button className="secondary-button" onClick={onBack}>
        ← Back to problem bank
      </button>

      <section className="panel">
        <p className="eyebrow">
          {problem.code} • {problem.topic} • {problem.difficulty}
        </p>
        <h1>{problem.title}</h1>
        <p className="statement">{problem.statement}</p>

        <div className="info-grid">
          <div>
            <h3>Expected language</h3>
            <p>{problem.expected_language || "Not specified"}</p>
          </div>

          <div>
            <h3>Supported misconceptions</h3>
            <ul>
              {problem.supported_misconceptions.map((item) => (
                <li key={item.id}>
                  <strong>{item.code}</strong> — {item.name}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="panel muted">
        Attempt submission form will come in Sprint 3.
      </section>
    </main>
  );
}