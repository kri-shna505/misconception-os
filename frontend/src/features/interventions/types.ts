import type {
  DiagnosisState,
} from "../../types/diagnosis";


export type MisconceptionEvolutionState =
  | "newly_detected"
  | "repeated"
  | "improving"
  | "corrected"
  | "replaced"
  | "uncertain";


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


export type HintTemplateSummary = {
  id: string;
  misconception_id: string;
  level: 1 | 2 | 3;
  hint_text: string;
  active: boolean;
};


export type HintProgressResponse = {
  diagnosis_id: string;
  attempt_id: string;
  student_alias_id: string;
  misconception_id: string;

  revealed_levels: number[];
  next_level: number | null;
  maximum_level: number;
  completed: boolean;
};


export type HintDeliveryResponse = {
  hint_event_id: string;
  diagnosis_id: string;
  attempt_id: string;
  student_alias_id: string;

  hint_template_id: string;
  misconception_id: string;

  level: 1 | 2 | 3;
  hint_text: string;

  is_final_level: boolean;
  remaining_levels: number;

  created_at: string;
};


export type RevealedHintListResponse = {
  diagnosis_id: string;
  items: HintDeliveryResponse[];
  total_items: number;
};


export type DiagnosticQuestionResponse = {
  id: string;
  diagnosis_id: string;
  attempt_id: string;
  student_alias_id: string;

  misconception_id: string;
  competing_misconception_id: string | null;

  question_text: string;
  created_at: string;
};


export type DiagnosticResponseCreate = {
  response_text: string;
};


export type DiagnosticResponseResult = {
  id: string;
  student_alias_id: string;
  attempt_id: string;
  diagnosis_id: string;
  diagnostic_question_id: string;

  response_text: string;

  evaluated: boolean;
  evaluated_at: string | null;

  created_at: string;
  updated_at: string;
};


export type DiagnosticReevaluationResponse = {
  diagnostic_response: DiagnosticResponseResult;

  original_diagnosis_id: string;
  resulting_diagnosis_id: string | null;

  previous_state: DiagnosisState;
  resulting_state: DiagnosisState | null;

  reevaluated: boolean;
  message: string;
};


export type RetryAttemptCreate = {
  final_answer?: string | null;
  written_reasoning: string;
  normalized_reasoning?: string | null;

  source_code?: string | null;

  speech_transcript?: string | null;
  speech_audio_reference?: string | null;
  speech_audio_retained?: boolean;
  speech_processing_status?: SpeechProcessingStatus;

  input_modality: InputModality;
  input_language: string;
  detected_language?: string | null;

  selected_language: string;
  response_time_seconds?: number | null;
};


export type RetryAttemptResponse = {
  id: string;
  student_alias_id: string;
  problem_id: string;

  parent_attempt_id: string;
  retry_number: number;

  final_answer?: string | null;
  written_reasoning?: string;
  normalized_reasoning?: string | null;

  source_code?: string | null;

  speech_transcript?: string | null;
  speech_audio_reference?: string | null;
  speech_audio_retained?: boolean;
  speech_processing_status?: SpeechProcessingStatus;

  input_modality?: InputModality;
  input_language?: string;
  detected_language?: string | null;

  selected_language: string;
  response_time_seconds: number | null;

  created_at: string;
  updated_at?: string;
};


export type MisconceptionEvolutionResponse = {
  id: string;

  student_alias_id: string;
  problem_id: string;

  attempt_id: string;
  diagnosis_id: string;

  previous_attempt_id: string | null;
  previous_diagnosis_id: string | null;

  previous_misconception_id: string | null;
  current_misconception_id: string | null;

  previous_diagnosis_state: DiagnosisState | null;
  current_diagnosis_state: DiagnosisState;

  evolution_state: MisconceptionEvolutionState;

  created_at: string;
  updated_at: string;
};


export type LearningHistoryItem = {
  attempt_id: string;
  problem_id: string;

  parent_attempt_id: string | null;
  retry_number: number;

  diagnosis_id: string | null;
  diagnosis_state: DiagnosisState | null;
  misconception_id: string | null;
  confidence: number | null;

  hint_levels_used: number[];
  diagnostic_question_answered: boolean;

  evolution_state: MisconceptionEvolutionState | null;

  created_at: string;
};


export type LearningHistoryResponse = {
  student_alias_id: string;
  problem_id: string | null;

  items: LearningHistoryItem[];
  total_items: number;
};


export function isHintComplete(
  progress: HintProgressResponse
): boolean {
  return progress.completed || progress.next_level === null;
}


export function hasRevealedHints(
  progress: HintProgressResponse
): boolean {
  return progress.revealed_levels.length > 0;
}


export function isFinalHintLevel(
  level: number
): boolean {
  return level >= 3;
}


export function isCorrectedEvolution(
  state: MisconceptionEvolutionState | null
): boolean {
  return state === "corrected";
}


export function isImprovingEvolution(
  state: MisconceptionEvolutionState | null
): boolean {
  return state === "improving";
}


export function isUncertainEvolution(
  state: MisconceptionEvolutionState | null
): boolean {
  return state === "uncertain";
}