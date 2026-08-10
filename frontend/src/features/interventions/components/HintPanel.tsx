import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getHintProgress,
  getRevealedHints,
  revealNextHint,
} from "../api";

import type {
  HintDeliveryResponse,
  HintProgressResponse,
} from "../types";


type HintPanelProps = {
  diagnosisId: string;
  studentAliasId: string;
  misconceptionCode?: string | null;
  misconceptionName?: string | null;
  onHintRevealed?: (
    hint: HintDeliveryResponse
  ) => void;
};


function formatHintLevel(
  level: number
): string {
  return `Level ${level}`;
}


function getHintLevelDescription(
  level: number
): string {
  if (level === 1) {
    return "Conceptual hint";
  }

  if (level === 2) {
    return "Guided hint";
  }

  return "Strong guidance";
}


function normalizeErrorMessage(
  error: unknown,
  fallback: string
): string {
  return error instanceof Error
    ? error.message
    : fallback;
}


function isAbortError(
  error: unknown
): boolean {
  return (
    error instanceof DOMException &&
    error.name === "AbortError"
  );
}


function buildProgressFromHints(
  diagnosisId: string,
  studentAliasId: string,
  hints: HintDeliveryResponse[]
): HintProgressResponse | null {
  if (hints.length === 0) {
    return null;
  }

  const orderedHints = [...hints].sort(
    (first, second) =>
      first.level - second.level
  );

  const latestHint =
    orderedHints[
      orderedHints.length - 1
    ];

  const maximumLevel = 3;

  return {
    diagnosis_id: diagnosisId,
    attempt_id:
      latestHint.attempt_id,
    student_alias_id:
      studentAliasId,
    misconception_id:
      latestHint.misconception_id,
    revealed_levels: orderedHints.map(
      (hint) => hint.level
    ),
    next_level:
      latestHint.level >= maximumLevel
        ? null
        : latestHint.level + 1,
    maximum_level: maximumLevel,
    completed:
      latestHint.level >= maximumLevel ||
      latestHint.is_final_level,
  };
}


