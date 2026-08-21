// Root App Router layout: typography, providers, and Mission Control AppShell (tc.v1).

import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Providers } from "./providers";
import { AppShell } from "../components/layout/AppShell";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

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
    <html lang="en" className={`dark ${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="bg-scada-bg font-sans antialiased text-scada-text selection:bg-scada-accent/30 selection:text-white min-h-screen overflow-hidden">
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
