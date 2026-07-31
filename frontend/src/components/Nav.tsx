"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";

import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

import LanguageSwitcher from "./LanguageSwitcher";
import PushToggle from "./PushToggle";

export default function Nav() {
  const { t } = useTranslation();
  const router = useRouter();
  const { user, clear } = useAuthStore();

  async function logout() {
    try {
      await api.post("/auth/logout");
    } catch {
      /* ignore */
    }
    clear();
    router.replace("/login");
  }

  return (
    <nav className="flex items-center gap-4 border-b border-charcoal/10 bg-paper px-4 py-3">
      <span className="font-serif font-semibold text-accent">{t("app.title")}</span>
      <Link href="/gallery" className="text-sm hover:underline">
        {t("nav.gallery")}
      </Link>
      <Link href="/favorites" className="text-sm hover:underline">
        {t("nav.favorites")}
      </Link>
      {user?.role === "admin" && (
        <Link href="/admin" className="text-sm hover:underline">
          {t("nav.admin")}
        </Link>
      )}
      <div className="ml-auto flex items-center gap-3">
        <PushToggle />
        <LanguageSwitcher />
        <button onClick={logout} className="text-sm text-gray-600 hover:underline">
          {t("nav.logout")}
        </button>
      </div>
    </nav>
  );
}
