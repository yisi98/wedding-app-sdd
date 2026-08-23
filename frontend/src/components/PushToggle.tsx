"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  currentSubscription,
  disablePush,
  enablePush,
  fetchVapidKey,
  pushSupported,
} from "@/lib/push";

/** Opt-in control for web-push notifications (FR-024). Renders nothing when push isn't
 * configured server-side or the device can't do it, so it never shows a dead button. */
export default function PushToggle() {
  const { t } = useTranslation();
  const [vapidKey, setVapidKey] = useState<string | null>(null);
  const [subscribed, setSubscribed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!pushSupported()) return;
    fetchVapidKey().then(setVapidKey);
    currentSubscription().then((s) => setSubscribed(!!s));
  }, []);

  if (!pushSupported() || !vapidKey) return null;
  const key = vapidKey; // const so the narrowing survives into the callback below

  async function toggle() {
    setBusy(true);
    setMessage("");
    try {
      if (subscribed) {
        await disablePush();
        setSubscribed(false);
      } else {
        if (Notification.permission === "denied") {
          setMessage(t("push.blocked"));
          return;
        }
        const granted = await enablePush(key);
        setSubscribed(granted);
        if (!granted) setMessage(t("push.blocked"));
      }
    } catch {
      // pushManager.subscribe() rejects for reasons outside our control — private
      // browsing (Chrome disables the Push API there), no push service reachable, an
      // expired key. Report it instead of leaving an unhandled rejection.
      setMessage(t("push.unsupported"));
      setSubscribed(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        onClick={toggle}
        disabled={busy}
        title={message || undefined}
        className="text-sm hover:underline disabled:opacity-50"
      >
        {subscribed ? `🔔 ${t("push.disable")}` : `🔕 ${t("push.enable")}`}
      </button>
      {message && <span className="text-xs text-red-500">{message}</span>}
    </>
  );
}
