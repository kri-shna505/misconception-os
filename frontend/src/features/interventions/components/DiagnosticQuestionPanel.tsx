import {
  type FormEvent,
  useEffect,
  useState,
} from "react";

import {
  getNextDiagnosticQuestion,
  submitDiagnosticResponse,
} from "../api";

import type {
  DiagnosticQuestionResponse,
  DiagnosticResponseResult,
} from "../types";


type DiagnosticQuestionPanelProps = {
  diagnosisId: string;
  studentAliasId: string;

  misconceptionCode?: string | null;
  misconceptionName?: string | null;

  onResponseSubmitted?: (
    response: DiagnosticResponseResult
  ) => void;
};


function normalizeErrorMessage(
  error: unknown,
  fallback: string
): string {
  return error instanceof Error
    ? error.message
    : fallback;
}


export default function DiagnosticQuestionPanel({
  diagnosisId,
  studentAliasId,
  misconceptionCode,
  misconceptionName,
  onResponseSubmitted,
}: DiagnosticQuestionPanelProps) {
  const [question, setQuestion] =
    useState<DiagnosticQuestionResponse | null>(
      null
    );

  const [responseText, setResponseText] =
    useState("");

  const [submittedResponse, setSubmittedResponse] =
    useState<DiagnosticResponseResult | null>(
      null
    );

  const [loading, setLoading] =
    useState(true);

  const [submitting, setSubmitting] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    const controller =
      new AbortController();

    async function loadQuestion() {
      try {
        setLoading(true);
        setError(null);
        setQuestion(null);
        setSubmittedResponse(null);
        setResponseText("");

        const result =
          await getNextDiagnosticQuestion(
            diagnosisId,
            studentAliasId,
            controller.signal
          );

        setQuestion(result);
      } catch (loadError) {
        if (
          loadError instanceof DOMException &&
          loadError.name === "AbortError"
        ) {
          return;
        }

        setError(
          normalizeErrorMessage(
            loadError,
            "Unable to load a diagnostic question."
          )
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadQuestion();

    return () => {
      controller.abort();
    };
  }, [
    diagnosisId,
    studentAliasId,
  ]);

  const normalizedResponseText =
    responseText.trim();

  const canSubmit =
    Boolean(question) &&
    normalizedResponseText.length > 0 &&
    !submitting &&
    !submittedResponse;

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (
      !question ||
      !canSubmit
    ) {
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const result =
        await submitDiagnosticResponse(
          diagnosisId,
          question.id,
          studentAliasId,
          {
            response_text:
              normalizedResponseText,
          }
        );

      setSubmittedResponse(result);

      onResponseSubmitted?.(
        result
      );
    } catch (submitError) {
      setError(
        normalizeErrorMessage(
          submitError,
          "Unable to submit the diagnostic response."
        )
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <section
        className="intervention-card diagnostic-question-panel"
        aria-busy="true"
      >
        <p className="section-kicker">
          Diagnostic follow-up
        </p>

        <h3>
          Loading diagnostic question...
        </h3>
      </section>
    );
  }

  if (
    error &&
    !question &&
    !submittedResponse
  ) {
    return (
      <section
        className="intervention-card diagnostic-question-panel"
        aria-labelledby="diagnostic-question-error-title"
      >
        <p className="section-kicker">
          Diagnostic follow-up
        </p>

        <h3 id="diagnostic-question-error-title">
          Question unavailable
        </h3>

        <div
          className="attempt-error"
          role="alert"
        >
          {error}
        </div>
      </section>
    );
  }

  if (submittedResponse) {
    return (
      <section
        className="intervention-card diagnostic-question-panel"
        aria-labelledby="diagnostic-question-complete-title"
      >
        <div className="intervention-card-header">
          <div>
            <p className="section-kicker">
              Diagnostic follow-up
            </p>

            <h3 id="diagnostic-question-complete-title">
              Response submitted
            </h3>

            <p>
              Your answer has been saved for
              diagnosis re-evaluation.
            </p>
          </div>

          <span className="state-pill state-pill-success">
            Submitted
          </span>
        </div>

        {(
          misconceptionCode ||
          misconceptionName
        ) && (
          <div className="hint-context-row">
            {misconceptionCode && (
              <span className="problem-chip">
                {misconceptionCode}
              </span>
            )}

            {misconceptionName && (
              <strong>
                {misconceptionName}
              </strong>
            )}
          </div>
        )}

        {question && (
          <div className="diagnostic-question-summary">
            <span>Question</span>
            <p>
              {question.question_text}
            </p>
          </div>
        )}

        <div className="diagnostic-response-summary">
          <span>Your response</span>
          <p>
            {submittedResponse.response_text}
          </p>
        </div>

        <div className="intervention-empty-state">
          <strong>
            Evaluation pending
          </strong>

          <p>
            The response is stored. The system
            can now use it as additional evidence
            during re-evaluation.
          </p>
        </div>
      </section>
    );
  }

  if (!question) {
    return (
      <section
        className="intervention-card diagnostic-question-panel"
      >
        <p className="section-kicker">
          Diagnostic follow-up
        </p>

        <h3>
          No diagnostic question available
        </h3>

        <p className="muted-text">
          No active unanswered question is
          configured for this diagnosis.
        </p>
      </section>
    );
  }

  return (
    <section
      className="intervention-card diagnostic-question-panel"
      aria-labelledby="diagnostic-question-title"
    >
      <div className="intervention-card-header">
        <div>
          <p className="section-kicker">
            Diagnostic follow-up
          </p>

          <h3 id="diagnostic-question-title">
            Explain your thinking
          </h3>

          <p>
            This question helps the system
            distinguish between similar
            misconception signals.
          </p>
        </div>

        <span className="state-pill state-pill-warning">
          Clarification needed
        </span>
      </div>

      {(
        misconceptionCode ||
        misconceptionName
      ) && (
        <div className="hint-context-row">
          {misconceptionCode && (
            <span className="problem-chip">
              {misconceptionCode}
            </span>
          )}

          {misconceptionName && (
            <strong>
              {misconceptionName}
            </strong>
          )}
        </div>
      )}

      <div className="diagnostic-question-prompt">
        <span>Question</span>

        <p>
          {question.question_text}
        </p>
      </div>

      <form
        className="diagnostic-question-form"
        onSubmit={handleSubmit}
        noValidate
      >
        <label className="form-field full-width">
          <span>
            Your explanation <strong>*</strong>
          </span>

          <textarea
            value={responseText}
            onChange={(event) =>
              setResponseText(
                event.target.value
              )
            }
            placeholder="Answer in your own words. Explain the assumption, rule, or step that supports your reasoning."
            rows={5}
            required
            disabled={submitting}
          />
        </label>

        <div className="diagnostic-response-guidance">
          <strong>
            What makes a useful response?
          </strong>

          <p>
            State what you expect to happen,
            why you expect it, and which part
            of the algorithm or memory model
            supports that expectation.
          </p>
        </div>

        {error && (
          <div
            className="attempt-error"
            role="alert"
          >
            {error}
          </div>
        )}

        <div className="intervention-actions">
          <div>
            <strong>
              Additional evidence
            </strong>

            <p>
              Your answer will be linked to
              this diagnosis and attempt.
            </p>
          </div>

          <button
            className="primary-button"
            type="submit"
            disabled={!canSubmit}
          >
            {submitting
              ? "Submitting response..."
              : "Submit response"}
          </button>
        </div>
      </form>
    </section>
  );
}