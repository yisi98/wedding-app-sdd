"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "@/lib/api";
import LanguageSwitcher, { syncLanguageToServer } from "@/components/LanguageSwitcher";
import { useAuthStore } from "@/stores/auth";

export default function LoginPage() {
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const setSession = useAuthStore((s) => s.setSession);
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(false);
    try {
      const { data } = await api.post("/auth/login", {
        display_name: name,
        event_password: password,
      });
      setSession(data.access_token, data.refresh_token, data.user);
      // Carry the language picked on this screen over to the account, so server-side
      // messages match the UI from the very first upload.
      syncLanguageToServer((i18n.language || "en").split("-")[0]);
      router.replace("/gallery");
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <form
        onSubmit={submit}
        className="w-full max-w-sm space-y-4 rounded-md border border-charcoal/10 bg-paper p-8"
      >
        <div className="flex items-center justify-between">
          <h1 className="font-serif text-xl font-semibold text-accent">{t("app.title")}</h1>
          <LanguageSwitcher />
        </div>
        <p className="text-sm text-gray-500">{t("login.hint")}</p>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t("login.displayName")}
          required
          className="w-full rounded border px-3 py-2"
        />
        <input
          type={showPassword ? "text" : "password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={t("login.eventPassword")}
          required
          className="w-full rounded border px-3 py-2"
        />
        <label className="flex items-center gap-2 text-sm text-gray-500">
          <input
            type="checkbox"
            checked={showPassword}
            onChange={(e) => setShowPassword(e.target.checked)}
            className="h-4 w-4"
          />
          {t("login.showPassword")}
        </label>
        {error && <p className="text-sm text-red-500">{t("login.error")}</p>}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded bg-accent py-2 font-medium text-white disabled:opacity-50"
        >
          {t("login.enter")}
        </button>
      </form>
    </main>
  );
}
