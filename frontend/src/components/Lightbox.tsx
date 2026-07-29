"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, mediaUrl } from "@/lib/api";
import type { Comment, Media } from "@/lib/types";

import BlurImage from "./BlurImage";
import ShareDialog from "./ShareDialog";

const REACTIONS = ["like", "love", "laugh"] as const;
const EMOJI: Record<string, string> = { like: "👍", love: "❤️", laugh: "😂" };

export default function Lightbox({
  media,
  onClose,
  onOpenMedia,
}: {
  media: Media;
  onClose: () => void;
  onOpenMedia: (m: Media) => void;
}) {
  const { t } = useTranslation();
  const [comments, setComments] = useState<Comment[]>([]);
  const [similar, setSimilar] = useState<Media[]>([]);
  const [reactionCount, setReactionCount] = useState(media.reaction_count);
  const [myReaction, setMyReaction] = useState<string | null>(null);
  const [favorited, setFavorited] = useState(false);
  const [text, setText] = useState("");
  const [showShare, setShowShare] = useState(false);

  useEffect(() => {
    setReactionCount(media.reaction_count);
    api.post(`/media/${media.id}/view`).catch(() => {});
    api.get(`/media/${media.id}/comments`).then(({ data }) => setComments(data)).catch(() => {});
    api.get(`/media/${media.id}/similar`).then(({ data }) => setSimilar(data)).catch(() => {});
  }, [media.id, media.reaction_count]);

  const react = useCallback(
    async (type: string) => {
      const { data } = await api.post(`/media/${media.id}/reactions`, { reaction_type: type });
      setMyReaction(data.reaction_type);
      setReactionCount(data.reaction_count);
    },
    [media.id]
  );

  async function favorite() {
    const { data } = await api.post(`/media/${media.id}/favorites`);
    setFavorited(data.favorited);
  }

  async function addComment() {
    if (!text.trim()) return;
    const { data } = await api.post(`/media/${media.id}/comments`, { content: text });
    setComments((c) => [...c, data]);
    setText("");
  }

  const isVideo = media.media_type === "video";
  const fullSrc = mediaUrl(isVideo ? media.storage_path : media.optimized_path || media.storage_path);

  return (
    <div className="fixed inset-0 z-40 flex flex-col overflow-auto bg-black/90 text-white">
      <div className="flex items-center justify-between p-3">
        <span className="text-sm">{media.original_filename}</span>
        <button onClick={onClose} aria-label="close" className="text-2xl">
          ×
        </button>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center p-4">
        {isVideo ? (
          <video src={fullSrc} controls className="max-h-[60vh] max-w-full" />
        ) : (
          <BlurImage src={fullSrc} lqip={media.lqip} alt={media.original_filename} className="max-h-[60vh] w-auto" />
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3 px-4 py-2">
        {REACTIONS.map((r) => (
          <button
            key={r}
            onClick={() => react(r)}
            className={`rounded px-2 py-1 ${myReaction === r ? "bg-blush text-ink" : "bg-white/10"}`}
          >
            {EMOJI[r]}
          </button>
        ))}
        <span className="text-sm">{reactionCount}</span>
        <button onClick={favorite} className="rounded bg-white/10 px-2 py-1">
          {favorited ? "★" : "☆"}
        </button>
        <a
          href={fullSrc}
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
            <div key={c.id} className="text-sm">
              <b>{c.username}</b> {c.content}
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={t("lightbox.addComment")}
            className="flex-1 rounded border-none px-2 py-1 text-ink"
          />
          <button onClick={addComment} className="rounded bg-blush px-3 py-1 text-ink">
            {t("lightbox.send")}
          </button>
        </div>
      </div>

      {showShare && <ShareDialog mediaId={media.id} onClose={() => setShowShare(false)} />}
    </div>
  );
}
