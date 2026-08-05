export type TeacherReviewStatus =
  | "pending"
  | "in_review"
  | "reviewed";

export type TeacherReviewDecision =
  | "accepted"
  | "overridden";

export type DiagnosisState =
  | "confident"
  | "possible"
  | "insufficient"
  | "no_misconception";

export interface ReviewQueueAttempt {
  id: string;
  selected_language: string;
  response_time_seconds: number | null;
  created_at: string;
}

export interface ReviewQueueStudent {
  id: string;
  alias: string;
  pseudonymous_id: string;
}

export interface ReviewQueueProblem {
  id: string;
  code: string;
  title: string;
  topic: string;
}

export interface SystemDiagnosisSummary {
  id: string;
  state: DiagnosisState;
  confidence: number;
  primary_misconception_id: string | null;
  model_version: string;
  next_action: string;
  created_at: string;
}

export interface TeacherReviewRecord {
  id: string;
  attempt_id: string;
  teacher_id: string;
  system_diagnosis_id: string | null;
  status: TeacherReviewStatus;
  decision: TeacherReviewDecision | null;
  final_state: DiagnosisState | null;
  final_misconception_id: string | null;
  override_reason: string | null;
  teacher_note: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TeacherReviewQueueItem {
  attempt: ReviewQueueAttempt;
  student: ReviewQueueStudent;
  problem: ReviewQueueProblem;
  system_diagnosis: SystemDiagnosisSummary | null;
  review: TeacherReviewRecord | null;
}

export interface PaginationMetadata {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_previous: boolean;
  has_next: boolean;
}

export interface TeacherReviewQueueResponse {
  items: TeacherReviewQueueItem[];
  pagination: PaginationMetadata;
}

export interface TeacherReviewDetailAttempt {
  id: string;
  final_answer: string | null;
  written_reasoning: string;
  source_code: string | null;
  speech_transcript: string | null;
  selected_language: string;
  response_time_seconds: number | null;
  created_at: string;
}

export interface TeacherReviewDetailResponse {
  attempt_id: string;
  attempt?: TeacherReviewDetailAttempt;
  student: ReviewQueueStudent;
  problem: ReviewQueueProblem;
  system_diagnosis: SystemDiagnosisSummary | null;
  review: TeacherReviewRecord | null;
}

export interface SaveTeacherReviewDraftRequest {
  status: "in_review";
  decision: TeacherReviewDecision | null;
  final_state: DiagnosisState | null;
  final_misconception_id: string | null;
  override_reason: string | null;
  teacher_note: string | null;
}

export interface AcceptTeacherReviewRequest {
  teacher_note: string | null;
}

export interface OverrideTeacherReviewRequest {
  final_state: DiagnosisState;
  final_misconception_id: string | null;
  override_reason: string;
  teacher_note: string | null;
}

export interface FinalizeTeacherReviewRequest {
  decision: TeacherReviewDecision;
  final_state: DiagnosisState;
  final_misconception_id?: string | null;
  override_reason?: string | null;
  teacher_note?: string | null;
}

export interface TeacherReviewMutationResponse {
  message: string;
  review: TeacherReviewRecord;
}

export interface TeacherReviewQueueQuery {
  page?: number;
  page_size?: number;
  review_status?: TeacherReviewStatus;
}

export interface ApiErrorResponse {
  detail:
    | string
    | Array<{
        loc: Array<string | number>;
        msg: string;
        type: string;
        input?: unknown;
        ctx?: Record<string, unknown>;
      }>;
}

export function isReviewed(
  review: TeacherReviewRecord | null,
): boolean {
  return review?.status === "reviewed";
}

export function isInReview(
  review: TeacherReviewRecord | null,
): boolean {
  return review?.status === "in_review";
}

export function getEffectiveReviewStatus(
  review: TeacherReviewRecord | null,
): TeacherReviewStatus {
  return review?.status ?? "pending";
}