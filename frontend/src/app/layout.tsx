import type { Metadata, Viewport } from "next";

import "./globals.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "Natasha & Yisi's Wedding",
  description: "Share photos and videos from Natasha & Yisi's wedding",
  manifest: "/manifest.webmanifest",
  // FR-037: a private, password-gated gallery must never be indexable. Emitted as
  // <meta name="robots"> on every page; robots.ts and nginx repeat it at their layers.
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: { index: false, follow: false, noimageindex: true },
  },
};

export const viewport: Viewport = {
  themeColor: "#e8b4bc",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
