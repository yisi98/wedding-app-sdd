"use client";

import axios from "axios";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, API_BASE } from "@/lib/api";

interface Item {
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

export default function Uploader({ onUploaded }: { onUploaded: () => void }) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [dragging, setDragging] = useState(false);

  async function uploadOne(file: File, index: number) {
    const setStatus = (patch: Partial<Item>) =>
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

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    const list = Array.from(files);
    const start = items.length;
    setItems((prev) => [...prev, ...list.map((f) => ({ name: f.name, progress: 0, status: "uploading" as const }))]);
    await Promise.all(list.map((file, i) => uploadOne(file, start + i)));
    onUploaded();
  }

  return (
    <div className="mb-4">
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={`cursor-pointer rounded-lg border-2 border-dashed p-6 text-center text-sm ${
          dragging ? "border-blush bg-blush/10" : "border-gray-300"
        }`}
      >
        {t("upload.drop")}
        <input
          ref={inputRef}
          type="file"
          accept="image/*,video/*"
          multiple
          hidden
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>
      {items.length > 0 && (
        <>
          {/* FR-006 aggregate progress across the batch, alongside the per-file rows. */}
          {(() => {
            const finished = items.filter((it) => it.status !== "uploading").length;
            const overall = Math.round(
              items.reduce((sum, it) => sum + (it.status === "uploading" ? it.progress : 100), 0) /
                items.length
            );
            return (
              <div className="mt-2 text-xs">
                <div className="mb-1 flex justify-between text-gray-500">
                  <span>{t("upload.overall", { done: finished, total: items.length })}</span>
                  <span>{overall}%</span>
                </div>
                <div className="h-1 w-full overflow-hidden rounded bg-gray-200">
                  <div className="h-full bg-blush transition-all" style={{ width: `${overall}%` }} />
                </div>
              </div>
            );
          })()}
        </>
      )}
      {items.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs">
          {items.map((it, i) => (
            <li key={i} className="flex flex-col gap-0.5">
              <div className="flex items-center gap-2">
                <span className="flex-1 truncate">{it.name}</span>
                <span
                  className={
                    it.status === "error"
                      ? "shrink-0 font-medium text-red-600"
                      : it.status === "duplicate"
                        ? "shrink-0 text-gray-500"
                        : "shrink-0"
                  }
                >
                  {it.status === "done"
                    ? t("upload.done")
                    : it.status === "duplicate"
                      ? t("upload.duplicate")
                      : it.status === "error"
                        ? t("upload.failed")
                        : `${it.progress}%`}
                </span>
              </div>
              {it.status === "error" && it.message && (
                <span role="alert" className="text-red-600">
                  {it.message}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
