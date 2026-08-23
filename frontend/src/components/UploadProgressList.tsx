"use client";

import { useTranslation } from "react-i18next";

import type { UploadItem } from "@/lib/useUploader";

export default function UploadProgressList({ items }: { items: UploadItem[] }) {
  const { t } = useTranslation();
  if (items.length === 0) return null;

  const finished = items.filter((it) => it.status !== "uploading").length;
  const overall = Math.round(
    items.reduce((sum, it) => sum + (it.status === "uploading" ? it.progress : 100), 0) / items.length
  );

  return (
    <div className="text-xs">
      {/* FR-006 aggregate progress across the batch, alongside the per-file rows. */}
      <div className="mb-1 flex justify-between text-gray-500">
        <span>{t("upload.overall", { done: finished, total: items.length })}</span>
        <span>{overall}%</span>
      </div>
      <div className="h-1 w-full overflow-hidden rounded bg-charcoal/10">
        <div className="h-full bg-accent transition-all" style={{ width: `${overall}%` }} />
      </div>
      <ul className="mt-2 space-y-1">
        {items.map((it, i) => (
          <li key={i} className="flex flex-col gap-0.5">
            <div className="flex items-center gap-2">
              <span className="flex-1 truncate">{it.name}</span>
              <span
                className={
                  it.status === "error"
                    ? "shrink-0 font-medium text-red-600"
                    : it.status === "duplicate"
                      ? "shrink-0 text-gray-500"
                      : "shrink-0"
                }
              >
                {it.status === "done"
                  ? t("upload.done")
                  : it.status === "duplicate"
                    ? t("upload.duplicate")
                    : it.status === "error"
                      ? t("upload.failed")
                      : `${it.progress}%`}
              </span>
            </div>
            {it.status === "error" && it.message && (
              <span role="alert" className="text-red-600">
                {it.message}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
