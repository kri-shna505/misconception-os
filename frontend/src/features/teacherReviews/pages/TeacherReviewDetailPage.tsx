import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";

import {
  acceptTeacherReview,
  finalizeTeacherReview,
  getTeacherReviewDetail,
  overrideTeacherReview,
  reopenTeacherReview,
  saveTeacherReviewDraft,
  TeacherReviewApiError,
} from "../api";

import { ReviewStatusBadge } from "../components/ReviewStatusBadge";

import type {
  DiagnosisState,
  FinalizeTeacherReviewRequest,
  OverrideTeacherReviewRequest,
  SaveTeacherReviewDraftRequest,
  TeacherReviewDecision,
  TeacherReviewDetailAttempt,
  TeacherReviewDetailResponse,
  TeacherReviewRecord,
} from "../types";


type ReviewFormState = {
  decision: TeacherReviewDecision | "";
  finalState: DiagnosisState | "";
  finalMisconceptionId: string;
  overrideReason: string;
  teacherNote: string;
};


type MutationAction =
  | "save"
  | "accept"
  | "override"
  | "finalize"
  | "reopen"
  | null;


type FlexibleDetailResponse =
  TeacherReviewDetailResponse & {
    final_answer?: string | null;
    written_reasoning?: string | null;
    source_code?: string | null;
    speech_transcript?: string | null;
    selected_language?: string | null;
    response_time_seconds?: number | null;
    created_at?: string | null;

    attempt_content?: Partial<TeacherReviewDetailAttempt> | null;
    submission?: Partial<TeacherReviewDetailAttempt> | null;
    student_attempt?: Partial<TeacherReviewDetailAttempt> | null;
  };


const EMPTY_FORM: ReviewFormState = {
  decision: "",
  finalState: "",
  finalMisconceptionId: "",
  overrideReason: "",
  teacherNote: "",
};


const DIAGNOSIS_STATE_OPTIONS: Array<{
  value: DiagnosisState;
  label: string;
}> = [
  {
    value: "confident",
    label: "Confident",
  },
  {
    value: "possible",
    label: "Possible",
  },
  {
    value: "insufficient",
    label: "Insufficient evidence",
  },
  {
    value: "no_misconception",
    label: "No misconception",
  },
];


function normalizeNullableText(
  value: unknown,
): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim();

  return normalized || null;
}


function normalizeNullableNumber(
  value: unknown,
): number | null {
  if (
    typeof value !== "number" ||
    !Number.isFinite(value)
  ) {
    return null;
  }

  return value;
}


function resolveAttempt(
  detail: TeacherReviewDetailResponse,
): TeacherReviewDetailAttempt {
  const flexibleDetail =
    detail as FlexibleDetailResponse;

  const nestedAttempt =
    flexibleDetail.attempt ??
    flexibleDetail.attempt_content ??
    flexibleDetail.submission ??
    flexibleDetail.student_attempt ??
    null;

  return {
    id:
      normalizeNullableText(
        nestedAttempt?.id,
      ) ??
      normalizeNullableText(
        flexibleDetail.attempt_id,
      ) ??
      "",

    final_answer:
      normalizeNullableText(
        nestedAttempt?.final_answer,
      ) ??
      normalizeNullableText(
        flexibleDetail.final_answer,
      ),

    written_reasoning:
      normalizeNullableText(
        nestedAttempt?.written_reasoning,
      ) ??
      normalizeNullableText(
        flexibleDetail.written_reasoning,
      ) ??
      "",

    source_code:
      normalizeNullableText(
        nestedAttempt?.source_code,
      ) ??
      normalizeNullableText(
        flexibleDetail.source_code,
      ),

    speech_transcript:
      normalizeNullableText(
        nestedAttempt?.speech_transcript,
      ) ??
      normalizeNullableText(
        flexibleDetail.speech_transcript,
      ),

    selected_language:
      normalizeNullableText(
        nestedAttempt?.selected_language,
      ) ??
      normalizeNullableText(
        flexibleDetail.selected_language,
      ) ??
      "Unknown",

    response_time_seconds:
      normalizeNullableNumber(
        nestedAttempt?.response_time_seconds,
      ) ??
      normalizeNullableNumber(
        flexibleDetail.response_time_seconds,
      ),

    created_at:
      normalizeNullableText(
        nestedAttempt?.created_at,
      ) ??
      normalizeNullableText(
        flexibleDetail.created_at,
      ) ??
      "",
  };
}


