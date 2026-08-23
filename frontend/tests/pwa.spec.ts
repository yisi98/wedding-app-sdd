import { expect, test, type Page } from "@playwright/test";

/**
 * T069 — US7 / SC-006 / Constitution Principle V.
 *
 * "A guest can install the app and continue viewing previously loaded content with
 * connectivity disabled." Three things have to hold: the manifest makes the app
 * installable, the service worker actually registers and activates, and content that
 * was loaded once still renders with the network off.
 *
 * These run against a production build (see playwright.config.ts). The backend is not
 * required — every assertion is about the app shell, which is exactly what has to
 * survive a dead connection on congested venue wifi.
 */

/** Resolve once the service worker controls this page, so the next load is served by it. */
async function waitUntilControlled(page: Page) {
  await page.waitForFunction(() => navigator.serviceWorker?.controller != null, null, {
    timeout: 30_000,
  });
}

test.describe("PWA", () => {
  test("is installable: the manifest is linked and complete", async ({ page, request }) => {
    await page.goto("/login");

    const href = await page.locator('link[rel="manifest"]').getAttribute("href");
    expect(href, "no <link rel=manifest> in the document head").toBeTruthy();

    const res = await request.get(new URL(href!, page.url()).toString());
    expect(res.status()).toBe(200);

    const manifest = await res.json();
    // The fields a browser needs before it will offer "Add to Home Screen".
    expect(manifest.name).toBeTruthy();
    expect(manifest.short_name).toBeTruthy();
    expect(manifest.start_url).toBeTruthy();
    expect(manifest.display).toBe("standalone");
    expect(Array.isArray(manifest.icons)).toBe(true);
    expect(manifest.icons.length).toBeGreaterThan(0);

    // Every declared icon must actually resolve, or installation silently degrades.
    for (const icon of manifest.icons) {
      const iconRes = await request.get(new URL(icon.src, page.url()).toString());
      expect(iconRes.status(), `icon ${icon.src} is not served`).toBe(200);
    }
  });

  test("registers a service worker and activates it", async ({ page }) => {
    await page.goto("/login");

    // `serviceWorker.ready` resolves as soon as there is an active worker, which can
    // still be "activating" for a tick — wait for the terminal state instead.
    const state = await page.evaluate(async () => {
      const reg = await navigator.serviceWorker.ready;
      const worker = reg.active!;
      if (worker.state !== "activated") {
        await new Promise<void>((resolve) => {
          worker.addEventListener("statechange", function onChange() {
            if (worker.state === "activated") {
              worker.removeEventListener("statechange", onChange);
              resolve();
            }
          });
        });
      }
      return { scope: reg.scope, active: worker.state, script: worker.scriptURL };
    });

    expect(state.active).toBe("activated");
    expect(state.script).toContain("/sw.js");
    expect(state.scope).toMatch(/\/$/);
  });

  test("serves previously loaded content with the network disabled (SC-006)", async ({
    page,
    context,
  }) => {
    // First visit: registers the worker and populates the cache.
    await page.goto("/login");
    await page.evaluate(() => navigator.serviceWorker.ready);

    // Reload so the worker is in control; the first load never is.
    await page.reload();
    await waitUntilControlled(page);
    await expect(page.locator('input[type="password"]')).toBeVisible();

    // Cut the network entirely — no server, no API.
    await context.setOffline(true);
    try {
      await page.reload();

      // The shell must still render from cache rather than the browser error page.
      await expect(page.locator('input[type="password"]')).toBeVisible({ timeout: 15_000 });
      expect(await page.title()).not.toBe("");
    } finally {
      await context.setOffline(false);
    }
  });

  test("does not cache API responses", async ({ page }) => {
    await page.goto("/login");
    await page.evaluate(() => navigator.serviceWorker.ready);

    // The worker skips /api/ so guests never see a stale gallery or a stale session.
    const cachedApiEntries = await page.evaluate(async () => {
      const names = await caches.keys();
      const urls: string[] = [];
      for (const name of names) {
        const cache = await caches.open(name);
        for (const req of await cache.keys()) urls.push(req.url);
      }
      return urls.filter((u) => new URL(u).pathname.startsWith("/api/"));
    });

    expect(cachedApiEntries).toEqual([]);
  });
});
