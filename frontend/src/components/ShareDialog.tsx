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
      <div className="w-80 rounded-lg bg-white p-6 text-center" onClick={(e) => e.stopPropagation()}>
        <h3 className="mb-4 font-semibold">{t("share.title")}</h3>
        {url ? (
          <>
            <div className="mb-4 flex justify-center">
              <QRCodeSVG value={url} size={160} />
            </div>
            <input readOnly value={url} className="mb-3 w-full rounded border px-2 py-1 text-xs" />
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
