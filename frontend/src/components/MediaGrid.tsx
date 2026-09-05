"use client";

import { useTranslation } from "react-i18next";

import { mediaUrl } from "@/lib/api";
import type { Media } from "@/lib/types";

import BlurImage from "./BlurImage";

export default function MediaGrid({
  items,
  onOpen,
  selectable = false,
  selected,
  onToggleSelect,
  view = "grid",
}: {
  items: Media[];
  onOpen: (m: Media) => void;
  selectable?: boolean;
  selected?: Set<number>;
  onToggleSelect?: (id: number) => void;
  view?: "grid" | "list";
}) {
  const { t } = useTranslation();

  const checkbox = (m: Media) =>
    selectable && (
      <input
        type="checkbox"
        aria-label={t("gallery.select")}
        checked={selected?.has(m.id) ?? false}
        onChange={() => onToggleSelect?.(m.id)}
        className="h-5 w-5"
      />
    );

  if (view === "list") {
    return (
      <ul className="divide-y divide-gray-100">
        {items.map((m) => (
          <li key={m.id} className="flex items-center gap-3 py-2">
            <span onClick={(e) => e.stopPropagation()}>{checkbox(m)}</span>
            <button onClick={() => (selectable ? onToggleSelect?.(m.id) : onOpen(m))} className="flex min-w-0 flex-1 items-center gap-3 text-left">
              <BlurImage
                src={mediaUrl(m.thumbnail_path || m.optimized_path)}
                lqip={m.lqip}
                alt={m.original_filename}
                className="h-14 w-14 shrink-0 rounded object-cover"
              />
              <span className="min-w-0">
                <span className="block truncate text-sm">
                  {m.original_filename}
                  {m.media_type === "video" && <span className="ml-1 text-gray-400">▶</span>}
                </span>
                <span className="block truncate text-xs text-gray-500">
                  {m.uploader_name ?? t("gallery.deletedGuest")} ·{" "}
                  {new Date(m.created_at).toLocaleDateString()}
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
      {items.map((m) => (
        <div key={m.id} className="relative aspect-square">
          <button onClick={() => (selectable ? onToggleSelect?.(m.id) : onOpen(m))} className="h-full w-full">
            <BlurImage
              src={mediaUrl(m.thumbnail_path || m.optimized_path)}
              lqip={m.lqip}
              alt={m.original_filename}
              className="h-full w-full rounded"
            />
          </button>
          {m.media_type === "video" && (
            <span className="pointer-events-none absolute bottom-1 right-1 rounded bg-black/60 px-1 text-xs text-white">
              ▶
            </span>
          )}
          <span className="pointer-events-none absolute bottom-1 left-1 max-w-[80%] truncate rounded bg-black/60 px-1 text-xs text-white">
            {m.uploader_name ?? t("gallery.deletedGuest")}
          </span>
          {selectable && (
            <span className="absolute left-1 top-1" onClick={(e) => e.stopPropagation()}>{checkbox(m)}</span>
          )}
        </div>
      ))}
    </div>
  );
}
