"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useLocalStorageValue } from "../lib/clientStorage";

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const menuRef = useRef<HTMLDivElement | null>(null);
  const lastScrollRef = useRef(0);

  const firstName = useLocalStorageValue("user_first_name");
  const email = useLocalStorageValue("user_email");
  const [menuOpen, setMenuOpen] = useState(false);
  const [showNavbar, setShowNavbar] = useState(true);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;

      if (currentScrollY < 10) {
        setShowNavbar(true);
        lastScrollRef.current = currentScrollY;
        return;
      }

      if (currentScrollY > lastScrollRef.current) {
        setShowNavbar(false);
        setMenuOpen(false);
      } else {
        setShowNavbar(true);
      }

      lastScrollRef.current = currentScrollY;
    };

    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("user_id");
    localStorage.removeItem("user_first_name");
    localStorage.removeItem("user_last_name");
    localStorage.removeItem("user_email");
    localStorage.removeItem("user_currency");
    localStorage.removeItem("access_token");
    sessionStorage.removeItem("show_welcome");
    router.push("/login");
  };

  const userInitial = firstName ? firstName[0].toUpperCase() : "U";
  const isActive = (path: string) => pathname === path;

  return (
    <nav
      style={{
        ...navStyle,
        transform: showNavbar ? "translateY(0)" : "translateY(-110%)",
      }}
    >
      <Link href="/dashboard" style={brandStyle}>
        <span style={logoDotStyle}>N</span>
        <span>Nilebook</span>
      </Link>

      <div style={linkGroupStyle}>
        <Link
          href="/dashboard"
          style={{
            ...navLinkStyle,
            ...(isActive("/dashboard") ? activeLinkStyle : {}),
          }}
        >
          Dashboard
        </Link>

        <Link
          href="/report"
          style={{
            ...navLinkStyle,
            ...(isActive("/report") ? activeLinkStyle : {}),
          }}
        >
          Report
        </Link>
      </div>

      <div style={profileWrapperStyle} ref={menuRef}>
        <button
          onClick={() => setMenuOpen((prev) => !prev)}
          style={avatarButtonStyle}
        >
          {userInitial}
        </button>

        {menuOpen && (
          <div style={menuStyle}>
            <div style={menuHeaderStyle}>
              <div style={menuAvatarStyle}>{userInitial}</div>

              <div>
                <strong style={menuNameStyle}>
                  {firstName ? `Hello, ${firstName}` : "Hello"}
                </strong>
                <p style={menuEmailStyle}>{email || "Signed in"}</p>
              </div>
            </div>

            <button
              onClick={() => {
                router.push("/profile");
                setMenuOpen(false);
              }}
              style={menuButtonStyle}
            >
              Profile
            </button>

            <button onClick={handleLogout} style={logoutButtonStyle}>
              Logout
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}

const navStyle: React.CSSProperties = {
  position: "sticky",
  top: 0,
  zIndex: 1000,
  display: "flex",
  alignItems: "center",
  gap: "1.25rem",
  padding: "0.9rem 2rem",
  borderBottom: "1px solid #d8e7db",
  background: "rgba(255, 255, 255, 0.92)",
  backdropFilter: "blur(14px)",
  boxShadow: "0 10px 30px rgba(35, 79, 48, 0.08)",
  transition: "transform 0.28s ease",
};

const brandStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.65rem",
  textDecoration: "none",
  color: "#14351f",
  fontWeight: 900,
  fontSize: "1rem",
};

const logoDotStyle: React.CSSProperties = {
  width: "34px",
  height: "34px",
  borderRadius: "12px",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "#1f7a45",
  color: "white",
  boxShadow: "0 10px 22px rgba(31, 122, 69, 0.22)",
};

const linkGroupStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.4rem",
};

const navLinkStyle: React.CSSProperties = {
  textDecoration: "none",
  color: "#5b6f60",
  fontWeight: 800,
  padding: "0.55rem 0.8rem",
  borderRadius: "999px",
};

const activeLinkStyle: React.CSSProperties = {
  background: "#eaf7ee",
  color: "#1f6b3c",
};

const profileWrapperStyle: React.CSSProperties = {
  marginLeft: "auto",
  position: "relative",
};

const avatarButtonStyle: React.CSSProperties = {
  width: "42px",
  height: "42px",
  borderRadius: "50%",
  border: "1px solid #cde2d1",
  cursor: "pointer",
  fontWeight: 900,
  background: "#e8f4eb",
  color: "#1f5f35",
};

const menuStyle: React.CSSProperties = {
  position: "absolute",
  top: "54px",
  right: 0,
  width: "260px",
  border: "1px solid #d8e7db",
  borderRadius: "18px",
  background: "white",
  boxShadow: "0 20px 50px rgba(35, 79, 48, 0.14)",
  padding: "0.75rem",
};

const menuHeaderStyle: React.CSSProperties = {
  display: "flex",
  gap: "0.75rem",
  alignItems: "center",
  padding: "0.75rem",
  borderBottom: "1px solid #edf3ee",
  marginBottom: "0.5rem",
};

const menuAvatarStyle: React.CSSProperties = {
  width: "40px",
  height: "40px",
  borderRadius: "50%",
  background: "#1f7a45",
  color: "white",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontWeight: 900,
};

const menuNameStyle: React.CSSProperties = {
  color: "#17351f",
};

const menuEmailStyle: React.CSSProperties = {
  margin: "0.15rem 0 0 0",
  color: "#6a7f70",
  fontSize: "0.82rem",
  wordBreak: "break-word",
};

const menuButtonStyle: React.CSSProperties = {
  width: "100%",
  textAlign: "left",
  padding: "0.75rem",
  border: "none",
  background: "white",
  color: "#245034",
  cursor: "pointer",
  borderRadius: "12px",
  fontWeight: 800,
};

const logoutButtonStyle: React.CSSProperties = {
  ...menuButtonStyle,
  color: "#b42318",
};
