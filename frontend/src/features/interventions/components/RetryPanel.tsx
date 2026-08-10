import {
  type FormEvent,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  createRetryAttempt,
} from "../api";

import type {
  RetryAttemptResponse,
} from "../types";


type RetryPanelProps = {
  parentAttemptId: string;
  studentAliasId: string;

  defaultLanguage?: string | null;

  initialFinalAnswer?: string | null;
  initialWrittenReasoning?: string | null;
  initialSourceCode?: string | null;
  initialSpeechTranscript?: string | null;

  onRetryCreated?: (
    retry: RetryAttemptResponse
  ) => void;
};


const LANGUAGE_OPTIONS = [
  {
    value: "python",
    label: "Python",
  },
  {
    value: "c",
    label: "C",
  },
  {
    value: "cpp",
    label: "C++",
  },
  {
    value: "java",
    label: "Java",
  },
  {
    value: "javascript",
    label: "JavaScript",
  },
  {
    value: "text",
    label: "Text / no code",
  },
] as const;


function normalizeLanguage(
  value?: string | null
): string {
  const normalized =
    value?.trim().toLowerCase();

  if (
    normalized === "python" ||
    normalized === "py"
  ) {
    return "python";
  }

  if (normalized === "c") {
    return "c";
  }

  if (
    normalized === "cpp" ||
    normalized === "c++" ||
    normalized === "cplusplus"
  ) {
    return "cpp";
  }

  if (normalized === "java") {
    return "java";
  }

  if (
    normalized === "javascript" ||
    normalized === "js" ||
    normalized === "node"
  ) {
    return "javascript";
  }

  if (
    normalized === "text" ||
    normalized === "none" ||
    normalized === "no code" ||
    normalized === "no-code"
  ) {
    return "text";
  }

  return "python";
}


function getCodePlaceholder(
  language: string
): string {
  if (language === "python") {
    return `def solution(...):
    # revise your code here`;
  }

  if (language === "c") {
    return `#include <stdio.h>

void solution(...) {
    // revise your code here
}`;
  }

  if (language === "cpp") {
    return `#include <bits/stdc++.h>
using namespace std;

void solution(...) {
    // revise your code here
}`;
  }

  if (language === "java") {
    return `class Solution {
    public void solution(...) {
        // revise your code here
    }
}`;
  }

  if (language === "javascript") {
    return `function solution(...) {
  // revise your code here
}`;
  }

  return (
    "Code is optional. Use the final answer and " +
    "written reasoning fields."
  );
}


function normalizeErrorMessage(
  error: unknown,
  fallback: string
): string {
  return error instanceof Error
    ? error.message
    : fallback;
}


