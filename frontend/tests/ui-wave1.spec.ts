import { expect, test, type Page } from "@playwright/test";

import en from "../src/locales/en.json";
import ru from "../src/locales/ru.json";
import zh from "../src/locales/zh.json";

// Synthetic sessions and API fixtures keep UI checks independent of private wedding data.
test.use({ serviceWorkers: "block" });

async function prepare(page: Page, language = "en", role = "admin") {
  await page.addInitScript(({ lang, userRole }) => {
    localStorage.setItem("i18nextLng", lang);
    localStorage.setItem("wmp-auth", JSON.stringify({
      state: {
        accessToken: "ui-test-token",
        refreshToken: "ui-test-refresh",
        user: { id: 1, username: "UI Test", role: userRole, language_preference: lang, is_active: true },
      },
      version: 0,
    }));
  }, { lang: language, userRole: role });
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown = [];
    if (["/api/v1/media", "/api/v1/admin/media", "/api/v1/admin/users"].includes(path)) {
      json = { items: [], has_more: false };
    } else if (path === "/api/v1/media/count") {
      json = 0;
    } else if (path === "/api/v1/media/uploaders") {
      json = ["UI Test"];
    } else if (["/api/v1/admin/stats", "/api/v1/admin/config"].includes(path)) {
      json = null;
    }
    await route.fulfill({ json });
  });
}

for (const [language, copy] of Object.entries({ en, zh, ru })) {
  test(`mobile loading, empty states, header and upload caption (${language})`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await prepare(page, language);
    let releaseGallery!: () => void;
    const galleryResponse = new Promise<void>((resolve) => { releaseGallery = resolve; });
    await page.route("**/api/v1/media?*", async (route) => {
      await galleryResponse;
      await route.fulfill({ json: { items: [], has_more: false } });
    });
    await page.goto("/gallery");
    const skeleton = page.getByRole("status", { name: copy.gallery.loading });
    await expect(skeleton).toBeVisible();
    await expect(skeleton.locator(".aspect-square")).toHaveCount(8);
    await expect(page.getByText(copy.gallery.empty, { exact: true })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: copy.app.title })).toBeVisible();
    await expect(page.getByText(copy.app.tagline)).toBeVisible();
    releaseGallery();
    await expect(skeleton).toHaveCount(0);
    await expect(page.getByText(copy.gallery.emptyMobile)).toBeVisible();
    await expect(page.getByText(copy.gallery.emptyDesktop)).toBeHidden();

    const upload = page.getByRole("button", { name: copy.nav.upload, exact: true });
    await expect(upload).toHaveText(copy.nav.upload);
    const box = await upload.boundingBox();
    expect(box).not.toBeNull();
    expect(Math.abs(box!.x + box!.width / 2 - 195)).toBeLessThan(1);
    expect(box!.y + box!.height).toBeLessThanOrEqual(844);
    const chooser = page.waitForEvent("filechooser");
    await upload.click();
    expect((await chooser).isMultiple()).toBe(true);
    await page.screenshot({ path: testInfo.outputPath("mobile-gallery.png") });

    let releaseFavorites!: () => void;
    const favoritesResponse = new Promise<void>((resolve) => { releaseFavorites = resolve; });
    await page.route("**/api/v1/media/favorites", async (route) => {
      await favoritesResponse;
      await route.fulfill({ json: [] });
    });
    await page.goto("/favorites");
    await expect(skeleton).toBeVisible();
    await expect(page.getByText(copy.favorites.empty)).toHaveCount(0);
    releaseFavorites();
    await expect(page.getByText(copy.favorites.empty)).toBeVisible();
    await expect(page.getByText(copy.gallery.empty, { exact: true })).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  });
}

