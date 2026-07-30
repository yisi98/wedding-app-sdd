"use client";

import { api } from "./api";

/** VAPID keys travel as base64url; PushManager wants raw bytes. Backed by an explicit
 * ArrayBuffer so the result is a plain BufferSource applicationServerKey accepts. */
function urlBase64ToUint8Array(base64: string) {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const normalized = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(normalized);
  const view = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i += 1) view[i] = raw.charCodeAt(i);
  return view;
}

export function pushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

/** The server's VAPID public key, or null when push isn't configured for this event. */
export async function fetchVapidKey(): Promise<string | null> {
  try {
    const { data } = await api.get("/push/vapid-public-key");
    return data.public_key || null;
  } catch {
    return null;
  }
}

export async function currentSubscription(): Promise<PushSubscription | null> {
  if (!pushSupported()) return null;
  const reg = await navigator.serviceWorker.ready;
  return reg.pushManager.getSubscription();
}

/** Ask permission, subscribe, and register with the API. Returns false if declined. */
export async function enablePush(vapidKey: string): Promise<boolean> {
  if (!pushSupported()) return false;
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return false;

  const reg = await navigator.serviceWorker.ready;
  const sub =
    (await reg.pushManager.getSubscription()) ??
    (await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidKey),
    }));

  // The API takes p256dh/auth flat, while PushSubscription.toJSON() nests them under
  // `keys` — so flatten before sending.
  const json = sub.toJSON() as { endpoint?: string; keys?: Record<string, string> };
  await api.post("/push/subscribe", {
    endpoint: json.endpoint,
    p256dh: json.keys?.p256dh,
    auth: json.keys?.auth,
  });
  return true;
}

export async function disablePush(): Promise<void> {
  const sub = await currentSubscription();
  if (!sub) return;
  const endpoint = sub.endpoint;
  await sub.unsubscribe().catch(() => {});
  await api
    .request({ url: "/push/subscribe", method: "DELETE", data: { endpoint } })
    .catch(() => {});
}
