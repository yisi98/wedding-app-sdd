"use client";

import { useTranslation } from "react-i18next";

import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

/** Mirror the chosen language onto the account so API-generated messages (upload
 * rejections, etc.) come back in the same language the UI is showing. No-op when signed
 * out — the login screen has a switcher too, and there is no session to update yet. */
export function syncLanguageToServer(lang: string) {
  if (!useAuthStore.getState().accessToken) return;
  api.put("/auth/profile", { language_preference: lang }).catch(() => {});
}

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const current = (i18n.language || "en").split("-")[0];
  return (
    <select
      aria-label="language"
      value={current}
      onChange={(e) => {
        i18n.changeLanguage(e.target.value);
        syncLanguageToServer(e.target.value);
      }}
      className="rounded border border-gray-300 bg-white px-2 py-1 text-sm"
    >
      <option value="en">EN</option>
      <option value="zh">中文</option>
      <option value="ru">RU</option>
    </select>
  );
}
