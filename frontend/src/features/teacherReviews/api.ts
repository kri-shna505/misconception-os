import {
  ApiError,
  apiGet,
  apiPost,
  apiPut,
  apiRequest,
} from "../../api/client";

import type {
  AcceptTeacherReviewRequest,
  FinalizeTeacherReviewRequest,
  OverrideTeacherReviewRequest,
  SaveTeacherReviewDraftRequest,
  TeacherReviewDetailResponse,
  TeacherReviewMutationResponse,
  TeacherReviewQueueQuery,
  TeacherReviewQueueResponse,
} from "./types";


const TEACHER_REVIEW_API_PREFIX =
  "/teacher/reviews";


/**
 * Backward-compatible alias.
 *
 * TeacherReviewDetailPage.tsx currently imports
 * TeacherReviewApiError from this module. The shared API
 * client throws ApiError, so exporting the same class under
 * the old name keeps instanceof checks working correctly.
 */
export {
  ApiError as TeacherReviewApiError,
};


function normalizeAttemptId(
  attemptId: string,
): string {
  const normalizedAttemptId =
    attemptId.trim();

  if (!normalizedAttemptId) {
    throw new Error(
      "attemptId is required for the teacher review request.",
    );
  }

  return normalizedAttemptId;
}


function normalizePositiveInteger(
  value: number | undefined,
  fallback: number,
  maximum?: number,
): number {
  if (
    value === undefined ||
    !Number.isFinite(value)
  ) {
    return fallback;
  }

  const normalizedValue = Math.max(
    1,
    Math.trunc(value),
  );

  if (maximum === undefined) {
    return normalizedValue;
  }

  return Math.min(
    normalizedValue,
    maximum,
  );
}


export async function getTeacherReviewQueue(
  query: TeacherReviewQueueQuery = {},
  signal?: AbortSignal,
): Promise<TeacherReviewQueueResponse> {
  const page = normalizePositiveInteger(
    query.page,
    1,
  );

  const pageSize =
    normalizePositiveInteger(
      query.page_size,
      20,
      100,
    );

  return apiGet<TeacherReviewQueueResponse>(
    TEACHER_REVIEW_API_PREFIX,
    {
      query: {
        page,
        page_size: pageSize,
        review_status:
          query.review_status,
      },
      signal,
    },
  );
}


export async function getTeacherReviewDetail(
  attemptId: string,
  signal?: AbortSignal,
): Promise<TeacherReviewDetailResponse> {
  const normalizedAttemptId =
    normalizeAttemptId(attemptId);

  return apiGet<TeacherReviewDetailResponse>(
    `${TEACHER_REVIEW_API_PREFIX}/${encodeURIComponent(
      normalizedAttemptId,
    )}`,
    {
      signal,
    },
  );
}


export async function saveTeacherReviewDraft(
  attemptId: string,
  request: SaveTeacherReviewDraftRequest,
  signal?: AbortSignal,
): Promise<TeacherReviewMutationResponse> {
  const normalizedAttemptId =
    normalizeAttemptId(attemptId);

  return apiPut<
    TeacherReviewMutationResponse,
    SaveTeacherReviewDraftRequest
  >(
    `${TEACHER_REVIEW_API_PREFIX}/${encodeURIComponent(
      normalizedAttemptId,
    )}/draft`,
    request,
    {
      signal,
    },
  );
}


export async function acceptTeacherReview(
  attemptId: string,
  request: AcceptTeacherReviewRequest,
  signal?: AbortSignal,
): Promise<TeacherReviewMutationResponse> {
  const normalizedAttemptId =
    normalizeAttemptId(attemptId);

  return apiPost<
    TeacherReviewMutationResponse,
    AcceptTeacherReviewRequest
  >(
    `${TEACHER_REVIEW_API_PREFIX}/${encodeURIComponent(
      normalizedAttemptId,
    )}/accept`,
    request,
    {
      signal,
    },
  );
}


export async function overrideTeacherReview(
  attemptId: string,
  request: OverrideTeacherReviewRequest,
  signal?: AbortSignal,
): Promise<TeacherReviewMutationResponse> {
  const normalizedAttemptId =
    normalizeAttemptId(attemptId);

  return apiPost<
    TeacherReviewMutationResponse,
    OverrideTeacherReviewRequest
  >(
    `${TEACHER_REVIEW_API_PREFIX}/${encodeURIComponent(
      normalizedAttemptId,
    )}/override`,
    request,
    {
      signal,
    },
  );
}


export async function finalizeTeacherReview(
  attemptId: string,
  request: FinalizeTeacherReviewRequest,
  signal?: AbortSignal,
): Promise<TeacherReviewMutationResponse> {
  const normalizedAttemptId =
    normalizeAttemptId(attemptId);

  return apiPost<
    TeacherReviewMutationResponse,
    FinalizeTeacherReviewRequest
  >(
    `${TEACHER_REVIEW_API_PREFIX}/${encodeURIComponent(
      normalizedAttemptId,
    )}/finalize`,
    request,
    {
      signal,
    },
  );
}


export async function reopenTeacherReview(
  attemptId: string,
  signal?: AbortSignal,
): Promise<TeacherReviewMutationResponse> {
  const normalizedAttemptId =
    normalizeAttemptId(attemptId);

  return apiRequest<TeacherReviewMutationResponse>(
    `${TEACHER_REVIEW_API_PREFIX}/${encodeURIComponent(
      normalizedAttemptId,
    )}/reopen`,
    {
      method: "POST",
      signal,
    },
  );
}


export const teacherReviewApi = {
  getQueue: getTeacherReviewQueue,
  getDetail: getTeacherReviewDetail,
  saveDraft: saveTeacherReviewDraft,
  accept: acceptTeacherReview,
  override: overrideTeacherReview,
  finalize: finalizeTeacherReview,
  reopen: reopenTeacherReview,
} as const;