import { expect, test, type Page } from "@playwright/test";

import en from "../src/locales/en.json";

test.use({ serviceWorkers: "block" });

async function prepare(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("i18nextLng", "en");
    localStorage.setItem("wmp-auth", JSON.stringify({ state: {
      accessToken: "ui-test-token", refreshToken: "ui-test-refresh",
      user: { id: 1, username: "UI Test", role: "guest", language_preference: "en", is_active: true },
    }, version: 0 }));
  });
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown = [];
    if (["/api/v1/media", "/api/v1/admin/media", "/api/v1/admin/users"].includes(path)) json = { items: [], has_more: false };
    else if (path === "/api/v1/media/count") json = 0;
    else if (path === "/api/v1/media/uploaders") json = ["UI Test"];
    await route.fulfill({ json });
  });
}

function media() {
  return { id: 1, uploader_id: 1, uploader_name: "UI Test", original_filename: "memory.jpg", thumbnail_path: "test.svg", optimized_path: "test.svg", storage_path: "test.svg", media_type: "image", lqip: null, created_at: new Date().toISOString(), reaction_count: 0 };
}

async function mockGallery(page: Page) {
  await page.route("**/api/v1/media?*", (route) => route.fulfill({ json: { items: [media()], has_more: false } }));
  await page.route("**/api/v1/media/count?*", (route) => route.fulfill({ json: 1 }));
  await page.route("**/api/v1/media/uploaders", (route) => route.fulfill({ json: ["UI Test"] }));
  await page.route("**/media-object/test.svg", (route) => route.fulfill({ contentType: "image/svg+xml", body: '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="#c17a5a"/></svg>' }));
}

test("select mode keeps browsing clean and toggles tiles plus bulk actions", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await prepare(page); await mockGallery(page); await page.goto("/gallery");
  await expect(page.getByRole("checkbox")).toHaveCount(0);
  await page.getByRole("button", { name: en.gallery.select, exact: true }).click();
  await expect(page.getByRole("checkbox")).toHaveCount(1);
  await expect(page.getByText(en.gallery.selectAllMatching)).toBeVisible();
  await page.getByRole("img", { name: "memory.jpg" }).click();
  await expect(page.getByRole("button", { name: /Delete 1/ })).toBeVisible();
  await page.getByRole("button", { name: en.gallery.cancelSelect, exact: true }).last().click();
  await expect(page.getByRole("checkbox")).toHaveCount(0);
});

test("owner delete is tucked into the lightbox overflow menu", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await prepare(page); await mockGallery(page); await page.goto("/gallery");
  await page.getByRole("img", { name: "memory.jpg" }).click();
  await expect(page.getByRole("button", { name: en.lightbox.delete, exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: en.lightbox.moreOptions, exact: true }).click();
  await expect(page.getByRole("button", { name: en.lightbox.delete, exact: true })).toBeVisible();
});
