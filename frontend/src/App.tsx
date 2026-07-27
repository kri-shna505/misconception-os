import { useEffect, useState } from "react";
import "./App.css";

import { LandingPage } from "./pages/LandingPage";
import { ProblemBankPage } from "./pages/ProblemBankPage";
import { ProblemDetailPage } from "./pages/ProblemDetailPage";
import { StudentSessionPage } from "./pages/StudentSessionPage";
import type { StudentSessionResponse } from "./types/student";

type AppView = "landing" | "student-session" | "problem-bank" | "problem-detail";

function App() {
  const [session, setSession] = useState<StudentSessionResponse | null>(null);
  const [selectedProblemId, setSelectedProblemId] = useState<string | null>(null);
  const [view, setView] = useState<AppView>("landing");

  useEffect(() => {
    const storedSession = localStorage.getItem("studentSession");

    if (storedSession) {
      setSession(JSON.parse(storedSession) as StudentSessionResponse);
      setView("problem-bank");
    }
  }, []);

  function handleSessionCreated(newSession: StudentSessionResponse) {
    setSession(newSession);
    setView("problem-bank");
  }

  function handleProblemSelected(problemId: string) {
    setSelectedProblemId(problemId);
    setView("problem-detail");
  }

  function handleResetSession() {
    localStorage.removeItem("studentSession");
    setSelectedProblemId(null);
    setSession(null);
    setView("landing");
  }

  if (view === "landing") {
    return <LandingPage onStartStudent={() => setView("student-session")} />;
  }

  if (view === "student-session") {
    return <StudentSessionPage onSessionCreated={handleSessionCreated} />;
  }

  if (view === "problem-detail" && selectedProblemId) {
    return (
      <ProblemDetailPage
        problemId={selectedProblemId}
        onBack={() => setView("problem-bank")}
      />
    );
  }

  if (session) {
    return (
      <ProblemBankPage
        session={session}
        onProblemSelected={handleProblemSelected}
        onResetSession={handleResetSession}
      />
    );
  }

  return <LandingPage onStartStudent={() => setView("student-session")} />;
}

export default App;