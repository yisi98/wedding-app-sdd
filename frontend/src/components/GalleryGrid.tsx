"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "@/lib/api";
import { downloadZip } from "@/lib/download";
import type { Media } from "@/lib/types";
import { useAuthStore } from "@/stores/auth";
import { useRealtimeStore } from "@/stores/realtime";

import FilterBar, { type GalleryView } from "./FilterBar";
import Lightbox from "./Lightbox";
import MediaGrid from "./MediaGrid";
import SelectionBar from "./SelectionBar";

const PAGE = 24;

export default function GalleryGrid({ refreshKey }: { refreshKey: number }) {
  const { t } = useTranslation();
  const myUserId = useAuthStore((s) => s.user?.id);
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
  const [deleting, setDeleting] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [count, setCount] = useState<number | null>(null);
  const [view, setView] = useState<GalleryView>("grid");
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

  // "N items" badge: total matching the filters (not just the loaded page).
  useEffect(() => {
    const params = new URLSearchParams();
    if (type) params.set("media_type", type);
    if (uploader) params.set("uploader", uploader);
    api
      .get<number>(`/media/count?${params.toString()}`)
      .then(({ data }) => setCount(data))
      .catch(() => {});
  }, [type, uploader, refreshKey, uploadTick]);

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

  // An upload was deleted by its owner from the lightbox: drop it from the grid and
  // close the lightbox (its `media` object no longer exists).
  function handleDeleted(id: number) {
    setItems((prev) => prev.filter((m) => m.id !== id));
    setActive(null);
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

  // Multi-select delete: only the caller's OWN uploads can go. If the selection mixes
  // own and foreign items, the confirm warns about the foreign ones; the backend then
  // deletes the own items and returns the foreign ids in `skipped` so their tiles stay.
  async function bulkDelete() {
    if (deleting || selected.size === 0) return;
    const selItems = items.filter((m) => selected.has(m.id));
    const mineCount = selItems.filter((m) => m.uploader_id === myUserId).length;
    const othersCount = selItems.length - mineCount;
    // "Select all matching" can exceed the loaded pages; those ids can't be checked
    // locally, but the server deletes own uploads only regardless.
    const uncheckedCount = selected.size - selItems.length;

    if (mineCount === 0 && uncheckedCount === 0) {
      window.alert(t("gallery.cannotDeleteOthers"));
      return;
    }
    let msg = t("gallery.deleteConfirm", { count: selected.size });
    if (othersCount > 0) msg += `\n${t("gallery.othersWarning", { count: othersCount })}`;
    else if (uncheckedCount > 0) msg += `\n${t("gallery.onlyOwnDeletes")}`;
    if (!window.confirm(msg)) return;

    setDeleting(true);
    try {
      const { data } = await api.post<{ deleted: number[]; skipped: number[] }>(
        "/media/bulk-delete",
        { media_ids: Array.from(selected) }
      );
      const deletedSet = new Set(data.deleted);
      setItems((prev) => prev.filter((m) => !deletedSet.has(m.id)));
      setActive((prev) => (prev && deletedSet.has(prev.id) ? null : prev));
      // Skipped (someone else's) items stay selected so the user sees they remain.
      setSelected(new Set(data.skipped));
      setCount((c) => (c === null ? c : Math.max(0, c - data.deleted.length)));
      if (data.deleted.length > 0) {
        const summary = [t("gallery.deletedCount", { count: data.deleted.length })];
        if (data.skipped.length > 0) {
          summary.push(t("gallery.skippedCount", { count: data.skipped.length }));
        }
        window.alert(summary.join("\n"));
      }
    } finally {
      setDeleting(false);
    }
  }

  async function bulkDownload() {
    if (downloading || selected.size === 0) return;
    setDownloading(true);
    try {
      await downloadZip(Array.from(selected), t("share.archiveFilename"));
    } catch {
      window.alert(t("share.downloadFailed"));
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div>
      <FilterBar
        type={type}
        uploader={uploader}
        sort={sort}
        uploaders={uploaders}
        count={count}
        view={view}
        onTypeChange={setType}
        onUploaderChange={setUploader}
        onSortChange={setSort}
        onViewChange={setView}
      />

      {items.length > 0 && (
        <SelectionBar
          count={selected.size}
          selectAllLabel={selectingAll ? t("gallery.selecting") : t("gallery.selectAllMatching")}
          selectingAll={selectingAll}
          onSelectAll={selectAllMatching}
          onClear={() => setSelected(new Set())}
          onDownload={bulkDownload}
          downloading={downloading}
          deleteLabel={
            deleting ? t("gallery.deleting") : `🗑 ${t("gallery.delete")} ${selected.size}`
          }
          onDelete={bulkDelete}
          deleting={deleting}
        />
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
          view={view}
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
          onDeleted={handleDeleted}
        />
      )}
    </div>
  );
}
