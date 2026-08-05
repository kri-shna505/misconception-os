import type {
  DiagnosisNextAction,
  DiagnosisResponse,
  DiagnosisState,
  EvidenceSource,
  EvidenceStrength,
  MisconceptionSummary,
} from "./diagnosis";


export type PaginationMeta = {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_previous: boolean;
  has_next: boolean;
};


export type TeacherStudentSummary = {
  id: string;
  alias: string;
  pseudonymous_id: string;
  consent_status: boolean;
  created_at: string;
};


export type TeacherProblemSummary = {
  id: string;
  code: string;
  title: string;
  topic: string;
  difficulty: string | null;
  expected_language: string | null;
  active: boolean;
  created_at: string;
};


export type TeacherSupportedMisconception = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  topic: string | null;
  active: boolean;
};


export type TeacherProblemDetail =
  TeacherProblemSummary & {
    statement: string;

    rule_context: Record<
      string,
      unknown
    > | null;

    supported_misconceptions:
      TeacherSupportedMisconception[];
  };


/*
 * The problem-analytics endpoint may return
 * statement when full problem context is included.
 *
 * It remains optional so the frontend type still
 * matches responses that only contain summary data.
 */
export type TeacherProblemAnalyticsSummary =
  TeacherProblemSummary & {
    statement?: string | null;
  };


export type TeacherAttemptSummary = {
  id: string;
  student_alias_id: string;
  problem_id: string;
  selected_language: string;
  response_time_seconds: number | null;
  created_at: string;
};


export type TeacherAttemptDetail = {
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


export type TeacherDiagnosisSummary = {
  id: string;
  attempt_id: string;
  state: DiagnosisState;
  confidence: number;
  primary_misconception_id: string | null;
  model_version: string;
  next_action: DiagnosisNextAction;
  created_at: string;
};


export type TeacherReviewStatus =
  | "pending"
  | "in_review"
  | "reviewed";


export type TeacherReviewDecision =
  | "accepted"
  | "overridden";


export type TeacherFinalDiagnosisState =
  | "confident"
  | "possible"
  | "insufficient"
  | "no_misconception";


export type TeacherReviewSummary = {
  id: string;
  attempt_id: string;
  teacher_id: string;
  system_diagnosis_id: string | null;

  status: TeacherReviewStatus;

  decision: TeacherReviewDecision | null;

  final_state:
    TeacherFinalDiagnosisState | null;

  final_misconception_id:
    string | null;

  override_reason: string | null;
  teacher_note: string | null;

  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
};


export type TeacherAttemptListItem = {
  attempt: TeacherAttemptSummary;
  student: TeacherStudentSummary;
  problem: TeacherProblemSummary;

  /*
   * Existing /teacher/attempts response field.
   */
  diagnosis: TeacherDiagnosisSummary | null;

  /*
   * Review-aware queue endpoints may return the same
   * automated diagnosis using system_diagnosis.
   */
  system_diagnosis?:
    TeacherDiagnosisSummary | null;

  /*
   * Final teacher decision.
   *
   * When status is reviewed and final_state exists,
   * the frontend must treat final_state as authoritative
   * instead of continuing to display diagnosis.state.
   */
  review: TeacherReviewSummary | null;
};


export type TeacherAttemptListResponse = {
  items: TeacherAttemptListItem[];
  pagination: PaginationMeta;
};


export type TeacherAttemptDetailResponse = {
  attempt: TeacherAttemptDetail;
  student: TeacherStudentSummary;
  problem: TeacherProblemDetail;
  diagnosis: DiagnosisResponse | null;

  /*
   * Optional so the existing teacher-attempt detail
   * endpoint remains backward compatible.
   */
  review: TeacherReviewSummary | null;
};


export type TeacherDashboardSummary = {
  total_students: number;
  total_attempts: number;
  total_diagnoses: number;
  verified_attempts: number;
  misconception_attempts: number;
  insufficient_attempts: number;
  undiagnosed_attempts: number;

  average_response_time_seconds:
    number | null;

  diagnosis_coverage_rate: number;
  verified_rate: number;
  misconception_rate: number;
};


export type AttemptsOverTimeItem = {
  date: string;
  attempt_count: number;
  diagnosis_count: number;
  verified_count: number;
  misconception_count: number;
};


export type MisconceptionAnalyticsItem = {
  misconception_id: string;
  code: string;
  name: string;
  topic: string | null;
  detection_count: number;
  percentage_of_diagnoses: number;
  average_confidence: number | null;
  affected_student_count: number;
  affected_problem_count: number;
};


export type TeacherDashboardResponse = {
  summary: TeacherDashboardSummary;

  misconception_analytics:
    MisconceptionAnalyticsItem[];

  attempts_over_time:
    AttemptsOverTimeItem[];

  generated_at: string;
};


export type StudentHistorySummary = {
  total_attempts: number;
  diagnosed_attempts: number;
  verified_attempts: number;
  misconception_attempts: number;
  insufficient_attempts: number;

  average_response_time_seconds:
    number | null;
};


export type StudentHistoryItem = {
  attempt: TeacherAttemptSummary;
  problem: TeacherProblemSummary;
  diagnosis: TeacherDiagnosisSummary | null;

  /*
   * Optional teacher-review context for future
   * student-history endpoint support.
   */
  review?: TeacherReviewSummary | null;
};


export type StudentHistoryResponse = {
  student: TeacherStudentSummary;
  summary: StudentHistorySummary;
  items: StudentHistoryItem[];
  pagination: PaginationMeta;
};


export type DiagnosisStateAnalyticsItem = {
  state: DiagnosisState;
  count: number;
  percentage: number;
};


export type ProblemAnalyticsResponse = {
  problem: TeacherProblemAnalyticsSummary;

  total_attempts: number;
  diagnosed_attempts: number;
  verified_attempts: number;
  misconception_attempts: number;
  insufficient_attempts: number;

  average_response_time_seconds:
    number | null;

  diagnosis_states:
    DiagnosisStateAnalyticsItem[];
};


export type MisconceptionAnalyticsResponse = {
  total_diagnoses: number;

  total_misconception_diagnoses:
    number;

  items: MisconceptionAnalyticsItem[];
};


export type TeacherAttemptFilters = {
  page?: number;
  page_size?: number;
  student_alias_id?: string;
  problem_id?: string;
  diagnosis_state?: DiagnosisState;
  misconception_code?: string;
  created_from?: string;
  created_to?: string;
  search?: string;
};


export type TeacherDashboardQuery = {
  days?: number;
  top_misconceptions?: number;
};


export type StudentHistoryQuery = {
  page?: number;
  page_size?: number;
};


export type MisconceptionAnalyticsQuery = {
  limit?: number;
};


export type TeacherEvidence = {
  id: string | null;
  diagnosis_id: string | null;
  source: EvidenceSource;
  strength: EvidenceStrength;
  text: string;
  sort_order: number;
  metadata: Record<string, unknown>;
};


export type TeacherMisconceptionSummary =
  MisconceptionSummary;


export type TeacherDiagnosisState =
  DiagnosisState;


export type TeacherNextAction =
  DiagnosisNextAction;