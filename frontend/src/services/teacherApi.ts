import {
  apiGet,
} from "../api/client";

import type {
  MisconceptionAnalyticsQuery,
  MisconceptionAnalyticsResponse,
  ProblemAnalyticsResponse,
  StudentHistoryQuery,
  StudentHistoryResponse,
  TeacherAttemptDetailResponse,
  TeacherAttemptFilters,
  TeacherAttemptListResponse,
  TeacherDashboardQuery,
  TeacherDashboardResponse,
} from "../types/teacher";


const TEACHER_API_PREFIX =
  "/teacher";


function sanitizeText(
  value: string | undefined
): string | undefined {
  const normalized =
    value?.trim();

  return normalized
    ? normalized
    : undefined;
}


function normalizePositiveInteger(
  value: number | undefined,
  fallback: number,
  maximum?: number
): number {
  if (
    value === undefined ||
    !Number.isFinite(value)
  ) {
    return fallback;
  }

  const normalized =
    Math.max(
      1,
      Math.trunc(value)
    );

  return maximum === undefined
    ? normalized
    : Math.min(
        normalized,
        maximum
      );
}


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


export async function getTeacherDashboard(
  query: TeacherDashboardQuery = {},
  signal?: AbortSignal
): Promise<TeacherDashboardResponse> {
  const days =
    normalizePositiveInteger(
      query.days,
      30,
      365
    );

  const topMisconceptions =
    normalizePositiveInteger(
      query.top_misconceptions,
      5,
      20
    );

  return apiGet<TeacherDashboardResponse>(
    `${TEACHER_API_PREFIX}/dashboard`,
    {
      query: {
        days,
        top_misconceptions:
          topMisconceptions,
      },
      signal,
    }
  );
}


export async function getTeacherAttempts(
  filters: TeacherAttemptFilters = {},
  signal?: AbortSignal
): Promise<TeacherAttemptListResponse> {
  const page =
    normalizePositiveInteger(
      filters.page,
      1
    );

  const pageSize =
    normalizePositiveInteger(
      filters.page_size,
      20,
      100
    );

  /*
   * The backend returns each attempt together with
   * diagnosis and teacher-review context, so the UI
   * does not need per-row follow-up requests.
   */
  return apiGet<TeacherAttemptListResponse>(
    `${TEACHER_API_PREFIX}/attempts`,
    {
      query: {
        page,
        page_size: pageSize,

        student_alias_id:
          sanitizeText(
            filters.student_alias_id
          ),

        problem_id:
          sanitizeText(
            filters.problem_id
          ),

        diagnosis_state:
          filters.diagnosis_state,

        misconception_code:
          sanitizeText(
            filters.misconception_code
          ),

        created_from:
          sanitizeText(
            filters.created_from
          ),

        created_to:
          sanitizeText(
            filters.created_to
          ),

        search:
          sanitizeText(
            filters.search
          ),
      },
      signal,
    }
  );
}


export async function getTeacherAttemptDetail(
  attemptId: string,
  signal?: AbortSignal
): Promise<TeacherAttemptDetailResponse> {
  const normalizedAttemptId =
    normalizeRequiredId(
      attemptId,
      "attemptId"
    );

  return apiGet<TeacherAttemptDetailResponse>(
    `${TEACHER_API_PREFIX}/attempts/${encodeURIComponent(
      normalizedAttemptId
    )}`,
    {
      signal,
    }
  );
}


export async function getStudentHistory(
  studentAliasId: string,
  query: StudentHistoryQuery = {},
  signal?: AbortSignal
): Promise<StudentHistoryResponse> {
  const normalizedStudentAliasId =
    normalizeRequiredId(
      studentAliasId,
      "studentAliasId"
    );

  const page =
    normalizePositiveInteger(
      query.page,
      1
    );

  const pageSize =
    normalizePositiveInteger(
      query.page_size,
      20,
      100
    );

  /*
   * Sprint 9F teacher-facing student history endpoint.
   *
   * The response is expected to contain:
   * - student summary;
   * - aggregate history summary;
   * - paginated attempt timeline;
   * - retry/intervention/evolution metadata on each item.
   *
   * The backend teacher history service must expose the
   * Sprint 9 metadata declared in StudentHistoryItem.
   */
  return apiGet<StudentHistoryResponse>(
    `${TEACHER_API_PREFIX}/students/${encodeURIComponent(
      normalizedStudentAliasId
    )}/history`,
    {
      query: {
        page,
        page_size: pageSize,
      },
      signal,
    }
  );
}


export async function getProblemAnalytics(
  problemId: string,
  signal?: AbortSignal
): Promise<ProblemAnalyticsResponse> {
  const normalizedProblemId =
    normalizeRequiredId(
      problemId,
      "problemId"
    );

  return apiGet<ProblemAnalyticsResponse>(
    `${TEACHER_API_PREFIX}/problems/${encodeURIComponent(
      normalizedProblemId
    )}/analytics`,
    {
      signal,
    }
  );
}


export async function getMisconceptionAnalytics(
  query: MisconceptionAnalyticsQuery = {},
  signal?: AbortSignal
): Promise<MisconceptionAnalyticsResponse> {
  const limit =
    normalizePositiveInteger(
      query.limit,
      20,
      100
    );

  return apiGet<MisconceptionAnalyticsResponse>(
    `${TEACHER_API_PREFIX}/misconceptions/analytics`,
    {
      query: {
        limit,
      },
      signal,
    }
  );
}


export const teacherApi = {
  getDashboard:
    getTeacherDashboard,

  getAttempts:
    getTeacherAttempts,

  getAttemptDetail:
    getTeacherAttemptDetail,

  getStudentHistory,

  getProblemAnalytics,

  getMisconceptionAnalytics,
} as const;