"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import Nav from "@/components/Nav";
import { api, API_BASE, mediaUrl } from "@/lib/api";
import type { Media, User } from "@/lib/types";
import { useAuthGuard } from "@/lib/useAuthGuard";
import { useAuthStore } from "@/stores/auth";

const PAGE = 24;

interface Stats {
  total_media: number;
  total_users: number;
  total_views: number;
  total_reactions: number;
  total_comments: number;
  storage_bytes: number;
  media_by_type: Record<string, number>;
  top_by_views: { id: number; filename: string; view_count: number }[];
}

interface EventConfig {
  uploads_enabled: boolean;
  max_image_bytes: number;
  max_video_bytes: number;
  event_name: string;
  event_date: string | null;
}

export default function AdminPage() {
  const { ready, user: me } = useAuthGuard(true);
  const { t } = useTranslation();
  const [stats, setStats] = useState<Stats | null>(null);
  const [config, setConfig] = useState<EventConfig | null>(null);

  const [users, setUsers] = useState<User[]>([]);
  const [userPage, setUserPage] = useState(0);
  const [usersHaveMore, setUsersHaveMore] = useState(false);
  const [userQuery, setUserQuery] = useState("");

  const [media, setMedia] = useState<Media[]>([]);
  const [mediaPage, setMediaPage] = useState(0);
  const [mediaHasMore, setMediaHasMore] = useState(false);

  const loadUsers = useCallback(async () => {
    const params = new URLSearchParams({
      limit: String(PAGE),
      offset: String(userPage * PAGE),
    });
    if (userQuery) params.set("q", userQuery);
    const { data } = await api.get(`/admin/users?${params}`);
    setUsers(data.items);
    setUsersHaveMore(data.has_more);
  }, [userPage, userQuery]);

  const loadMedia = useCallback(async () => {
    const { data } = await api.get(`/admin/media?limit=${PAGE}&offset=${mediaPage * PAGE}`);
    setMedia(data.items);
    setMediaHasMore(data.has_more);
  }, [mediaPage]);

  const loadSummary = useCallback(async () => {
    const [s, c] = await Promise.all([api.get("/admin/stats"), api.get("/admin/config")]);
    setStats(s.data);
    setConfig(c.data);
  }, []);

  useEffect(() => {
    if (ready) loadSummary().catch(() => {});
  }, [ready, loadSummary]);
  useEffect(() => {
    if (ready) loadUsers().catch(() => {});
  }, [ready, loadUsers]);
  useEffect(() => {
    if (ready) loadMedia().catch(() => {});
  }, [ready, loadMedia]);

  // Searching while on a later page would otherwise land on an empty page of results.
  function search(value: string) {
    setUserQuery(value);
    setUserPage(0);
  }

  async function patchUser(id: number, body: Record<string, unknown>) {
    await api.patch(`/admin/users/${id}`, body);
    await Promise.all([loadUsers(), loadSummary()]);
  }

  async function removeUser(id: number) {
    if (!confirm(t("admin.confirmDeleteUser"))) return;
    await api.delete(`/admin/users/${id}`);
    await Promise.all([loadUsers(), loadSummary()]);
  }

  async function toggleVisibility(m: Media) {
    await api.patch(`/admin/media/${m.id}/visibility`, { is_visible: !m.is_visible });
    loadMedia();
  }

  async function removeMedia(m: Media) {
    if (!confirm(t("admin.confirmDeleteMedia"))) return;
    await api.delete(`/admin/media/${m.id}`);
    await Promise.all([loadMedia(), loadSummary()]);
  }

  async function toggleUploads() {
    if (!config) return;
    const { data } = await api.patch("/admin/config", {
      uploads_enabled: !config.uploads_enabled,
    });
    setConfig(data);
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
      <main className="pb-24 md:pb-4 md:pl-56">
        <div className="mx-auto max-w-5xl space-y-6 p-4">
          <section>
            <h2 className="mb-2 font-serif font-semibold">{t("admin.stats")}</h2>
            {stats && (
              <>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <Stat label={t("admin.totalMedia")} value={stats.total_media} />
                  <Stat label={t("admin.totalUsers")} value={stats.total_users} />
                  <Stat label={t("admin.totalViews")} value={stats.total_views} />
                  <Stat label={t("admin.totalReactions")} value={stats.total_reactions} />
                  <Stat label={t("admin.totalComments")} value={stats.total_comments} />
                  <Stat
                    label={t("admin.storage")}
                    value={`${(stats.storage_bytes / 1e6).toFixed(1)} MB`}
                  />
                </div>

                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <Breakdown
                    title={t("admin.byType")}
                    data={stats.media_by_type}
                    empty={t("admin.noneYet")}
                  />
                  <div className="rounded-md border border-charcoal/10 bg-paper p-3">
                    <div className="mb-1 text-xs font-medium text-gray-500">
                      {t("admin.topByViews")}
                    </div>
                    {stats.top_by_views.length === 0 ? (
                      <div className="text-xs text-gray-400">{t("admin.noneYet")}</div>
                    ) : (
                      <ul className="space-y-0.5 text-xs">
                        {stats.top_by_views.map((row) => (
                          <li key={row.id} className="flex justify-between gap-2">
                            <span className="truncate">{row.filename}</span>
                            <span className="shrink-0 text-gray-500">{row.view_count}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </>
            )}
          </section>

          <section>
            <h2 className="mb-2 font-serif font-semibold">{t("admin.settings")}</h2>
            {config && (
              <div className="flex flex-wrap items-center gap-3 rounded-md border border-charcoal/10 bg-paper p-3">
                <button
                  onClick={toggleUploads}
                  className={`rounded px-3 py-1 text-sm text-white ${
                    config.uploads_enabled ? "bg-accent" : "bg-red-500"
                  }`}
                >
                  {config.uploads_enabled ? t("admin.closeUploads") : t("admin.openUploads")}
                </button>
                <span className="text-sm text-gray-600">
                  {config.uploads_enabled ? t("admin.archiveOn") : t("admin.archiveOff")}
                </span>
              </div>
            )}
          </section>

          <section>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="font-serif font-semibold">{t("admin.media")}</h2>
              <button onClick={exportCsv} className="rounded bg-accent px-3 py-1 text-sm text-white">
                {t("admin.export")}
              </button>
            </div>
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
              {media.map((m) => {
                // Pending/failed items have no derivative yet; an <img> with an empty src
                // renders as a broken icon, which is exactly the state an admin most needs
                // to be able to identify and act on.
                const thumb = m.thumbnail_path || m.optimized_path;
                return (
                <div key={m.id} className="relative">
                  {thumb ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={mediaUrl(thumb)}
                      alt={m.original_filename}
                      className={`aspect-square w-full rounded object-cover ${
                        m.is_visible ? "" : "opacity-40"
                      }`}
                    />
                  ) : (
                    <div
                      className={`flex aspect-square w-full flex-col justify-center rounded bg-gray-200 p-1 text-center ${
                        m.is_visible ? "" : "opacity-40"
                      }`}
                    >
                      <span className="truncate text-[10px] text-gray-600">
                        {m.original_filename}
                      </span>
                      <span className="text-[10px] uppercase text-gray-400">{m.status}</span>
                    </div>
                  )}
                  <button
                    onClick={() => toggleVisibility(m)}
                    className="absolute bottom-1 right-1 rounded bg-black/70 px-1 text-xs text-white"
                  >
                    {m.is_visible ? t("admin.hide") : t("admin.show")}
                  </button>
                  <button
                    onClick={() => removeMedia(m)}
                    aria-label={t("admin.delete")}
                    className="absolute right-1 top-1 rounded bg-red-600/90 px-1 text-xs leading-none text-white"
                  >
                    ×
                  </button>
                </div>
                );
              })}
            </div>
            <Pager
              page={mediaPage}
              hasMore={mediaHasMore}
              onPrev={() => setMediaPage((p) => Math.max(0, p - 1))}
              onNext={() => setMediaPage((p) => p + 1)}
              prevLabel={t("admin.prev")}
              nextLabel={t("admin.next")}
            />
          </section>

          <section>
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-serif font-semibold">{t("admin.users")}</h2>
              <input
                value={userQuery}
                onChange={(e) => search(e.target.value)}
                placeholder={t("admin.searchUsers")}
                className="rounded border px-2 py-1 text-base sm:text-sm"
              />
            </div>
            <table className="w-full text-sm">
              <tbody>
                {users.map((u) => {
                  const isSelf = u.id === me?.id;
                  return (
                    <tr key={u.id} className="border-b">
                      <td className="py-1">
                        {u.username}
                        {isSelf && (
                          <span className="ml-1 text-xs text-gray-400">({t("admin.you")})</span>
                        )}
                      </td>
                      <td>{u.role}</td>
                      <td>{u.is_active ? "✓" : "✗"}</td>
                      <td className="space-x-2 py-1 text-right">
                        {/* FR-031: the API refuses self-edits, so don't offer them. */}
                        {!isSelf && (
                          <>
                            <button
                              onClick={() =>
                                patchUser(u.id, { role: u.role === "admin" ? "guest" : "admin" })
                              }
                              className="text-accent hover:underline"
                            >
                              {u.role === "admin" ? t("admin.demote") : t("admin.promote")}
                            </button>
                            <button
                              onClick={() => patchUser(u.id, { is_active: !u.is_active })}
                              className="text-gray-500 hover:underline"
                            >
                              {u.is_active ? t("admin.deactivate") : t("admin.activate")}
                            </button>
                            <button
                              onClick={() => removeUser(u.id)}
                              className="text-red-600 hover:underline"
                            >
                              {t("admin.delete")}
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <Pager
              page={userPage}
              hasMore={usersHaveMore}
              onPrev={() => setUserPage((p) => Math.max(0, p - 1))}
              onNext={() => setUserPage((p) => p + 1)}
              prevLabel={t("admin.prev")}
              nextLabel={t("admin.next")}
            />
          </section>
        </div>
      </main>
    </>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-md border border-charcoal/10 bg-paper p-3 text-center">
      <div className="font-serif text-2xl font-semibold">{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

function Breakdown({
  title,
  data,
  empty,
}: {
  title: string;
  data: Record<string, number>;
  empty: string;
}) {
  const entries = Object.entries(data ?? {});
  return (
    <div className="rounded-md border border-charcoal/10 bg-paper p-3">
      <div className="mb-1 text-xs font-medium text-gray-500">{title}</div>
      {entries.length === 0 ? (
        <div className="text-xs text-gray-400">{empty}</div>
      ) : (
        <ul className="space-y-0.5 text-xs">
          {entries.map(([key, count]) => (
            <li key={key} className="flex justify-between gap-2">
              <span className="truncate">{key}</span>
              <span className="shrink-0 text-gray-500">{count}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Pager({
  page,
  hasMore,
  onPrev,
  onNext,
  prevLabel,
  nextLabel,
}: {
  page: number;
  hasMore: boolean;
  onPrev: () => void;
  onNext: () => void;
  prevLabel: string;
  nextLabel: string;
}) {
  if (page === 0 && !hasMore) return null;
  return (
    <div className="mt-2 flex items-center gap-2 text-sm">
      <button
        onClick={onPrev}
        disabled={page === 0}
        className="rounded border px-2 py-1 disabled:opacity-40"
      >
        {prevLabel}
      </button>
      <span className="text-gray-500">{page + 1}</span>
      <button
        onClick={onNext}
        disabled={!hasMore}
        className="rounded border px-2 py-1 disabled:opacity-40"
      >
        {nextLabel}
      </button>
    </div>
  );
}
