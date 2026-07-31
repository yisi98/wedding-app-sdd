"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import BlurImage from "@/components/BlurImage";
import { api, mediaUrl } from "@/lib/api";
import type { Media } from "@/lib/types";

export default function SharePage() {
  const { t } = useTranslation();
  const params = useParams();
  const token = String(params.token);
  const [media, setMedia] = useState<Media | null>(null);
  const [kind, setKind] = useState<string>("");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    api
      .get(`/share/${token}`)
      .then(({ data }) => {
        setKind(data.type);
        setMedia(data.media);
      })
      .catch((e) => setError(e.response?.status === 410 ? t("share.expired") : "404"));
  }, [token, t]);

  return (
    <main className="mx-auto max-w-3xl p-6 text-center">
      <h1 className="mb-4 text-xl font-semibold text-blush">{t("app.title")}</h1>
      {error && <p className="text-gray-500">{error}</p>}
      {kind === "gallery" && (
        <a href="/gallery" className="rounded bg-blush px-4 py-2 text-ink">
          {t("share.gallery")}
        </a>
      )}
      {kind === "item" && media && (
        media.media_type === "video" ? (
          <video src={mediaUrl(media.storage_path)} controls className="mx-auto max-h-[70vh]" />
        ) : (
          <BlurImage
            src={mediaUrl(media.optimized_path || media.storage_path)}
            lqip={media.lqip}
            alt={media.original_filename}
            className="mx-auto max-h-[70vh] w-auto"
            fit="contain"
          />
        )
      )}
    </main>
  );
}
