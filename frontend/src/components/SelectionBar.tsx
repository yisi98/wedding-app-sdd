"use client";

import { useTranslation } from "react-i18next";

type SelectionBarProps = {
  /** Number of currently selected items; action buttons appear when > 0. */
  count: number;
  selectAllLabel: string;
  onSelectAll: () => void;
  selectingAll?: boolean;
  onClear: () => void;
  onDownload: () => void;
  downloading?: boolean;
  /** Full label for the destructive action (caller composes text + count). */
  deleteLabel: string;
  onDelete: () => void;
  deleting?: boolean;
};

/**
 * Selection toolbar shared by the gallery (delete own uploads) and favorites
 * (remove from favorites): select all / clear / download ZIP / destructive action.
 */
export default function SelectionBar({
  count,
  selectAllLabel,
  onSelectAll,
  selectingAll = false,
  onClear,
  onDownload,
  downloading = false,
  deleteLabel,
  onDelete,
  deleting = false,
}: SelectionBarProps) {
  const { t } = useTranslation();

  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      <button
        onClick={onSelectAll}
        disabled={selectingAll}
        className="rounded border px-2 py-1 text-sm disabled:opacity-50"
      >
        {selectAllLabel}
      </button>
      {count > 0 && (
        <>
          <button onClick={onClear} className="rounded border px-2 py-1 text-sm">
            {t("gallery.clearSelection")}
          </button>
          <button
            onClick={onDownload}
            disabled={downloading}
            title={t("gallery.downloadSelected")}
            aria-label={t("gallery.downloadSelected")}
            className="rounded bg-accent px-3 py-1 text-sm text-white disabled:opacity-50"
          >
            {downloading ? t("gallery.downloading") : `⬇ ${count}`}
          </button>
          <button
            onClick={onDelete}
            disabled={deleting}
            className="rounded bg-red-600 px-3 py-1 text-sm text-white disabled:opacity-50"
          >
            {deleteLabel}
          </button>
        </>
      )}
    </div>
  );
}
