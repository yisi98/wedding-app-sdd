"use client";

import { useTranslation } from "react-i18next";

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const current = (i18n.language || "en").split("-")[0];
  return (
    <select
      aria-label="language"
      value={current}
      onChange={(e) => i18n.changeLanguage(e.target.value)}
      className="rounded border border-gray-300 bg-white px-2 py-1 text-sm"
    >
      <option value="en">EN</option>
      <option value="zh">中文</option>
      <option value="ru">RU</option>
    </select>
  );
}
