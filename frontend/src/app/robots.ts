import type { MetadataRoute } from "next";

// FR-037: the event gallery is private to invited guests and must not be indexed.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", disallow: "/" }],
  };
}
