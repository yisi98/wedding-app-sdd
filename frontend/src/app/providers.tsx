"use client";

import { useEffect } from "react";

import Toasts from "@/components/Toasts";
import "@/lib/i18n";

export default function Providers({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
  }, []);

  return (
    <>
      {children}
      <Toasts />
    </>
  );
}
