"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "@/lib/api";
import { useUploader } from "@/lib/useUploader";
import { useAuthStore } from "@/stores/auth";

import { IconGallery, IconPerson, IconPlus, IconSliders, IconStar } from "./icons";
import LanguageSwitcher from "./LanguageSwitcher";
import PushToggle from "./PushToggle";
import UploadProgressList from "./UploadProgressList";

const LINKS = [
  { href: "/gallery", key: "nav.gallery" },
  { href: "/favorites", key: "nav.favorites" },
] as const;

export default function Nav() {
  const { t } = useTranslation();
  const router = useRouter();
  const pathname = usePathname();
  const { user, clear } = useAuthStore();
  const [menuOpen, setMenuOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // Refresh callback is a no-op: a successful upload's own websocket broadcast already
  // bumps GalleryGrid's uploadTick and triggers its refetch, on whatever page it's mounted.
  const { items: uploadItems, handleFiles } = useUploader(() => {});

  async function logout() {
    try {
      await api.post("/auth/logout");
    } catch {
      /* ignore */
    }
    clear();
    router.replace("/login");
  }

  const linkClass = (href: string, base: string) =>
    `${base} ${pathname === href ? "text-accent" : "text-charcoal"}`;

  const utilityControls = (
    <>
      <PushToggle />
      <LanguageSwitcher />
      <button onClick={logout} className="text-left text-sm text-gray-600 hover:underline">
        {t("nav.logout")}
      </button>
    </>
  );

  return (
    <>
      {/* Desktop: fixed left sidebar. Upload happens via the dropzone on the gallery page
          (drag-and-drop), so there's no separate upload entry here. */}
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-56 flex-col border-r border-charcoal/10 bg-paper p-4 md:flex">
        <span className="mb-6 font-serif text-lg font-semibold text-accent">{t("app.title")}</span>
        <nav className="flex flex-col gap-1">
          {LINKS.map(({ href, key }) => (
            <Link
              key={href}
              href={href}
              className={linkClass(
                href,
                `rounded px-3 py-2 text-sm ${pathname === href ? "bg-accent/10 font-medium" : "hover:bg-charcoal/5"}`
              )}
            >
              {t(key)}
            </Link>
          ))}
          {user?.role === "admin" && (
            <Link
              href="/admin"
              className={linkClass(
                "/admin",
                `mt-2 rounded px-3 py-2 text-sm ${pathname === "/admin" ? "bg-accent/10 font-medium" : "hover:bg-charcoal/5"}`
              )}
            >
              {t("nav.admin")}
            </Link>
          )}
        </nav>
        <div className="mt-auto flex flex-col items-start gap-3 border-t border-charcoal/10 pt-4">
          {utilityControls}
        </div>
      </aside>

      {/* Mobile: fixed bottom tab bar. No drag-and-drop on mobile — the "+" button opens
          the native file picker directly (a real synchronous click, not a delayed one
          after navigation, which iOS Safari otherwise blocks). */}
      <nav className="fixed inset-x-0 bottom-0 z-20 flex items-center justify-around border-t border-charcoal/10 bg-paper py-2 md:hidden">
        <Link href="/gallery" className={linkClass("/gallery", "flex flex-col items-center gap-1 text-[11px]")}>
          <IconGallery />
          {t("nav.gallery")}
        </Link>
        <Link href="/favorites" className={linkClass("/favorites", "flex flex-col items-center gap-1 text-[11px]")}>
          <IconStar />
          {t("nav.favorites")}
        </Link>
        <button
          onClick={() => fileInputRef.current?.click()}
          aria-label={t("nav.upload")}
          className="-mt-6 flex h-12 w-12 items-center justify-center rounded-full bg-accent text-white shadow"
        >
          <IconPlus width={24} height={24} strokeWidth={2} />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,video/*"
          multiple
          hidden
          onChange={(e) => {
            handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
        {user?.role === "admin" && (
          <Link href="/admin" className={linkClass("/admin", "flex flex-col items-center gap-1 text-[11px]")}>
            <IconSliders />
            {t("nav.admin")}
          </Link>
        )}
        <button
          onClick={() => setMenuOpen((v) => !v)}
          className="flex flex-col items-center gap-1 text-[11px] text-charcoal"
        >
          <IconPerson />
          {t("nav.profile")}
        </button>
      </nav>

      {/* Mobile: upload progress, floating above the tab bar regardless of which page
          triggered it. */}
      {uploadItems.length > 0 && (
        <div className="fixed inset-x-3 bottom-16 z-20 rounded-md border border-charcoal/10 bg-paper p-3 shadow md:hidden">
          <UploadProgressList items={uploadItems} />
        </div>
      )}

      {/* Mobile: profile/settings popover */}
      {menuOpen && (
        <div className="fixed inset-0 z-30 md:hidden" onClick={() => setMenuOpen(false)}>
          <div
            className="absolute bottom-16 right-3 flex flex-col items-start gap-3 rounded-md border border-charcoal/10 bg-paper p-4 shadow"
            onClick={(e) => e.stopPropagation()}
          >
            {utilityControls}
          </div>
        </div>
      )}
    </>
  );
}
