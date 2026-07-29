"use client";

import { mediaUrl } from "@/lib/api";
import type { Media } from "@/lib/types";

import BlurImage from "./BlurImage";

export default function MediaGrid({
  items,
  onOpen,
  selectable = false,
  selected,
  onToggleSelect,
}: {
  items: Media[];
  onOpen: (m: Media) => void;
  selectable?: boolean;
  selected?: Set<number>;
  onToggleSelect?: (id: number) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
      {items.map((m) => (
        <div key={m.id} className="relative aspect-square">
          <button onClick={() => onOpen(m)} className="h-full w-full">
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
            {m.uploader_name}
          </span>
          {selectable && (
            <input
              type="checkbox"
              aria-label="select"
              checked={selected?.has(m.id) ?? false}
              onChange={() => onToggleSelect?.(m.id)}
              className="absolute left-1 top-1 h-5 w-5"
            />
          )}
        </div>
      ))}
    </div>
  );
}
