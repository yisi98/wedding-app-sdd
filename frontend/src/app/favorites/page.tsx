"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import GallerySkeleton from "@/components/GallerySkeleton";
import Lightbox from "@/components/Lightbox";
import MediaGrid from "@/components/MediaGrid";
import Nav from "@/components/Nav";
import SelectionBar from "@/components/SelectionBar";
import { api } from "@/lib/api";
import { downloadZip } from "@/lib/download";
import type { Media } from "@/lib/types";
import { useAuthGuard } from "@/lib/useAuthGuard";

export default function FavoritesPage() {
  const { ready } = useAuthGuard();
  const { t } = useTranslation();
  const [items, setItems] = useState<Media[]>([]);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState<Media | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [downloading, setDownloading] = useState(false);
  const [removing, setRemoving] = useState(false);

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    setLoading(true);
    api.get("/media/favorites")
      .then(({ data }) => {
        if (!cancelled) setItems(data);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [ready]);

  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  // A favorited item deleted by its owner: drop it locally instead of refetching.
  function handleDeleted(id: number) {
    setItems((prev) => prev.filter((m) => m.id !== id));
    setSelected((prev) => {
      if (!prev.has(id)) return prev;
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
    setActive(null);
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

  // "Delete" on this page means removing items from the favorites list — the media
  // itself stays in the gallery (owners can still delete their own uploads there).
  async function bulkRemove() {
    if (removing || selected.size === 0) return;
    if (!window.confirm(t("favorites.removeConfirm", { count: selected.size }))) return;
    setRemoving(true);
    try {
      const { data } = await api.post<{ removed: number[]; skipped: number[] }>(
        "/media/favorites/bulk-remove",
        { media_ids: Array.from(selected) }
      );
      const removedSet = new Set(data.removed);
      setItems((prev) => prev.filter((m) => !removedSet.has(m.id)));
      setActive((prev) => (prev && removedSet.has(prev.id) ? null : prev));
      setSelected(new Set());
      if (data.removed.length > 0) {
        window.alert(t("favorites.removedCount", { count: data.removed.length }));
      }
    } catch {
      window.alert(t("favorites.removeFailed"));
    } finally {
      setRemoving(false);
    }
  }

  if (!ready) return null;

  return (
    <>
      <Nav />
      <main className="pb-24 md:pb-4 md:pl-56">
        <div className="mx-auto max-w-5xl p-4">
          <h1 className="mb-3 text-lg font-semibold">{t("nav.favorites")}</h1>
          {items.length > 0 && (
            <SelectionBar
              count={selected.size}
              selectAllLabel={t("favorites.selectAll")}
              onSelectAll={() => setSelected(new Set(items.map((m) => m.id)))}
              onClear={() => setSelected(new Set())}
              onDownload={bulkDownload}
              downloading={downloading}
              deleteLabel={
                removing
                  ? t("favorites.removing")
                  : `♥ ${t("favorites.remove")} ${selected.size}`
              }
              onDelete={bulkRemove}
              deleting={removing}
            />
          )}
          {loading && items.length === 0 ? (
            <GallerySkeleton />
          ) : items.length === 0 ? (
            <p className="py-10 text-center text-gray-500">{t("favorites.empty")}</p>
          ) : (
            <MediaGrid
              items={items}
              onOpen={setActive}
              selectable
              selected={selected}
              onToggleSelect={toggleSelect}
            />
          )}
        </div>
      </main>
      {active && (
        <Lightbox
          media={active}
          items={items}
          onClose={() => setActive(null)}
          onOpenMedia={setActive}
          onDeleted={handleDeleted}
        />
      )}
    </>
  );
}
