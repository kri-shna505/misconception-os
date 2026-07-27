import type { FormEvent } from "react";
import { useMemo, useState } from "react";

import { submitAttempt } from "../services/attemptApi";
import type { AttemptResponse } from "../services/attemptApi";

import { createDiagnosisFromAttempt } from "../services/diagnosisApi";
import type { DiagnosisResponse } from "../types/diagnosis";

type AttemptSubmissionFormProps = {
  studentAliasId: string;
  problemId: string;
  problemTitle: string;
};

function formatConfidence(value: number) {
  return `${Math.round(value * 100)}%`;
}

function formatState(value: string) {
  return value.replaceAll("_", " ");
}

export default function AttemptSubmissionForm({
  studentAliasId,
  problemId,
  problemTitle,
}: AttemptSubmissionFormProps) {
  const [finalAnswer, setFinalAnswer] = useState("");
  const [writtenReasoning, setWrittenReasoning] = useState("");
  const [sourceCode, setSourceCode] = useState("");
  const [speechTranscript, setSpeechTranscript] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState("python");

  const [startedAt, setStartedAt] = useState(() => Date.now());
  const [submitting, setSubmitting] = useState(false);
  const [submittedAttempt, setSubmittedAttempt] =
    useState<AttemptResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [diagnosis, setDiagnosis] = useState<DiagnosisResponse | null>(null);
  const [diagnosing, setDiagnosing] = useState(false);
  const [diagnosisError, setDiagnosisError] = useState<string | null>(null);

  const responseTimeSeconds = useMemo(() => {
    return Math.max(1, Math.round((Date.now() - startedAt) / 1000));
  }, [startedAt, finalAnswer, writtenReasoning, sourceCode, speechTranscript]);

  const canSubmit =
    writtenReasoning.trim().length >= 5 &&
    (finalAnswer.trim().length > 0 ||
      sourceCode.trim().length > 0 ||
      speechTranscript.trim().length > 0) &&
    !submitting;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setError(null);
    setSubmittedAttempt(null);
    setDiagnosis(null);
    setDiagnosisError(null);

    if (!canSubmit) {
      setError(
        "Write your reasoning and include at least one of final answer, code, or speech transcript."
      );
      return;
    }

    try {
      setSubmitting(true);

      const result = await submitAttempt({
        student_alias_id: studentAliasId,
        problem_id: problemId,
        final_answer: finalAnswer.trim(),
        written_reasoning: writtenReasoning.trim(),
        source_code: sourceCode.trim() ? sourceCode.trim() : null,
        speech_transcript: speechTranscript.trim()
          ? speechTranscript.trim()
          : null,
        selected_language: selectedLanguage.trim().toLowerCase() || "python",
        response_time_seconds: responseTimeSeconds,
      });

      setSubmittedAttempt(result);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Attempt submission failed.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGenerateDiagnosis() {
    if (!submittedAttempt) {
      return;
    }

    setDiagnosisError(null);

    try {
      setDiagnosing(true);
      const result = await createDiagnosisFromAttempt(submittedAttempt.id);
      setDiagnosis(result);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Diagnosis generation failed.";
      setDiagnosisError(message);
    } finally {
      setDiagnosing(false);
    }
  }

  function handleSubmitAnotherAttempt() {
    setSubmittedAttempt(null);
    setDiagnosis(null);
    setDiagnosisError(null);
    setFinalAnswer("");
    setWrittenReasoning("");
    setSourceCode("");
    setSpeechTranscript("");
    setStartedAt(Date.now());
  }

  if (submittedAttempt) {
    return (
      <section className="attempt-card attempt-success-card">
        <p className="section-kicker">Attempt saved</p>
        <h2>Your submission was recorded.</h2>
        <p>
          This attempt is stored separately from diagnosis. Generate a diagnosis
          only when you are ready to inspect the misconception evidence.
        </p>

        <div className="attempt-result-grid">
          <div>
            <span>Attempt ID</span>
            <strong>{submittedAttempt.id}</strong>
          </div>
          <div>
            <span>Language</span>
            <strong>{submittedAttempt.selected_language}</strong>
          </div>
          <div>
            <span>Response time</span>
            <strong>
              {submittedAttempt.response_time_seconds ?? responseTimeSeconds}s
            </strong>
          </div>
          <div>
            <span>Status</span>
            <strong>Submitted</strong>
          </div>
        </div>

        <div className="attempt-actions">
          <button
            className="primary-button"
            type="button"
            onClick={handleGenerateDiagnosis}
            disabled={diagnosing}
          >
            {diagnosing ? "Generating diagnosis..." : "Generate diagnosis"}
          </button>

          <button
            className="secondary-button"
            type="button"
            onClick={handleSubmitAnotherAttempt}
          >
            Submit another attempt
          </button>
        </div>

        {diagnosisError && (
          <div className="attempt-error">{diagnosisError}</div>
        )}

        {diagnosis && (
          <section className="diagnosis-card">
            <div className="diagnosis-card-header">
              <div>
                <p className="section-kicker">Diagnosis result</p>
                <h2>
                  {diagnosis.primary_misconception
                    ? diagnosis.primary_misconception.name
                    : "No confident misconception detected"}
                </h2>
              </div>

              <div className="diagnosis-confidence">
                <span>{formatConfidence(diagnosis.confidence)}</span>
                <small>confidence</small>
              </div>
            </div>

            <div className="diagnosis-meta-grid">
              <div>
                <span>State</span>
                <strong>{formatState(diagnosis.state)}</strong>
              </div>
              <div>
                <span>Misconception code</span>
                <strong>{diagnosis.primary_misconception?.code ?? "—"}</strong>
              </div>
              <div>
                <span>Topic</span>
                <strong>{diagnosis.primary_misconception?.topic ?? "—"}</strong>
              </div>
              <div>
                <span>Model version</span>
                <strong>{diagnosis.model_version}</strong>
              </div>
            </div>

            <div className="diagnosis-section">
              <h3>Observable evidence</h3>
              {diagnosis.evidence.length > 0 ? (
                <ul className="diagnosis-evidence-list">
                  {diagnosis.evidence.map((item) => (
                    <li key={item.id}>
                      <span>{item.source}</span>
                      <p>{item.text}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No evidence was returned for this diagnosis.</p>
              )}
            </div>

            {diagnosis.alternatives.length > 0 && (
              <div className="diagnosis-section">
                <h3>Alternative possibilities</h3>
                <ul className="diagnosis-alternative-list">
                  {diagnosis.alternatives.map((item) => (
                    <li key={item.id}>
                      <strong>{item.misconception.code}</strong>{" "}
                      {item.misconception.name} —{" "}
                      {formatConfidence(item.confidence)}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="diagnosis-next-action">
              <span>Next action</span>
              <strong>{formatState(diagnosis.next_action)}</strong>
            </div>

            <p className="diagnosis-note">{diagnosis.decision_reason}</p>
          </section>
        )}
      </section>
    );
  }

  return (
    <section className="attempt-card">
      <div className="attempt-form-header">
        <div>
          <p className="section-kicker">Student attempt</p>
          <h2>Submit your reasoning</h2>
          <p>
            Problem: <strong>{problemTitle}</strong>
          </p>
        </div>

        <div className="attempt-privacy-note">
          No real names, emails, phone numbers, or roll numbers.
        </div>
      </div>

      <form className="attempt-form" onSubmit={handleSubmit}>
        <label>
          Final answer
          <textarea
            value={finalAnswer}
            onChange={(event) => setFinalAnswer(event.target.value)}
            placeholder="Write your final answer or approach."
            rows={3}
          />
        </label>

        <label>
          Written reasoning <span className="required-mark">*</span>
          <textarea
            value={writtenReasoning}
            onChange={(event) => setWrittenReasoning(event.target.value)}
            placeholder="Explain why your approach should work. Mention assumptions, base cases, loop conditions, or preconditions."
            rows={5}
          />
        </label>

        <label>
          Source code
          <textarea
            value={sourceCode}
            onChange={(event) => setSourceCode(event.target.value)}
            placeholder={`def solution(...):\n    # write your code here`}
            rows={8}
            className="code-textarea"
          />
        </label>

        <div className="attempt-form-row">
          <label>
            Selected language
            <select
              value={selectedLanguage}
              onChange={(event) => setSelectedLanguage(event.target.value)}
            >
              <option value="python">Python</option>
              <option value="java">Java</option>
              <option value="cpp">C++</option>
              <option value="javascript">JavaScript</option>
            </select>
          </label>

          <label>
            Response time
            <input value={`${responseTimeSeconds}s`} readOnly />
          </label>
        </div>

        <label>
          Optional speech transcript
          <textarea
            value={speechTranscript}
            onChange={(event) => setSpeechTranscript(event.target.value)}
            placeholder="Paste speech transcript here if available. Audio upload is not part of this sprint."
            rows={3}
          />
        </label>

        {error && <div className="attempt-error">{error}</div>}

        <div className="attempt-actions">
          <button className="primary-button" type="submit" disabled={!canSubmit}>
            {submitting ? "Submitting..." : "Submit attempt"}
          </button>

          <p>
            This only saves the attempt. Diagnosis is generated separately after
            submission.
          </p>
        </div>
      </form>
    </section>
  );
}