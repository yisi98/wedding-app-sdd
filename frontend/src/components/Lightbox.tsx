"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, mediaUrl } from "@/lib/api";
import type { Comment, Media } from "@/lib/types";
import { useAuthStore } from "@/stores/auth";

import BlurImage from "./BlurImage";
import ShareDialog from "./ShareDialog";

const REACTIONS = ["like", "love", "laugh"] as const;
const EMOJI: Record<string, string> = { like: "👍", love: "❤️", laugh: "😂" };
// Horizontal travel (px) that counts as a swipe rather than a tap or a vertical scroll.
const SWIPE_THRESHOLD = 50;

export default function Lightbox({
  media,
  items = [],
  onClose,
  onOpenMedia,
}: {
  media: Media;
  /** The list the viewer is browsing, so prev/next can move through it (FR-014). */
  items?: Media[];
  onClose: () => void;
  onOpenMedia: (m: Media) => void;
}) {
  const { t } = useTranslation();
  const myUserId = useAuthStore((s) => s.user?.id);
  const [comments, setComments] = useState<Comment[]>([]);
  const [similar, setSimilar] = useState<Media[]>([]);
  const [reactionCount, setReactionCount] = useState(media.reaction_count);
  const [myReaction, setMyReaction] = useState<string | null>(null);
  const [favorited, setFavorited] = useState(false);
  const [text, setText] = useState("");
  const [showShare, setShowShare] = useState(false);
  const [busy, setBusy] = useState(false);
  const touchStartX = useRef<number | null>(null);
  const touchStartY = useRef<number | null>(null);

  useEffect(() => {
    setReactionCount(media.reaction_count);
    setMyReaction(null);
    setFavorited(false);
    api.post(`/media/${media.id}/view`).catch(() => {});
    api.get(`/media/${media.id}/comments`).then(({ data }) => setComments(data)).catch(() => {});
    api.get(`/media/${media.id}/similar`).then(({ data }) => setSimilar(data)).catch(() => {});
  }, [media.id, media.reaction_count]);

  const index = items.findIndex((m) => m.id === media.id);
  const prev = index > 0 ? items[index - 1] : null;
  const next = index >= 0 && index < items.length - 1 ? items[index + 1] : null;

  const goPrev = useCallback(() => {
    if (prev) onOpenMedia(prev);
  }, [prev, onOpenMedia]);
  const goNext = useCallback(() => {
    if (next) onOpenMedia(next);
  }, [next, onOpenMedia]);

  // Keyboard: arrows to move, Escape to leave. Skipped while typing a comment so the
  // arrow keys still move the caret inside the input.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const el = e.target as HTMLElement | null;
      const typing = el && /^(INPUT|TEXTAREA)$/.test(el.tagName);
      if (e.key === "Escape") {
        // The share dialog is layered above and closes itself first.
        if (!showShare) onClose();
        return;
      }
      if (typing || showShare) return;
      if (e.key === "ArrowLeft") goPrev();
      if (e.key === "ArrowRight") goNext();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [goPrev, goNext, onClose, showShare]);

  function onTouchStart(e: React.TouchEvent) {
    touchStartX.current = e.touches[0].clientX;
    touchStartY.current = e.touches[0].clientY;
  }

  function onTouchEnd(e: React.TouchEvent) {
    if (touchStartX.current === null || touchStartY.current === null) return;
    const dx = e.changedTouches[0].clientX - touchStartX.current;
    const dy = e.changedTouches[0].clientY - touchStartY.current;
    touchStartX.current = null;
    touchStartY.current = null;
    // Ignore mostly-vertical gestures — the panel below the image scrolls.
    if (Math.abs(dx) < SWIPE_THRESHOLD || Math.abs(dx) < Math.abs(dy)) return;
    if (dx > 0) goPrev();
    else goNext();
  }

  const react = useCallback(
    async (type: string) => {
      setBusy(true);
      try {
        const { data } = await api.post(`/media/${media.id}/reactions`, { reaction_type: type });
        setMyReaction(data.reaction_type);
        setReactionCount(data.reaction_count);
      } finally {
        setBusy(false);
      }
    },
    [media.id]
  );

  async function favorite() {
    setBusy(true);
    try {
      const { data } = await api.post(`/media/${media.id}/favorites`);
      setFavorited(data.favorited);
    } finally {
      setBusy(false);
    }
  }

  async function addComment() {
    if (!text.trim() || busy) return;
    setBusy(true);
    try {
      const { data } = await api.post(`/media/${media.id}/comments`, { content: text });
      setComments((c) => [...c, data]);
      setText("");
    } finally {
      setBusy(false);
    }
  }

  async function deleteComment(id: number) {
    await api.delete(`/media/${media.id}/comments/${id}`);
    setComments((c) => c.filter((x) => x.id !== id));
  }

  const isVideo = media.media_type === "video";
  // optimized_path is a browser-safe derivative when set (WebP for images; an H.264/AAC MP4
  // transcode for videos whose original container/codec most browsers can't play natively).
  // The original at storage_path is unchanged and is what downloads always serve.
  const fullSrc = mediaUrl(media.optimized_path || media.storage_path);

  return (
    <div className="fixed inset-0 z-40 flex flex-col overflow-auto bg-black/90 text-white">
      <div className="flex items-center justify-between p-3">
        <span className="text-sm">
          {media.original_filename}
          <span className="ml-2 text-white/60">
            {t("gallery.uploadedBy", { name: media.uploader_name })}
          </span>
          {index >= 0 && items.length > 1 && (
            <span className="ml-2 text-white/40">
              {index + 1}/{items.length}
            </span>
          )}
        </span>
        <button onClick={onClose} aria-label="close" className="px-2 text-2xl leading-none">
          ×
        </button>
      </div>

      <div
        className="relative flex flex-1 flex-col items-center justify-center p-4"
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
      >
        {isVideo ? (
          <video src={fullSrc} controls className="max-h-[60vh] max-w-full" />
        ) : (
          <BlurImage
            src={fullSrc}
            lqip={media.lqip}
            alt={media.original_filename}
            className="max-h-[60vh] w-auto"
          />
        )}

        {prev && (
          <button
            onClick={goPrev}
            aria-label={t("lightbox.previous")}
            className="absolute left-1 top-1/2 -translate-y-1/2 rounded-full bg-black/50 px-3 py-2 text-2xl leading-none hover:bg-black/70"
          >
            ‹
          </button>
        )}
        {next && (
          <button
            onClick={goNext}
            aria-label={t("lightbox.next")}
            className="absolute right-1 top-1/2 -translate-y-1/2 rounded-full bg-black/50 px-3 py-2 text-2xl leading-none hover:bg-black/70"
          >
            ›
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3 px-4 py-2">
        {REACTIONS.map((r) => (
          <button
            key={r}
            onClick={() => react(r)}
            disabled={busy}
            className={`rounded px-2 py-1 disabled:opacity-50 ${
              myReaction === r ? "bg-blush text-ink" : "bg-white/10"
            }`}
          >
            {EMOJI[r]}
          </button>
        ))}
        <span className="text-sm">{reactionCount}</span>
        <button
          onClick={favorite}
          disabled={busy}
          className="rounded bg-white/10 px-2 py-1 disabled:opacity-50"
        >
          {favorited ? "★" : "☆"}
        </button>
        <a
          href={mediaUrl(media.storage_path)}
          download={media.original_filename}
          className="rounded bg-white/10 px-2 py-1 text-sm"
        >
          {t("lightbox.download")}
        </a>
        <button onClick={() => setShowShare(true)} className="rounded bg-white/10 px-2 py-1 text-sm">
          {t("lightbox.share")}
        </button>
      </div>

      {similar.length > 0 && (
        <div className="px-4 py-2">
          <p className="mb-1 text-xs uppercase text-gray-400">{t("lightbox.similar")}</p>
          <div className="flex gap-2 overflow-x-auto">
            {similar.map((s) => (
              <button key={s.id} onClick={() => onOpenMedia(s)} className="h-16 w-16 flex-shrink-0">
                <BlurImage
                  src={mediaUrl(s.thumbnail_path || s.optimized_path)}
                  lqip={s.lqip}
                  alt={s.original_filename}
                  className="h-full w-full rounded"
                />
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="px-4 py-3">
        <p className="mb-2 text-xs uppercase text-gray-400">{t("lightbox.comments")}</p>
        <div className="mb-2 space-y-1">
          {comments.map((c) => (
            <div key={c.id} className="flex items-start gap-2 text-sm">
              <span className="flex-1">
                <b>{c.username}</b> {c.content}
              </span>
              {c.user_id === myUserId && (
                <button
                  onClick={() => deleteComment(c.id)}
                  aria-label={t("lightbox.deleteComment")}
                  title={t("lightbox.deleteComment")}
                  className="shrink-0 px-1 text-white/40 hover:text-white"
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") addComment();
            }}
            placeholder={t("lightbox.addComment")}
            className="flex-1 rounded border-none px-2 py-1 text-ink"
          />
          <button
            onClick={addComment}
            disabled={busy || !text.trim()}
            className="rounded bg-blush px-3 py-1 text-ink disabled:opacity-50"
          >
            {t("lightbox.send")}
          </button>
        </div>
      </div>

      {showShare && <ShareDialog mediaId={media.id} onClose={() => setShowShare(false)} />}
    </div>
  );
}
