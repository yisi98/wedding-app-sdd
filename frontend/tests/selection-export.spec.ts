import { expect, test } from "@playwright/test";
import en from "../src/locales/en.json";
import ru from "../src/locales/ru.json";
import zh from "../src/locales/zh.json";

test.use({ serviceWorkers: "block" });

for (const [language, strings] of Object.entries({ en, ru, zh })) {
  test(`${language}: selection controls and CSV export with session renewal`, async ({ page }) => {
    await page.addInitScript((lang) => {
      localStorage.setItem("i18nextLng", lang);
      localStorage.setItem("wmp-auth", JSON.stringify({ state: {
        accessToken: "expired", refreshToken: "refresh",
        user: { id: 1, username: "Admin", role: "admin", language_preference: lang, is_active: true },
      }, version: 0 }));
    }, language);
    let failExport = true;
    let renewals = 0;
    let downloads = 0;
    page.on("download", () => downloads++);
    const item = { id: 1, uploader_id: 1, original_filename: "photo.jpg", thumbnail_path: null,
      media_type: "image", created_at: new Date().toISOString(), status: "ready", is_visible: true };
    await page.route("**/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path === "/api/v1/admin/export/media") {
        if (failExport) return route.fulfill({ status: 503, json: { detail: "Unavailable" } });
        if (route.request().headers().authorization !== "Bearer renewed") {
          return route.fulfill({ status: 401, json: { detail: "Expired" } });
        }
        return route.fulfill({ contentType: "text/csv; charset=utf-8", body: 'id,original_filename\r\n1,"Наташа, 婚礼.jpg"\r\n' });
      }
      if (path === "/api/v1/auth/refresh") {
        renewals++;
        return route.fulfill({ json: { access_token: "renewed", refresh_token: "next-refresh" } });
      }
      let json: unknown = [];
      if (path === "/api/v1/media" || path === "/api/v1/admin/media") json = { items: [item], has_more: false };
      if (path === "/api/v1/media/count") json = 1;
      if (path === "/api/v1/admin/users") json = { items: [{ id: 2, username: "Guest", role: "guest", is_active: true }], has_more: false };
      if (path === "/api/v1/admin/stats") json = { total_media: 1, total_users: 2, total_views: 0, total_reactions: 0, total_comments: 0, storage_bytes: 0, media_by_type: {}, top_by_views: [] };
      if (path === "/api/v1/admin/config") json = { uploads_enabled: true };
      return route.fulfill({ json });
    });
    await page.goto("/gallery");
    await page.getByRole("button", { name: strings.gallery.select, exact: true }).click();
    await expect(page.getByRole("button", { name: strings.gallery.selectAllMatching, exact: true })).toBeVisible();
    await page.getByRole("checkbox").check();
    await expect(page.getByRole("button", { name: strings.gallery.cancelSelect, exact: true })).toHaveCount(1);
    await expect(page.getByRole("button", { name: strings.gallery.downloadSelected })).toHaveText(`${strings.lightbox.download} 1`);

    await page.goto("/admin");
    const guest = page.getByRole("row").filter({ hasText: "Guest" });
    await expect(guest).toBeVisible();
    await expect(guest.getByRole("button", { name: strings.admin.delete, exact: true })).toHaveCount(0);
    await expect(guest.getByRole("button", { name: strings.admin.deactivate, exact: true })).toBeVisible();
    const exportButton = page.getByRole("button", { name: strings.admin.export, exact: true });
    await exportButton.click();
    await expect(page.locator("main").getByRole("alert")).toHaveText(strings.admin.exportError);
    expect(downloads).toBe(0);
    failExport = false;
    const downloadPromise = page.waitForEvent("download");
    await exportButton.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe("media.csv");
    const stream = await download.createReadStream();
    const chunks: Buffer[] = [];
    for await (const chunk of stream!) chunks.push(Buffer.from(chunk));
    expect(Buffer.concat(chunks).toString("utf8")).toBe('\uFEFFid,original_filename\r\n1,"Наташа, 婚礼.jpg"\r\n');
    expect(renewals).toBe(1);
    expect(downloads).toBe(1);
    await expect(page.locator("main").getByRole("alert")).toHaveCount(0);
  });
}
