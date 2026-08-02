export type DiagnosisState =
  | "confident"
  | "possible"
  | "insufficient"
  | "no_misconception";

export type EvidenceSource =
  | "problem"
  | "written_reasoning"
  | "source_code"
  | "speech_transcript"
  | "rule_engine";

export type EvidenceStrength =
  | "strong"
  | "medium"
  | "weak";

export type DiagnosisNextAction =
  | "show_hint"
  | "ask_diagnostic_question"
  | "ask_clarification"
  | "no_action";

export type MisconceptionSummary = {
  id: string;
  code: string;
  name: string;
  topic: string | null;
};

export type DiagnosisEvidenceMetadata = Record<
  string,
  unknown
>;

export type DiagnosisEvidence = {
  id: string | null;
  diagnosis_id: string | null;
  source: EvidenceSource;
  strength: EvidenceStrength;
  text: string;
  sort_order: number;
  metadata: DiagnosisEvidenceMetadata;
};

export type DiagnosisAlternative = {
  id: string | null;
  diagnosis_id: string | null;
  misconception: MisconceptionSummary;
  confidence: number;
  reason: string | null;
};

export type DiagnosisResponse = {
  id: string;
  attempt_id: string;
  state: DiagnosisState;
  confidence: number;
  primary_misconception: MisconceptionSummary | null;
  evidence: DiagnosisEvidence[];
  alternatives: DiagnosisAlternative[];
  model_version: string;
  decision_reason: string | null;
  next_action: DiagnosisNextAction;
  created_at: string;
};

export type DiagnosisSummary = {
  id: string;
  attempt_id: string;
  state: DiagnosisState;
  confidence: number;
  primary_misconception: MisconceptionSummary | null;
  model_version: string;
  decision_reason: string | null;
  next_action: DiagnosisNextAction;
  created_at: string;
};

export function isMisconceptionDiagnosis(
  diagnosis: DiagnosisResponse | DiagnosisSummary
): boolean {
  return (
    diagnosis.state === "confident" ||
    diagnosis.state === "possible"
  );
}

export function isVerifiedDiagnosis(
  diagnosis: DiagnosisResponse | DiagnosisSummary
): boolean {
  return diagnosis.state === "no_misconception";
}

export function requiresTeacherReview(
  diagnosis: DiagnosisResponse | DiagnosisSummary
): boolean {
  return (
    diagnosis.state === "possible" ||
    diagnosis.state === "insufficient"
  );
}