"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

import LanguageSwitcher from "./LanguageSwitcher";
import PushToggle from "./PushToggle";

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
      {/* Desktop: fixed left sidebar */}
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
          <Link
            href="/gallery?upload=1"
            className="mt-2 rounded bg-accent px-3 py-2 text-center text-sm font-medium text-white"
          >
            + {t("nav.upload")}
          </Link>
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

      {/* Mobile: fixed bottom tab bar */}
      <nav className="fixed inset-x-0 bottom-0 z-20 flex items-center justify-around border-t border-charcoal/10 bg-paper py-2 md:hidden">
        <Link href="/gallery" className={linkClass("/gallery", "flex flex-col items-center gap-0.5 text-xs")}>
          <span aria-hidden className="text-lg leading-none">🖼️</span>
          {t("nav.gallery")}
        </Link>
        <Link href="/favorites" className={linkClass("/favorites", "flex flex-col items-center gap-0.5 text-xs")}>
          <span aria-hidden className="text-lg leading-none">★</span>
          {t("nav.favorites")}
        </Link>
        <Link
          href="/gallery?upload=1"
          aria-label={t("nav.upload")}
          className="-mt-6 flex h-12 w-12 items-center justify-center rounded-full bg-accent text-2xl leading-none text-white shadow"
        >
          +
        </Link>
        {user?.role === "admin" && (
          <Link href="/admin" className={linkClass("/admin", "flex flex-col items-center gap-0.5 text-xs")}>
            <span aria-hidden className="text-lg leading-none">⚙️</span>
            {t("nav.admin")}
          </Link>
        )}
        <button
          onClick={() => setMenuOpen((v) => !v)}
          className="flex flex-col items-center gap-0.5 text-xs text-charcoal"
        >
          <span aria-hidden className="text-lg leading-none">👤</span>
          {t("nav.profile")}
        </button>
      </nav>

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