test("clearing a no-match result resets both filters and restores the gallery", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await prepare(page);
  await page.route("**/api/v1/media?*", async (route) => {
    const params = new URL(route.request().url()).searchParams;
    const filtered = params.has("media_type") || params.has("uploader");
    await route.fulfill({ json: {
      items: filtered ? [] : [{ id: 1, original_filename: "wedding-test.svg", media_type: "image", uploader_name: "UI Test", thumbnail_path: "test.svg" }],
      has_more: false,
    } });
  });
  await page.route("**/media-object/test.svg", (route) => route.fulfill({
    contentType: "image/svg+xml",
    body: '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="#c17a5a"/></svg>',
  }));
  await page.goto("/gallery");
  await expect(page.getByRole("img", { name: "wedding-test.svg" })).toBeVisible();
  await page.getByRole("button", { name: en.gallery.allMedia, exact: true }).click();
  await page.getByRole("option", { name: en.gallery.videos, exact: true }).click();
  await expect(page.getByText(en.gallery.noMatches)).toBeVisible();
  await page.getByRole("button", { name: en.gallery.allUploaders, exact: true }).click();
  await page.getByRole("option", { name: "UI Test", exact: true }).click();
  await expect(page.getByText(en.gallery.noMatches)).toBeVisible();
  const resetRequest = page.waitForRequest((request) => {
    const url = new URL(request.url());
    return url.pathname === "/api/v1/media" && !url.searchParams.has("media_type") && !url.searchParams.has("uploader");
  });
  await page.getByRole("button", { name: en.gallery.clearFilters, exact: true }).click();
  await resetRequest;
  await expect(page.getByRole("button", { name: en.gallery.allMedia, exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: en.gallery.allUploaders, exact: true })).toBeVisible();
  await expect(page.getByRole("img", { name: "wedding-test.svg" })).toBeVisible();
  await expect(page.getByText(en.gallery.noMatches)).toHaveCount(0);
});

for (const path of ["gallery", "favorites", "admin"]) {
  test(`desktop ${path} centres in the space beside the sidebar`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await prepare(page);
    await page.goto(`/${path}`);
    const content = page.locator("main > div");
    await expect(content).toBeVisible();
    const box = await content.boundingBox();
    expect(box).not.toBeNull();
    expect(Math.abs((box!.x - 224) - (1440 - box!.x - box!.width))).toBeLessThan(1);
    expect(box!.width).toBeLessThanOrEqual(1024);
    if (path === "gallery") {
      await expect(page.getByText(en.app.tagline)).toBeHidden();
      await expect(page.getByText(en.gallery.emptyDesktop)).toBeVisible();
      await expect(page.getByText(en.gallery.emptyMobile)).toBeHidden();
    }
    await page.screenshot({ path: testInfo.outputPath(`desktop-${path}.png`) });
  });
}

for (const mobile of [true, false]) {
  test(`${mobile ? "mobile guest picker" : "desktop dropzone"} uploads a batch`, async ({ page }) => {
    await page.setViewportSize({ width: mobile ? 390 : 1440, height: 844 });
    await prepare(page, "en", "guest");
    let releaseUploads!: () => void;
    const uploadResponse = new Promise<void>((resolve) => { releaseUploads = resolve; });
    let nextId = 0;
    await page.route("**/api/v1/media/upload/init", (route) => {
      const id = ++nextId;
      return route.fulfill({ json: { media_id: id, upload_url: `/api/v1/ui-test-upload/${id}` } });
    });
    await page.route("**/api/v1/ui-test-upload/*", async (route) => {
      await uploadResponse;
      await route.fulfill({ json: {} });
    });
    await page.goto("/gallery");
    if (mobile) {
      const upload = page.getByRole("button", { name: en.nav.upload, exact: true });
      const box = await upload.boundingBox();
      expect(Math.abs(box!.x + box!.width / 2 - 195)).toBeLessThan(1);
      const chooser = page.waitForEvent("filechooser");
      await upload.click();
      await (await chooser).setFiles([1, 2, 3].map((id) => ({
        name: `test-${id}.png`, mimeType: "image/png", buffer: Buffer.from(`synthetic-upload-${id}`),
      })));
    } else {
      const dataTransfer = await page.evaluateHandle(() => {
        const transfer = new DataTransfer();
        for (const id of [1, 2, 3]) {
          transfer.items.add(new File([`synthetic-upload-${id}`], `test-${id}.png`, { type: "image/png" }));
        }
        return transfer;
      });
      await page.getByText(en.upload.drop, { exact: true }).dispatchEvent("drop", { dataTransfer });
      await dataTransfer.dispose();
    }
    await expect(page.getByText("0 of 3 done", { exact: true })).toBeVisible();
    releaseUploads();
    await expect(page.getByText("3 of 3 done", { exact: true })).toBeVisible();
    await expect(page.getByText(en.upload.done, { exact: true })).toHaveCount(0);
    await page.getByText("3 of 3 done", { exact: true }).click();
    await expect(page.getByText(en.upload.done, { exact: true })).toHaveCount(3);
    await expect(page.getByText("3 of 3 done", { exact: true })).toHaveCount(0, { timeout: 6000 });
  });
}

