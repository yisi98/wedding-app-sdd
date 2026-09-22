import { expect, test } from "@playwright/test";
import { createHash } from "node:crypto";
import en from "../src/locales/en.json";

test.use({ serviceWorkers: "block", viewport: { width: 390, height: 844 } });

test("mobile videos queue safely and appear without a socket or reload", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("i18nextLng", "en");
    localStorage.setItem("wmp-auth", JSON.stringify({ state: {
      accessToken: "test", refreshToken: "test",
      user: { id: 1, username: "Guest", role: "guest", is_active: true },
    }, version: 0 }));
    const read = Blob.prototype.arrayBuffer;
    Blob.prototype.arrayBuffer = function () {
      if (this.size > 1024 * 1024) throw new Error("Unbounded file read");
      return read.call(this);
    };
    Object.defineProperty(crypto, "subtle", { value: undefined });
  });
  const bytes = Buffer.alloc(2 * 1024 * 1024 + 57, 42);
  const initiated: { original_filename: string; mime_type: string; file_hash: string }[] = [];
  const visible: object[] = [];
  let releaseFirst!: () => void;
  const firstPending = new Promise<void>((resolve) => { releaseFirst = resolve; });
  let delayed: object | undefined;
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/upload/init")) {
      initiated.push(route.request().postDataJSON());
      return route.fulfill({ json: { media_id: initiated.length, upload_url: "/api/v1/media/upload/raw" } });
    }
    if (path.endsWith("/upload/raw")) return route.fulfill({ status: 204 });
    if (path.endsWith("/upload/confirm")) {
      const id = route.request().postDataJSON().media_id;
      if (id === 1) await firstPending;
      const item = { id, uploader_id: 1, original_filename: initiated[id - 1].original_filename,
        thumbnail_path: "test.svg", media_type: "video", created_at: new Date().toISOString(), status: "ready" };
      if (id === 2) delayed = item;
      else visible.unshift(item);
      return route.fulfill({ json: { status: id === 2 ? "processing" : "ready" } });
    }
    if (path === "/api/v1/media") return route.fulfill({ json: { items: visible, has_more: false } });
    if (path.endsWith("/count")) return route.fulfill({ json: visible.length });
    return route.fulfill({ json: [] });
  });
  await page.route("**/media-object/test.svg", (route) => route.fulfill({ contentType: "image/svg+xml", body: '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"/>' }));
  await page.goto("/gallery");
  const chooserPromise = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: en.nav.upload, exact: true }).click();
  await (await chooserPromise).setFiles([
    { name: "first.MOV", mimeType: "", buffer: bytes },
    { name: "second.mp4", mimeType: "application/octet-stream", buffer: Buffer.from("second") },
  ]);
  await expect.poll(() => initiated.length).toBe(1);
  expect(initiated[0].file_hash).toBe(createHash("sha256").update(bytes).digest("hex"));
  expect(initiated[0].mime_type).toBe("video/quicktime");
  releaseFirst();
  await expect(page.getByRole("img", { name: "first.MOV" })).toBeVisible();
  await expect.poll(() => delayed).toBeTruthy();
  expect(initiated[1].mime_type).toBe("video/mp4");
  visible.unshift(delayed!);
  await expect(page.getByRole("img", { name: "second.mp4" })).toBeVisible({ timeout: 6000 });
});
