// Root App Router layout: global nav, providers, and page shell.

import type { Metadata } from "next";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "TrackChain — Integrated Railway Track Monitoring & Defect Intelligence",
  description:
    "Ministry of Railways AI-powered real-time track telemetry, vision defect detection, and EN 13848 geometry analytics platform.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-scada-bg font-sans antialiased text-scada-text selection:bg-scada-cyan/30 selection:text-white">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
