"use client";

import { useEffect } from "react";
import { useTranslation } from "react-i18next";

export default function ConfirmDialog({ message, onConfirm, onCancel }: { message: string; onConfirm: () => void; onCancel: () => void }) {
  const { t } = useTranslation();
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") onCancel(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
    <div className="w-full max-w-sm rounded-lg bg-paper p-5 shadow-xl">
      <p className="text-sm text-charcoal">{message}</p>
      <div className="mt-5 flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="rounded border border-charcoal/20 px-3 py-2 text-sm">{t("common.cancel")}</button>
        <button type="button" onClick={onConfirm} className="rounded bg-accent px-3 py-2 text-sm text-white">{t("common.confirm")}</button>
      </div>
    </div>
  </div>;
}
