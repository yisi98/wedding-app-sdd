"use client";

import { useState } from "react";

// LQIP blur-up (US7 / FR-028): show the base64 placeholder until the full image loads.
export default function BlurImage({
  src,
  lqip,
  alt,
  className = "",
  fit = "cover",
}: {
  src: string;
  lqip: string | null;
  alt: string;
  className?: string;
  /** "cover" crops to fill (grid thumbnails); "contain" shows the whole photo (full-size viewers). */
  fit?: "cover" | "contain";
}) {
  const [loaded, setLoaded] = useState(false);
  const fitClass = fit === "contain" ? "object-contain" : "object-cover";
  return (
    <div className={`relative overflow-hidden bg-gray-200 ${className}`}>
      {lqip && !loaded && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={lqip} alt="" className={`absolute inset-0 h-full w-full scale-110 ${fitClass} blur-lg`} />
      )}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        loading="lazy"
        onLoad={() => setLoaded(true)}
        className={`h-full w-full ${fitClass} transition-opacity duration-300 ${
          loaded ? "opacity-100" : "opacity-0"
        }`}
      />
    </div>
  );
}
