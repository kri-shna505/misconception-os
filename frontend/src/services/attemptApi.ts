const API_BASE_URL = "http://127.0.0.1:8000/api";

export type AttemptCreatePayload = {
  student_alias_id: string;
  problem_id: string;
  final_answer: string;
  written_reasoning: string;
  source_code: string | null;
  speech_transcript: string | null;
  selected_language: string;
  response_time_seconds: number | null;
};

export type AttemptResponse = {
  id: string;
  student_alias_id: string;
  problem_id: string;
  final_answer: string | null;
  written_reasoning: string;
  source_code: string | null;
  speech_transcript: string | null;
  selected_language: string;
  response_time_seconds: number | null;
  created_at: string;
};

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

  const data = await response.json();

  if (!response.ok) {
    const detail =
      typeof data?.detail === "string"
        ? data.detail
        : Array.isArray(data?.detail)
          ? data.detail.map((item: any) => item.msg).join(" ")
          : "Attempt submission failed.";

    throw new Error(detail);
  }

  return data;
}