export default function RetryPanel({
  parentAttemptId,
  studentAliasId,
  defaultLanguage,
  initialFinalAnswer,
  initialWrittenReasoning,
  initialSourceCode,
  initialSpeechTranscript,
  onRetryCreated,
}: RetryPanelProps) {
  const [expanded, setExpanded] =
    useState(false);

  const [finalAnswer, setFinalAnswer] =
    useState(
      initialFinalAnswer ?? ""
    );

  const [
    writtenReasoning,
    setWrittenReasoning,
  ] = useState(
    initialWrittenReasoning ?? ""
  );

  const [sourceCode, setSourceCode] =
    useState(
      initialSourceCode ?? ""
    );

  const [
    speechTranscript,
    setSpeechTranscript,
  ] = useState(
    initialSpeechTranscript ?? ""
  );

  const [
    selectedLanguage,
    setSelectedLanguage,
  ] = useState(
    normalizeLanguage(
      defaultLanguage
    )
  );

  const [startedAt, setStartedAt] =
    useState(() => Date.now());

  const [
    elapsedSeconds,
    setElapsedSeconds,
  ] = useState(1);

  const [submitting, setSubmitting] =
    useState(false);

  const [
    createdRetry,
    setCreatedRetry,
  ] = useState<RetryAttemptResponse | null>(
    null
  );

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    setFinalAnswer(
      initialFinalAnswer ?? ""
    );

    setWrittenReasoning(
      initialWrittenReasoning ?? ""
    );

    setSourceCode(
      initialSourceCode ?? ""
    );

    setSpeechTranscript(
      initialSpeechTranscript ?? ""
    );

    setSelectedLanguage(
      normalizeLanguage(
        defaultLanguage
      )
    );

    setExpanded(false);
    setCreatedRetry(null);
    setError(null);
    setStartedAt(Date.now());
    setElapsedSeconds(1);
  }, [
    defaultLanguage,
    initialFinalAnswer,
    initialSourceCode,
    initialSpeechTranscript,
    initialWrittenReasoning,
    parentAttemptId,
  ]);

  useEffect(() => {
    if (
      !expanded ||
      createdRetry
    ) {
      return;
    }

    const timer =
      window.setInterval(
        () => {
          setElapsedSeconds(
            Math.max(
              1,
              Math.round(
                (
                  Date.now() -
                  startedAt
                ) / 1000
              )
            )
          );
        },
        1000
      );

    return () => {
      window.clearInterval(
        timer
      );
    };
  }, [
    createdRetry,
    expanded,
    startedAt,
  ]);

  const responseTimeSeconds =
    useMemo(
      () =>
        Math.max(
          1,
          elapsedSeconds
        ),
      [elapsedSeconds]
    );

  const normalizedReasoning =
    writtenReasoning.trim();

  const hasRequiredReasoning =
    normalizedReasoning.length >= 5;

  const hasSubmissionContent =
    finalAnswer.trim().length > 0 ||
    sourceCode.trim().length > 0 ||
    speechTranscript.trim().length > 0;

  const canSubmit =
    hasRequiredReasoning &&
    hasSubmissionContent &&
    !submitting &&
    !createdRetry;

  function handleOpenRetry() {
    setExpanded(true);
    setError(null);
    setStartedAt(Date.now());
    setElapsedSeconds(1);
  }

  function handleCancelRetry() {
    if (submitting) {
      return;
    }

    setExpanded(false);
    setError(null);
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (!canSubmit) {
      if (!hasRequiredReasoning) {
        setError(
          "Written reasoning must contain at least 5 characters."
        );

        return;
      }

      if (!hasSubmissionContent) {
        setError(
          "Include at least one of final answer, source code, or speech transcript."
        );

        return;
      }

      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const result =
        await createRetryAttempt(
          parentAttemptId,
          studentAliasId,
          {
            final_answer:
              finalAnswer.trim()
                ? finalAnswer.trim()
                : null,

            written_reasoning:
              normalizedReasoning,

            source_code:
              sourceCode.trim()
                ? sourceCode.trim()
                : null,

            speech_transcript:
              speechTranscript.trim()
                ? speechTranscript.trim()
                : null,

            selected_language:
              selectedLanguage,

            response_time_seconds:
              responseTimeSeconds,
          }
        );

      setCreatedRetry(result);

      onRetryCreated?.(
        result
      );
    } catch (submitError) {
      setError(
        normalizeErrorMessage(
          submitError,
          "Unable to create the retry attempt."
        )
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (createdRetry) {
    return (
      <section
        className="intervention-card retry-panel"
        aria-labelledby="retry-created-title"
      >
        <div className="intervention-card-header">
          <div>
            <p className="section-kicker">
              Retry attempt
            </p>

            <h3 id="retry-created-title">
              Retry saved
            </h3>

            <p>
              Your revised submission is
              linked to the previous
              attempt and is ready for a
              new diagnosis.
            </p>
          </div>

          <span className="state-pill state-pill-success">
            Retry {createdRetry.retry_number}
          </span>
        </div>

        <div className="saved-attempt-grid">
          <div>
            <span>Retry attempt ID</span>
            <strong className="mono-value">
              {createdRetry.id}
            </strong>
          </div>

          <div>
            <span>Parent attempt ID</span>
            <strong className="mono-value">
              {
                createdRetry.parent_attempt_id
              }
            </strong>
          </div>

          <div>
            <span>Language</span>
            <strong>
              {
                createdRetry.selected_language
              }
            </strong>
          </div>

          <div>
            <span>Response time</span>
            <strong>
              {
                createdRetry.response_time_seconds ??
                0
              }
              s
            </strong>
          </div>
        </div>

        <div className="intervention-empty-state">
          <strong>
            Next step
          </strong>

          <p>
            Generate a diagnosis for this
            retry attempt, then record the
            misconception evolution.
          </p>
        </div>
      </section>
    );
  }

  if (!expanded) {
    return (
      <section
        className="intervention-card retry-panel"
        aria-labelledby="retry-panel-title"
      >
        <div className="intervention-card-header">
          <div>
            <p className="section-kicker">
              Learning retry
            </p>

            <h3 id="retry-panel-title">
              Try the problem again
            </h3>

            <p>
              Use the diagnosis, hint, or
              diagnostic question to revise
              your reasoning and submit a
              linked retry.
            </p>
          </div>

          <button
            className="secondary-button"
            type="button"
            onClick={
              handleOpenRetry
            }
          >
            Start retry
          </button>
        </div>
      </section>
    );
  }

  return (
    <section
      className="intervention-card retry-panel"
      aria-labelledby="retry-form-title"
    >
      <div className="intervention-card-header">
        <div>
          <p className="section-kicker">
            Learning retry
          </p>

          <h3 id="retry-form-title">
            Revise your attempt
          </h3>

          <p>
            Explain what you changed and
            why. The retry will remain
            linked to the previous attempt.
          </p>
        </div>

        <span className="state-pill state-pill-info">
          Linked retry
        </span>
      </div>

      <form
        className="attempt-form-redesign retry-attempt-form"
        onSubmit={handleSubmit}
        noValidate
      >
        <div className="attempt-form-grid">
          <label className="form-field full-width">
            <span>
              Revised final answer
            </span>

            <textarea
              value={finalAnswer}
              onChange={(event) =>
                setFinalAnswer(
                  event.target.value
                )
              }
              placeholder="Write your revised answer or approach."
              rows={3}
              disabled={submitting}
            />
          </label>

          <label className="form-field full-width">
            <span>
              Revised reasoning{" "}
              <strong>*</strong>
            </span>

            <textarea
              value={writtenReasoning}
              onChange={(event) =>
                setWrittenReasoning(
                  event.target.value
                )
              }
              placeholder="Explain what you changed after reviewing the diagnosis or hint."
              rows={5}
              required
              disabled={submitting}
            />
          </label>

          <label className="form-field full-width">
            <span>
              Revised source code
            </span>

            <textarea
              value={sourceCode}
              onChange={(event) =>
                setSourceCode(
                  event.target.value
                )
              }
              placeholder={
                getCodePlaceholder(
                  selectedLanguage
                )
              }
              rows={9}
              className="code-textarea"
              spellCheck={false}
              disabled={submitting}
            />
          </label>

          <label className="form-field">
            <span>Language</span>

            <select
              value={selectedLanguage}
              onChange={(event) =>
                setSelectedLanguage(
                  event.target.value
                )
              }
              disabled={submitting}
            >
              {LANGUAGE_OPTIONS.map(
                (option) => (
                  <option
                    value={option.value}
                    key={option.value}
                  >
                    {option.label}
                  </option>
                )
              )}
            </select>
          </label>

          <label className="form-field">
            <span>Response time</span>

            <input
              value={`${responseTimeSeconds}s`}
              readOnly
              aria-label="Retry response time"
            />
          </label>

          <label className="form-field full-width">
            <span>
              Speech transcript optional
            </span>

            <textarea
              value={speechTranscript}
              onChange={(event) =>
                setSpeechTranscript(
                  event.target.value
                )
              }
              placeholder="Paste a revised speech transcript only if one is available."
              rows={3}
              disabled={submitting}
            />
          </label>
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
          <button
            className="secondary-button"
            type="button"
            onClick={
              handleCancelRetry
            }
            disabled={submitting}
          >
            Cancel
          </button>

          <button
            className="primary-button"
            type="submit"
            disabled={!canSubmit}
          >
            {submitting
              ? "Saving retry..."
              : "Save retry attempt"}
          </button>
        </div>
      </form>
    </section>
  );
}