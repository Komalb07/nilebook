"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    const userId = localStorage.getItem("user_id");

    if (userId) {
      router.push("/dashboard");
    } else {
      router.push("/login");
    }
  }, [router]);

  return <div style={{ padding: "2rem" }}>Loading...</div>;
}