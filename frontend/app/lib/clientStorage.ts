"use client";

import { useSyncExternalStore } from "react";

function subscribeToStorage(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

export function useLocalStorageValue(key: string, fallback = "") {
  return useSyncExternalStore(
    subscribeToStorage,
    () => localStorage.getItem(key) || fallback,
    () => fallback
  );
}

export function useSessionStorageValue(key: string, fallback = "") {
  return useSyncExternalStore(
    subscribeToStorage,
    () => sessionStorage.getItem(key) || fallback,
    () => fallback
  );
}
