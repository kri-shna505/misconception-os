import {
  apiGet,
  apiPost,
} from "../../api/client";

import type {
  DiagnosticQuestionResponse,
  DiagnosticResponseCreate,
  DiagnosticResponseResult,
  HintDeliveryResponse,
  HintProgressResponse,
  LearningHistoryResponse,
  MisconceptionEvolutionResponse,
  RetryAttemptCreate,
  RetryAttemptResponse,
  RevealedHintListResponse,
} from "./types";

const INTERVENTION_API_PREFIX =
  "/interventions";

function normalizeRequiredId(
  value: string,
  fieldName: string
): string {
  const normalizedValue =
    value.trim();

  if (!normalizedValue) {
    throw new Error(
      `${fieldName} is required.`
    );
  }

  return normalizedValue;
}

function normalizeOptionalId(
  value?: string | null
): string | undefined {
  const normalizedValue =
    value?.trim();

  return normalizedValue
    ? normalizedValue
    : undefined;
}

export async function getHintProgress(
  diagnosisId: string,
  studentAliasId: string,
  signal?: AbortSignal
): Promise<HintProgressResponse> {
  const normalizedDiagnosisId =
    normalizeRequiredId(
      diagnosisId,
      "diagnosisId"
    );

  const normalizedStudentAliasId =
    normalizeRequiredId(
      studentAliasId,
      "studentAliasId"
    );

  return apiGet<HintProgressResponse>(
    `${INTERVENTION_API_PREFIX}/diagnoses/${encodeURIComponent(
      normalizedDiagnosisId
    )}/hints/progress`,
    {
      query: {
        student_alias_id:
          normalizedStudentAliasId,
      },
      signal,
    }
  );
}

export async function revealNextHint(
  diagnosisId: string,
  studentAliasId: string,
  signal?: AbortSignal
): Promise<HintDeliveryResponse> {
  const normalizedDiagnosisId =
    normalizeRequiredId(
      diagnosisId,
      "diagnosisId"
    );

  const normalizedStudentAliasId =
    normalizeRequiredId(
      studentAliasId,
      "studentAliasId"
    );

  return apiPost<
    HintDeliveryResponse,
    Record<string, never>
  >(
    `${INTERVENTION_API_PREFIX}/diagnoses/${encodeURIComponent(
      normalizedDiagnosisId
    )}/hints/next`,
    {},
    {
      query: {
        student_alias_id:
          normalizedStudentAliasId,
      },
      signal,
    }
  );
}

export async function getRevealedHints(
  diagnosisId: string,
  studentAliasId: string,
  signal?: AbortSignal
): Promise<RevealedHintListResponse> {
  const normalizedDiagnosisId =
    normalizeRequiredId(
      diagnosisId,
      "diagnosisId"
    );

  const normalizedStudentAliasId =
    normalizeRequiredId(
      studentAliasId,
      "studentAliasId"
    );

  return apiGet<RevealedHintListResponse>(
    `${INTERVENTION_API_PREFIX}/diagnoses/${encodeURIComponent(
      normalizedDiagnosisId
    )}/hints`,
    {
      query: {
        student_alias_id:
          normalizedStudentAliasId,
      },
      signal,
    }
  );
}

export async function getNextDiagnosticQuestion(
  diagnosisId: string,
  studentAliasId: string,
  signal?: AbortSignal
): Promise<DiagnosticQuestionResponse> {
  const normalizedDiagnosisId =
    normalizeRequiredId(
      diagnosisId,
      "diagnosisId"
    );

  const normalizedStudentAliasId =
    normalizeRequiredId(
      studentAliasId,
      "studentAliasId"
    );

  return apiGet<DiagnosticQuestionResponse>(
    `${INTERVENTION_API_PREFIX}/diagnoses/${encodeURIComponent(
      normalizedDiagnosisId
    )}/question`,
    {
      query: {
        student_alias_id:
          normalizedStudentAliasId,
      },
      signal,
    }
  );
}

