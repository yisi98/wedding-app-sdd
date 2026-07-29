"use client";

import { useState } from "react";

// LQIP blur-up (US7 / FR-028): show the base64 placeholder until the full image loads.
export default function BlurImage({
  src,
  lqip,
  alt,
  className = "",
}: {
  src: string;
  lqip: string | null;
  alt: string;
  className?: string;
}) {
  const [loaded, setLoaded] = useState(false);
  return (
    <div className={`relative overflow-hidden bg-gray-200 ${className}`}>
      {lqip && !loaded && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={lqip} alt="" className="absolute inset-0 h-full w-full scale-110 object-cover blur-lg" />
      )}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        loading="lazy"
        onLoad={() => setLoaded(true)}
        className={`h-full w-full object-cover transition-opacity duration-300 ${
          loaded ? "opacity-100" : "opacity-0"
        }`}
      />
    </div>
  );
}
