import type { Metadata, Viewport } from "next";

import "./globals.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "Our Wedding",
  description: "Share photos and videos from our wedding",
  manifest: "/manifest.webmanifest",
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
