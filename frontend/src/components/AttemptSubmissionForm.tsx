import { useMemo, useState } from "react";
import type { FormEvent } from "react";

import { submitAttempt } from "../services/attemptApi";
import type { AttemptResponse } from "../services/attemptApi";

type AttemptSubmissionFormProps = {
  studentAliasId: string;
  problemId: string;
  problemTitle: string;
};

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

  const [startedAt] = useState(() => Date.now());
  const [submitting, setSubmitting] = useState(false);
  const [submittedAttempt, setSubmittedAttempt] =
    useState<AttemptResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  if (submittedAttempt) {
    return (
      <section className="attempt-card attempt-success-card">
        <p className="section-kicker">Attempt saved</p>
        <h2>Your submission was recorded.</h2>
        <p>
          This attempt is now stored for diagnosis. The next sprint will connect
          this saved attempt to the misconception diagnosis engine.
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

        <button
          className="primary-button"
          type="button"
          onClick={() => {
            setSubmittedAttempt(null);
            setFinalAnswer("");
            setWrittenReasoning("");
            setSourceCode("");
            setSpeechTranscript("");
          }}
        >
          Submit another attempt
        </button>
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
            This only saves the attempt. Diagnosis will be generated in the next
            sprint.
          </p>
        </div>
      </form>
    </section>
  );
}