export async function submitDiagnosticResponse(
  diagnosisId: string,
  diagnosticQuestionId: string,
  studentAliasId: string,
  payload: DiagnosticResponseCreate,
  signal?: AbortSignal
): Promise<DiagnosticResponseResult> {
  const normalizedDiagnosisId =
    normalizeRequiredId(
      diagnosisId,
      "diagnosisId"
    );

  const normalizedQuestionId =
    normalizeRequiredId(
      diagnosticQuestionId,
      "diagnosticQuestionId"
    );

  const normalizedStudentAliasId =
    normalizeRequiredId(
      studentAliasId,
      "studentAliasId"
    );

  const normalizedResponseText =
    payload.response_text.trim();

  if (!normalizedResponseText) {
    throw new Error(
      "Diagnostic response must not be blank."
    );
  }

  return apiPost<
    DiagnosticResponseResult,
    DiagnosticResponseCreate
  >(
    `${INTERVENTION_API_PREFIX}/diagnoses/${encodeURIComponent(
      normalizedDiagnosisId
    )}/questions/${encodeURIComponent(
      normalizedQuestionId
    )}/responses`,
    {
      response_text:
        normalizedResponseText,
    },
    {
      query: {
        student_alias_id:
          normalizedStudentAliasId,
      },
      signal,
    }
  );
}

export async function getDiagnosticResponse(
  diagnosticResponseId: string,
  studentAliasId: string,
  signal?: AbortSignal
): Promise<DiagnosticResponseResult> {
  const normalizedResponseId =
    normalizeRequiredId(
      diagnosticResponseId,
      "diagnosticResponseId"
    );

  const normalizedStudentAliasId =
    normalizeRequiredId(
      studentAliasId,
      "studentAliasId"
    );

  return apiGet<DiagnosticResponseResult>(
    `${INTERVENTION_API_PREFIX}/diagnostic-responses/${encodeURIComponent(
      normalizedResponseId
    )}`,
    {
      query: {
        student_alias_id:
          normalizedStudentAliasId,
      },
      signal,
    }
  );
}

export async function markDiagnosticResponseEvaluated(
  diagnosticResponseId: string,
  studentAliasId: string,
  signal?: AbortSignal
): Promise<DiagnosticResponseResult> {
  const normalizedResponseId =
    normalizeRequiredId(
      diagnosticResponseId,
      "diagnosticResponseId"
    );

  const normalizedStudentAliasId =
    normalizeRequiredId(
      studentAliasId,
      "studentAliasId"
    );

  return apiPost<
    DiagnosticResponseResult,
    Record<string, never>
  >(
    `${INTERVENTION_API_PREFIX}/diagnostic-responses/${encodeURIComponent(
      normalizedResponseId
    )}/evaluated`,
    {},
    {
      query: {
        student_alias_id:
          normalizedStudentAliasId,
      },
      signal,
    }
  );
}

