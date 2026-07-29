"use client";

import axios from "axios";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, API_BASE } from "@/lib/api";

interface Item {
  name: string;
  progress: number;
  status: "uploading" | "done" | "duplicate" | "error";
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
      const status = axios.isAxiosError(err) && err.response?.status === 409 ? "duplicate" : "error";
      setStatus({ status });
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
        <ul className="mt-2 space-y-1 text-xs">
          {items.map((it, i) => (
            <li key={i} className="flex items-center gap-2">
              <span className="flex-1 truncate">{it.name}</span>
              <span>
                {it.status === "done"
                  ? t("upload.done")
                  : it.status === "duplicate"
                    ? t("upload.duplicate")
                    : it.status === "error"
                      ? "!"
                      : `${it.progress}%`}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
