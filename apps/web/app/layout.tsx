import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ITMS — Railway Control Center",
  description:
    "Integrated Track Monitoring System — Ministry of Railways, India",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-scada-bg bg-grid antialiased">
        {children}
      </body>
    </html>
  );
}
