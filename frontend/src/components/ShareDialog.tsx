"use client";

import { QRCodeSVG } from "qrcode.react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "@/lib/api";

export default function ShareDialog({
  mediaId,
  onClose,
}: {
  mediaId?: number | null;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [url, setUrl] = useState<string>("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api
      .post("/share", { media_id: mediaId ?? null })
      .then(({ data }) => setUrl(`${window.location.origin}/share/${data.token}`))
      .catch(() => setUrl(""));
  }, [mediaId]);

  // Escape must dismiss this: on a phone the backdrop is only a ~35px strip either side
  // of the dialog, so tapping outside is an awkward and easily-missed target.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
      }
    }
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [onClose]);

  async function copy() {
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function nativeShare() {
    if (navigator.share) await navigator.share({ url }).catch(() => {});
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="relative w-80 rounded-lg bg-white p-6 text-center"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          aria-label={t("share.close")}
          className="absolute right-2 top-1 px-2 text-2xl leading-none text-gray-400 hover:text-gray-700"
        >
          ×
        </button>
        <h3 className="mb-4 font-semibold">{t("share.title")}</h3>
        {url ? (
          <>
            <div className="mb-4 flex justify-center">
              <QRCodeSVG value={url} size={160} />
            </div>
            <input readOnly value={url} className="mb-3 w-full rounded border px-2 py-1 text-base sm:text-xs" />
            <div className="flex gap-2">
              <button onClick={copy} className="flex-1 rounded bg-blush px-3 py-2 text-sm">
                {copied ? t("share.copied") : t("share.copy")}
              </button>
              {typeof navigator !== "undefined" && "share" in navigator && (
                <button onClick={nativeShare} className="rounded bg-sage px-3 py-2 text-sm text-white">
                  {t("lightbox.share")}
                </button>
              )}
            </div>
          </>
        ) : (
          <p className="text-sm text-gray-500">…</p>
        )}
      </div>
    </div>
  );
}
