"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiUrl } from "../lib/api";

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [message, setMessage] = useState("");
  const [showResendVerification, setShowResendVerification] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResending, setIsResending] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    setIsSubmitting(true);
    setMessage("");
    setShowResendVerification(false);

    try {
      const response = await fetch(apiUrl("/login"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        const errorMessage = data.detail || "Login failed";
        setMessage(errorMessage);

        if (
          typeof errorMessage === "string" &&
          errorMessage.toLowerCase().includes("verify your email")
        ) {
          setShowResendVerification(true);
        }

        return;
      }

      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("user_id", data.user_id);
      localStorage.setItem("user_first_name", data.first_name);
      localStorage.setItem("user_last_name", data.last_name);
      localStorage.setItem("user_email", data.email);
      localStorage.setItem("user_currency", data.default_currency);

      sessionStorage.setItem("show_welcome", "true");

      router.push("/dashboard");
    } catch {
      setMessage("Could not connect to backend");
    } finally {
      setIsSubmitting(false);
    }
  };

  const resendVerificationEmail = async () => {
    if (!email.trim()) {
      setMessage("Enter your email first.");
      return;
    }

    setIsResending(true);
    setMessage("");

    try {
      const response = await fetch(apiUrl("/resend-verification"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setMessage(data.detail || "Could not resend verification email.");
        return;
      }

      setMessage(data.message || "Verification link sent. Please check your inbox.");
      setShowResendVerification(false);
    } catch {
      setMessage("Could not connect to backend.");
    } finally {
      setIsResending(false);
    }
  };

  return (
    <main style={pageStyle}>
      <section style={authShellStyle}>
        <div style={brandPanelStyle}>
          <div style={brandLogoStyle}>N</div>
          <h1 style={brandTitleStyle}>Nilebook</h1>
          <p style={brandSubtitleStyle}>
            Enter your Nilebook workspace to add new notes, review saved transactions, and see your money flow with less effort.
          </p>

          <div style={featureListStyle}>
            <Feature text="Add what happened in a few words" />
            <Feature text="Review the details before they matter" />
            <Feature text="Clean weekly and monthly reports" />
          </div>
        </div>

        <div style={formCardStyle}>
          <p style={eyebrowStyle}>Welcome back</p>
          <h2 style={formTitleStyle}>Log in to Nilebook</h2>
          <p style={formSubtitleStyle}>
            Continue to your personal finance workspace.
          </p>

          <form onSubmit={handleLogin} style={formStyle}>
            <label style={fieldStyle}>
              <span style={fieldLabelStyle}>Email</span>
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={inputStyle}
              />
            </label>

            <label style={fieldStyle}>
              <span style={fieldLabelStyle}>Password</span>
              <input
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={inputStyle}
              />
            </label>

            <button
              type="button"
              onClick={() => router.push("/forgot-password")}
              style={forgotPasswordStyle}
            >
              Forgot password?
            </button>

            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                ...primaryButtonStyle,
                opacity: isSubmitting ? 0.75 : 1,
                cursor: isSubmitting ? "not-allowed" : "pointer",
              }}
            >
              {isSubmitting ? "Logging in..." : "Login"}
            </button>
          </form>

          {message && <div style={messageStyle}>{message}</div>}

          {showResendVerification && (
            <button
              type="button"
              onClick={resendVerificationEmail}
              disabled={isResending}
              style={{
                ...resendButtonStyle,
                opacity: isResending ? 0.75 : 1,
                cursor: isResending ? "not-allowed" : "pointer",
              }}
            >
              {isResending ? "Sending verification link..." : "Resend verification email"}
            </button>
          )}

          <p style={switchTextStyle}>
            New to Nilebook?{" "}
            <button
              onClick={() => router.push("/signup")}
              style={linkButtonStyle}
            >
              Create account
            </button>
          </p>
        </div>
      </section>
    </main>
  );
}

function Feature({ text }: { text: string }) {
  return (
    <div style={featureItemStyle}>
      <span style={featureDotStyle} />
      <span>{text}</span>
    </div>
  );
}

const pageStyle: React.CSSProperties = {
  minHeight: "100vh",
  padding: "2rem",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "linear-gradient(180deg, #f7fbf7 0%, #eef5ef 100%)",
  color: "#17351f",
};

const authShellStyle: React.CSSProperties = {
  width: "100%",
  maxWidth: "1040px",
  display: "grid",
  gridTemplateColumns: "1.1fr 0.9fr",
  gap: "1.25rem",
  alignItems: "stretch",
};

