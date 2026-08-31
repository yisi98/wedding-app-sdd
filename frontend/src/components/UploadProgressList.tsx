"use client";

import { useTranslation } from "react-i18next";

import type { UploadItem } from "@/lib/useUploader";

export default function UploadProgressList({ items }: { items: UploadItem[] }) {
  const { t } = useTranslation();
  if (items.length === 0) return null;

  // Failed files never transferred any bytes, so they are excluded from the batch
  // progress — counting them as "100% done" made the bar jump to 50% the instant a
  // rejection landed, even while the real upload was still at 0%.
  const tracked = items.filter((it) => it.status !== "error");
  const failed = items.filter((it) => it.status === "error").length;
  const done = tracked.filter((it) => it.status !== "uploading").length;
  const overall = tracked.length
    ? Math.round(
        tracked.reduce((sum, it) => sum + (it.status === "uploading" ? it.progress : 100), 0) /
          tracked.length
      )
    : null;

  return (
    <div className="text-xs">
      {/* FR-006 aggregate progress across the batch, alongside the per-file rows. */}
      {tracked.length > 0 && (
        <>
          <div className="mb-1 flex justify-between text-gray-500">
            <span>
              {t("upload.overall", { done, total: tracked.length })}
              {failed > 0 && (
                <span className="ml-2 text-red-600">
                  {t("upload.failedCount", { count: failed })}
                </span>
              )}
            </span>
            <span>{overall}%</span>
          </div>
          <div className="h-1 w-full overflow-hidden rounded bg-charcoal/10">
            <div className="h-full bg-accent transition-all" style={{ width: `${overall}%` }} />
          </div>
        </>
      )}
      <ul className="mt-2 space-y-1">
        {items.map((it, i) => (
          <li key={i} className="flex flex-col gap-0.5">
            <div
              className={`flex items-center gap-2 rounded px-1 py-0.5 ${
                it.status === "error" ? "bg-red-500/10" : ""
              }`
            }
            >
              <span className="flex-1 truncate">{it.name}</span>
              <span
                className={
                  it.status === "error"
                    ? "shrink-0 font-medium text-red-600"
                    : it.status === "duplicate"
                      ? "shrink-0 text-gray-500"
                      : it.status === "done"
                        ? "shrink-0 text-green-600"
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
            {it.status === "uploading" && (
              <div className="h-0.5 w-full overflow-hidden rounded bg-charcoal/10">
                <div
                  className="h-full bg-accent transition-all"
                  style={{ width: `${it.progress}%` }}
                />
              </div>
            )}
            {it.status === "error" && it.message && (
              <span role="alert" className="px-1 text-red-600">
                {it.message}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