test("select mode keeps browsing clean and toggles tiles plus bulk actions", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await prepare(page, "en", "guest");
  const media = {
    id: 1, uploader_id: 1, uploader_name: "UI Test", original_filename: "memory.jpg",
    thumbnail_path: "test.svg", optimized_path: "test.svg", storage_path: "test.svg",
    media_type: "image", lqip: null, created_at: new Date().toISOString(), reaction_count: 0,
  };
  await page.route("**/api/v1/media?*", (route) => route.fulfill({ json: { items: [media], has_more: false } }));
  await page.route("**/api/v1/media/count?*", (route) => route.fulfill({ json: 1 }));
  await page.route("**/api/v1/media/uploaders", (route) => route.fulfill({ json: ["UI Test"] }));
  await page.route("**/media-object/test.svg", (route) => route.fulfill({ contentType: "image/svg+xml", body: '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="#c17a5a"/></svg>' }));
  await page.goto("/gallery");
  await expect(page.getByRole("checkbox")).toHaveCount(0);
  await expect(page.getByRole("button", { name: en.gallery.select, exact: true })).toBeVisible();
  await page.getByRole("button", { name: en.gallery.select, exact: true }).click();
  await expect(page.getByRole("checkbox")).toHaveCount(1);
  await expect(page.getByText(en.gallery.selectAllMatching)).toBeVisible();
  await expect(page.getByText(en.gallery.clearSelection)).toHaveCount(0);
  await page.getByRole("img", { name: "memory.jpg" }).click();
  await expect(page.getByText(en.gallery.clearSelection)).toBeVisible();
  await expect(page.getByRole("button", { name: /Delete 1/ })).toBeVisible();
  await page.getByRole("button", { name: en.gallery.cancelSelect, exact: true }).last().click();
  await expect(page.getByRole("checkbox")).toHaveCount(0);
  await expect(page.getByRole("button", { name: en.gallery.select, exact: true })).toBeVisible();
});

test("owner delete is tucked into the lightbox overflow menu", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await prepare(page, "en", "guest");
  const media = {
    id: 1, uploader_id: 1, uploader_name: "UI Test", original_filename: "memory.jpg",
    thumbnail_path: "test.svg", optimized_path: "test.svg", storage_path: "test.svg",
    media_type: "image", lqip: null, created_at: new Date().toISOString(), reaction_count: 0,
  };
  await page.route("**/api/v1/media?*", (route) => route.fulfill({ json: { items: [media], has_more: false } }));
  await page.route("**/api/v1/media/count?*", (route) => route.fulfill({ json: 1 }));
  await page.route("**/api/v1/media/uploaders", (route) => route.fulfill({ json: ["UI Test"] }));
  await page.route("**/api/v1/media/1/**", (route) => route.fulfill({ json: [] }));
  await page.route("**/media-object/test.svg", (route) => route.fulfill({ contentType: "image/svg+xml", body: '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="#c17a5a"/></svg>' }));
  await page.goto("/gallery");
  await page.getByRole("img", { name: "memory.jpg" }).click();
  await expect(page.getByRole("button", { name: en.lightbox.delete, exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "More options" }).click();
  await expect(page.getByRole("button", { name: en.lightbox.delete, exact: true })).toBeVisible();
});
