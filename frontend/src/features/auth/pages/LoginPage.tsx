import {
  type FormEvent,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useLocation,
  useNavigate,
} from "react-router-dom";

import {
  getApiAccessToken,
} from "../../../api/client";

import {
  loginTeacher,
} from "../api";


type LoginLocationState = {
  from?: string;
};


const LOGIN_RETURN_TO_STORAGE_KEY =
  "teacher_login_return_to";


function getErrorMessage(
  error: unknown,
): string {
  if (error instanceof Error) {
    return error.message;
  }

  return (
    "Login failed. Please check your " +
    "credentials and try again."
  );
}


function isSafeInternalPath(
  value: string | null | undefined,
): value is string {
  if (!value) {
    return false;
  }

  return (
    value.startsWith("/") &&
    !value.startsWith("//") &&
    !value.includes("://")
  );
}


function resolveRedirectPath(
  locationState: LoginLocationState | null,
  search: string,
): string {
  const searchParams =
    new URLSearchParams(search);

  const queryReturnTo =
    searchParams.get("returnTo");

  if (isSafeInternalPath(queryReturnTo)) {
    return queryReturnTo;
  }

  if (
    isSafeInternalPath(
      locationState?.from,
    )
  ) {
    return locationState.from;
  }

  const storedReturnTo =
    window.sessionStorage.getItem(
      LOGIN_RETURN_TO_STORAGE_KEY,
    );

  if (
    isSafeInternalPath(
      storedReturnTo,
    )
  ) {
    return storedReturnTo;
  }

  return "/teacher/reviews";
}


