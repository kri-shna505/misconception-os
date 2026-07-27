import { apiRequest } from "../api/client";
import type { DiagnosisResponse } from "../types/diagnosis";

export async function createDiagnosisFromAttempt(
  attemptId: string
): Promise<DiagnosisResponse> {
  return apiRequest<DiagnosisResponse>(
    `/diagnoses/from-attempt/${attemptId}`,
    {
      method: "POST",
    }
  );
}