function createFormState(
  detail: TeacherReviewDetailResponse,
): ReviewFormState {
  const review = detail.review;

  const systemDiagnosis =
    detail.system_diagnosis;

  return {
    decision:
      review?.decision ??
      "",

    finalState:
      review?.final_state ??
      systemDiagnosis?.state ??
      "",

    finalMisconceptionId:
      review?.final_misconception_id ??
      systemDiagnosis?.primary_misconception_id ??
      "",

    overrideReason:
      review?.override_reason ??
      "",

    teacherNote:
      review?.teacher_note ??
      "",
  };
}


function formatDateTime(
  value: string | null | undefined,
): string {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(
    undefined,
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(date);
}


function formatDuration(
  seconds: number | null | undefined,
): string {
  if (
    seconds === null ||
    seconds === undefined
  ) {
    return "Not recorded";
  }

  if (seconds < 60) {
    return `${seconds} sec`;
  }

  const minutes =
    Math.floor(seconds / 60);

  const remainingSeconds =
    seconds % 60;

  if (remainingSeconds === 0) {
    return `${minutes} min`;
  }

  return (
    `${minutes} min ` +
    `${remainingSeconds} sec`
  );
}


function formatDiagnosisState(
  state: DiagnosisState | null | undefined,
): string {
  switch (state) {
    case "confident":
      return "Confident";

    case "possible":
      return "Possible";

    case "insufficient":
      return "Insufficient evidence";

    case "no_misconception":
      return "No misconception";

    default:
      return "Not diagnosed";
  }
}


function formatDecision(
  decision:
    | TeacherReviewDecision
    | null
    | undefined,
): string {
  switch (decision) {
    case "accepted":
      return "Accepted";

    case "overridden":
      return "Overridden";

    default:
      return "Not selected";
  }
}


function formatConfidence(
  confidence: number | null | undefined,
): string {
  if (
    confidence === null ||
    confidence === undefined ||
    !Number.isFinite(confidence)
  ) {
    return "Not available";
  }

  const percentage =
    confidence <= 1
      ? confidence * 100
      : confidence;

  return `${Math.round(percentage)}%`;
}


function getErrorMessage(
  error: unknown,
): string {
  if (
    error instanceof TeacherReviewApiError
  ) {
    if (error.status === 0) {
      return (
        "Could not connect to the backend. " +
        "Confirm that FastAPI is running."
      );
    }

    if (error.status === 401) {
      return (
        "Your teacher session is missing or expired. " +
        "Log in again and retry."
      );
    }

    if (error.status === 403) {
      return (
        "This account does not have permission " +
        "to access teacher reviews."
      );
    }

    if (error.status === 404) {
      return (
        "The requested student attempt " +
        "could not be found."
      );
    }

    if (error.status === 409) {
      return (
        "This review is already finalized. " +
        "Reopen it before making changes."
      );
    }

    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return (
    "The teacher review request failed."
  );
}


function isFinalized(
  review: TeacherReviewRecord | null,
): boolean {
  return review?.status === "reviewed";
}


function validateOverride(
  form: ReviewFormState,
): string | null {
  if (!form.finalState) {
    return (
      "Select a final diagnosis state " +
      "before saving the override."
    );
  }

  if (!form.overrideReason.trim()) {
    return (
      "An override reason is required."
    );
  }

  if (
    form.finalState ===
      "no_misconception" &&
    form.finalMisconceptionId.trim()
  ) {
    return (
      "A no-misconception decision cannot " +
      "include a misconception ID."
    );
  }

  return null;
}


function validateFinalize(
  form: ReviewFormState,
): string | null {
  if (!form.decision) {
    return (
      "Choose accepted or overridden " +
      "before finalizing."
    );
  }

  if (!form.finalState) {
    return (
      "Select the final diagnosis state " +
      "before finalizing."
    );
  }

  if (
    form.decision === "overridden" &&
    !form.overrideReason.trim()
  ) {
    return (
      "An override reason is required " +
      "for an overridden review."
    );
  }

  if (
    form.finalState ===
      "no_misconception" &&
    form.finalMisconceptionId.trim()
  ) {
    return (
      "A no-misconception decision cannot " +
      "include a misconception ID."
    );
  }

  return null;
}


function hasContent(
  value: string | null | undefined,
): boolean {
  return Boolean(value?.trim());
}


export function TeacherReviewDetailPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const { attemptId } = useParams<{
    attemptId: string;
  }>();

  const [
    detail,
    setDetail,
  ] =
    useState<TeacherReviewDetailResponse | null>(
      null,
    );

  const [
    form,
    setForm,
  ] =
    useState<ReviewFormState>(
      EMPTY_FORM,
    );

  const [
    isLoading,
    setIsLoading,
  ] =
    useState(true);

  const [
    mutationAction,
    setMutationAction,
  ] =
    useState<MutationAction>(
      null,
    );

  const [
    errorMessage,
    setErrorMessage,
  ] =
    useState<string | null>(
      null,
    );

  const [
    successMessage,
    setSuccessMessage,
  ] =
    useState<string | null>(
      null,
    );


  const loadReview = useCallback(
    async (
      signal?: AbortSignal,
    ): Promise<void> => {
      if (!attemptId) {
        setDetail(null);

        setErrorMessage(
          "The attempt ID is missing from the URL.",
        );

        setIsLoading(false);

        return;
      }

      setIsLoading(true);
      setErrorMessage(null);
      setSuccessMessage(null);

      try {
        const response =
          await getTeacherReviewDetail(
            attemptId,
            signal,
          );

        setDetail(response);

        setForm(
          createFormState(response),
        );
      } catch (error) {
        if (
          error instanceof DOMException &&
          error.name === "AbortError"
        ) {
          return;
        }

        setDetail(null);

        setErrorMessage(
          getErrorMessage(error),
        );
      } finally {
        if (!signal?.aborted) {
          setIsLoading(false);
        }
      }
    },
    [attemptId],
  );


  useEffect(
    () => {
      const controller =
        new AbortController();

      void loadReview(
        controller.signal,
      );

      return () => {
        controller.abort();
      };
    },
    [loadReview],
  );


  const review =
    detail?.review ??
    null;

  const systemDiagnosis =
    detail?.system_diagnosis ??
    null;

  const attempt = useMemo(
    () =>
      detail
        ? resolveAttempt(detail)
        : null,
    [detail],
  );

  const finalized =
    isFinalized(review);

  const isMutating =
    mutationAction !== null;

  const effectiveDecision =
    form.decision ||
    review?.decision ||
    "";


  const canFinalize = useMemo(
    () => {
      if (
        finalized ||
        isMutating
      ) {
        return false;
      }

      if (
        !effectiveDecision ||
        !form.finalState
      ) {
        return false;
      }

      if (
        effectiveDecision ===
          "overridden" &&
        !form.overrideReason.trim()
      ) {
        return false;
      }

      if (
        form.finalState ===
          "no_misconception" &&
        form.finalMisconceptionId.trim()
      ) {
        return false;
      }

      return true;
    },
    [
      effectiveDecision,
      finalized,
      form.finalMisconceptionId,
      form.finalState,
      form.overrideReason,
      isMutating,
    ],
  );


  function navigateToQueue(): void {
    navigate(
      "/teacher/reviews",
    );
  }


  function navigateToLogin(): void {
    const returnTo =
      location.pathname +
      location.search;

    /*
     * Remove stale tokens before opening the login page.
     * Earlier frontend versions used different storage keys.
     */
    window.localStorage.removeItem(
      "teacher_access_token",
    );

    window.localStorage.removeItem(
      "misconceptionos_access_token",
    );

    window.sessionStorage.setItem(
      "teacher_login_return_to",
      returnTo,
    );

    const loginUrl =
      "/teacher/login?returnTo=" +
      encodeURIComponent(returnTo);

    /*
     * Use a hard navigation here so an expired-session page
     * cannot remain stuck behind stale React Router state.
     */
    window.location.assign(loginUrl);
  }


  function updateForm<
    Key extends keyof ReviewFormState
  >(
    key: Key,
    value: ReviewFormState[Key],
  ): void {
    setForm(
      (current) => ({
        ...current,
        [key]: value,
      }),
    );

    setSuccessMessage(null);
    setErrorMessage(null);
  }


  function applyMutationResponse(
    message: string,
    updatedReview: TeacherReviewRecord,
  ): void {
    setDetail(
      (current) => {
        if (!current) {
          return current;
        }

        const nextDetail:
          TeacherReviewDetailResponse = {
            ...current,
            review: updatedReview,
          };

        setForm(
          createFormState(nextDetail),
        );

        return nextDetail;
      },
    );

    setSuccessMessage(message);
    setErrorMessage(null);
  }


  async function runMutation(
    action: Exclude<
      MutationAction,
      null
    >,
    mutation: () => Promise<{
      message: string;
      review: TeacherReviewRecord;
    }>,
  ): Promise<void> {
    if (isMutating) {
      return;
    }

    setMutationAction(action);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const response =
        await mutation();

      applyMutationResponse(
        response.message,
        response.review,
      );
    } catch (error) {
      setErrorMessage(
        getErrorMessage(error),
      );

      if (
        error instanceof TeacherReviewApiError &&
        error.status === 401
      ) {
        return;
      }
    } finally {
      setMutationAction(null);
    }
  }


  async function handleSaveDraft(): Promise<void> {
    if (
      !attemptId ||
      finalized
    ) {
      return;
    }

    const request:
      SaveTeacherReviewDraftRequest = {
        status: "in_review",

        decision:
          form.decision ||
          null,

        final_state:
          form.finalState ||
          null,

        final_misconception_id:
          form.finalState ===
          "no_misconception"
            ? null
            : (
                form.finalMisconceptionId.trim() ||
                null
              ),

        override_reason:
          form.overrideReason.trim() ||
          null,

        teacher_note:
          form.teacherNote.trim() ||
          null,
      };

    await runMutation(
      "save",
      () =>
        saveTeacherReviewDraft(
          attemptId,
          request,
        ),
    );
  }


  async function handleAccept(): Promise<void> {
    if (
      !attemptId ||
      !systemDiagnosis ||
      finalized
    ) {
      return;
    }

    await runMutation(
      "accept",
      () =>
        acceptTeacherReview(
          attemptId,
          {
            teacher_note:
              form.teacherNote.trim() ||
              null,
          },
        ),
    );
  }


  async function handleOverride(): Promise<void> {
    if (
      !attemptId ||
      finalized
    ) {
      return;
    }

    const validationError =
      validateOverride(form);

    if (validationError) {
      setErrorMessage(
        validationError,
      );

      return;
    }

    const request:
      OverrideTeacherReviewRequest = {
        final_state:
          form.finalState as DiagnosisState,

        final_misconception_id:
          form.finalState ===
          "no_misconception"
            ? null
            : (
                form.finalMisconceptionId.trim() ||
                null
              ),

        override_reason:
          form.overrideReason.trim(),

        teacher_note:
          form.teacherNote.trim() ||
          null,
      };

    await runMutation(
      "override",
      () =>
        overrideTeacherReview(
          attemptId,
          request,
        ),
    );
  }


  async function handleFinalize(): Promise<void> {
    if (
      !attemptId ||
      finalized
    ) {
      return;
    }

    const validationError =
      validateFinalize(form);

    if (validationError) {
      setErrorMessage(
        validationError,
      );

      return;
    }

    const request:
      FinalizeTeacherReviewRequest = {
        decision:
          form.decision as TeacherReviewDecision,

        final_state:
          form.finalState as DiagnosisState,

        final_misconception_id:
          form.finalState ===
          "no_misconception"
            ? null
            : (
                form.finalMisconceptionId.trim() ||
                null
              ),

        override_reason:
          form.decision ===
          "overridden"
            ? form.overrideReason.trim()
            : null,

        teacher_note:
          form.teacherNote.trim() ||
          null,
      };

    await runMutation(
      "finalize",
      () =>
        finalizeTeacherReview(
          attemptId,
          request,
        ),
    );
  }


  async function handleReopen(): Promise<void> {
    if (
      !attemptId ||
      !finalized
    ) {
      return;
    }

    await runMutation(
      "reopen",
      () =>
        reopenTeacherReview(
          attemptId,
        ),
    );
  }


  if (isLoading) {
    return (
      <main className="teacher-review-detail-shell">
        <section className="teacher-review-detail-state">
          <div className="teacher-review-state-spinner" />

          <p className="teacher-review-detail-eyebrow">
            Teacher review
          </p>

          <h1>
            Loading review
          </h1>

          <p>
            Retrieving the student attempt,
            system diagnosis, and saved teacher
            decision.
          </p>
        </section>
      </main>
    );
  }


  if (!detail) {
    const authenticationError =
      errorMessage?.includes(
        "session is missing or expired",
      ) ?? false;

    return (
      <main className="teacher-review-detail-shell">
        <section className="teacher-review-detail-state">
          <div className="teacher-review-state-icon">
            !
          </div>

          <p className="teacher-review-detail-eyebrow">
            Teacher review
          </p>

          <h1>
            Review unavailable
          </h1>

          <p>
            {errorMessage ??
              "The teacher review could not be loaded."}
          </p>

          <div className="teacher-review-detail-state-actions">
            {authenticationError ? (
              <button
                type="button"
                className="teacher-review-primary-button"
                onClick={navigateToLogin}
              >
                Log in again
              </button>
            ) : (
              <button
                type="button"
                className="teacher-review-primary-button"
                onClick={() => {
                  void loadReview();
                }}
              >
                Try again
              </button>
            )}

            <button
              type="button"
              className="teacher-review-secondary-button"
              onClick={navigateToQueue}
            >
              Back to review queue
            </button>
          </div>
        </section>
      </main>
    );
  }


  return (
    <main className="teacher-review-detail-shell">
      <header className="teacher-review-detail-header">
        <div className="teacher-review-detail-title-group">
          <p className="teacher-review-detail-eyebrow">
            Complete attempt review
          </p>

          <h1>
            {detail.problem.code}
            {" · "}
            {detail.problem.title}
          </h1>

          <p className="teacher-review-detail-subtitle">
            {detail.problem.topic}
          </p>
        </div>

        <div className="teacher-review-detail-header-actions">
          <ReviewStatusBadge
            review={review}
          />

          <button
            type="button"
            className="teacher-review-secondary-button"
            onClick={navigateToQueue}
          >
            Back to queue
          </button>
        </div>
      </header>


      {errorMessage ? (
        <div
          className="teacher-review-alert teacher-review-alert-error"
          role="alert"
        >
          <strong>
            Request failed
          </strong>

          <span>
            {errorMessage}
          </span>
        </div>
      ) : null}


      {successMessage ? (
        <div
          className="teacher-review-alert teacher-review-alert-success"
          role="status"
        >
          <strong>
            Saved
          </strong>

          <span>
            {successMessage}
          </span>
        </div>
      ) : null}


      <section className="teacher-review-detail-summary-grid">
        <article className="teacher-review-summary-card">
          <span>
            Student
          </span>

          <strong>
            {detail.student.alias}
          </strong>

          <small>
            {detail.student.pseudonymous_id}
          </small>
        </article>


        <article className="teacher-review-summary-card">
          <span>
            Submitted
          </span>

          <strong>
            {formatDateTime(
              attempt?.created_at,
            )}
          </strong>

          <small>
            {attempt?.selected_language ??
              "Language unavailable"}
          </small>
        </article>


        <article className="teacher-review-summary-card">
          <span>
            Response time
          </span>

          <strong>
            {formatDuration(
              attempt?.response_time_seconds,
            )}
          </strong>

          <small>
            Recorded attempt duration
          </small>
        </article>


        <article className="teacher-review-summary-card">
          <span>
            System diagnosis
          </span>

          <strong>
            {formatDiagnosisState(
              systemDiagnosis?.state,
            )}
          </strong>

          <small>
            {systemDiagnosis
              ? `${formatConfidence(
                  systemDiagnosis.confidence,
                )} confidence`
              : "No saved diagnosis"}
          </small>
        </article>
      </section>


      <div className="teacher-review-detail-main-grid">
        <section className="teacher-review-detail-card">
          <div className="teacher-review-card-heading">
            <div>
              <p className="teacher-review-detail-eyebrow">
                Student submission
              </p>

              <h2>
                Attempt content
              </h2>
            </div>
          </div>


          <div className="teacher-review-content-block">
            <h3>
              Final answer
            </h3>

            <div className="teacher-review-content-surface">
              {hasContent(
                attempt?.final_answer,
              )
                ? attempt?.final_answer
                : (
                    "No final answer was " +
                    "submitted."
                  )}
            </div>
          </div>


          <div className="teacher-review-content-block">
            <h3>
              Written reasoning
            </h3>

            <div className="teacher-review-content-surface teacher-review-content-prewrap">
              {hasContent(
                attempt?.written_reasoning,
              )
                ? attempt?.written_reasoning
                : (
                    "No written reasoning was " +
                    "submitted."
                  )}
            </div>
          </div>


          <div className="teacher-review-content-block">
            <h3>
              Source code
            </h3>

            <pre className="teacher-review-code-block">
              <code>
                {hasContent(
                  attempt?.source_code,
                )
                  ? attempt?.source_code
                  : (
                      "No source code was " +
                      "submitted."
                    )}
              </code>
            </pre>
          </div>


          <div className="teacher-review-content-block">
            <h3>
              Speech transcript
            </h3>

            <div className="teacher-review-content-surface teacher-review-content-prewrap">
              {hasContent(
                attempt?.speech_transcript,
              )
                ? attempt?.speech_transcript
                : (
                    "No speech transcript was " +
                    "submitted."
                  )}
            </div>
          </div>
        </section>


        <section className="teacher-review-detail-card">
          <div className="teacher-review-card-heading">
            <div>
              <p className="teacher-review-detail-eyebrow">
                Automated result
              </p>

              <h2>
                System diagnosis
              </h2>
            </div>

            {systemDiagnosis ? (
              <span className="teacher-review-diagnosis-confidence">
                {formatConfidence(
                  systemDiagnosis.confidence,
                )}
              </span>
            ) : null}
          </div>


          {systemDiagnosis ? (
            <>
              <div className="teacher-review-diagnosis-hero">
                <span className="teacher-review-diagnosis-pill">
                  {formatDiagnosisState(
                    systemDiagnosis.state,
                  )}
                </span>

                <strong>
                  {formatConfidence(
                    systemDiagnosis.confidence,
                  )}
                </strong>
              </div>

              <dl className="teacher-review-definition-list">
                <div>
                  <dt>
                    State
                  </dt>

                  <dd>
                    {formatDiagnosisState(
                      systemDiagnosis.state,
                    )}
                  </dd>
                </div>

                <div>
                  <dt>
                    Confidence
                  </dt>

                  <dd>
                    {formatConfidence(
                      systemDiagnosis.confidence,
                    )}
                  </dd>
                </div>

                <div>
                  <dt>
                    Misconception ID
                  </dt>

                  <dd>
                    {systemDiagnosis
                      .primary_misconception_id ??
                      "None"}
                  </dd>
                </div>

                <div>
                  <dt>
                    Model version
                  </dt>

                  <dd>
                    {systemDiagnosis.model_version}
                  </dd>
                </div>

                <div>
                  <dt>
                    Next action
                  </dt>

                  <dd>
                    {systemDiagnosis.next_action}
                  </dd>
                </div>

                <div>
                  <dt>
                    Created
                  </dt>

                  <dd>
                    {formatDateTime(
                      systemDiagnosis.created_at,
                    )}
                  </dd>
                </div>
              </dl>
            </>
          ) : (
            <div className="teacher-review-empty-state">
              No diagnosis was saved for this
              attempt.
            </div>
          )}


          <button
            type="button"
            className="teacher-review-primary-button teacher-review-card-action"
            disabled={
              !systemDiagnosis ||
              finalized ||
              isMutating
            }
            onClick={() => {
              void handleAccept();
            }}
          >
            {mutationAction === "accept"
              ? "Accepting..."
              : "Accept system diagnosis"}
          </button>
        </section>
      </div>


      <section className="teacher-review-detail-card">
        <div className="teacher-review-card-heading">
          <div>
            <p className="teacher-review-detail-eyebrow">
              Teacher decision
            </p>

            <h2>
              Review controls
            </h2>
          </div>

          <ReviewStatusBadge
            review={review}
          />
        </div>


        {finalized ? (
          <div className="teacher-review-finalized-view">
            <div className="teacher-review-finalized-summary">
              <div>
                <span>
                  Decision
                </span>

                <strong>
                  {formatDecision(
                    review?.decision,
                  )}
                </strong>
              </div>

              <div>
                <span>
                  Final state
                </span>

                <strong>
                  {formatDiagnosisState(
                    review?.final_state,
                  )}
                </strong>
              </div>

              <div>
                <span>
                  Reviewed
                </span>

                <strong>
                  {formatDateTime(
                    review?.reviewed_at,
                  )}
                </strong>
              </div>
            </div>

            <div className="teacher-review-finalized-details">
              <div className="teacher-review-content-block">
                <h3>
                  Final misconception
                </h3>

                <div className="teacher-review-content-surface">
                  {review?.final_misconception_id ??
                    "No misconception selected"}
                </div>
              </div>

              {review?.decision === "overridden" ? (
                <div className="teacher-review-content-block">
                  <h3>
                    Override reason
                  </h3>

                  <div className="teacher-review-content-surface teacher-review-content-prewrap">
                    {hasContent(
                      review.override_reason,
                    )
                      ? review.override_reason
                      : "No override reason was recorded."}
                  </div>
                </div>
              ) : null}

              <div className="teacher-review-content-block">
                <h3>
                  Teacher note
                </h3>

                <div className="teacher-review-content-surface teacher-review-content-prewrap">
                  {hasContent(
                    review?.teacher_note,
                  )
                    ? review?.teacher_note
                    : "No teacher note was recorded."}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="teacher-review-form-grid">
            <label className="teacher-review-field">
              <span>
                Decision
              </span>

              <select
                value={form.decision}
                disabled={isMutating}
                onChange={(event) => {
                  const nextDecision =
                    event.target.value as
                      | TeacherReviewDecision
                      | "";

                  updateForm(
                    "decision",
                    nextDecision,
                  );

                  if (
                    nextDecision === "accepted" &&
                    systemDiagnosis
                  ) {
                    updateForm(
                      "finalState",
                      systemDiagnosis.state,
                    );

                    updateForm(
                      "finalMisconceptionId",
                      systemDiagnosis
                        .primary_misconception_id ??
                        "",
                    );

                    updateForm(
                      "overrideReason",
                      "",
                    );
                  }
                }}
              >
                <option value="">
                  Select decision
                </option>

                <option value="accepted">
                  Accepted
                </option>

                <option value="overridden">
                  Overridden
                </option>
              </select>
            </label>

            <label className="teacher-review-field">
              <span>
                Final diagnosis state
              </span>

              <select
                value={form.finalState}
                disabled={isMutating}
                onChange={(event) => {
                  const value =
                    event.target.value as
                      | DiagnosisState
                      | "";

                  updateForm(
                    "finalState",
                    value,
                  );

                  if (
                    value ===
                    "no_misconception"
                  ) {
                    updateForm(
                      "finalMisconceptionId",
                      "",
                    );
                  }
                }}
              >
                <option value="">
                  Select final state
                </option>

                {DIAGNOSIS_STATE_OPTIONS.map(
                  (option) => (
                    <option
                      key={option.value}
                      value={option.value}
                    >
                      {option.label}
                    </option>
                  ),
                )}
              </select>
            </label>

            <label className="teacher-review-field teacher-review-field-wide">
              <span>
                Final misconception ID
              </span>

              <input
                type="text"
                value={
                  form.finalMisconceptionId
                }
                disabled={
                  isMutating ||
                  form.finalState ===
                    "no_misconception"
                }
                placeholder="Optional misconception UUID"
                onChange={(event) => {
                  updateForm(
                    "finalMisconceptionId",
                    event.target.value,
                  );
                }}
              />
            </label>

            <label className="teacher-review-field teacher-review-field-wide">
              <span>
                Override reason
              </span>

              <textarea
                value={form.overrideReason}
                disabled={
                  isMutating ||
                  form.decision ===
                    "accepted"
                }
                placeholder={
                  "Explain why the automated " +
                  "diagnosis should be changed."
                }
                rows={4}
                onChange={(event) => {
                  updateForm(
                    "overrideReason",
                    event.target.value,
                  );
                }}
              />
            </label>

            <label className="teacher-review-field teacher-review-field-wide">
              <span>
                Teacher note
              </span>

              <textarea
                value={form.teacherNote}
                disabled={isMutating}
                placeholder={
                  "Add an optional internal note."
                }
                rows={4}
                onChange={(event) => {
                  updateForm(
                    "teacherNote",
                    event.target.value,
                  );
                }}
              />
            </label>
          </div>
        )}

        <div className="teacher-review-action-row">
          {!finalized ? (
            <>
              <button
                type="button"
                className="teacher-review-secondary-button"
                disabled={isMutating}
                onClick={() => {
                  void handleSaveDraft();
                }}
              >
                {mutationAction === "save"
                  ? "Saving..."
                  : "Save draft"}
              </button>

              <button
                type="button"
                className="teacher-review-secondary-button"
                disabled={
                  isMutating ||
                  form.decision ===
                    "accepted"
                }
                onClick={() => {
                  void handleOverride();
                }}
              >
                {mutationAction === "override"
                  ? "Saving override..."
                  : "Save override"}
              </button>

              <button
                type="button"
                className="teacher-review-primary-button"
                disabled={!canFinalize}
                onClick={() => {
                  void handleFinalize();
                }}
              >
                {mutationAction === "finalize"
                  ? "Finalizing..."
                  : "Finalize review"}
              </button>
            </>
          ) : (
            <button
              type="button"
              className="teacher-review-primary-button"
              disabled={isMutating}
              onClick={() => {
                void handleReopen();
              }}
            >
              {mutationAction === "reopen"
                ? "Reopening..."
                : "Reopen review"}
            </button>
          )}
        </div>


        {review ? (
          <details className="teacher-review-metadata-panel">
            <summary>
              Review metadata
            </summary>

            <dl className="teacher-review-definition-list teacher-review-saved-metadata">
              <div>
                <dt>
                  Review ID
                </dt>

                <dd>
                  {review.id}
                </dd>
              </div>

              <div>
                <dt>
                  Teacher ID
                </dt>

                <dd>
                  {review.teacher_id}
                </dd>
              </div>

              <div>
                <dt>
                  Decision
                </dt>

                <dd>
                  {formatDecision(
                    review.decision,
                  )}
                </dd>
              </div>

              <div>
                <dt>
                  Created
                </dt>

                <dd>
                  {formatDateTime(
                    review.created_at,
                  )}
                </dd>
              </div>

              <div>
                <dt>
                  Updated
                </dt>

                <dd>
                  {formatDateTime(
                    review.updated_at,
                  )}
                </dd>
              </div>

              <div>
                <dt>
                  Reviewed
                </dt>

                <dd>
                  {formatDateTime(
                    review.reviewed_at,
                  )}
                </dd>
              </div>
            </dl>
          </details>
        ) : null}
      </section>
    </main>
  );
}