"use client";

import { useEffect } from "react";
import { useTranslation } from "react-i18next";

import { useRealtimeStore, type Toast as ToastType } from "@/stores/realtime";

function Toast({ toast, onDone }: { toast: ToastType; onDone: () => void }) {
  const { t } = useTranslation();
  useEffect(() => {
    const timer = setTimeout(onDone, 4000);
    return () => clearTimeout(timer);
  }, [onDone]);
  return (
    <div className="rounded bg-ink px-4 py-2 text-sm text-white shadow-lg">
      <b>{toast.user}</b> {t(`activity.${toast.event_type}`)}
    </div>
  );
}

export default function Toasts() {
  const { toasts, dismiss } = useRealtimeStore();
  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onDone={() => dismiss(toast.id)} />
      ))}
    </div>
  );
}
