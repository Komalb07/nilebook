"use client";

import { useState } from "react";
import Navbar from "../components/Navbar";
import { apiUrl } from "../lib/api";
import { useLocalStorageValue } from "../lib/clientStorage";

const currencies = [
  "USD", "INR", "EUR", "GBP", "CAD",
  "AUD", "JPY", "CNY", "RUB", "AED", "CHF"
];

export default function ProfilePage() {
  const [currency, setCurrency] = useState("");
  const [savedCurrency, setSavedCurrency] = useState("");
  const userId = useLocalStorageValue("user_id", "__pending__");
  const firstName = useLocalStorageValue("user_first_name");
  const lastName = useLocalStorageValue("user_last_name");
  const email = useLocalStorageValue("user_email");
  const storedCurrency = useLocalStorageValue("user_currency", "USD");
  const [message, setMessage] = useState("");
  const [deletePassword, setDeletePassword] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  const getAuthHeaders = () => {
    const token = localStorage.getItem("access_token");

    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    };
  };

  const updateCurrency = async () => {
    if (!userId || userId === "__pending__") {
      setMessage("Missing user. Please log in again.");
      return;
    }

    try {
      const nextCurrency = currency || storedCurrency;
      const response = await fetch(apiUrl(`/users/${userId}/currency?currency=${nextCurrency}`), {method: "PUT", headers: getAuthHeaders(), });

      const data = await response.json();

      if (!response.ok) {
        setMessage(
          typeof data.detail === "string"
            ? data.detail
            : "Failed to update currency"
        );
        return;
      }

      localStorage.setItem("user_currency", data.currency || nextCurrency);
      setSavedCurrency(data.currency || nextCurrency);
      setCurrency(data.currency || nextCurrency);
      setMessage("Currency updated successfully.");
    } catch {
      setMessage("Could not connect to backend.");
    }
  };

  const deleteAccount = async () => {
    if (!userId || userId === "__pending__") {
      setMessage("Missing user. Please log in again.");
      return;
    }

    if (!deletePassword.trim()) {
      setMessage("Please enter your password to delete your account.");
      return;
    }

    const confirmed = window.confirm(
      "Are you sure you want to permanently delete your account? This will delete all your transactions and cannot be undone."
    );

    if (!confirmed) return;

    setIsDeleting(true);
    setMessage("");

    try {
      const response = await fetch(apiUrl(`/users/${userId}`), {
        method: "DELETE",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          password: deletePassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setMessage(
          typeof data.detail === "string"
            ? data.detail
            : "Failed to delete account"
        );
        return;
      }

      localStorage.clear();
      sessionStorage.clear();

      window.location.href = "/login";
    } catch {
      setMessage("Could not connect to backend.");
    } finally {
      setIsDeleting(false);
    }
  };

  const fullName = `${firstName} ${lastName}`.trim() || "User";

  return (
    <>
      <Navbar />

      <main style={pageStyle}>
        <section style={heroStyle}>
          <p style={eyebrowStyle}>Profile</p>
          <h1 style={titleStyle}>Account Settings</h1>
          <p style={subtitleStyle}>
            Manage your profile details and default finance preferences.
          </p>
        </section>

        <section style={profileCardStyle}>
          <div style={profileHeaderStyle}>
            <div style={avatarStyle}>{firstName ? firstName[0].toUpperCase() : "U"}</div>

            <div>
              <h2 style={cardTitleStyle}>{fullName}</h2>
              <p style={emailStyle}>{email || "No email found"}</p>
            </div>
          </div>

          <div style={detailsGridStyle}>
            <InfoItem label="First Name" value={firstName || "Not available"} />
            <InfoItem label="Last Name" value={lastName || "Not available"} />
            <InfoItem label="Email" value={email || "Not available"} />
            <InfoItem label="Current Currency" value={savedCurrency || storedCurrency} />
          </div>

          <div style={settingsBoxStyle}>
            <div>
              <p style={eyebrowStyle}>Preference</p>
              <h3 style={sectionTitleStyle}>Default Currency</h3>
              <p style={settingHelpStyle}>
                This currency will be used for new finance journal notes unless you change it here.
              </p>
            </div>

            <div style={currencyRowStyle}>
              <select
                value={currency || storedCurrency}
                onChange={(e) => setCurrency(e.target.value)}
                style={selectStyle}
              >
                {currencies.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>

              <button onClick={updateCurrency} style={primaryButtonStyle}>
                Save Currency
              </button>
            </div>
          </div>

          <div style={dangerZoneStyle}>
            <div>
              <p style={dangerEyebrowStyle}>Danger Zone</p>
              <h3 style={dangerTitleStyle}>Delete Account</h3>
              <p style={dangerHelpStyle}>
                This will permanently delete your account and all saved transactions.
                This action cannot be undone.
              </p>
            </div>

            <div style={currencyRowStyle}>
              <input
                type="password"
                placeholder="Confirm password"
                value={deletePassword}
                onChange={(e) => setDeletePassword(e.target.value)}
                style={selectStyle}
              />

              <button
                onClick={deleteAccount}
                disabled={isDeleting}
                style={{
                  ...dangerButtonStyle,
                  opacity: isDeleting ? 0.75 : 1,
                  cursor: isDeleting ? "not-allowed" : "pointer",
                }}
              >
                {isDeleting ? "Deleting..." : "Delete Account"}
              </button>
            </div>
          </div>

          {message && <div style={messageStyle}>{message}</div>}
        </section>
      </main>
    </>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div style={infoItemStyle}>
      <span style={infoLabelStyle}>{label}</span>
      <strong style={infoValueStyle}>{value}</strong>
    </div>
  );
}

const pageStyle: React.CSSProperties = {
  minHeight: "100vh",
  padding: "2rem",
  background: "linear-gradient(180deg, #f7fbf7 0%, #eef5ef 100%)",
  color: "#17351f",
};

const heroStyle: React.CSSProperties = {
  maxWidth: "980px",
  margin: "0 auto 1.5rem auto",
};

const eyebrowStyle: React.CSSProperties = {
  margin: 0,
  fontSize: "0.78rem",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#5d7a66",
  fontWeight: 700,
};

const titleStyle: React.CSSProperties = {
  margin: "0.25rem 0",
  fontSize: "2rem",
  color: "#14351f",
};

const subtitleStyle: React.CSSProperties = {
  margin: 0,
  color: "#5b6f60",
  maxWidth: "680px",
  lineHeight: 1.6,
};

const profileCardStyle: React.CSSProperties = {
  width: "100%",
  maxWidth: "980px",
  margin: "0 auto",
  border: "1px solid #d8e7db",
  borderRadius: "22px",
  padding: "1.5rem",
  background: "rgba(255, 255, 255, 0.92)",
  boxShadow: "0 22px 60px rgba(35, 79, 48, 0.10)",
};

const profileHeaderStyle: React.CSSProperties = {
  display: "flex",
  gap: "1rem",
  alignItems: "center",
  marginBottom: "1.25rem",
};

const avatarStyle: React.CSSProperties = {
  width: "64px",
  height: "64px",
  borderRadius: "20px",
  background: "#1f7a45",
  color: "white",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: "1.5rem",
  fontWeight: 900,
  boxShadow: "0 14px 30px rgba(31, 122, 69, 0.22)",
};

const cardTitleStyle: React.CSSProperties = {
  margin: 0,
  color: "#14351f",
};

const emailStyle: React.CSSProperties = {
  margin: "0.25rem 0 0 0",
  color: "#667c6b",
};

const detailsGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
  gap: "0.75rem",
  marginBottom: "1.25rem",
};