const LOGIN_PAGE_STYLES = `
  .teacher-login-page {
    min-height: 100vh;
    padding: 32px 20px;
    display: grid;
    place-items: center;
    background:
      radial-gradient(
        circle at 12% 10%,
        rgba(37, 99, 235, 0.10),
        transparent 34%
      ),
      radial-gradient(
        circle at 88% 12%,
        rgba(245, 158, 11, 0.09),
        transparent 30%
      ),
      #f7f5ef;
    color: #07142d;
  }

  .teacher-login-shell {
    width: min(100%, 1040px);
    min-height: 640px;
    display: grid;
    grid-template-columns:
      minmax(0, 1.05fr)
      minmax(380px, 0.95fr);
    overflow: hidden;
    border: 1px solid #d7dfec;
    border-radius: 28px;
    background: #ffffff;
    box-shadow:
      0 30px 80px rgba(15, 23, 42, 0.13);
  }

  .teacher-login-visual {
    position: relative;
    padding: 52px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    overflow: hidden;
    background:
      linear-gradient(
        145deg,
        #07142d 0%,
        #10264c 58%,
        #173a72 100%
      );
    color: #ffffff;
  }

  .teacher-login-visual::before,
  .teacher-login-visual::after {
    content: "";
    position: absolute;
    border-radius: 999px;
    pointer-events: none;
  }

  .teacher-login-visual::before {
    width: 320px;
    height: 320px;
    top: -120px;
    right: -100px;
    background: rgba(59, 130, 246, 0.18);
  }

  .teacher-login-visual::after {
    width: 260px;
    height: 260px;
    left: -110px;
    bottom: -100px;
    background: rgba(245, 158, 11, 0.12);
  }

  .teacher-login-brand,
  .teacher-login-copy,
  .teacher-login-highlights {
    position: relative;
    z-index: 1;
  }

  .teacher-login-brand {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .teacher-login-brand-mark {
    width: 58px;
    height: 48px;
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    border-radius: 14px;
    background: #ffffff;
    color: #07142d;
    font-weight: 900;
    letter-spacing: -0.04em;
    box-shadow:
      0 14px 30px rgba(0, 0, 0, 0.18);
  }

  .teacher-login-brand-name {
    margin: 0;
    font-size: 18px;
    font-weight: 800;
  }

  .teacher-login-brand-subtitle {
    margin: 3px 0 0;
    color: #bdcae2;
    font-size: 13px;
  }

  .teacher-login-copy {
    max-width: 470px;
    margin: 72px 0;
  }

  .teacher-login-eyebrow {
    margin: 0 0 14px;
    color: #8cb7ff;
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }

  .teacher-login-copy h2 {
    margin: 0;
    max-width: 430px;
    font-size: clamp(40px, 5vw, 64px);
    line-height: 0.98;
    letter-spacing: -0.055em;
  }

  .teacher-login-copy p {
    margin: 24px 0 0;
    max-width: 450px;
    color: #c9d4e8;
    font-size: 16px;
    line-height: 1.75;
  }

  .teacher-login-highlights {
    display: grid;
    gap: 12px;
  }

  .teacher-login-highlight {
    display: flex;
    align-items: center;
    gap: 12px;
    color: #d9e3f3;
    font-size: 14px;
  }

  .teacher-login-highlight-icon {
    width: 28px;
    height: 28px;
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    border: 1px solid rgba(255, 255, 255, 0.20);
    border-radius: 9px;
    background: rgba(255, 255, 255, 0.08);
    font-weight: 900;
  }

  .teacher-login-panel {
    padding: 52px;
    display: flex;
    align-items: center;
    background: #ffffff;
  }

  .teacher-login-form-container {
    width: 100%;
    max-width: 440px;
    margin: 0 auto;
  }

  .teacher-login-mobile-brand {
    display: none;
  }

  .teacher-login-form-header {
    margin-bottom: 34px;
  }

  .teacher-login-form-header p {
    margin: 0 0 10px;
    color: #2563eb;
    font-size: 12px;
    font-weight: 900;
    letter-spacing: 0.15em;
    text-transform: uppercase;
  }

  .teacher-login-form-header h1 {
    margin: 0;
    color: #07142d;
    font-size: clamp(36px, 4vw, 50px);
    line-height: 1;
    letter-spacing: -0.05em;
  }

  .teacher-login-form-header span {
    display: block;
    margin-top: 16px;
    color: #64748b;
    font-size: 15px;
    line-height: 1.65;
  }

  .teacher-login-form {
    display: grid;
    gap: 22px;
  }

  .teacher-login-field {
    display: grid;
    gap: 9px;
  }

  .teacher-login-field label {
    color: #1e293b;
    font-size: 13px;
    font-weight: 800;
  }

  .teacher-login-input-wrapper {
    position: relative;
  }

  .teacher-login-input {
    width: 100%;
    min-height: 54px;
    padding: 0 16px;
    border: 1px solid #ccd6e5;
    border-radius: 13px;
    outline: none;
    background: #fbfcfe;
    color: #07142d;
    font: inherit;
    font-size: 15px;
    transition:
      border-color 160ms ease,
      box-shadow 160ms ease,
      background 160ms ease;
    box-sizing: border-box;
  }

  .teacher-login-input:hover {
    border-color: #aebbd0;
  }

  .teacher-login-input:focus {
    border-color: #2563eb;
    background: #ffffff;
    box-shadow:
      0 0 0 4px rgba(37, 99, 235, 0.12);
  }

  .teacher-login-input:disabled {
    cursor: not-allowed;
    opacity: 0.7;
  }

  .teacher-login-password-input {
    padding-right: 72px;
  }

  .teacher-login-password-toggle {
    position: absolute;
    top: 50%;
    right: 9px;
    min-width: 54px;
    min-height: 36px;
    padding: 0 10px;
    transform: translateY(-50%);
    border: 0;
    border-radius: 9px;
    background: transparent;
    color: #475569;
    font-size: 12px;
    font-weight: 800;
    cursor: pointer;
  }

  .teacher-login-password-toggle:hover {
    background: #eef3fa;
    color: #07142d;
  }

  .teacher-login-password-toggle:focus-visible {
    outline: 3px solid rgba(37, 99, 235, 0.25);
  }

  .teacher-login-error {
    padding: 13px 14px;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    border: 1px solid #fecaca;
    border-radius: 12px;
    background: #fff5f5;
    color: #b91c1c;
    font-size: 13px;
    line-height: 1.5;
  }

  .teacher-login-error-icon {
    width: 20px;
    height: 20px;
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    border-radius: 999px;
    background: #fee2e2;
    font-weight: 900;
  }

  .teacher-login-actions {
    display: grid;
    gap: 12px;
    margin-top: 4px;
  }

  .teacher-login-primary-button,
  .teacher-login-secondary-button {
    min-height: 52px;
    padding: 0 20px;
    border-radius: 13px;
    font: inherit;
    font-size: 14px;
    font-weight: 900;
    cursor: pointer;
    transition:
      transform 150ms ease,
      box-shadow 150ms ease,
      background 150ms ease;
  }

  .teacher-login-primary-button {
    border: 1px solid #07142d;
    background: #07142d;
    color: #ffffff;
    box-shadow:
      0 14px 28px rgba(7, 20, 45, 0.18);
  }

  .teacher-login-primary-button:hover:not(:disabled) {
    transform: translateY(-1px);
    background: #10264c;
    box-shadow:
      0 18px 34px rgba(7, 20, 45, 0.22);
  }

  .teacher-login-secondary-button {
    border: 1px solid #d5deeb;
    background: #ffffff;
    color: #334155;
  }

  .teacher-login-secondary-button:hover:not(:disabled) {
    background: #f5f8fc;
    color: #07142d;
  }

  .teacher-login-primary-button:disabled,
  .teacher-login-secondary-button:disabled {
    cursor: not-allowed;
    opacity: 0.65;
    transform: none;
  }

  .teacher-login-footer {
    margin: 28px 0 0;
    color: #94a3b8;
    font-size: 12px;
    line-height: 1.6;
    text-align: center;
  }

  @media (max-width: 860px) {
    .teacher-login-page {
      padding: 20px;
    }

    .teacher-login-shell {
      min-height: auto;
      grid-template-columns: 1fr;
      border-radius: 22px;
    }

    .teacher-login-visual {
      display: none;
    }

    .teacher-login-panel {
      padding: 42px 28px;
    }

    .teacher-login-mobile-brand {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 42px;
    }

    .teacher-login-mobile-brand .teacher-login-brand-mark {
      width: 52px;
      height: 44px;
      background: #07142d;
      color: #ffffff;
      box-shadow: none;
    }

    .teacher-login-mobile-brand .teacher-login-brand-name {
      color: #07142d;
    }

    .teacher-login-mobile-brand .teacher-login-brand-subtitle {
      color: #64748b;
    }
  }

  @media (max-width: 520px) {
    .teacher-login-page {
      padding: 0;
      place-items: stretch;
      background: #ffffff;
    }

    .teacher-login-shell {
      min-height: 100vh;
      border: 0;
      border-radius: 0;
      box-shadow: none;
    }

    .teacher-login-panel {
      padding: 28px 20px;
      align-items: flex-start;
    }

    .teacher-login-mobile-brand {
      margin-bottom: 54px;
    }

    .teacher-login-form-header h1 {
      font-size: 40px;
    }
  }
`;


