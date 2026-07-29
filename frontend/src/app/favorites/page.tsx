"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import Lightbox from "@/components/Lightbox";
import MediaGrid from "@/components/MediaGrid";
import Nav from "@/components/Nav";
import { api } from "@/lib/api";
import type { Media } from "@/lib/types";
import { useAuthGuard } from "@/lib/useAuthGuard";

export default function FavoritesPage() {
  const { ready } = useAuthGuard();
  const { t } = useTranslation();
  const [items, setItems] = useState<Media[]>([]);
  const [active, setActive] = useState<Media | null>(null);

  useEffect(() => {
    if (ready) api.get("/media/favorites").then(({ data }) => setItems(data)).catch(() => {});
  }, [ready]);

  if (!ready) return null;

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-5xl p-4">
        <h1 className="mb-3 text-lg font-semibold">{t("nav.favorites")}</h1>
        {items.length === 0 ? (
          <p className="py-10 text-center text-gray-400">{t("gallery.empty")}</p>
        ) : (
          <MediaGrid items={items} onOpen={setActive} />
        )}
      </main>
      {active && <Lightbox media={active} onClose={() => setActive(null)} onOpenMedia={setActive} />}
    </>
  );
}
