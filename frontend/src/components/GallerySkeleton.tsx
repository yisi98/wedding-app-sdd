"use client";

import { useTranslation } from "react-i18next";

export default function GallerySkeleton() {
  const { t } = useTranslation();

  return (
    <div role="status" aria-label={t("gallery.loading")}>
      <span className="sr-only">{t("gallery.loading")}</span>
      <div aria-hidden="true" className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
        {Array.from({ length: 8 }, (_, index) => (
          <div
            key={index}
            className="aspect-square animate-pulse rounded bg-gray-200 motion-reduce:animate-none"
          />
        ))}
      </div>
    </div>
  );
}