const infoItemStyle: React.CSSProperties = {
  padding: "0.9rem",
  border: "1px solid #e2ece4",
  borderRadius: "15px",
  background: "#ffffff",
};

const infoLabelStyle: React.CSSProperties = {
  display: "block",
  color: "#6a7f70",
  fontSize: "0.78rem",
  marginBottom: "0.25rem",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  fontWeight: 700,
};

const infoValueStyle: React.CSSProperties = {
  color: "#17351f",
  wordBreak: "break-word",
};

const settingsBoxStyle: React.CSSProperties = {
  border: "1px solid #d7e7da",
  borderRadius: "18px",
  padding: "1.2rem",
  background: "#fbfdfb",
};

const sectionTitleStyle: React.CSSProperties = {
  margin: "0.2rem 0 0 0",
  color: "#17351f",
};

const settingHelpStyle: React.CSSProperties = {
  color: "#6a7f70",
  marginBottom: "1rem",
};

const currencyRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "0.75rem",
  flexWrap: "wrap",
};

const selectStyle: React.CSSProperties = {
  minWidth: "160px",
  padding: "0.72rem 0.8rem",
  borderRadius: "12px",
  border: "1px solid #cfded2",
  background: "#ffffff",
  color: "#17351f",
  outline: "none",
};

const primaryButtonStyle: React.CSSProperties = {
  border: "none",
  borderRadius: "999px",
  padding: "0.75rem 1.1rem",
  background: "#1f7a45",
  color: "white",
  fontWeight: 800,
  cursor: "pointer",
  boxShadow: "0 10px 24px rgba(31, 122, 69, 0.22)",
};

const messageStyle: React.CSSProperties = {
  marginTop: "1rem",
  padding: "0.8rem 1rem",
  background: "#f0f8f2",
  border: "1px solid #cfe6d5",
  borderRadius: "14px",
  color: "#225b34",
  fontWeight: 700,
};

const dangerZoneStyle: React.CSSProperties = {
  marginTop: "1.25rem",
  border: "1px solid #f2c7c3",
  borderRadius: "18px",
  padding: "1.2rem",
  background: "#fff5f4",
};

const dangerEyebrowStyle: React.CSSProperties = {
  margin: 0,
  fontSize: "0.78rem",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#b42318",
  fontWeight: 800,
};

const dangerTitleStyle: React.CSSProperties = {
  margin: "0.2rem 0 0 0",
  color: "#7a271a",
};

const dangerHelpStyle: React.CSSProperties = {
  color: "#8a3a2f",
  marginBottom: "1rem",
};

const dangerButtonStyle: React.CSSProperties = {
  border: "none",
  borderRadius: "999px",
  padding: "0.75rem 1.1rem",
  background: "#b42318",
  color: "white",
  fontWeight: 800,
  cursor: "pointer",
  boxShadow: "0 10px 24px rgba(180, 35, 24, 0.18)",
};