export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState(
    "teacher@misconceptionos.local",
  );

  const [password, setPassword] =
    useState("");

  const [
    isPasswordVisible,
    setIsPasswordVisible,
  ] = useState(false);

  const [
    isSubmitting,
    setIsSubmitting,
  ] = useState(false);

  const [
    errorMessage,
    setErrorMessage,
  ] = useState<string | null>(null);

  const locationState =
    location.state as
      | LoginLocationState
      | null;

  const redirectPath = useMemo(
    () =>
      resolveRedirectPath(
        locationState,
        location.search,
      ),
    [
      location.search,
      locationState,
    ],
  );


  useEffect(() => {
    const existingToken =
      getApiAccessToken();

    if (!existingToken) {
      return;
    }

    window.sessionStorage.removeItem(
      LOGIN_RETURN_TO_STORAGE_KEY,
    );

    navigate(
      redirectPath,
      {
        replace: true,
      },
    );
  }, [
    navigate,
    redirectPath,
  ]);


  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

    setErrorMessage(null);

    const normalizedEmail =
      email.trim();

    if (!normalizedEmail) {
      setErrorMessage(
        "Enter your teacher email address.",
      );

      return;
    }

    if (!password) {
      setErrorMessage(
        "Enter your password.",
      );

      return;
    }

    setIsSubmitting(true);

    try {
      const response =
        await loginTeacher({
          email: normalizedEmail,
          password,
        });

      if (
        response.user.role !== "teacher" &&
        response.user.role !== "admin"
      ) {
        throw new Error(
          "This account cannot access " +
          "the teacher console.",
        );
      }

      if (!response.user.is_active) {
        throw new Error(
          "This teacher account is inactive.",
        );
      }

      window.sessionStorage.removeItem(
        LOGIN_RETURN_TO_STORAGE_KEY,
      );

      navigate(
        redirectPath,
        {
          replace: true,
        },
      );
    } catch (error) {
      setErrorMessage(
        getErrorMessage(error),
      );
    } finally {
      setIsSubmitting(false);
    }
  }


  function handleBackToLanding(): void {
    navigate("/");
  }


  return (
    <>
      <style>
        {LOGIN_PAGE_STYLES}
      </style>

      <main className="teacher-login-page">
        <section
          className="teacher-login-shell"
          aria-labelledby="teacher-login-title"
        >
          <aside
            className="teacher-login-visual"
            aria-label="Teacher review console overview"
          >
            <div className="teacher-login-brand">
              <div className="teacher-login-brand-mark">
                M/OS
              </div>

              <div>
                <p className="teacher-login-brand-name">
                  MisconceptionOS
                </p>

                <p className="teacher-login-brand-subtitle">
                  Teacher Review Console
                </p>
              </div>
            </div>

            <div className="teacher-login-copy">
              <p className="teacher-login-eyebrow">
                Evidence-based review
              </p>

              <h2>
                Turn student attempts into
                clear teaching decisions.
              </h2>

              <p>
                Review student reasoning, inspect
                automated diagnoses, and finalize
                classroom feedback from one focused
                workspace.
              </p>
            </div>

            <div className="teacher-login-highlights">
              <div className="teacher-login-highlight">
                <span className="teacher-login-highlight-icon">
                  ✓
                </span>

                <span>
                  Review pseudonymous student work
                </span>
              </div>

              <div className="teacher-login-highlight">
                <span className="teacher-login-highlight-icon">
                  ✓
                </span>

                <span>
                  Accept or override diagnoses
                </span>
              </div>

              <div className="teacher-login-highlight">
                <span className="teacher-login-highlight-icon">
                  ✓
                </span>

                <span>
                  Save drafts and finalize reviews
                </span>
              </div>
            </div>
          </aside>

          <div className="teacher-login-panel">
            <div className="teacher-login-form-container">
              <div className="teacher-login-mobile-brand">
                <div className="teacher-login-brand-mark">
                  M/OS
                </div>

                <div>
                  <p className="teacher-login-brand-name">
                    MisconceptionOS
                  </p>

                  <p className="teacher-login-brand-subtitle">
                    Teacher Review Console
                  </p>
                </div>
              </div>

              <header className="teacher-login-form-header">
                <p>
                  Secure teacher access
                </p>

                <h1 id="teacher-login-title">
                  Welcome back
                </h1>

                <span>
                  Sign in with a teacher or
                  administrator account to continue.
                </span>
              </header>

              <form
                className="teacher-login-form"
                onSubmit={handleSubmit}
                noValidate
              >
                <div className="teacher-login-field">
                  <label htmlFor="teacher-email">
                    Email address
                  </label>

                  <div className="teacher-login-input-wrapper">
                    <input
                      className="teacher-login-input"
                      id="teacher-email"
                      name="email"
                      type="email"
                      inputMode="email"
                      autoComplete="username"
                      autoFocus
                      value={email}
                      onChange={(event) => {
                        setEmail(
                          event.target.value,
                        );

                        if (errorMessage) {
                          setErrorMessage(null);
                        }
                      }}
                      placeholder={
                        "teacher@" +
                        "misconceptionos.local"
                      }
                      disabled={isSubmitting}
                      aria-invalid={
                        Boolean(errorMessage)
                      }
                      required
                    />
                  </div>
                </div>

                <div className="teacher-login-field">
                  <label htmlFor="teacher-password">
                    Password
                  </label>

                  <div className="teacher-login-input-wrapper">
                    <input
                      className={
                        "teacher-login-input " +
                        "teacher-login-password-input"
                      }
                      id="teacher-password"
                      name="password"
                      type={
                        isPasswordVisible
                          ? "text"
                          : "password"
                      }
                      autoComplete="current-password"
                      value={password}
                      onChange={(event) => {
                        setPassword(
                          event.target.value,
                        );

                        if (errorMessage) {
                          setErrorMessage(null);
                        }
                      }}
                      placeholder="Enter your password"
                      disabled={isSubmitting}
                      aria-invalid={
                        Boolean(errorMessage)
                      }
                      required
                    />

                    <button
                      className={
                        "teacher-login-password-toggle"
                      }
                      type="button"
                      onClick={() => {
                        setIsPasswordVisible(
                          (currentValue) =>
                            !currentValue,
                        );
                      }}
                      disabled={isSubmitting}
                      aria-label={
                        isPasswordVisible
                          ? "Hide password"
                          : "Show password"
                      }
                    >
                      {isPasswordVisible
                        ? "Hide"
                        : "Show"}
                    </button>
                  </div>
                </div>

                {errorMessage ? (
                  <div
                    className="teacher-login-error"
                    role="alert"
                  >
                    <span className="teacher-login-error-icon">
                      !
                    </span>

                    <span>
                      {errorMessage}
                    </span>
                  </div>
                ) : null}

                <div className="teacher-login-actions">
                  <button
                    className={
                      "teacher-login-primary-button"
                    }
                    type="submit"
                    disabled={isSubmitting}
                  >
                    {isSubmitting
                      ? "Signing in..."
                      : "Sign in to review console"}
                  </button>

                  <button
                    className={
                      "teacher-login-secondary-button"
                    }
                    type="button"
                    onClick={handleBackToLanding}
                    disabled={isSubmitting}
                  >
                    Back to landing page
                  </button>
                </div>
              </form>

              <p className="teacher-login-footer">
                Protected teacher workspace.
                Access is restricted to authorized
                teacher and administrator accounts.
              </p>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}