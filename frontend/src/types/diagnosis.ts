export type DiagnosisState = "confident" | "possible" | "insufficient";

export type EvidenceSource =
  | "problem"
  | "written_reasoning"
  | "source_code"
  | "speech_transcript";

export type MisconceptionSummary = {
  id: string;
  code: string;
  name: string;
  topic: string;
};

export type DiagnosisEvidence = {
  id: string;
  diagnosis_id: string;
  source: EvidenceSource | string;
  strength: string;
  text: string;
  sort_order: number;
  metadata: Record<string, unknown>;
};

export type DiagnosisAlternative = {
  id: string;
  diagnosis_id: string;
  misconception: MisconceptionSummary;
  confidence: number;
  reason: string;
};

export type DiagnosisResponse = {
  id: string;
  attempt_id: string;
  state: DiagnosisState | string;
  confidence: number;
  primary_misconception: MisconceptionSummary | null;
  evidence: DiagnosisEvidence[];
  alternatives: DiagnosisAlternative[];
  model_version: string;
  decision_reason: string;
  next_action: string;
  created_at: string;
};