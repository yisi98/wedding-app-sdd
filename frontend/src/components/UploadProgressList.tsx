"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { UploadItem } from "@/lib/useUploader";

export default function UploadProgressList({ items, onDismiss }: { items: UploadItem[]; onDismiss?: () => void }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  if (items.length === 0) return null;

  // Failed files never transferred any bytes, so they are excluded from the batch
  // progress — counting them as "100% done" made the bar jump to 50% the instant a
  // rejection landed, even while the real upload was still at 0%.
  const tracked = items.filter((it) => it.status !== "error");
  const failed = items.filter((it) => it.status === "error").length;
  const done = tracked.filter((it) => it.status !== "uploading").length;
  const total = items.length;
  const overall = tracked.length
    ? Math.round(
        tracked.reduce((sum, it) => sum + (it.status === "uploading" ? it.progress : 100), 0) /
          tracked.length
      )
    : null;

  return (
    <div className="text-xs">
      {/* FR-006 aggregate progress across the batch, alongside the per-file rows. */}
      {(tracked.length > 0 || failed > 0) && (
        <>
          <div className="mb-1 flex items-center gap-2 text-gray-500">
            <button type="button" onClick={() => setExpanded((value) => !value)} className="flex min-w-0 flex-1 items-center gap-2 text-left">
              <span className={`text-[10px] transition-transform ${expanded ? "rotate-180" : ""}`}>⌄</span>
              <span className="truncate">
              {t("upload.overall", { done, total })}
              {failed > 0 && (
                <span className="ml-2 text-red-600">
                  {t("upload.failedCount", { count: failed })}
                </span>
              )}
              </span>
              {overall !== null && <span className="shrink-0">{overall}%</span>}
            </button>
            {onDismiss && <button type="button" onClick={onDismiss} aria-label={t("upload.dismiss")} className="shrink-0 px-1 text-lg leading-none text-gray-500 hover:text-charcoal">×</button>}
          </div>
          {overall !== null && <div className="h-1 w-full overflow-hidden rounded bg-charcoal/10">
            <div className="h-full bg-accent transition-all" style={{ width: `${overall}%` }} />
          </div>}
        </>
      )}
      {expanded && <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto pr-1">
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
      </ul>}
    </div>
  );
}
