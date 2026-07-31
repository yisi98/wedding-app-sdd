"use client";

import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { useUploader } from "@/lib/useUploader";

import UploadProgressList from "./UploadProgressList";

/** Drag-and-drop dropzone. Desktop-only — mobile has no drag gesture for files, so it
 * uploads via the nav's "+" button instead (see Nav.tsx). */
export default function Uploader({ onUploaded }: { onUploaded: () => void }) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const { items, handleFiles } = useUploader(onUploaded);

  return (
    <div className="mb-4 hidden md:block">
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
        className={`cursor-pointer rounded-md border-2 border-dashed p-6 text-center text-sm ${
          dragging ? "border-accent bg-accent/10" : "border-charcoal/20"
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
        <div className="mt-2">
          <UploadProgressList items={items} />
        </div>
      )}
    </div>
  );
}