const brandPanelStyle: React.CSSProperties = {
  border: "1px solid #d8e7db",
  borderRadius: "26px",
  padding: "2rem",
  background:
    "linear-gradient(145deg, rgba(31,122,69,0.96), rgba(20,53,31,0.96))",
  color: "white",
  boxShadow: "0 24px 70px rgba(35, 79, 48, 0.18)",
  display: "flex",
  flexDirection: "column",
  justifyContent: "center",
};

const brandLogoStyle: React.CSSProperties = {
  width: "52px",
  height: "52px",
  borderRadius: "50%",
  background: "rgba(255,255,255,0.16)",
  border: "1px solid rgba(255,255,255,0.28)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  color: "#fff",
  fontWeight: 900,
  fontSize: "1.4rem",
  marginBottom: "1rem",
};

const brandTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: "2.4rem",
  letterSpacing: "-0.03em",
};

const brandSubtitleStyle: React.CSSProperties = {
  margin: "0.75rem 0 1.5rem 0",
  color: "rgba(255,255,255,0.82)",
  fontSize: "1rem",
  lineHeight: 1.7,
  maxWidth: "560px",
};

const featureListStyle: React.CSSProperties = {
  display: "grid",
  gap: "0.75rem",
};

const featureItemStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.65rem",
  color: "rgba(255,255,255,0.9)",
  fontWeight: 700,
};

const featureDotStyle: React.CSSProperties = {
  width: "9px",
  height: "9px",
  borderRadius: "50%",
  background: "#cdebd4",
};

const formCardStyle: React.CSSProperties = {
  border: "1px solid #d8e7db",
  borderRadius: "26px",
  padding: "2rem",
  background: "rgba(255, 255, 255, 0.94)",
  boxShadow: "0 22px 60px rgba(35, 79, 48, 0.10)",
};

const eyebrowStyle: React.CSSProperties = {
  margin: 0,
  fontSize: "0.78rem",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#5d7a66",
  fontWeight: 800,
};

const formTitleStyle: React.CSSProperties = {
  margin: "0.3rem 0",
  fontSize: "1.8rem",
  color: "#14351f",
};

const formSubtitleStyle: React.CSSProperties = {
  margin: "0 0 1.25rem 0",
  color: "#667c6b",
  lineHeight: 1.5,
};

const formStyle: React.CSSProperties = {
  display: "grid",
  gap: "0.9rem",
};

const fieldStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "0.35rem",
};

const fieldLabelStyle: React.CSSProperties = {
  fontWeight: 800,
  color: "#294c32",
  fontSize: "0.86rem",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "0.78rem 0.85rem",
  borderRadius: "13px",
  border: "1px solid #cfded2",
  background: "#fbfdfb",
  color: "#17351f",
  outline: "none",
};

const primaryButtonStyle: React.CSSProperties = {
  border: "none",
  borderRadius: "999px",
  padding: "0.82rem 1.1rem",
  background: "#1f7a45",
  color: "white",
  fontWeight: 900,
  cursor: "pointer",
  boxShadow: "0 10px 24px rgba(31, 122, 69, 0.22)",
  marginTop: "0.25rem",
};

const messageStyle: React.CSSProperties = {
  marginTop: "1rem",
  padding: "0.8rem 1rem",
  background: "#fff5f4",
  border: "1px solid #f2c7c3",
  borderRadius: "14px",
  color: "#b42318",
  fontWeight: 700,
};

const switchTextStyle: React.CSSProperties = {
  margin: "1.2rem 0 0 0",
  color: "#6b7d70",
};

const linkButtonStyle: React.CSSProperties = {
  border: "none",
  background: "none",
  color: "#1f7a45",
  cursor: "pointer",
  padding: 0,
  fontWeight: 900,
};

const forgotPasswordStyle: React.CSSProperties = {
  border: "none",
  background: "none",
  color: "#1f7a45",
  cursor: "pointer",
  padding: 0,
  fontWeight: 800,
  justifySelf: "end",
};

const resendButtonStyle: React.CSSProperties = {
  width: "100%",
  marginTop: "0.9rem",
  border: "1px solid #c8d9cc",
  borderRadius: "999px",
  padding: "0.75rem 1rem",
  background: "#ffffff",
  color: "#245034",
  fontWeight: 900,
};
