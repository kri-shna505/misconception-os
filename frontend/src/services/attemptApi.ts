const API_BASE_URL = "http://127.0.0.1:8000/api";

export type SpeechProcessingStatus =
  | "not_provided"
  | "pending"
  | "processing"
  | "completed"
  | "failed";

export type InputModality =
  | "text"
  | "code"
  | "speech"
  | "text_code"
  | "text_speech"
  | "code_speech"
  | "text_code_speech";

export type AttemptCreatePayload = {
  student_alias_id: string;
  problem_id: string;

  final_answer: string | null;
  written_reasoning: string;
  normalized_reasoning: string | null;

  source_code: string | null;

  speech_transcript: string | null;
  speech_audio_reference: string | null;
  speech_audio_retained: boolean;
  speech_processing_status: SpeechProcessingStatus;

  input_modality: InputModality;
  input_language: string;
  detected_language: string | null;

  selected_language: string;
  response_time_seconds: number | null;
};

export type AttemptResponse = {
  id: string;
  student_alias_id: string;
  problem_id: string;

  parent_attempt_id: string | null;
  retry_number: number;

  final_answer: string | null;
  written_reasoning: string;
  normalized_reasoning: string | null;

  source_code: string | null;

  speech_transcript: string | null;
  speech_audio_reference: string | null;
  speech_audio_retained: boolean;
  speech_processing_status: SpeechProcessingStatus;

  input_modality: InputModality;
  input_language: string;
  detected_language: string | null;

  selected_language: string;
  response_time_seconds: number | null;

  created_at: string;
  updated_at: string;
};

type ApiValidationErrorItem = {
  msg?: unknown;
};

type ApiErrorBody = {
  detail?: unknown;
};

function isRecord(
  value: unknown
): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}

function getErrorMessage(
  data: unknown,
  fallback: string
): string {
  if (!isRecord(data)) {
    return fallback;
  }

  const detail = data.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item: ApiValidationErrorItem) =>
        typeof item?.msg === "string" ? item.msg : null
      )
      .filter((message): message is string => Boolean(message));

    if (messages.length > 0) {
      return messages.join(" ");
    }
  }

  return fallback;
}

async function parseJsonResponse(
  response: Response
): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";

  if (!contentType.includes("application/json")) {
    return null;
  }

  return response.json();
}

export async function submitAttempt(
  payload: AttemptCreatePayload
): Promise<AttemptResponse> {
  const response = await fetch(`${API_BASE_URL}/attempts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = (await parseJsonResponse(response)) as
    | AttemptResponse
    | ApiErrorBody
    | null;

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        "Attempt submission failed."
      )
    );
  }

  if (!data || !("id" in data)) {
    throw new Error(
      "Attempt submission succeeded but returned an invalid response."
    );
  }

  return data as AttemptResponse;
}

export async function getAttemptById(
  attemptId: string
): Promise<AttemptResponse> {
  const response = await fetch(
    `${API_BASE_URL}/attempts/${encodeURIComponent(attemptId)}`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    }
  );

  const data = (await parseJsonResponse(response)) as
    | AttemptResponse
    | ApiErrorBody
    | null;

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        "Unable to load the attempt."
      )
    );
  }

  if (!data || !("id" in data)) {
    throw new Error(
      "Attempt lookup succeeded but returned an invalid response."
    );
  }

  return data as AttemptResponse;
}