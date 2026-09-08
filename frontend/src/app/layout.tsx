import type { Metadata, Viewport } from "next";

import "./globals.css";
import BeianFooter from "@/components/BeianFooter";
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
  themeColor: "#c17a5a",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      {/* Sticky-footer layout: the content column grows to fill the viewport so the
          ICP/PSB filing footer always rests at the bottom of the page (MIIT requires
          it at the bottom of the homepage), even when a page's content is short. */}
      <body className="flex min-h-screen flex-col">
        <Providers>
          <div className="flex flex-1 flex-col">{children}</div>
        </Providers>
        <BeianFooter />
      </body>
    </html>
  );
}
