"use client";

import axios from "axios";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "@/lib/api";

/** How long finished upload rows stay on screen before clearing themselves. */
const CLEAR_AFTER_MS = 3000;

export interface UploadItem {
  name: string;
  progress: number;
  status: "uploading" | "done" | "duplicate" | "error";
  /** The server's reason for a rejection, shown to the guest. */
  message?: string;
}

/** The API localizes its own error messages (EN/ZH/RU), so prefer its `detail` over a
 * generic client-side string — it's what distinguishes "wrong type" from "too large"
 * from "uploads are closed". Shapes vary: a plain string, or `{message, ...}` for 409. */
function serverMessage(err: unknown): string | undefined {
  if (!axios.isAxiosError(err)) return undefined;
  const detail = err.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && typeof detail.message === "string") {
    return detail.message;
  }
  return undefined;
}

async function sha256Hex(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/** Shared upload flow — used by the desktop dropzone and the mobile nav's "+" button, so
 * there is exactly one implementation of hash/init/PUT/confirm and its progress state. */
export function useUploader(onUploaded: () => void) {
  const { t } = useTranslation();
  const [items, setItems] = useState<UploadItem[]>([]);
  function dismiss() {
    setItems((list) => list.filter((it) => it.status === "uploading"));
  }

  // Once nothing is still uploading, tidy the list away so it doesn't sit there for the
  // rest of the evening. Rejections stay put — a guest needs time to read why a file
  // failed and to retry it.
  useEffect(() => {
    if (items.length === 0) return;
    const busy = items.some((it) => it.status === "uploading");
    const failed = items.some((it) => it.status === "error");
    if (busy || failed) return;
    const timer = setTimeout(() => setItems([]), CLEAR_AFTER_MS);
    return () => clearTimeout(timer);
  }, [items]);

  async function uploadOne(file: File, index: number) {
    const setStatus = (patch: Partial<UploadItem>) =>
      setItems((list) => list.map((it, i) => (i === index ? { ...it, ...patch } : it)));
    try {
      const fileHash = await sha256Hex(file);
      const init = await api.post("/media/upload/init", {
        original_filename: file.name,
        mime_type: file.type,
        file_size: file.size,
        file_hash: fileHash,
      });
      const { media_id, upload_url } = init.data;

      if (upload_url.startsWith("http")) {
        // Direct presigned PUT to object storage (prod).
        await axios.put(upload_url, file, {
          headers: { "Content-Type": file.type },
          onUploadProgress: (e) => setStatus({ progress: Math.round((100 * e.loaded) / (e.total || 1)) }),
        });
      } else {
        // Dev stand-in endpoint (requires auth via the api instance).
        await api.put(upload_url.replace("/api/v1", ""), file, {
          headers: { "Content-Type": "application/octet-stream" },
          onUploadProgress: (e) => setStatus({ progress: Math.round((100 * e.loaded) / (e.total || 1)) }),
        });
      }
      await api.post("/media/upload/confirm", { media_id });
      setStatus({ progress: 100, status: "done" });
    } catch (err) {
      const isDuplicate = axios.isAxiosError(err) && err.response?.status === 409;
      setStatus({
        status: isDuplicate ? "duplicate" : "error",
        // No response at all (offline, server unreachable) means there is no server
        // message to show — fall back to something actionable.
        message: isDuplicate ? undefined : (serverMessage(err) ?? t("upload.errorGeneric")),
      });
    }
  }

  /** The picker's `accept` attribute only filters the file dialog — dropped files bypass
   * it entirely. Anything that is clearly not an image/video (e.g. an .mkv some browsers
   * report no MIME type for) is rejected locally, instead of hashing hundreds of MB only
   * for the server to refuse it. The backend still validates against its own allow-list. */
  function isAllowedType(file: File): boolean {
    return file.type.startsWith("image/") || file.type.startsWith("video/");
  }

  async function handleFiles(files: FileList | File[] | null) {
    if (!files || files.length === 0) return;
    const list = Array.from(files);
    const start = items.length;
    setItems((prev) => [
      ...prev,
      ...list.map((f) =>
        isAllowedType(f)
          ? { name: f.name, progress: 0, status: "uploading" as const }
          : {
              name: f.name,
              progress: 0,
              status: "error" as const,
              message: t("upload.typeNotAllowed"),
            }
      ),
    ]);
    await Promise.all(
      list
        .map((file, i) => ({ file, i }))
        .filter(({ file }) => isAllowedType(file))
        .map(({ file, i }) => uploadOne(file, start + i))
    );
    onUploaded();
  }

  return { items, handleFiles, dismiss };
}
