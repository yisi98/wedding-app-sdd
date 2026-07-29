"use client";

import { useState } from "react";

import ActivityFeed from "@/components/ActivityFeed";
import GalleryGrid from "@/components/GalleryGrid";
import Nav from "@/components/Nav";
import Uploader from "@/components/Uploader";
import { useAuthGuard } from "@/lib/useAuthGuard";

export default function GalleryPage() {
  const { ready } = useAuthGuard();
  const [refreshKey, setRefreshKey] = useState(0);

  if (!ready) return null;

  return (
    <>
      <Nav />
      <ActivityFeed />
      <main className="mx-auto max-w-5xl p-4">
        <Uploader onUploaded={() => setRefreshKey((k) => k + 1)} />
        <GalleryGrid refreshKey={refreshKey} />
      </main>
    </>
  );
}
