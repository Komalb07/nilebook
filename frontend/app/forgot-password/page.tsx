"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiUrl } from "../lib/api";

export default function ForgotPasswordPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();

    setIsSubmitting(true);
    setMessage("");
    setIsSuccess(false);

    try {
      const response = await fetch(apiUrl("/forgot-password"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (!response.ok) {
        setMessage(data.detail || "Could not request password reset.");
        return;
      }

      setIsSuccess(true);
      setMessage(data.message || "Password reset link requested.");
    } catch {
      setMessage("Could not connect to backend.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main style={pageStyle}>
      <section style={cardStyle}>
        <div style={logoStyle}>N</div>

        <p style={eyebrowStyle}>Password Help</p>
        <h1 style={titleStyle}>Reset your password</h1>
        <p style={subtitleStyle}>
          Enter your Nilebook email address. If an account exists, we’ll send a reset link.
        </p>

        <form onSubmit={handleForgotPassword} style={formStyle}>
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

          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              ...primaryButtonStyle,
              opacity: isSubmitting ? 0.75 : 1,
              cursor: isSubmitting ? "not-allowed" : "pointer",
            }}
          >
            {isSubmitting ? "Sending..." : "Send Reset Link"}
          </button>
        </form>

        {message && (
          <div
            style={{
              ...messageStyle,
              background: isSuccess ? "#f0f8f2" : "#fff5f4",
              border: isSuccess ? "1px solid #cfe6d5" : "1px solid #f2c7c3",
              color: isSuccess ? "#225b34" : "#b42318",
            }}
          >
            {message}
          </div>
        )}

        <button onClick={() => router.push("/login")} style={linkButtonStyle}>
          Back to login
        </button>
      </section>
    </main>
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

const cardStyle: React.CSSProperties = {
  width: "100%",
  maxWidth: "480px",
  border: "1px solid #d8e7db",
  borderRadius: "26px",
  padding: "2rem",
  background: "rgba(255, 255, 255, 0.94)",
  boxShadow: "0 22px 60px rgba(35, 79, 48, 0.10)",
};

const logoStyle: React.CSSProperties = {
  width: "56px",
  height: "56px",
  borderRadius: "50%",
  background: "#1f7a45",
  color: "white",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontWeight: 900,
  fontSize: "1.4rem",
  marginBottom: "1rem",
  boxShadow: "0 12px 28px rgba(31, 122, 69, 0.24)",
};

const eyebrowStyle: React.CSSProperties = {
  margin: 0,
  fontSize: "0.78rem",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#5d7a66",
  fontWeight: 800,
};

const titleStyle: React.CSSProperties = {
  margin: "0.35rem 0",
  color: "#14351f",
};

const subtitleStyle: React.CSSProperties = {
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
};

const messageStyle: React.CSSProperties = {
  marginTop: "1rem",
  padding: "0.8rem 1rem",
  borderRadius: "14px",
  fontWeight: 700,
};

const linkButtonStyle: React.CSSProperties = {
  marginTop: "1rem",
  border: "none",
  background: "none",
  color: "#1f7a45",
  cursor: "pointer",
  padding: 0,
  fontWeight: 900,
};
