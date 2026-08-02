import { useEffect, useState } from "react";
import "./App.css";

import { LandingPage } from "./pages/LandingPage";
import {
  ProblemBankPage,
  type ProblemProgressState,
} from "./pages/ProblemBankPage";
import { ProblemDetailPage } from "./pages/ProblemDetailPage";
import { StudentSessionPage } from "./pages/StudentSessionPage";
import { TeacherAttemptDetailPage } from "./pages/TeacherAttemptDetailPage";
import { TeacherAttemptsPage } from "./pages/TeacherAttemptsPage";
import { TeacherDashboardPage } from "./pages/TeacherDashboardPage";
import { TeacherProblemAnalyticsPage } from "./pages/TeacherProblemAnalyticsPage";
import { TeacherStudentHistoryPage } from "./pages/TeacherStudentHistoryPage";
import type { StudentSessionResponse } from "./types/student";

type AppView =
  | "landing"
  | "student-session"
  | "problem-bank"
  | "problem-detail"
  | "teacher-dashboard"
  | "teacher-attempts"
  | "teacher-attempt-detail"
  | "teacher-student-history"
  | "teacher-problem-analytics";

type ProblemProgressMap = Record<
  string,
  ProblemProgressState
>;

const SESSION_STORAGE_KEY = "studentSession";
const VIEW_STORAGE_KEY = "studentAppView";
const SELECTED_PROBLEM_STORAGE_KEY = "selectedProblemId";

const SELECTED_TEACHER_ATTEMPT_STORAGE_KEY =
  "selectedTeacherAttemptId";

const SELECTED_TEACHER_STUDENT_STORAGE_KEY =
  "selectedTeacherStudentAliasId";

const SELECTED_TEACHER_PROBLEM_STORAGE_KEY =
  "selectedTeacherProblemId";

function getProgressStorageKey(
  sessionId: string
): string {
  return `problemProgress:${sessionId}`;
}

function isTeacherView(view: AppView): boolean {
  return (
    view === "teacher-dashboard" ||
    view === "teacher-attempts" ||
    view === "teacher-attempt-detail" ||
    view === "teacher-student-history" ||
    view === "teacher-problem-analytics"
  );
}

function isValidAppView(
  value: string | null
): value is AppView {
  return (
    value === "landing" ||
    value === "student-session" ||
    value === "problem-bank" ||
    value === "problem-detail" ||
    value === "teacher-dashboard" ||
    value === "teacher-attempts" ||
    value === "teacher-attempt-detail" ||
    value === "teacher-student-history" ||
    value === "teacher-problem-analytics"
  );
}

function readStoredProgress(
  sessionId: string
): ProblemProgressMap {
  const storageKey =
    getProgressStorageKey(sessionId);

  const storedProgress =
    localStorage.getItem(storageKey);

  if (!storedProgress) {
    return {};
  }

  try {
    return JSON.parse(
      storedProgress
    ) as ProblemProgressMap;
  } catch {
    localStorage.removeItem(storageKey);
    return {};
  }
}

