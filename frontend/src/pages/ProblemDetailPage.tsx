import { useEffect, useState } from "react";
import { apiRequest } from "../api/client";
import AttemptSubmissionForm from "../components/AttemptSubmissionForm";
import type { ProblemDetail } from "../types/problem";
import type { StudentSessionResponse } from "../types/student";

interface ProblemDetailPageProps {
  problemId: string;
  session: StudentSessionResponse;
  onBack: () => void;
}

export function ProblemDetailPage({
  problemId,
  session,
  onBack,
}: ProblemDetailPageProps) {
  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadProblemDetail() {
      try {
        setLoading(true);
        setError("");

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
    return (
      <main className="page-shell">
        <section className="panel muted">Loading problem detail...</section>
      </main>
    );
  }

  if (error || !problem) {
    return (
      <main className="page-shell">
        <section className="error-box">{error || "Problem not found"}</section>

        <button className="secondary-button" type="button" onClick={onBack}>
          ← Back to problem bank
        </button>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <button className="secondary-button" type="button" onClick={onBack}>
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

            {problem.supported_misconceptions.length > 0 ? (
              <ul>
                {problem.supported_misconceptions.map((item) => (
                  <li key={item.id}>
                    <strong>{item.code}</strong> — {item.name}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No supported misconceptions configured for this problem.</p>
            )}
          </div>
        </div>
      </section>

      <AttemptSubmissionForm
        studentAliasId={session.student_alias_id}
        problemId={problem.id}
        problemTitle={problem.title}
      />
    </main>
  );
}