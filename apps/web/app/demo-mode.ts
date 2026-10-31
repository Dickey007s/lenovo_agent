"use client";

import { useSyncExternalStore } from "react";

// Demo mode asks the API to plan and analyse with an offline simulator, so no model is called.
const KEY = "office-agent-demo-simulated";
const EVENT = "office-agent-demo-mode";

export const demoSimulated = () => typeof window !== "undefined" && window.localStorage.getItem(KEY) === "1";
export const simulatedBody = (): { simulated?: true } => (demoSimulated() ? { simulated: true } : {});

const subscribe = (notify: () => void) => {
  window.addEventListener(EVENT, notify);
  window.addEventListener("storage", notify);
  return () => { window.removeEventListener(EVENT, notify); window.removeEventListener("storage", notify); };
};

export function useDemoMode(): [boolean, (value: boolean) => void] {
  const value = useSyncExternalStore(subscribe, demoSimulated, () => false);
  const set = (next: boolean) => {
    window.localStorage.setItem(KEY, next ? "1" : "0");
    window.dispatchEvent(new Event(EVENT));
  };
  return [value, set];
}
