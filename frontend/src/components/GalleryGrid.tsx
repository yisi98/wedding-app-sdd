"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, API_BASE } from "@/lib/api";
import type { Media } from "@/lib/types";
import { useAuthStore } from "@/stores/auth";
import { useRealtimeStore } from "@/stores/realtime";

import Lightbox from "./Lightbox";
import MediaGrid from "./MediaGrid";

const PAGE = 24;

export default function GalleryGrid({ refreshKey }: { refreshKey: number }) {
  const { t } = useTranslation();
  const [items, setItems] = useState<Media[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [type, setType] = useState("");
  const [uploader, setUploader] = useState("");
  const [uploaders, setUploaders] = useState<string[]>([]);
  const [sort, setSort] = useState("newest");
  const [active, setActive] = useState<Media | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [selectingAll, setSelectingAll] = useState(false);
  const [loading, setLoading] = useState(false);
  const uploadTick = useRealtimeStore((s) => s.uploadTick);
  const sentinel = useRef<HTMLDivElement | null>(null);

  const load = useCallback(
    async (reset: boolean) => {
      const nextOffset = reset ? 0 : offset;
      const params = new URLSearchParams({ sort, limit: String(PAGE), offset: String(nextOffset) });
      if (type) params.set("media_type", type);
      if (uploader) params.set("uploader", uploader);
      setLoading(true);
      try {
        const { data } = await api.get(`/media?${params.toString()}`);
        setItems((prev) => (reset ? data.items : [...prev, ...data.items]));
        setHasMore(data.has_more);
        setOffset(nextOffset + PAGE);
      } finally {
        setLoading(false);
      }
    },
    [offset, sort, type, uploader]
  );

  useEffect(() => {
    load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sort, type, uploader, refreshKey]);

  useEffect(() => {
    api.get("/media/uploaders").then(({ data }) => setUploaders(data));
  }, [refreshKey, uploadTick]);

  // Someone else uploaded: pull the first page again so the new photo actually appears,
  // instead of only announcing it via a toast (FR-022).
  useEffect(() => {
    if (uploadTick === 0) return;
    load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uploadTick]);

  // FR-011 infinite scroll: fetch the next page as the sentinel comes into view. The
  // "Load more" button stays as a fallback for browsers without IntersectionObserver.
  useEffect(() => {
    const node = sentinel.current;
    if (!node || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loading) load(false);
      },
      { rootMargin: "300px" }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [hasMore, loading, load]);

  // A selection made under one filter combination doesn't necessarily make sense under
  // another (it may include items no longer shown), so changing filters clears it.
  useEffect(() => {
    setSelected(new Set());
  }, [type, uploader]);

  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function selectAllMatching() {
    setSelectingAll(true);
    try {
      const params = new URLSearchParams();
      if (type) params.set("media_type", type);
      if (uploader) params.set("uploader", uploader);
      const { data } = await api.get(`/media/ids?${params.toString()}`);
      setSelected(new Set<number>(data));
    } finally {
      setSelectingAll(false);
    }
  }

  async function bulkDownload() {
    const token = useAuthStore.getState().accessToken;
    const res = await fetch(`${API_BASE}/api/v1/downloads/bulk`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ media_ids: Array.from(selected) }),
    });
    if (!res.ok) {
      alert(t("share.downloadFailed"));
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = t("share.archiveFilename");
    // Safari (and some older WebKit builds) only honors a click-triggered download when
    // the anchor is actually in the document; an unattached element silently no-ops there.
    document.body.appendChild(a);
    a.click();
    a.remove();
    // Revoking synchronously can race the browser's own read of the blob URL, so give it
    // a moment before freeing it.
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <select value={type} onChange={(e) => setType(e.target.value)} className="rounded border px-2 py-1 text-sm">
          <option value="">{t("gallery.all")}</option>
          <option value="image">{t("gallery.images")}</option>
          <option value="video">{t("gallery.videos")}</option>
        </select>
        <select
          value={uploader}
          onChange={(e) => setUploader(e.target.value)}
          className="rounded border px-2 py-1 text-sm"
        >
          <option value="">{t("gallery.allUploaders")}</option>
          {uploaders.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value)} className="rounded border px-2 py-1 text-sm">
          <option value="newest">{t("gallery.sortNewest")}</option>
          <option value="oldest">{t("gallery.sortOldest")}</option>
          <option value="most_viewed">{t("gallery.sortMostViewed")}</option>
          <option value="most_liked">{t("gallery.sortMostLiked")}</option>
        </select>
      </div>

      {items.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <button
            onClick={selectAllMatching}
            disabled={selectingAll}
            className="rounded border px-2 py-1 text-sm disabled:opacity-50"
          >
            {selectingAll ? t("gallery.selecting") : t("gallery.selectAllMatching")}
          </button>
          {selected.size > 0 && (
            <>
              <button onClick={() => setSelected(new Set())} className="rounded border px-2 py-1 text-sm">
                {t("gallery.clearSelection")}
              </button>
              <button onClick={bulkDownload} className="rounded bg-accent px-3 py-1 text-sm text-white">
                ⬇ {selected.size}
              </button>
            </>
          )}
        </div>
      )}

      {items.length === 0 ? (
        <p className="py-10 text-center text-gray-400">{t("gallery.empty")}</p>
      ) : (
        <MediaGrid
          items={items}
          onOpen={setActive}
          selectable
          selected={selected}
          onToggleSelect={toggleSelect}
        />
      )}

      <div ref={sentinel} aria-hidden className="h-1" />

      {hasMore && (
        <div className="mt-4 text-center">
          <button
            onClick={() => load(false)}
            disabled={loading}
            className="rounded bg-accent px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {loading ? t("gallery.loading") : t("gallery.loadMore")}
          </button>
        </div>
      )}

      {active && (
        <Lightbox
          media={active}
          items={items}
          onClose={() => setActive(null)}
          onOpenMedia={setActive}
        />
      )}
    </div>
  );
}
