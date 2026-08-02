import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";

import {
  submitAttempt,
  type AttemptResponse,
} from "../services/attemptApi";
import { createDiagnosisFromAttempt } from "../services/diagnosisApi";
import type { DiagnosisResponse } from "../types/diagnosis";

type AttemptSubmissionFormProps = {
  studentAliasId: string;
  problemId: string;
  problemTitle: string;
  expectedLanguage?: string | null;
  savedAttemptId?: string | null;
  onAttemptSaved?: (attemptId: string) => void;
  onDiagnosisGenerated?: () => void;
};

const LANGUAGE_OPTIONS = [
  { value: "python", label: "Python" },
  { value: "c", label: "C" },
  { value: "cpp", label: "C++" },
  { value: "java", label: "Java" },
  { value: "javascript", label: "JavaScript" },
  { value: "text", label: "Text / no code" },
] as const;

function formatConfidence(value: number) {
  const safeValue = Number.isFinite(value) ? value : 0;
  return `${Math.round(safeValue * 100)}%`;
}

function formatState(value?: string | null) {
  if (!value) {
    return "Not set";
  }

  return value.replaceAll("_", " ");
}

function normalizeLanguage(value?: string | null) {
  const normalized = value?.trim().toLowerCase();

  if (normalized === "python" || normalized === "py") {
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

function getLanguageLabel(value?: string | null) {
  const normalized = normalizeLanguage(value);

  return (
    LANGUAGE_OPTIONS.find((option) => option.value === normalized)?.label ??
    normalized
  );
}

function getCodePlaceholder(language: string) {
  if (language === "python") {
    return `def solution(...):
    # write your code here`;
  }

  if (language === "c") {
    return `#include <stdio.h>

void solution(...) {
    // write your code here
}`;
  }

  if (language === "cpp") {
    return `#include <bits/stdc++.h>
using namespace std;

void solution(...) {
    // write your code here
}`;
  }

  if (language === "java") {
    return `class Solution {
    public void solution(...) {
        // write your code here
    }
}`;
  }

  if (language === "javascript") {
    return `function solution(...) {
  // write your code here
}`;
  }

  return "Code is optional for this problem. Use the final answer and written reasoning fields.";
}

function getStateLabelClass(state?: string | null) {
  const normalized = state?.trim().toLowerCase();

  if (
    normalized === "confident" ||
    normalized === "no_misconception"
  ) {
    return "state-pill state-pill-success";
  }

  if (normalized === "possible") {
    return "state-pill state-pill-warning";
  }

  if (normalized === "insufficient") {
    return "state-pill state-pill-muted";
  }

  return "state-pill";
}

function isNoMisconceptionState(state?: string | null) {
  return state?.trim().toLowerCase() === "no_misconception";
}

function getDiagnosisTitle(diagnosis: DiagnosisResponse) {
  if (isNoMisconceptionState(diagnosis.state)) {
    return "No supported misconception detected";
  }

  if (diagnosis.primary_misconception) {
    return diagnosis.primary_misconception.name;
  }

  return "No confident misconception detected";
}

function getDiagnosisStateLabel(state?: string | null) {
  if (isNoMisconceptionState(state)) {
    return "No misconception";
  }

  return formatState(state);
}

function getNextActionLabel(
  nextAction?: string | null,
  state?: string | null
) {
  if (
    isNoMisconceptionState(state) ||
    nextAction?.trim().toLowerCase() === "no_action"
  ) {
    return "No action required";
  }

  return formatState(nextAction);
}

function normalizeEvidenceSource(value?: string | null) {
  return value?.trim().toLowerCase().replaceAll(" ", "_") ?? "";
}

function getMissingSignalMessage(diagnosis: DiagnosisResponse) {
  const normalizedState = diagnosis.state?.trim().toLowerCase();

  if (
    normalizedState === "confident" ||
    normalizedState === "no_misconception"
  ) {
    return null;
  }

  const evidenceSources = new Set(
    diagnosis.evidence.map((item) => normalizeEvidenceSource(item.source))
  );

  const hasReasoningEvidence = [...evidenceSources].some(
    (source) =>
      source.includes("reasoning") ||
      source.includes("explanation") ||
      source.includes("transcript")
  );

  const hasCodeEvidence = [...evidenceSources].some(
    (source) => source.includes("code") || source.includes("implementation")
  );

  if (!hasReasoningEvidence && !hasCodeEvidence) {
    return "Missing signal: the diagnosis needs clearer step-by-step reasoning or implementation evidence before it can commit to a misconception.";
  }

  if (!hasCodeEvidence) {
    return "Missing signal: the written explanation suggests a possible misconception, but the submitted code does not provide direct implementation evidence.";
  }

  if (!hasReasoningEvidence) {
    return "Missing signal: the code provides a partial signal, but the reasoning does not clearly explain the assumption or decision that caused it.";
  }

  return "Missing signal: the available evidence is mixed or incomplete, so the engine needs one clearer diagnostic signal before increasing confidence.";
}

export default function AttemptSubmissionForm({
  studentAliasId,
  problemId,
  problemTitle,
  expectedLanguage,
  savedAttemptId,
  onAttemptSaved,
  onDiagnosisGenerated,
}: AttemptSubmissionFormProps) {
  const [finalAnswer, setFinalAnswer] = useState("");
  const [writtenReasoning, setWrittenReasoning] = useState("");
  const [sourceCode, setSourceCode] = useState("");
  const [speechTranscript, setSpeechTranscript] = useState("");

  const [selectedLanguage, setSelectedLanguage] = useState(() =>
    normalizeLanguage(expectedLanguage)
  );

  const [startedAt, setStartedAt] = useState(() => Date.now());
  const [elapsedSeconds, setElapsedSeconds] = useState(1);

  const [submitting, setSubmitting] = useState(false);
  const [submittedAttempt, setSubmittedAttempt] =
    useState<AttemptResponse | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  const [diagnosis, setDiagnosis] = useState<DiagnosisResponse | null>(null);
  const [diagnosing, setDiagnosing] = useState(false);
  const [diagnosisError, setDiagnosisError] = useState<string | null>(null);

  useEffect(() => {
    setSelectedLanguage(normalizeLanguage(expectedLanguage));
    setFinalAnswer("");
    setWrittenReasoning("");
    setSourceCode("");
    setSpeechTranscript("");

    setSubmittedAttempt(null);
    setDiagnosis(null);

    setSubmissionError(null);
    setDiagnosisError(null);

    setStartedAt(Date.now());
    setElapsedSeconds(1);
  }, [expectedLanguage, problemId]);

  useEffect(() => {
    if (submittedAttempt || savedAttemptId) {
      return;
    }

    const timer = window.setInterval(() => {
      const seconds = Math.max(
        1,
        Math.round((Date.now() - startedAt) / 1000)
      );

      setElapsedSeconds(seconds);
    }, 1000);

    return () => {
      window.clearInterval(timer);
    };
  }, [startedAt, submittedAttempt, savedAttemptId]);

  const responseTimeSeconds = useMemo(
    () => Math.max(1, elapsedSeconds),
    [elapsedSeconds]
  );

  const activeAttemptId = submittedAttempt?.id ?? savedAttemptId ?? null;

  const hasRequiredReasoning = writtenReasoning.trim().length >= 5;

  const hasSubmissionContent =
    finalAnswer.trim().length > 0 ||
    sourceCode.trim().length > 0 ||
    speechTranscript.trim().length > 0;

  const canSaveAttempt =
    hasRequiredReasoning &&
    hasSubmissionContent &&
    !submitting &&
    !activeAttemptId;

  const missingSignalMessage = diagnosis
    ? getMissingSignalMessage(diagnosis)
    : null;

  const diagnosisIsClear =
    diagnosis !== null && isNoMisconceptionState(diagnosis.state);

  const shouldShowConfidence =
    diagnosis !== null &&
    !diagnosisIsClear &&
    diagnosis.confidence > 0;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setSubmissionError(null);
    setDiagnosisError(null);
    setDiagnosis(null);

    if (!hasRequiredReasoning) {
      setSubmissionError(
        "Written reasoning must contain at least 5 characters."
      );
      return;
    }

    if (!hasSubmissionContent) {
      setSubmissionError(
        "Include at least one of final answer, source code, or speech transcript."
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
        selected_language: selectedLanguage,
        response_time_seconds: responseTimeSeconds,
      });

      setSubmittedAttempt(result);
      onAttemptSaved?.(result.id);
    } catch (error) {
      setSubmissionError(
        error instanceof Error
          ? error.message
          : "Attempt submission failed."
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGenerateDiagnosis() {
    if (!activeAttemptId || diagnosing || diagnosis) {
      return;
    }

    setDiagnosisError(null);

    try {
      setDiagnosing(true);

      const result = await createDiagnosisFromAttempt(activeAttemptId);

      setDiagnosis(result);
      onDiagnosisGenerated?.();
    } catch (error) {
      setDiagnosisError(
        error instanceof Error
          ? error.message
          : "Diagnosis generation failed."
      );
    } finally {
      setDiagnosing(false);
    }
  }

  function handleSubmitAnotherAttempt() {
    setSubmittedAttempt(null);
    setDiagnosis(null);

    setSubmissionError(null);
    setDiagnosisError(null);

    setFinalAnswer("");
    setWrittenReasoning("");
    setSourceCode("");
    setSpeechTranscript("");

    setSelectedLanguage(normalizeLanguage(expectedLanguage));
    setStartedAt(Date.now());
    setElapsedSeconds(1);
  }

  if (activeAttemptId) {
    return (
      <div className="attempt-flow">
        <section className="attempt-saved-card">
          <div className="attempt-saved-header">
            <div>
              <div className="attempt-status-row">
                <span className="state-pill state-pill-success">Saved</span>

                {diagnosis && (
                  <span className="state-pill state-pill-info">
                    Diagnosis generated
                  </span>
                )}
              </div>

              <p className="section-kicker">Attempt saved</p>
              <h2>Your attempt has been recorded.</h2>
              <p>
                The submission is saved. Diagnosis remains a separate action.
              </p>
            </div>
          </div>

          <div className="saved-attempt-grid">
            <div>
              <span>Problem</span>
              <strong>{problemTitle}</strong>
            </div>

            <div>
              <span>Language</span>
              <strong>
                {getLanguageLabel(
                  submittedAttempt?.selected_language ?? selectedLanguage
                )}
              </strong>
            </div>

            <div>
              <span>Response time</span>
              <strong>
                {submittedAttempt?.response_time_seconds ??
                  responseTimeSeconds}
                s
              </strong>
            </div>

            <div>
              <span>Attempt ID</span>
              <strong className="mono-value">{activeAttemptId}</strong>
            </div>
          </div>

          <div className="attempt-actions split-actions">
            {!diagnosis && (
              <button
                className="primary-button"
                type="button"
                onClick={handleGenerateDiagnosis}
                disabled={diagnosing}
              >
                {diagnosing
                  ? "Generating diagnosis..."
                  : "Generate diagnosis"}
              </button>
            )}

            <button
              className="secondary-button"
              type="button"
              onClick={handleSubmitAnotherAttempt}
            >
              New attempt
            </button>
          </div>

          {diagnosisError && (
            <div className="attempt-error" role="alert">
              {diagnosisError}
            </div>
          )}
        </section>

        {diagnosis && (
          <section className="diagnosis-result-card">
            <div className="diagnosis-result-header">
              <div>
                <p className="section-kicker">Diagnosis result</p>

                <h2>{getDiagnosisTitle(diagnosis)}</h2>
              </div>

              {diagnosisIsClear ? (
                <div className="diagnosis-score-card diagnosis-score-card-clear">
                  <strong>Verified</strong>
                  <span>no supported issue</span>
                </div>
              ) : shouldShowConfidence ? (
                <div className="diagnosis-score-card">
                  <strong>{formatConfidence(diagnosis.confidence)}</strong>
                  <span>confidence</span>
                </div>
              ) : null}
            </div>

            <div className="diagnosis-status-row">
              <span className={getStateLabelClass(diagnosis.state)}>
                {getDiagnosisStateLabel(diagnosis.state)}
              </span>

              {diagnosis.primary_misconception && (
                <>
                  <span className="problem-chip">
                    {diagnosis.primary_misconception.code}
                  </span>

                  {diagnosis.primary_misconception.topic && (
                    <span className="problem-chip">
                      {diagnosis.primary_misconception.topic}
                    </span>
                  )}
                </>
              )}

              <span className="problem-chip">{diagnosis.model_version}</span>
            </div>

            <div className="diagnosis-section">
              <h3>Observable evidence</h3>

              {diagnosis.evidence.length > 0 ? (
                <ol className="evidence-list">
                  {diagnosis.evidence.map((item) => (
                    <li className="evidence-row" key={item.id}>
                      <span className="evidence-source">
                        {formatState(item.source)}
                      </span>
                      <p className="evidence-text">{item.text}</p>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="muted-text">
                  No observable evidence was returned.
                </p>
              )}
            </div>

            {missingSignalMessage && (
              <div className="diagnosis-missing-signal">
                <span>Missing signal</span>
                <p>{missingSignalMessage}</p>
              </div>
            )}

            {diagnosis.alternatives.length > 0 && (
              <div className="diagnosis-section">
                <h3>Alternative possibilities</h3>

                <div className="alternative-list">
                  {diagnosis.alternatives.map((item) => (
                    <div className="alternative-item" key={item.id}>
                      <div>
                        <strong>{item.misconception.code}</strong>
                        <span>{item.misconception.name}</span>
                      </div>

                      <strong>{formatConfidence(item.confidence)}</strong>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="diagnosis-next-action">
              <span>Next action</span>
              <strong>
                {getNextActionLabel(
                  diagnosis.next_action,
                  diagnosis.state
                )}
              </strong>
            </div>

            {diagnosisIsClear && (
              <p className="diagnosis-note diagnosis-note-success">
                The submitted reasoning and implementation do not match any
                supported misconception rule for this problem.
              </p>
            )}

            {diagnosis.decision_reason && (
              <p className="diagnosis-note">{diagnosis.decision_reason}</p>
            )}
          </section>
        )}
      </div>
    );
  }

  return (
    <form
      className="attempt-form-redesign"
      onSubmit={handleSubmit}
      noValidate
    >
      <div className="attempt-form-status">
        <span className="state-pill state-pill-muted">Draft</span>
        <span>Your work is not saved yet.</span>
      </div>

      <div className="attempt-form-grid">
        <label className="form-field full-width">
          <span>Final answer</span>

          <textarea
            value={finalAnswer}
            onChange={(event) => setFinalAnswer(event.target.value)}
            placeholder="Write the final answer or high-level approach."
            rows={3}
          />
        </label>

        <label className="form-field full-width">
          <span>
            Written reasoning <strong>*</strong>
          </span>

          <textarea
            value={writtenReasoning}
            onChange={(event) => setWrittenReasoning(event.target.value)}
            placeholder="Explain why your approach should work. Mention assumptions, stopping conditions, loop logic, or preconditions."
            rows={5}
            required
          />
        </label>

        <label className="form-field full-width">
          <span>Source code</span>

          <textarea
            value={sourceCode}
            onChange={(event) => setSourceCode(event.target.value)}
            placeholder={getCodePlaceholder(selectedLanguage)}
            rows={9}
            className="code-textarea"
            spellCheck={false}
          />
        </label>

        <label className="form-field">
          <span>Language</span>

          <select
            value={selectedLanguage}
            onChange={(event) => setSelectedLanguage(event.target.value)}
          >
            {LANGUAGE_OPTIONS.map((option) => (
              <option value={option.value} key={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="form-field">
          <span>Response time</span>

          <input
            value={`${responseTimeSeconds}s`}
            readOnly
            aria-label="Response time"
          />
        </label>

        <label className="form-field full-width">
          <span>Speech transcript optional</span>

          <textarea
            value={speechTranscript}
            onChange={(event) => setSpeechTranscript(event.target.value)}
            placeholder="Paste a speech transcript only if one is available."
            rows={3}
          />
        </label>
      </div>

      {submissionError && (
        <div className="attempt-error" role="alert">
          {submissionError}
        </div>
      )}

      <div className="attempt-submit-row">
        <p>Save the attempt first. Diagnosis is generated separately.</p>

        <button
          className="primary-button"
          type="submit"
          disabled={!canSaveAttempt}
        >
          {submitting ? "Saving attempt..." : "Save attempt"}
        </button>
      </div>
    </form>
  );
}