function App() {
  const [session, setSession] =
    useState<StudentSessionResponse | null>(
      null
    );

  const [
    selectedProblemId,
    setSelectedProblemId,
  ] = useState<string | null>(null);

  const [
    selectedTeacherAttemptId,
    setSelectedTeacherAttemptId,
  ] = useState<string | null>(null);

  const [
    selectedTeacherStudentAliasId,
    setSelectedTeacherStudentAliasId,
  ] = useState<string | null>(null);

  /*
   * This value serves two purposes:
   *
   * 1. It identifies the problem shown by
   *    TeacherProblemAnalyticsPage.
   *
   * 2. It becomes the initial problem filter
   *    when TeacherAttemptsPage is opened from
   *    problem analytics.
   */
  const [
    selectedTeacherProblemId,
    setSelectedTeacherProblemId,
  ] = useState<string | null>(null);

  const [
    progressByProblemId,
    setProgressByProblemId,
  ] = useState<ProblemProgressMap>({});

  const [view, setView] =
    useState<AppView>("landing");

  const [isHydrated, setIsHydrated] =
    useState(false);

  useEffect(() => {
    const storedView =
      localStorage.getItem(
        VIEW_STORAGE_KEY
      );

    const restoredView: AppView =
      isValidAppView(storedView)
        ? storedView
        : "landing";

    const storedTeacherAttemptId =
      localStorage.getItem(
        SELECTED_TEACHER_ATTEMPT_STORAGE_KEY
      );

    const storedTeacherStudentAliasId =
      localStorage.getItem(
        SELECTED_TEACHER_STUDENT_STORAGE_KEY
      );

    const storedTeacherProblemId =
      localStorage.getItem(
        SELECTED_TEACHER_PROBLEM_STORAGE_KEY
      );

    if (isTeacherView(restoredView)) {
      setSelectedProblemId(null);

      setSelectedTeacherAttemptId(
        storedTeacherAttemptId
      );

      setSelectedTeacherStudentAliasId(
        storedTeacherStudentAliasId
      );

      setSelectedTeacherProblemId(
        storedTeacherProblemId
      );

      if (
        restoredView ===
          "teacher-attempt-detail" &&
        storedTeacherAttemptId
      ) {
        setView("teacher-attempt-detail");
      } else if (
        restoredView ===
          "teacher-student-history" &&
        storedTeacherStudentAliasId
      ) {
        setView("teacher-student-history");
      } else if (
        restoredView ===
          "teacher-problem-analytics" &&
        storedTeacherProblemId
      ) {
        setView("teacher-problem-analytics");
      } else if (
        restoredView ===
          "teacher-attempt-detail" ||
        restoredView ===
          "teacher-student-history" ||
        restoredView ===
          "teacher-problem-analytics"
      ) {
        setSelectedTeacherAttemptId(null);
        setSelectedTeacherStudentAliasId(null);
        setView("teacher-attempts");
      } else {
        setView(restoredView);
      }

      setIsHydrated(true);
      return;
    }

    const storedSession =
      localStorage.getItem(
        SESSION_STORAGE_KEY
      );

    if (!storedSession) {
      setView(
        restoredView === "student-session"
          ? "student-session"
          : "landing"
      );

      setIsHydrated(true);
      return;
    }

    try {
      const parsedSession = JSON.parse(
        storedSession
      ) as StudentSessionResponse;

      const storedProblemId =
        localStorage.getItem(
          SELECTED_PROBLEM_STORAGE_KEY
        );

      const restoredProgress =
        readStoredProgress(
          parsedSession.student_alias_id
        );

      setSession(parsedSession);

      setProgressByProblemId(
        restoredProgress
      );

      if (
        storedProblemId &&
        restoredView === "problem-detail"
      ) {
        setSelectedProblemId(
          storedProblemId
        );

        setView("problem-detail");
      } else {
        setSelectedProblemId(null);
        setView("problem-bank");
      }
    } catch {
      localStorage.removeItem(
        SESSION_STORAGE_KEY
      );

      localStorage.removeItem(
        VIEW_STORAGE_KEY
      );

      localStorage.removeItem(
        SELECTED_PROBLEM_STORAGE_KEY
      );

      localStorage.removeItem(
        SELECTED_TEACHER_ATTEMPT_STORAGE_KEY
      );

      localStorage.removeItem(
        SELECTED_TEACHER_STUDENT_STORAGE_KEY
      );

      localStorage.removeItem(
        SELECTED_TEACHER_PROBLEM_STORAGE_KEY
      );

      setSession(null);
      setSelectedProblemId(null);
      setSelectedTeacherAttemptId(null);
      setSelectedTeacherStudentAliasId(null);
      setSelectedTeacherProblemId(null);
      setProgressByProblemId({});
      setView("landing");
    } finally {
      setIsHydrated(true);
    }
  }, []);

  useEffect(() => {
    if (!isHydrated) {
      return;
    }

    localStorage.setItem(
      VIEW_STORAGE_KEY,
      view
    );
  }, [isHydrated, view]);

  useEffect(() => {
    if (!isHydrated) {
      return;
    }

    if (selectedProblemId) {
      localStorage.setItem(
        SELECTED_PROBLEM_STORAGE_KEY,
        selectedProblemId
      );
    } else {
      localStorage.removeItem(
        SELECTED_PROBLEM_STORAGE_KEY
      );
    }
  }, [
    isHydrated,
    selectedProblemId,
  ]);

  useEffect(() => {
    if (!isHydrated) {
      return;
    }

    if (selectedTeacherAttemptId) {
      localStorage.setItem(
        SELECTED_TEACHER_ATTEMPT_STORAGE_KEY,
        selectedTeacherAttemptId
      );
    } else {
      localStorage.removeItem(
        SELECTED_TEACHER_ATTEMPT_STORAGE_KEY
      );
    }
  }, [
    isHydrated,
    selectedTeacherAttemptId,
  ]);

  useEffect(() => {
    if (!isHydrated) {
      return;
    }

    if (selectedTeacherStudentAliasId) {
      localStorage.setItem(
        SELECTED_TEACHER_STUDENT_STORAGE_KEY,
        selectedTeacherStudentAliasId
      );
    } else {
      localStorage.removeItem(
        SELECTED_TEACHER_STUDENT_STORAGE_KEY
      );
    }
  }, [
    isHydrated,
    selectedTeacherStudentAliasId,
  ]);

  useEffect(() => {
    if (!isHydrated) {
      return;
    }

    if (selectedTeacherProblemId) {
      localStorage.setItem(
        SELECTED_TEACHER_PROBLEM_STORAGE_KEY,
        selectedTeacherProblemId
      );
    } else {
      localStorage.removeItem(
        SELECTED_TEACHER_PROBLEM_STORAGE_KEY
      );
    }
  }, [
    isHydrated,
    selectedTeacherProblemId,
  ]);

  useEffect(() => {
    if (!isHydrated || !session) {
      return;
    }

    localStorage.setItem(
      getProgressStorageKey(
        session.student_alias_id
      ),
      JSON.stringify(
        progressByProblemId
      )
    );
  }, [
    isHydrated,
    progressByProblemId,
    session,
  ]);

  function clearTeacherSelection(): void {
    setSelectedTeacherAttemptId(null);
    setSelectedTeacherStudentAliasId(null);
    setSelectedTeacherProblemId(null);
  }

  function clearTeacherRecordSelection(): void {
    /*
     * Keep selectedTeacherProblemId intact.
     *
     * This preserves the problem filter when the
     * teacher returns from attempt detail to the
     * related attempts list.
     */
    setSelectedTeacherAttemptId(null);
    setSelectedTeacherStudentAliasId(null);
  }

  function handleStartStudent(): void {
    setSelectedProblemId(null);
    clearTeacherSelection();
    setView("student-session");
  }

  function handleStartTeacher(): void {
    setSelectedProblemId(null);
    clearTeacherSelection();
    setView("teacher-dashboard");
  }

  function handleOpenTeacherAttempts(): void {
    /*
     * Opening from the dashboard means:
     * show every attempt, with no problem filter.
     */
    clearTeacherSelection();
    setView("teacher-attempts");
  }

  function handleOpenRelatedTeacherAttempts(
    problemId: string
  ): void {
    /*
     * Opening from problem analytics means:
     * retain the problem ID and pass it into
     * TeacherAttemptsPage as initialProblemId.
     */
    setSelectedTeacherAttemptId(null);
    setSelectedTeacherStudentAliasId(null);
    setSelectedTeacherProblemId(problemId);
    setView("teacher-attempts");
  }

  function handleOpenTeacherAttempt(
    attemptId: string
  ): void {
    /*
     * Do not clear selectedTeacherProblemId here.
     * It may contain the active related-attempts
     * filter that must be restored on Back.
     */
    setSelectedTeacherAttemptId(
      attemptId
    );

    setView("teacher-attempt-detail");
  }

  function handleOpenStudentHistory(
    studentAliasId: string
  ): void {
    setSelectedTeacherStudentAliasId(
      studentAliasId
    );

    setView("teacher-student-history");
  }

  function handleOpenProblemAnalytics(
    problemId: string
  ): void {
    setSelectedTeacherProblemId(
      problemId
    );

    setView("teacher-problem-analytics");
  }

  function handleBackToTeacherAttempts(): void {
    /*
     * Clear the selected record but retain the
     * selected problem filter.
     */
    clearTeacherRecordSelection();
    setView("teacher-attempts");
  }

  function handleBackFromStudentHistory(): void {
    setSelectedTeacherStudentAliasId(null);

    if (selectedTeacherAttemptId) {
      setView("teacher-attempt-detail");
      return;
    }

    setView("teacher-attempts");
  }

  function handleBackFromProblemAnalytics(): void {
    if (selectedTeacherStudentAliasId) {
      setView("teacher-student-history");
      return;
    }

    if (selectedTeacherAttemptId) {
      setView("teacher-attempt-detail");
      return;
    }

    /*
     * Keep selectedTeacherProblemId so the
     * attempts page can restore the problem
     * filter when returning from analytics.
     */
    setView("teacher-attempts");
  }

  function handleBackToTeacherDashboard(): void {
    clearTeacherSelection();
    setView("teacher-dashboard");
  }

  function handleSessionCreated(
    newSession: StudentSessionResponse
  ): void {
    localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify(newSession)
    );

    setSession(newSession);
    setSelectedProblemId(null);
    clearTeacherSelection();

    setProgressByProblemId(
      readStoredProgress(
        newSession.student_alias_id
      )
    );

    setView("problem-bank");
  }

  function handleProblemSelected(
    problemId: string
  ): void {
    setProgressByProblemId(
      (currentProgress) => {
        const existingProgress =
          currentProgress[problemId] ??
          "not_started";

        if (
          existingProgress !==
          "not_started"
        ) {
          return currentProgress;
        }

        return {
          ...currentProgress,
          [problemId]: "in_progress",
        };
      }
    );

    setSelectedProblemId(problemId);
    setView("problem-detail");
  }

  function handleBackToProblemBank(): void {
    setSelectedProblemId(null);
    setView("problem-bank");
  }

  function handleBackToLanding(): void {
    setSelectedProblemId(null);
    clearTeacherSelection();
    setView("landing");
  }

  function handleResetSession(): void {
    if (session) {
      localStorage.removeItem(
        getProgressStorageKey(
          session.student_alias_id
        )
      );
    }

    localStorage.removeItem(
      SESSION_STORAGE_KEY
    );

    localStorage.removeItem(
      VIEW_STORAGE_KEY
    );

    localStorage.removeItem(
      SELECTED_PROBLEM_STORAGE_KEY
    );

    localStorage.removeItem(
      SELECTED_TEACHER_ATTEMPT_STORAGE_KEY
    );

    localStorage.removeItem(
      SELECTED_TEACHER_STUDENT_STORAGE_KEY
    );

    localStorage.removeItem(
      SELECTED_TEACHER_PROBLEM_STORAGE_KEY
    );

    setSession(null);
    setSelectedProblemId(null);
    clearTeacherSelection();
    setProgressByProblemId({});
    setView("landing");
  }

  if (!isHydrated) {
    return (
      <main className="app-loading-page">
        <section className="state-card">
          Loading workspace...
        </section>
      </main>
    );
  }

  if (view === "landing") {
    return (
      <LandingPage
        onStartStudent={
          handleStartStudent
        }
        onStartTeacher={
          handleStartTeacher
        }
      />
    );
  }

  if (view === "teacher-dashboard") {
    return (
      <TeacherDashboardPage
        onBack={handleBackToLanding}
        onOpenAttempts={
          handleOpenTeacherAttempts
        }
      />
    );
  }

  if (view === "teacher-attempts") {
    return (
      <TeacherAttemptsPage
        onBack={
          handleBackToTeacherDashboard
        }
        onOpenAttempt={
          handleOpenTeacherAttempt
        }
        onOpenStudentHistory={
          handleOpenStudentHistory
        }
        onOpenProblemAnalytics={
          handleOpenProblemAnalytics
        }
        initialProblemId={
          selectedTeacherProblemId ??
          undefined
        }
      />
    );
  }

  if (
    view ===
      "teacher-attempt-detail" &&
    selectedTeacherAttemptId
  ) {
    return (
      <TeacherAttemptDetailPage
        attemptId={
          selectedTeacherAttemptId
        }
        onBack={
          handleBackToTeacherAttempts
        }
        onOpenStudentHistory={
          handleOpenStudentHistory
        }
        onOpenProblemAnalytics={
          handleOpenProblemAnalytics
        }
      />
    );
  }

  if (
    view ===
      "teacher-student-history" &&
    selectedTeacherStudentAliasId
  ) {
    return (
      <TeacherStudentHistoryPage
        studentAliasId={
          selectedTeacherStudentAliasId
        }
        onBack={
          handleBackFromStudentHistory
        }
        onOpenAttempt={
          handleOpenTeacherAttempt
        }
        onOpenProblemAnalytics={
          handleOpenProblemAnalytics
        }
      />
    );
  }

  if (
    view ===
      "teacher-problem-analytics" &&
    selectedTeacherProblemId
  ) {
    return (
      <TeacherProblemAnalyticsPage
        problemId={
          selectedTeacherProblemId
        }
        onBack={
          handleBackFromProblemAnalytics
        }
        onOpenAttempts={
          handleOpenRelatedTeacherAttempts
        }
      />
    );
  }

  /*
   * Recovery fallback for an invalid or missing
   * teacher record selection.
   */
  if (
    view === "teacher-attempt-detail" ||
    view === "teacher-student-history" ||
    view === "teacher-problem-analytics"
  ) {
    return (
      <TeacherAttemptsPage
        onBack={
          handleBackToTeacherDashboard
        }
        onOpenAttempt={
          handleOpenTeacherAttempt
        }
        onOpenStudentHistory={
          handleOpenStudentHistory
        }
        onOpenProblemAnalytics={
          handleOpenProblemAnalytics
        }
        initialProblemId={
          selectedTeacherProblemId ??
          undefined
        }
      />
    );
  }

  if (view === "student-session") {
    return (
      <StudentSessionPage
        onSessionCreated={
          handleSessionCreated
        }
      />
    );
  }

  if (!session) {
    return (
      <LandingPage
        onStartStudent={
          handleStartStudent
        }
        onStartTeacher={
          handleStartTeacher
        }
      />
    );
  }

  if (
    view === "problem-detail" &&
    selectedProblemId
  ) {
    return (
      <ProblemDetailPage
        problemId={selectedProblemId}
        session={session}
        onBack={
          handleBackToProblemBank
        }
      />
    );
  }

  return (
    <ProblemBankPage
      session={session}
      progressByProblemId={
        progressByProblemId
      }
      onProblemSelected={
        handleProblemSelected
      }
      onResetSession={
        handleResetSession
      }
    />
  );
}

export default App;