"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiUrl } from "../lib/api";

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<VerificationShell message="Verifying your email..." isSuccess={false} />}>
      <VerifyEmailContent />
    </Suspense>
  );
}

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [message, setMessage] = useState(
    token ? "Verifying your email..." : "Verification token is missing."
  );
  const [isSuccess, setIsSuccess] = useState(false);

  useEffect(() => {
    if (!token) {
      return;
    }

    const verifyEmail = async () => {
      try {
        const response = await fetch(
          apiUrl(`/verify-email?token=${token}`)
        );

        const data = await response.json();

        if (!response.ok) {
          setMessage(data.detail || "Email verification failed.");
          setIsSuccess(false);
          return;
        }

        setMessage(data.message || "Email verified successfully.");
        setIsSuccess(true);

        setTimeout(() => {
          router.push("/login");
        }, 1600);
      } catch {
        setMessage("Could not connect to backend.");
        setIsSuccess(false);
      }
    };

    verifyEmail();
  }, [router, token]);

  return (
    <VerificationShell
      message={message}
      isSuccess={isSuccess}
      onLogin={() => router.push("/login")}
    />
  );
}

function VerificationShell({
  message,
  isSuccess,
  onLogin,
}: {
  message: string;
  isSuccess: boolean;
  onLogin?: () => void;
}) {
  return (
      <main style={pageStyle}>
        <section style={cardStyle}>
          <div style={logoStyle}>N</div>

          <p style={eyebrowStyle}>Email Verification</p>
          <h1 style={titleStyle}>
            {isSuccess ? "You're verified" : "Verifying your email"}
          </h1>

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

          {onLogin && (
            <button onClick={onLogin} style={primaryButtonStyle}>
              Go to Login
            </button>
          )}
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
  textAlign: "center",
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
  margin: "0 auto 1rem auto",
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
  margin: "0.35rem 0 1rem 0",
  color: "#14351f",
};

const messageStyle: React.CSSProperties = {
  padding: "0.85rem 1rem",
  borderRadius: "14px",
  fontWeight: 700,
  marginBottom: "1rem",
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
