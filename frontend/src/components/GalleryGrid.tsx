"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "@/lib/api";
import { downloadZip } from "@/lib/download";
import type { Media } from "@/lib/types";
import { useAuthStore } from "@/stores/auth";
import { useRealtimeStore } from "@/stores/realtime";

import FilterBar, { type GalleryView } from "./FilterBar";
import GallerySkeleton from "./GallerySkeleton";
import Lightbox from "./Lightbox";
import MediaGrid from "./MediaGrid";
import SelectionBar from "./SelectionBar";

const PAGE = 24;

export default function GalleryGrid({ refreshKey }: { refreshKey: number }) {
  const { t } = useTranslation();
  const myUserId = useAuthStore((s) => s.user?.id);
  const [items, setItems] = useState<Media[]>([]);
  const offset = useRef(0);
  const pending = useRef<AbortController | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [type, setType] = useState("");
  const [uploader, setUploader] = useState("");
  const [uploaders, setUploaders] = useState<string[]>([]);
  const [sort, setSort] = useState("newest");
  const [active, setActive] = useState<Media | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [selectMode, setSelectMode] = useState(false);
  const [selectingAll, setSelectingAll] = useState(false);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [count, setCount] = useState<number | null>(null);
  const [view, setView] = useState<GalleryView>("grid");
  const uploadTick = useRealtimeStore((s) => s.uploadTick);
  const sentinel = useRef<HTMLDivElement | null>(null);

  const load = useCallback(
    async (reset: boolean, background = false) => {
      if (background && pending.current) return;
      pending.current?.abort();
      const controller = new AbortController();
      pending.current = controller;
      const nextOffset = reset ? 0 : offset.current;
      const limit = reset ? Math.max(PAGE, offset.current) : PAGE;
      if (!background) setLoading(true);
      try {
        const refreshed: Media[] = [];
        let more = false;
        do {
          const params = new URLSearchParams({ sort, limit: String(Math.min(100, limit - refreshed.length)), offset: String(nextOffset + refreshed.length) });
          if (type) params.set("media_type", type);
          if (uploader) params.set("uploader", uploader);
          const { data } = await api.get(`/media?${params}`, { signal: controller.signal });
          refreshed.push(...data.items);
          more = data.has_more;
          if (!data.items.length) break;
        } while (more && refreshed.length < limit);
        if (controller.signal.aborted) return;
        setItems((prev) => reset ? refreshed : [...prev, ...refreshed]);
        setHasMore(more);
        offset.current = nextOffset + refreshed.length;
      } catch {
        // Preserve the current gallery during a transient failure; polling retries.
      } finally {
        if (pending.current === controller) {
          pending.current = null;
          setLoading(false);
        }
      }
    },
    [sort, type, uploader]
  );

  useEffect(() => {
    offset.current = 0;
    return () => pending.current?.abort();
  }, [load]);

  useEffect(() => {
    void load(true);
  }, [load, refreshKey, uploadTick]);

  useEffect(() => {
    const refresh = () => {
      if (document.visibilityState !== "visible") return;
      void load(true, true);
      const params = new URLSearchParams();
      if (type) params.set("media_type", type);
      if (uploader) params.set("uploader", uploader);
      api.get<number>(`/media/count?${params}`).then(({ data }) => setCount(data)).catch(() => {});
    };
    const timer = window.setInterval(refresh, 3000);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [load, type, uploader]);

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

  function exitSelectMode() {
    setSelectMode(false);
    setSelected(new Set());
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
        onTypeChange={(value) => {
          if (value !== type) setLoading(true);
          setType(value);
        }}
        onUploaderChange={(value) => {
          if (value !== uploader) setLoading(true);
          setUploader(value);
        }}
        onSortChange={(value) => {
          if (value !== sort) setLoading(true);
          setSort(value);
        }}
        onViewChange={setView}
        selectMode={selectMode}
        onToggleSelectMode={() => (selectMode ? exitSelectMode() : setSelectMode(true))}
      />

      {selectMode && items.length > 0 && (
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

      {loading && items.length === 0 ? (
        <GallerySkeleton />
      ) : items.length === 0 ? (
        type || uploader ? (
          <div className="space-y-3 py-10 text-center">
            <p className="text-gray-500">{t("gallery.noMatches")}</p>
            <button
              type="button"
              onClick={() => {
                setLoading(true);
                setType("");
                setUploader("");
              }}
              className="rounded border border-charcoal/20 px-3 py-2 text-sm hover:bg-charcoal/5"
            >
              {t("gallery.clearFilters")}
            </button>
          </div>
        ) : (
          <div className="space-y-2 py-10 text-center text-gray-500">
            <p>{t("gallery.empty")}</p>
            <p className="text-sm md:hidden">{t("gallery.emptyMobile")}</p>
            <p className="hidden text-sm md:block">{t("gallery.emptyDesktop")}</p>
          </div>
        )
      ) : (
        <MediaGrid
          items={items}
          onOpen={setActive}
          selectable={selectMode}
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