export async function createRetryAttempt(
  parentAttemptId: string,
  studentAliasId: string,
  payload: RetryAttemptCreate,
  signal?: AbortSignal
): Promise<RetryAttemptResponse> {
  const normalizedParentAttemptId =
    normalizeRequiredId(
      parentAttemptId,
      "parentAttemptId"
    );

  const normalizedStudentAliasId =
    normalizeRequiredId(
      studentAliasId,
      "studentAliasId"
    );

  const normalizedReasoning =
    payload.written_reasoning.trim();

  const normalizedLanguage =
    payload.selected_language
      .trim()
      .toLowerCase();

  const normalizedInputLanguage =
    payload.input_language
      .trim()
      .toLowerCase();

  const normalizedInputModality =
    payload.input_modality;

  const normalizedFinalAnswer =
    normalizeOptionalId(
      payload.final_answer
    ) ?? null;

  const normalizedSourceCode =
    normalizeOptionalId(
      payload.source_code
    ) ?? null;

  const normalizedSpeechTranscript =
    normalizeOptionalId(
      payload.speech_transcript
    ) ?? null;

  if (!normalizedReasoning) {
    throw new Error(
      "Retry written reasoning must not be blank."
    );
  }

  if (!normalizedLanguage) {
    throw new Error(
      "Retry selected language is required."
    );
  }

  if (!normalizedInputLanguage) {
    throw new Error(
      "Retry input language is required."
    );
  }

  if (!normalizedInputModality) {
    throw new Error(
      "Retry input modality is required."
    );
  }

  /*
   * Sprint 10 consistency protection.
   *
   * A speech transcript must never be sent with a modality
   * that does not advertise speech. The backend intentionally
   * rejects that inconsistent payload.
   */
  if (
    normalizedSpeechTranscript &&
    !normalizedInputModality.includes("speech")
  ) {
    throw new Error(
      "Retry input modality must include speech when a speech transcript is provided."
    );
  }

  return apiPost<
    RetryAttemptResponse,
    RetryAttemptCreate
  >(
    `${INTERVENTION_API_PREFIX}/attempts/${encodeURIComponent(
      normalizedParentAttemptId
    )}/retry`,
    {
      final_answer:
        normalizedFinalAnswer,

      written_reasoning:
        normalizedReasoning,

      normalized_reasoning:
        payload.normalized_reasoning ??
        null,

      source_code:
        normalizedSourceCode,

      speech_transcript:
        normalizedSpeechTranscript,

      speech_audio_reference:
        normalizeOptionalId(
          payload.speech_audio_reference
        ) ?? null,

      speech_audio_retained:
        payload.speech_audio_retained ??
        false,

      speech_processing_status:
        payload.speech_processing_status ??
        (
          normalizedSpeechTranscript
            ? "completed"
            : "not_provided"
        ),

      selected_language:
        normalizedLanguage,

      response_time_seconds:
        payload.response_time_seconds ??
        null,

      input_language:
        normalizedInputLanguage,

      input_modality:
        normalizedInputModality,

      detected_language:
        normalizeOptionalId(
          payload.detected_language
        ) ?? null,
    },
    {
      query: {
        student_alias_id:
          normalizedStudentAliasId,
      },
      signal,
    }
  );
}

export async function recordMisconceptionEvolution(
  diagnosisId: string,
  signal?: AbortSignal
): Promise<MisconceptionEvolutionResponse> {
  const normalizedDiagnosisId =
    normalizeRequiredId(
      diagnosisId,
      "diagnosisId"
    );

  return apiPost<
    MisconceptionEvolutionResponse,
    Record<string, never>
  >(
    `${INTERVENTION_API_PREFIX}/diagnoses/${encodeURIComponent(
      normalizedDiagnosisId
    )}/evolution`,
    {},
    {
      signal,
    }
  );
}

export async function getLearningHistory(
  studentAliasId: string,
  problemId?: string | null,
  signal?: AbortSignal
): Promise<LearningHistoryResponse> {
  const normalizedStudentAliasId =
    normalizeRequiredId(
      studentAliasId,
      "studentAliasId"
    );

  return apiGet<LearningHistoryResponse>(
    `${INTERVENTION_API_PREFIX}/students/${encodeURIComponent(
      normalizedStudentAliasId
    )}/learning-history`,
    {
      query: {
        problem_id:
          normalizeOptionalId(
            problemId
          ),
      },
      signal,
    }
  );
}

export const interventionApi = {
  getHintProgress,
  revealNextHint,
  getRevealedHints,
  getNextDiagnosticQuestion,
  submitDiagnosticResponse,
  getDiagnosticResponse,
  markDiagnosticResponseEvaluated,
  createRetryAttempt,
  recordMisconceptionEvolution,
  getLearningHistory,
} as const;