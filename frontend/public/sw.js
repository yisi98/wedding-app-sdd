// Service worker: offline-tolerant caching (US7 / Principle V).
// v2: pages are network-first so deployments are actually picked up — v1 served the
// app shell cache-first, which froze guests on old JS bundles forever. Only the
// content-hashed build output stays cache-first, because those URLs are immutable.
const CACHE = "wmp-v2";
const APP_SHELL = ["/", "/gallery", "/manifest.webmanifest", "/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

// Web push (FR-024). Without these handlers a delivered push shows nothing at all.
self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch {
    payload = { body: event.data ? event.data.text() : "" };
  }
  const title = payload.title || "Our Wedding";
  event.waitUntil(
    self.registration.showNotification(title, {
      body: payload.body || "",
      icon: "/icon.svg",
      badge: "/icon.svg",
      // Collapse bursts of activity into one notification per kind.
      tag: payload.tag || payload.event_type || "wmp",
      data: { url: payload.url || "/gallery" },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || "/gallery";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      // Focus an already-open tab rather than piling up new ones.
      for (const client of clients) {
        if ("focus" in client) return client.focus();
      }
      return self.clients.openWindow(target);
    })
  );
});

// API is never cached. Content-hashed build assets (immutable URLs) are cache-first;
// everything else — pages, the manifest — is network-first with the cache as an
// offline fallback, so a redeploy shows up on the next visit instead of never.
self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.pathname.startsWith("/api/")) return; // don't cache API responses

  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            const copy = response.clone();
            caches.open(CACHE).then((c) => c.put(request, copy)).catch(() => {});
            return response;
          })
      )
    );
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((c) => c.put(request, copy)).catch(() => {});
        return response;
      })
      .catch(() =>
        caches.match(request).then((cached) => cached || Response.error())
      )
  );
});
