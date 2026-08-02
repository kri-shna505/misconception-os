import { useEffect, useMemo, useState } from "react";
import { apiRequest } from "../api/client";
import AttemptSubmissionForm from "../components/AttemptSubmissionForm";
import type { ProblemDetail } from "../types/problem";
import type { StudentSessionResponse } from "../types/student";

interface ProblemDetailPageProps {
  problemId: string;
  session: StudentSessionResponse;
  onBack: () => void;

  /**
   * Optional callback used by App.tsx to refresh the Problem Bank progress
   * after an attempt has been successfully saved or diagnosed.
   */
  onProgressChanged?: () => void;
}

function formatValue(value?: string | null, fallback = "Not set") {
  const normalizedValue = value?.trim();

  if (!normalizedValue) {
    return fallback;
  }

  return normalizedValue;
}

function formatDisplayValue(value?: string | null, fallback = "Not set") {
  const normalizedValue = formatValue(value, fallback);

  if (normalizedValue === fallback) {
    return normalizedValue;
  }

  return (
    normalizedValue.charAt(0).toUpperCase() +
    normalizedValue.slice(1)
  );
}

function getPrimaryMisconceptionCode(problemCode: string) {
  const normalizedCode = problemCode.trim().toUpperCase();

  const misconceptionMap: Record<string, string> = {
    P1: "M1",
    P2: "M2",
    P3: "M3",
    P4: "M4",
    P5: "M5",
  };

  return misconceptionMap[normalizedCode] ?? "";
}

export function ProblemDetailPage({
  problemId,
  session,
  onBack,
  onProgressChanged,
}: ProblemDetailPageProps) {
  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [attemptSaved, setAttemptSaved] = useState(false);
  const [savedAttemptId, setSavedAttemptId] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadProblemDetail() {
      try {
        setLoading(true);
        setError("");
        setAttemptSaved(false);
        setSavedAttemptId(null);

        const data = await apiRequest<ProblemDetail>(
          `/problems/${problemId}`
        );

        if (isMounted) {
          setProblem(data);
        }
      } catch (err) {
        if (isMounted) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load problem"
          );
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    void loadProblemDetail();

    return () => {
      isMounted = false;
    };
  }, [problemId]);

  const supportedMisconceptions = useMemo(
    () => problem?.supported_misconceptions ?? [],
    [problem]
  );

  const primaryMisconception = useMemo(() => {
    if (!problem || supportedMisconceptions.length === 0) {
      return undefined;
    }

    const primaryCode = getPrimaryMisconceptionCode(problem.code);

    return (
      supportedMisconceptions.find(
        (item) =>
          item.code.trim().toUpperCase() ===
          primaryCode.toUpperCase()
      ) ?? supportedMisconceptions[0]
    );
  }, [problem, supportedMisconceptions]);

  function handleAttemptSaved(attemptId: string) {
    setAttemptSaved(true);
    setSavedAttemptId(attemptId);
    onProgressChanged?.();
  }

  function handleDiagnosisGenerated() {
    onProgressChanged?.();
  }

  if (loading) {
    return (
      <main className="student-page">
        <section className="student-shell">
          <div className="state-card" role="status">
            Loading problem detail...
          </div>
        </section>
      </main>
    );
  }

  if (error || !problem) {
    return (
      <main className="student-page">
        <section className="student-shell">
          <header className="student-topbar">
            <div className="brand-lockup">
              <div className="brand-mark" aria-label="MisconceptionOS">
                M/OS
              </div>

              <div>
                <strong>MisconceptionOS</strong>
                <span>DSA Diagnostic Tutor</span>
              </div>
            </div>

            <button
              className="secondary-button"
              type="button"
              onClick={onBack}
            >
              Back
            </button>
          </header>

          <div className="error-box" role="alert">
            {error || "Problem not found"}
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="student-page">
      <section className="student-shell">
        <header className="student-topbar">
          <div className="brand-lockup">
            <div className="brand-mark" aria-label="MisconceptionOS">
              M/OS
            </div>

            <div>
              <strong>MisconceptionOS</strong>
              <span>DSA Diagnostic Tutor</span>
            </div>
          </div>

          <div className="session-strip">
            <span>
              Alias: <strong>{session.alias}</strong>
            </span>

            <span>
              ID: <strong>{session.pseudonymous_id}</strong>
            </span>

            <button
              className="secondary-button"
              type="button"
              onClick={onBack}
            >
              Back
            </button>
          </div>
        </header>

        <section className="detail-hero-card">
          <div className="detail-hero-main">
            <p className="eyebrow">Problem workspace</p>

            <div className="problem-chip-row">
              <span className="problem-chip problem-chip-dark">
                {problem.code}
              </span>

              <span className="problem-chip">
                {formatDisplayValue(problem.topic, "DSA")}
              </span>

              <span className="problem-chip">
                {formatDisplayValue(
                  problem.difficulty,
                  "Not set"
                )}
              </span>

              {primaryMisconception && (
                <span className="problem-chip">
                  {primaryMisconception.code}
                </span>
              )}
            </div>

            <h1>{problem.title}</h1>

            <p className="problem-statement">
              {problem.statement}
            </p>
          </div>

          <aside
            className="detail-meta-card"
            aria-label="Problem metadata"
          >
            <div>
              <span>Default language</span>
              <strong>
                {formatDisplayValue(
                  problem.expected_language,
                  "Not set"
                )}
              </strong>
            </div>

            <div>
              <span>Mapped rules</span>
              <strong>{supportedMisconceptions.length}</strong>
            </div>
          </aside>
        </section>

        {supportedMisconceptions.length > 0 && (
          <section className="mapped-rules-card">
            <p className="section-kicker">
              Supported misconception rules
            </p>

            <div className="mapped-rule-list">
              {supportedMisconceptions.map((item) => (
                <div
                  className="mapped-rule-item"
                  key={item.id}
                >
                  <span>{item.code}</span>
                  <strong>{item.name}</strong>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="attempt-workspace-card">
          <div className="attempt-workspace-heading">
            <div>
              <p className="section-kicker">
                Student attempt
              </p>

              <h2>
                Write your answer, reasoning, and code.
              </h2>

              <p>
                Save the attempt first. Generate diagnosis
                only after the attempt is saved.
              </p>
            </div>

            <div
              className={`attempt-stage-badge ${
                attemptSaved ? "saved" : "draft"
              }`}
            >
              {attemptSaved ? "Attempt saved" : "Draft"}
            </div>
          </div>

          <AttemptSubmissionForm
            studentAliasId={session.student_alias_id}
            problemId={problem.id}
            problemTitle={problem.title}
            expectedLanguage={problem.expected_language}
            onAttemptSaved={handleAttemptSaved}
            onDiagnosisGenerated={handleDiagnosisGenerated}
            savedAttemptId={savedAttemptId}
          />
        </section>
      </section>
    </main>
  );
}