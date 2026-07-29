"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import Nav from "@/components/Nav";
import { api, API_BASE, mediaUrl } from "@/lib/api";
import type { Media, User } from "@/lib/types";
import { useAuthGuard } from "@/lib/useAuthGuard";
import { useAuthStore } from "@/stores/auth";

interface Stats {
  total_media: number;
  total_users: number;
  total_views: number;
  storage_bytes: number;
}

export default function AdminPage() {
  const { ready } = useAuthGuard(true);
  const { t } = useTranslation();
  const [stats, setStats] = useState<Stats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [media, setMedia] = useState<Media[]>([]);

  async function refresh() {
    const [s, u, m] = await Promise.all([
      api.get("/admin/stats"),
      api.get("/admin/users"),
      api.get("/admin/media"),
    ]);
    setStats(s.data);
    setUsers(u.data.items);
    setMedia(m.data);
  }

  useEffect(() => {
    if (ready) refresh().catch(() => {});
  }, [ready]);

  async function promote(id: number) {
    await api.patch(`/admin/users/${id}`, { role: "admin" });
    refresh();
  }
  async function deactivate(id: number) {
    await api.patch(`/admin/users/${id}`, { is_active: false });
    refresh();
  }
  async function toggleVisibility(m: Media) {
    await api.patch(`/admin/media/${m.id}/visibility`, { is_visible: !m.is_visible });
    refresh();
  }

  async function exportCsv() {
    const token = useAuthStore.getState().accessToken;
    const res = await fetch(`${API_BASE}/api/v1/admin/export/media`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "media.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  if (!ready) return null;

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-5xl space-y-6 p-4">
        <section>
          <h2 className="mb-2 font-semibold">{t("admin.stats")}</h2>
          {stats && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label={t("admin.totalMedia")} value={stats.total_media} />
              <Stat label={t("admin.totalUsers")} value={stats.total_users} />
              <Stat label={t("admin.totalViews")} value={stats.total_views} />
              <Stat label={t("admin.storage")} value={`${(stats.storage_bytes / 1e6).toFixed(1)} MB`} />
            </div>
          )}
        </section>

        <section>
          <div className="mb-2 flex items-center justify-between">
            <h2 className="font-semibold">{t("admin.media")}</h2>
            <button onClick={exportCsv} className="rounded bg-sage px-3 py-1 text-sm text-white">
              {t("admin.export")}
            </button>
          </div>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
            {media.map((m) => (
              <div key={m.id} className="relative">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={mediaUrl(m.thumbnail_path || m.optimized_path)}
                  alt={m.original_filename}
                  className={`aspect-square w-full rounded object-cover ${m.is_visible ? "" : "opacity-40"}`}
                />
                <button
                  onClick={() => toggleVisibility(m)}
                  className="absolute bottom-1 right-1 rounded bg-black/70 px-1 text-xs text-white"
                >
                  {m.is_visible ? t("admin.hide") : t("admin.show")}
                </button>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="mb-2 font-semibold">{t("admin.users")}</h2>
          <table className="w-full text-sm">
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b">
                  <td className="py-1">{u.username}</td>
                  <td>{u.role}</td>
                  <td>{u.is_active ? "✓" : "✗"}</td>
                  <td className="text-right">
                    {u.role !== "admin" && (
                      <button onClick={() => promote(u.id)} className="mr-2 text-blush hover:underline">
                        {t("admin.promote")}
                      </button>
                    )}
                    <button onClick={() => deactivate(u.id)} className="text-gray-500 hover:underline">
                      {t("admin.deactivate")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </main>
    </>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg bg-white p-3 text-center shadow">
      <div className="text-2xl font-semibold">{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}