export default function HintPanel({
  diagnosisId,
  studentAliasId,
  misconceptionCode,
  misconceptionName,
  onHintRevealed,
}: HintPanelProps) {
  const [progress, setProgress] =
    useState<HintProgressResponse | null>(
      null
    );

  const [revealedHints, setRevealedHints] =
    useState<HintDeliveryResponse[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [revealing, setRevealing] =
    useState(false);

  const [progressError, setProgressError] =
    useState<string | null>(null);

  const [historyError, setHistoryError] =
    useState<string | null>(null);

  const normalizedDiagnosisId =
    diagnosisId.trim();

  const normalizedStudentAliasId =
    studentAliasId.trim();

  const loadHintState = useCallback(
    async (
      signal?: AbortSignal
    ) => {
      setProgressError(null);
      setHistoryError(null);

      let loadedHints:
        | HintDeliveryResponse[]
        | null = null;

      try {
        const revealedResult =
          await getRevealedHints(
            normalizedDiagnosisId,
            normalizedStudentAliasId,
            signal
          );

        loadedHints = [
          ...revealedResult.items,
        ].sort(
          (first, second) =>
            first.level - second.level
        );

        setRevealedHints(
          loadedHints
        );
      } catch (error) {
        if (isAbortError(error)) {
          throw error;
        }

        setHistoryError(
          normalizeErrorMessage(
            error,
            "Previously revealed hints could not be loaded."
          )
        );

        setRevealedHints([]);
      }

      try {
        const progressResult =
          await getHintProgress(
            normalizedDiagnosisId,
            normalizedStudentAliasId,
            signal
          );

        setProgress(progressResult);
      } catch (error) {
        if (isAbortError(error)) {
          throw error;
        }

        const fallbackProgress =
          buildProgressFromHints(
            normalizedDiagnosisId,
            normalizedStudentAliasId,
            loadedHints ?? []
          );

        setProgress(
          fallbackProgress
        );

        setProgressError(
          normalizeErrorMessage(
            error,
            "Hint progress could not be loaded."
          )
        );
      }
    },
    [
      normalizedDiagnosisId,
      normalizedStudentAliasId,
    ]
  );

  useEffect(() => {
    const controller =
      new AbortController();

    async function load() {
      if (
        !normalizedDiagnosisId ||
        !normalizedStudentAliasId
      ) {
        setLoading(false);
        setProgress(null);
        setRevealedHints([]);
        setProgressError(
          "Diagnosis ID and student alias ID are required."
        );
        return;
      }

      try {
        setLoading(true);

        await loadHintState(
          controller.signal
        );
      } catch (error) {
        if (!isAbortError(error)) {
          setProgressError(
            normalizeErrorMessage(
              error,
              "Unable to load hint state."
            )
          );
        }
      } finally {
        if (
          !controller.signal.aborted
        ) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      controller.abort();
    };
  }, [
    loadHintState,
    normalizedDiagnosisId,
    normalizedStudentAliasId,
  ]);

  const nextLevel =
    progress?.next_level ?? null;

  const maximumLevel =
    progress?.maximum_level ?? 3;

  const completed =
    progress?.completed ?? false;

  const revealButtonLabel =
    useMemo(() => {
      if (revealing) {
        return "Revealing hint...";
      }

      if (completed) {
        return "All hints revealed";
      }

      if (nextLevel === null) {
        return "Retry loading progress";
      }

      return `Reveal ${formatHintLevel(
        nextLevel
      )}`;
    }, [
      completed,
      nextLevel,
      revealing,
    ]);

  const progressSteps =
    useMemo(
      () =>
        Array.from(
          {
            length: maximumLevel,
          },
          (_, index) => index + 1
        ),
      [maximumLevel]
    );

  async function handleRevealNextHint() {
    if (
      revealing ||
      completed
    ) {
      return;
    }

    if (nextLevel === null) {
      try {
        setLoading(true);
        await loadHintState();
      } finally {
        setLoading(false);
      }

      return;
    }

    try {
      setRevealing(true);
      setProgressError(null);

      const revealed =
        await revealNextHint(
          normalizedDiagnosisId,
          normalizedStudentAliasId
        );

      setRevealedHints(
        (currentHints) => {
          const alreadyExists =
            currentHints.some(
              (item) =>
                item.hint_event_id ===
                revealed.hint_event_id
            );

          if (alreadyExists) {
            return currentHints;
          }

          return [
            ...currentHints,
            revealed,
          ].sort(
            (
              first,
              second
            ) =>
              first.level -
              second.level
          );
        }
      );

      setProgress(
        (currentProgress) => {
          const resolvedMaximumLevel =
            currentProgress
              ?.maximum_level ?? 3;

          const next =
            revealed.level >=
            resolvedMaximumLevel
              ? null
              : revealed.level + 1;

          return {
            diagnosis_id:
              revealed.diagnosis_id,
            attempt_id:
              revealed.attempt_id,
            student_alias_id:
              revealed.student_alias_id,
            misconception_id:
              revealed.misconception_id,
            revealed_levels: [
              ...new Set([
                ...(
                  currentProgress
                    ?.revealed_levels ??
                  []
                ),
                revealed.level,
              ]),
            ].sort(
              (
                first,
                second
              ) => first - second
            ),
            next_level: next,
            maximum_level:
              resolvedMaximumLevel,
            completed:
              revealed.is_final_level ||
              revealed.level >=
                resolvedMaximumLevel,
          };
        }
      );

      onHintRevealed?.(
        revealed
      );
    } catch (error) {
      setProgressError(
        normalizeErrorMessage(
          error,
          "Unable to reveal the next hint."
        )
      );
    } finally {
      setRevealing(false);
    }
  }

  if (loading) {
    return (
      <section
        className="intervention-card hint-panel"
        aria-busy="true"
      >
        <div className="intervention-card-header">
          <div>
            <p className="section-kicker">
              Guided intervention
            </p>

            <h3>
              Preparing progressive hints
            </h3>

            <p>
              Loading your current hint
              level and previous guidance.
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section
      className="intervention-card hint-panel"
      aria-labelledby="hint-panel-title"
    >
      <div className="intervention-card-header">
        <div>
          <p className="section-kicker">
            Guided intervention
          </p>

          <h3 id="hint-panel-title">
            Progressive hints
          </h3>

          <p>
            Reveal one approved hint at a
            time. Each level gives more
            guidance without immediately
            exposing the full solution.
          </p>
        </div>

        <div className="hint-progress-summary">
          <strong>
            {revealedHints.length}/
            {maximumLevel}
          </strong>

          <span>hints revealed</span>
        </div>
      </div>

      {(
        misconceptionCode ||
        misconceptionName
      ) && (
        <div className="hint-context-row">
          {misconceptionCode && (
            <span className="problem-chip">
              {misconceptionCode}
            </span>
          )}

          {misconceptionName && (
            <strong>
              {misconceptionName}
            </strong>
          )}
        </div>
      )}

      <div
        className="hint-level-track"
        aria-label="Hint progression"
      >
        {progressSteps.map(
          (level) => {
            const isRevealed =
              revealedHints.some(
                (hint) =>
                  hint.level === level
              );

            const isNext =
              nextLevel === level;

            return (
              <div
                className={[
                  "hint-level-step",
                  isRevealed
                    ? "revealed"
                    : "",
                  isNext
                    ? "next"
                    : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                key={level}
              >
                <span>
                  {isRevealed
                    ? "✓"
                    : level}
                </span>

                <strong>
                  {formatHintLevel(level)}
                </strong>

                <small>
                  {getHintLevelDescription(
                    level
                  )}
                </small>
              </div>
            );
          }
        )}
      </div>

      {revealedHints.length > 0 ? (
        <div className="revealed-hint-list">
          {revealedHints.map(
            (hint) => (
              <article
                className="revealed-hint-item"
                key={
                  hint.hint_event_id
                }
              >
                <div className="revealed-hint-meta">
                  <span className="state-pill state-pill-info">
                    {formatHintLevel(
                      hint.level
                    )}
                  </span>

                  <span>
                    {getHintLevelDescription(
                      hint.level
                    )}
                  </span>
                </div>

                <p>
                  {hint.hint_text}
                </p>
              </article>
            )
          )}
        </div>
      ) : (
        <div className="intervention-empty-state">
          <strong>
            Start with a conceptual hint.
          </strong>

          <p>
            Level 1 points you toward the
            governing concept without
            giving away the implementation.
          </p>
        </div>
      )}

      {progressError && (
        <div
          className="attempt-error"
          role="alert"
        >
          <strong>
            Hint service response
          </strong>

          <p>
            {progressError}
          </p>

          <small>
            Diagnosis ID:{" "}
            {normalizedDiagnosisId}
          </small>
        </div>
      )}

      {historyError && (
        <div
          className="diagnosis-note"
          role="status"
        >
          {historyError}
        </div>
      )}

      <div className="intervention-actions">
        <div>
          {completed ? (
            <>
              <strong>
                Hint progression complete
              </strong>

              <p>
                You have reached the
                strongest approved hint.
                Apply the guidance in a
                linked retry.
              </p>
            </>
          ) : (
            <>
              <strong>
                {nextLevel === null
                  ? "Progress needs to be reloaded"
                  : `Next: ${formatHintLevel(
                      nextLevel
                    )}`}
              </strong>

              <p>
                {nextLevel === null
                  ? "Reload hint progress before revealing the next level."
                  : getHintLevelDescription(
                      nextLevel
                    )}
              </p>
            </>
          )}
        </div>

        <button
          className="primary-button"
          type="button"
          onClick={
            handleRevealNextHint
          }
          disabled={
            revealing ||
            completed
          }
        >
          {revealButtonLabel}
        </button>
      </div>
    </section>
  );
}