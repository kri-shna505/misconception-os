interface LandingPageProps {
  onStartStudent: () => void;
  onStartTeacher: () => void;
}

export function LandingPage({
  onStartStudent,
  onStartTeacher,
}: LandingPageProps) {
  return (
    <main className="landing-shell">
      <nav className="landing-nav">
        <div className="brand-lockup">
          <div className="brand-mark">M/OS</div>

          <div>
            <strong>MisconceptionOS</strong>
            <span>DSA Misconception Diagnosis Platform</span>
          </div>
        </div>

        <div className="nav-actions">
          <button
            className="nav-button muted-button"
            onClick={onStartTeacher}
          >
            Open Teacher Console
          </button>

          <button
            className="nav-button"
            onClick={onStartStudent}
          >
            Start Student Session
          </button>
        </div>
      </nav>

      <section className="landing-hero human-hero">
        <div className="hero-copy">
          <p className="eyebrow">
            Human-controlled • AI-assisted • Teacher-reviewed
          </p>

          <h1>Understand why students get DSA wrong.</h1>

          <p className="hero-description">
            MisconceptionOS helps students and teachers see the reasoning gap
            behind wrong answers using privacy-preserving, evidence-backed
            diagnosis.
          </p>

          <div className="trust-strip">
            <span>No direct answer giveaway</span>
            <span>Observable evidence first</span>
            <span>Refuses weak guesses</span>
          </div>

          <div className="hero-actions">
            <button
              className="primary-button"
              onClick={onStartStudent}
            >
              Start as Student
            </button>

            <button
              className="ghost-button"
              onClick={onStartTeacher}
            >
              Open Teacher Dashboard
            </button>
          </div>
        </div>

        <div className="human-diagnosis-board">
          <div className="teacher-note">
            <span className="note-label">Student attempt</span>

            <p>
              “I used binary search because it is O(log n), but the array is
              [4, 1, 7, 3, 9].”
            </p>
          </div>

          <div className="evidence-panel">
            <div className="card-header">
              <span className="pulse-dot" />
              <span>Evidence Review</span>
            </div>

            <div className="evidence-item">
              <span>01</span>
              <p>Array is not sorted.</p>
            </div>

            <div className="evidence-item">
              <span>02</span>
              <p>Student used binary-search reasoning.</p>
            </div>

            <div className="evidence-item">
              <span>03</span>
              <p>Sorted-input precondition is missing.</p>
            </div>

            <div className="diagnosis-summary">
              <small>Likely misconception</small>
              <strong>Binary Search on Unsorted Data</strong>

              <div className="confidence-bar">
                <span />
              </div>

              <em>Evidence-backed confidence: 92%</em>
            </div>
          </div>
        </div>
      </section>

      <section className="human-proof-grid">
        <article className="proof-card">
          <span>Student</span>

          <h3>Wrong answer becomes a learning signal.</h3>

          <p>
            The system looks at reasoning and code to understand the
            misconception, not to simply mark the answer wrong.
          </p>
        </article>

        <article className="proof-card">
          <span>Teacher</span>

          <h3>Classroom patterns become visible.</h3>

          <p>
            Repeated misconceptions can be reviewed through anonymized attempts,
            labels, and dashboard trends.
          </p>
        </article>

        <article className="proof-card">
          <span>Research</span>

          <h3>Every diagnosis stays evidence-backed.</h3>

          <p>
            Confidence, refusal, diagnostic questions, and teacher review make
            the system safer than a random chatbot.
          </p>
        </article>
      </section>

      <section className="workflow-section">
        <div className="workflow-copy">
          <p className="eyebrow">Diagnosis flow</p>

          <h2>From wrong answer to learning signal.</h2>

          <p>
            The system does not jump to an answer. It checks student reasoning,
            extracts evidence, maps the likely misconception, and keeps teacher
            review in the loop.
          </p>
        </div>

        <div className="workflow">
          <div>
            <span>01</span>
            <strong>Student attempt</strong>
          </div>

          <div>
            <span>02</span>
            <strong>Evidence extraction</strong>
          </div>

          <div>
            <span>03</span>
            <strong>Misconception mapping</strong>
          </div>

          <div>
            <span>04</span>
            <strong>Question / hint</strong>
          </div>

          <div>
            <span>05</span>
            <strong>Teacher review</strong>
          </div>
        </div>
      </section>

      <section className="role-section">
        <article
          className="role-card primary-role"
          onClick={onStartStudent}
        >
          <p className="eyebrow">Student mode</p>

          <h3>Start a private diagnostic session</h3>

          <p>
            Use a pseudonymous alias, choose a seeded DSA problem, and submit
            reasoning for diagnosis.
          </p>

          <button type="button">
            Continue as Student
          </button>
        </article>

        <article
          className="role-card teacher-role"
          onClick={onStartTeacher}
        >
          <p className="eyebrow">Teacher mode</p>

          <h3>Review misconception evidence</h3>

          <p>
            Inspect student attempts, diagnosis evidence, class trends, problem
            analytics, and misconception patterns.
          </p>

          <button type="button">
            Open Teacher Dashboard
          </button>
        </article>
      </section>
    </main>
  );
}