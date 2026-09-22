import { sha256 } from "@noble/hashes/sha2";
import { bytesToHex } from "@noble/hashes/utils";

const CHUNK_SIZE = 1024 * 1024;

export async function hashFile(file: Blob, onProgress: (percent: number) => void): Promise<string> {
  const hash = sha256.create();
  try {
    for (let offset = 0; offset < file.size; offset += CHUNK_SIZE) {
      const chunk = await file.slice(offset, offset + CHUNK_SIZE).arrayBuffer();
      hash.update(new Uint8Array(chunk));
      onProgress(Math.round(100 * Math.min(offset + CHUNK_SIZE, file.size) / file.size));
      // Let the phone paint progress and respond to touches between chunks.
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
    return bytesToHex(hash.digest());
  } finally {
    hash.destroy();
  }
}

export function uploadMimeType(file: Pick<File, "name" | "type">): string {
  const type = file.type.toLowerCase();
  if (type === "video/x-m4v") return "video/mp4";
  if (type && type !== "application/octet-stream") return type;
  // Some mobile file providers omit the MIME type. The server still validates it.
  const types: Record<string, string> = {
    mp4: "video/mp4", m4v: "video/mp4", mov: "video/quicktime", webm: "video/webm",
    jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", webp: "image/webp",
    gif: "image/gif", heic: "image/heic",
  };
  return types[file.name.split(".").pop()?.toLowerCase() || ""] || "application/octet-stream";
}
