import { useState } from "react";
import { apiRequest } from "../api/client";
import type { StudentSessionResponse } from "../types/student";

interface StudentSessionPageProps {
  onSessionCreated: (session: StudentSessionResponse) => void;
}

export function StudentSessionPage({ onSessionCreated }: StudentSessionPageProps) {
  const [alias, setAlias] = useState("");
  const [consentStatus, setConsentStatus] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const session = await apiRequest<StudentSessionResponse>("/student/session", {
        method: "POST",
        body: JSON.stringify({
          alias,
          consent_status: consentStatus,
        }),
      });

      localStorage.setItem("studentSession", JSON.stringify(session));
      onSessionCreated(session);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create session");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page-shell">
      <section className="hero-card">
        <p className="eyebrow">MisconceptionOS</p>
        <h1>Diagnose the misconception, not just the mistake.</h1>
        <p className="hero-text">
          Enter a pseudonymous alias to continue. Do not enter your real name,
          email address, phone number, or roll number.
        </p>
      </section>

      <section className="panel">
        <h2>Student session</h2>
        <p className="muted">
          This project uses pseudonymous IDs so student attempts can be studied
          without storing direct personal identity.
        </p>

        <form onSubmit={handleSubmit} className="form-stack">
          <label>
            Alias
            <input
              value={alias}
              onChange={(event) => setAlias(event.target.value)}
              placeholder="example: student-fox-21"
              minLength={3}
              maxLength={80}
              required
            />
          </label>

          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={consentStatus}
              onChange={(event) => setConsentStatus(event.target.checked)}
            />
            <span>
              I agree to use a pseudonymous alias and understand that my attempt
              may be used for misconception diagnosis research.
            </span>
          </label>

          {error && <div className="error-box">{error}</div>}

          <button type="submit" disabled={loading}>
            {loading ? "Creating session..." : "Continue to problem bank"}
          </button>
        </form>
      </section>
    </main>
  );
}