import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import type { StudentSessionResponse } from "../types/student";

interface StudentSessionPageProps {
  onSessionCreated: (session: StudentSessionResponse) => void;
}

type StudentSessionRequest = {
  alias: string;
  consent_status: boolean;
};

const API_BASE_URL = "http://127.0.0.1:8000/api";

function hasPersonalIdentity(value: string) {
  const emailPattern = /\S+@\S+\.\S+/;
  const phonePattern = /(\+?\d[\d\s-]{7,}\d)/;
  const rollPattern = /\b(roll|reg|register|id)\s*[:#-]?\s*\d+/i;

  return (
    emailPattern.test(value) ||
    phonePattern.test(value) ||
    rollPattern.test(value)
  );
}

function getErrorMessage(data: unknown) {
  if (
    typeof data === "object" &&
    data !== null &&
    "detail" in data
  ) {
    const detail = (data as { detail: unknown }).detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (
            typeof item === "object" &&
            item !== null &&
            "msg" in item &&
            typeof (item as { msg: unknown }).msg === "string"
          ) {
            return (item as { msg: string }).msg;
          }

          return "Validation error";
        })
        .join(" ");
    }
  }

  return "Unable to create student session.";
}

async function createStudentSession(
  payload: StudentSessionRequest
): Promise<StudentSessionResponse> {
  const response = await fetch(`${API_BASE_URL}/student/session`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data: unknown = await response.json();

  if (!response.ok) {
    throw new Error(getErrorMessage(data));
  }

  return data as StudentSessionResponse;
}

export function StudentSessionPage({
  onSessionCreated,
}: StudentSessionPageProps) {
  const [alias, setAlias] = useState("");
  const [consentStatus, setConsentStatus] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const normalizedAlias = useMemo(() => alias.trim(), [alias]);

  const aliasLooksPrivate =
    normalizedAlias.length >= 3 && !hasPersonalIdentity(normalizedAlias);

  const canContinue = aliasLooksPrivate && consentStatus && !submitting;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (!normalizedAlias) {
      setError("Enter a pseudonymous alias to continue.");
      return;
    }

    if (normalizedAlias.length < 3) {
      setError("Alias must be at least 3 characters.");
      return;
    }

    if (hasPersonalIdentity(normalizedAlias)) {
      setError(
        "Alias must not contain your real name, email address, phone number, roll number, or registration ID."
      );
      return;
    }

    if (!consentStatus) {
      setError("Consent is required to create a student session.");
      return;
    }

    try {
      setSubmitting(true);

      const session = await createStudentSession({
        alias: normalizedAlias,
        consent_status: consentStatus,
      });

      localStorage.setItem("studentSession", JSON.stringify(session));
      onSessionCreated(session);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to create student session."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="session-v21-page">
      <section className="session-v21-shell">
        <header className="session-v21-topbar">
          <button
            className="session-v21-back"
            type="button"
            onClick={() => window.location.reload()}
          >
            ← Back to home
          </button>

          <div className="session-v21-brand-note">
            Private student entry · Pseudonymous research session
          </div>
        </header>

        <section className="session-v21-main-card">
          <div className="session-v21-copy">
            <p className="session-v21-kicker">Private student entry</p>

            <h1>Start a private diagnostic session.</h1>

            <p>
              Create a pseudonymous alias, select a seeded DSA problem, and
              submit your reasoning without exposing direct personal identity.
            </p>

            <div className="session-v21-rules">
              <span>No real name</span>
              <span>No email</span>
              <span>No phone</span>
              <span>No roll number</span>
            </div>
          </div>

          <form className="session-v21-form" onSubmit={handleSubmit}>
            <div className="session-v21-form-head">
              <p>Student session</p>
              <h2>Enter alias</h2>
            </div>

            <label className="session-v21-field">
              Pseudonymous alias
              <input
                value={alias}
                onChange={(event) => setAlias(event.target.value)}
                placeholder="example: student-lion-31"
                autoComplete="off"
              />
            </label>

            <div
              className={
                alias.length === 0
                  ? "session-v21-check neutral"
                  : aliasLooksPrivate
                    ? "session-v21-check good"
                    : "session-v21-check bad"
              }
            >
              {alias.length === 0
                ? "Alias will be checked before session creation."
                : aliasLooksPrivate
                  ? "Alias looks safe to use."
                  : "Alias may contain personal identity or is too short."}
            </div>

            <label className="session-v21-consent">
              <input
                type="checkbox"
                checked={consentStatus}
                onChange={(event) => setConsentStatus(event.target.checked)}
              />

              <span>
                I agree to use a pseudonymous alias and understand that my
                attempt may be used for misconception diagnosis research.
              </span>
            </label>

            {error && <div className="session-v21-error">{error}</div>}

            <button
              className="session-v21-submit"
              type="submit"
              disabled={!canContinue}
            >
              {submitting ? "Creating session..." : "Continue to problem bank"}
            </button>
          </form>
        </section>

        <section className="session-v21-flow">
          <div>
            <span>01</span>
            <strong>Create alias</strong>
            <p>Alias becomes a research ID.</p>
          </div>

          <div>
            <span>02</span>
            <strong>Select problem</strong>
            <p>Choose a seeded DSA task.</p>
          </div>

          <div>
            <span>03</span>
            <strong>Submit reasoning</strong>
            <p>Final answer, reasoning, code, or transcript.</p>
          </div>

          <div>
            <span>04</span>
            <strong>Diagnosis later</strong>
            <p>Attempt submission is separate from diagnosis.</p>
          </div>
        </section>
      </section>
    </main>
  );
}