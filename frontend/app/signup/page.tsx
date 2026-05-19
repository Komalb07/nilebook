"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiUrl } from "../lib/api";

export default function SignupPage() {
  const router = useRouter();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [message, setMessage] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const readErrorMessage = async (response: Response) => {
    try {
      const data = await response.json();

      if (Array.isArray(data.detail)) {
        return "The email ID you entered is not valid. Please enter a valid email address.";
      }

      return data.detail || "Signup failed";
    } catch {
      return "Signup failed. Please check the backend terminal for details.";
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();

    setIsSubmitting(true);
    setMessage("");
    setIsSuccess(false);

    if (password !== confirmPassword) {
      setMessage("Passwords do not match. Please re-enter your password.");
      setIsSubmitting(false);
      return;
    }

    try {
      const response = await fetch(apiUrl("/signup"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          first_name: firstName,
          last_name: lastName,
          email,
          password,
        }),
      });

      if (!response.ok) {
        setMessage(await readErrorMessage(response));
        return;
      }

      await response.json();

      setIsSuccess(true);
      setMessage("Account created successfully. Redirecting to login...");

      setTimeout(() => {
        router.push("/login");
      }, 900);
    } catch {
      setMessage("Could not connect to backend");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main style={pageStyle}>
      <section style={authShellStyle}>
        <div style={brandPanelStyle}>
          <div style={brandLogoStyle}>N</div>
          <h1 style={brandTitleStyle}>Start with Nilebook</h1>
          <p style={brandSubtitleStyle}>
            Your money story starts with small moments. Nilebook helps you capture them simply and turn them into a record you can actually use.
          </p>

          <div style={featureListStyle}>
            <Feature text="Keep track without changing how you think" />
            <Feature text="Understand where your money is moving" />
            <Feature text="Feel more in control of your money over time" />
          </div>
        </div>

        <div style={formCardStyle}>
          <p style={eyebrowStyle}>Create account</p>
          <h2 style={formTitleStyle}>Join Nilebook</h2>
          <p style={formSubtitleStyle}>
            Create your workspace and start organizing transactions naturally.
          </p>

          <form onSubmit={handleSignup} style={formStyle}>
            <div style={twoColumnStyle}>
              <label style={fieldStyle}>
                <span style={fieldLabelStyle}>First Name</span>
                <input
                  type="text"
                  placeholder="First name"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  required
                  style={inputStyle}
                />
              </label>

              <label style={fieldStyle}>
                <span style={fieldLabelStyle}>Last Name</span>
                <input
                  type="text"
                  placeholder="Last name"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  required
                  style={inputStyle}
                />
              </label>
            </div>

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
                placeholder="Create a password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={inputStyle}
              />
            </label>

            <label style={fieldStyle}>
              <span style={fieldLabelStyle}>Confirm Password</span>
              <input
                type="password"
                placeholder="Re-enter your password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                style={inputStyle}
              />
            </label>

            <button
              type="submit"
              disabled={isSubmitting || password !== confirmPassword}
              style={{
                ...primaryButtonStyle,
                opacity: isSubmitting || password !== confirmPassword ? 0.75 : 1,
                cursor:
                  isSubmitting || password !== confirmPassword
                    ? "not-allowed"
                    : "pointer",
              }}
            >
              {isSubmitting ? "Creating account..." : "Create Account"}
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

          <p style={switchTextStyle}>
            Already have an account?{" "}
            <button
              onClick={() => router.push("/login")}
              style={linkButtonStyle}
            >
              Log in
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

const twoColumnStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "0.75rem",
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
  borderRadius: "14px",
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
