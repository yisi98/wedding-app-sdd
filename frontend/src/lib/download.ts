import { API_BASE } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

/**
 * POST the given ids to /downloads/bulk and save the streamed ZIP via a blob URL.
 * One ZIP beats N individual saves: browsers throttle/block multiple automatic
 * downloads, and the server-side archive keeps original filenames.
 * Throws on a failed request so each caller can surface its own error copy.
 */
export async function downloadZip(mediaIds: number[], filename: string): Promise<void> {
  const token = useAuthStore.getState().accessToken;
  const res = await fetch(`${API_BASE}/api/v1/downloads/bulk`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ media_ids: mediaIds }),
  });
  if (!res.ok) throw new Error(`bulk download failed: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  // Safari (and some older WebKit builds) only honors a click-triggered download when
  // the anchor is actually in the document; an unattached element silently no-ops there.
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Revoking synchronously can race the browser's own read of the blob URL, so give it
  // a moment before freeing it.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
