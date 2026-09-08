"use client";

import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import ActivityFeed from "@/components/ActivityFeed";
import GalleryGrid from "@/components/GalleryGrid";
import Nav from "@/components/Nav";
import Uploader from "@/components/Uploader";
import { useAuthGuard } from "@/lib/useAuthGuard";

export default function GalleryPage() {
  const { ready } = useAuthGuard();
  const { t } = useTranslation();
  const [refreshKey, setRefreshKey] = useState(0);
  const uploadPicker = useRef<(() => void) | null>(null);

  if (!ready) return null;

  return (
    <>
      <Nav />
      <ActivityFeed />
      <main className="pb-24 md:pb-4 md:pl-56">
        <div className="mx-auto max-w-5xl p-4">
          <header className="mb-4 md:hidden">
            <h1 className="font-serif text-xl font-semibold text-accent">{t("app.title")}</h1>
            <p className="text-sm text-gray-500">{t("app.tagline")}</p>
            <p className="text-xs text-gray-400">{t("app.date")}</p>
          </header>
          <Uploader onUploaded={() => setRefreshKey((k) => k + 1)} onPickerReady={(open) => { uploadPicker.current = open; }} />
          <GalleryGrid refreshKey={refreshKey} onUpload={() => uploadPicker.current?.()} />
        </div>
      </main>
    </>
  );
}
