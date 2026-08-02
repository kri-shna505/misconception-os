import { useEffect, useState } from "react";
import "./App.css";

import { LandingPage } from "./pages/LandingPage";
import {
  ProblemBankPage,
  type ProblemProgressState,
} from "./pages/ProblemBankPage";
import { ProblemDetailPage } from "./pages/ProblemDetailPage";
import { StudentSessionPage } from "./pages/StudentSessionPage";
import type { StudentSessionResponse } from "./types/student";

type AppView =
  | "landing"
  | "student-session"
  | "problem-bank"
  | "problem-detail";

type ProblemProgressMap = Record<string, ProblemProgressState>;

const SESSION_STORAGE_KEY = "studentSession";
const VIEW_STORAGE_KEY = "studentAppView";
const SELECTED_PROBLEM_STORAGE_KEY = "selectedProblemId";

function getProgressStorageKey(sessionId: string) {
  return `problemProgress:${sessionId}`;
}

function isValidAppView(value: string | null): value is AppView {
  return (
    value === "landing" ||
    value === "student-session" ||
    value === "problem-bank" ||
    value === "problem-detail"
  );
}

function readStoredProgress(sessionId: string): ProblemProgressMap {
  const storedProgress = localStorage.getItem(
    getProgressStorageKey(sessionId)
  );

  if (!storedProgress) {
    return {};
  }

  try {
    return JSON.parse(storedProgress) as ProblemProgressMap;
  } catch {
    localStorage.removeItem(getProgressStorageKey(sessionId));
    return {};
  }
}

function App() {
  const [session, setSession] =
    useState<StudentSessionResponse | null>(null);

  const [selectedProblemId, setSelectedProblemId] =
    useState<string | null>(null);

  const [progressByProblemId, setProgressByProblemId] =
    useState<ProblemProgressMap>({});

  const [view, setView] = useState<AppView>("landing");
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    const storedSession = localStorage.getItem(SESSION_STORAGE_KEY);

    if (!storedSession) {
      setIsHydrated(true);
      return;
    }

    try {
      const parsedSession =
        JSON.parse(storedSession) as StudentSessionResponse;

      const storedView = localStorage.getItem(VIEW_STORAGE_KEY);
      const storedProblemId = localStorage.getItem(
        SELECTED_PROBLEM_STORAGE_KEY
      );

      const restoredProgress = readStoredProgress(
        parsedSession.student_alias_id
      );

      setSession(parsedSession);
      setProgressByProblemId(restoredProgress);

      if (
        storedProblemId &&
        storedView === "problem-detail"
      ) {
        setSelectedProblemId(storedProblemId);
        setView("problem-detail");
      } else {
        setSelectedProblemId(null);
        setView(
          isValidAppView(storedView) &&
            storedView === "problem-bank"
            ? "problem-bank"
            : "problem-bank"
        );
      }
    } catch {
      localStorage.removeItem(SESSION_STORAGE_KEY);
      localStorage.removeItem(VIEW_STORAGE_KEY);
      localStorage.removeItem(SELECTED_PROBLEM_STORAGE_KEY);

      setSession(null);
      setSelectedProblemId(null);
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

    localStorage.setItem(VIEW_STORAGE_KEY, view);
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
  }, [isHydrated, selectedProblemId]);

  useEffect(() => {
    if (!isHydrated || !session) {
      return;
    }

    localStorage.setItem(
      getProgressStorageKey(session.student_alias_id),
      JSON.stringify(progressByProblemId)
    );
  }, [isHydrated, progressByProblemId, session]);

  function handleStartStudent() {
    setSelectedProblemId(null);
    setView("student-session");
  }

  function handleSessionCreated(
    newSession: StudentSessionResponse
  ) {
    localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify(newSession)
    );

    setSession(newSession);
    setSelectedProblemId(null);
    setProgressByProblemId(
      readStoredProgress(newSession.student_alias_id)
    );
    setView("problem-bank");
  }

  function handleProblemSelected(problemId: string) {
    setProgressByProblemId((currentProgress) => {
      const existingProgress =
        currentProgress[problemId] ?? "not_started";

      if (existingProgress !== "not_started") {
        return currentProgress;
      }

      return {
        ...currentProgress,
        [problemId]: "in_progress",
      };
    });

    setSelectedProblemId(problemId);
    setView("problem-detail");
  }

  function handleBackToProblemBank() {
    setSelectedProblemId(null);
    setView("problem-bank");
  }

  function handleResetSession() {
    if (session) {
      localStorage.removeItem(
        getProgressStorageKey(session.student_alias_id)
      );
    }

    localStorage.removeItem(SESSION_STORAGE_KEY);
    localStorage.removeItem(VIEW_STORAGE_KEY);
    localStorage.removeItem(
      SELECTED_PROBLEM_STORAGE_KEY
    );

    setSession(null);
    setSelectedProblemId(null);
    setProgressByProblemId({});
    setView("landing");
  }

  if (!isHydrated) {
    return (
      <main className="app-loading-page">
        <section className="state-card">
          Loading student workspace...
        </section>
      </main>
    );
  }

  if (view === "landing") {
    return (
      <LandingPage onStartStudent={handleStartStudent} />
    );
  }

  if (view === "student-session") {
    return (
      <StudentSessionPage
        onSessionCreated={handleSessionCreated}
      />
    );
  }

  if (!session) {
    return (
      <LandingPage onStartStudent={handleStartStudent} />
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
        onBack={handleBackToProblemBank}
      />
    );
  }

  return (
    <ProblemBankPage
      session={session}
      progressByProblemId={progressByProblemId}
      onProblemSelected={handleProblemSelected}
      onResetSession={handleResetSession}
    />
  );
}

export default App;