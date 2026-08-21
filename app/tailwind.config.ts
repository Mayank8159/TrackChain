// Tailwind CSS theme configuration locked for TrackChain Mission Control UI (tc.v1).

import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Operational Mission Control Palette
        scada: {
          bg: "#0F172A", // Deep navy app background
          panel: "#1E293B", // Dense slate card/panel surface
          "panel-header": "#151E32", // Slate panel header
          border: "#334155", // Restrained 1px slate border
          "border-bright": "#475569", // Focused / hover border
          text: "#F1F5F9", // High contrast primary text
          muted: "#94A3B8", // Secondary / caption text
          accent: "#3B82F6", // Interactive accent blue (strictly for controls/links)
          "accent-hover": "#2563EB", // Hover state for interactive blue
          cyan: "#00F0FF", // Telemetry vector / sensor line
          green: "#10B981", // Operational normal
          amber: "#F59E0B", // Warning / caution
          red: "#EF4444", // Critical alarm
        },
        // 5-Tier Severity System Colors
        severity: {
          ok: "#10B981", // Green
          low: "#84CC16", // Lime
          medium: "#F59E0B", // Amber
          high: "#F97316", // Orange
          critical: "#EF4444", // Red
        },
      },
      borderRadius: {
        card: "10px",
        control: "6px",
        badge: "9999px",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Inter", "system-ui", "sans-serif"],
        mono: [
          "var(--font-mono)",
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      keyframes: {
        glow: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.6" },
        },
        pulseCritical: {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.7", transform: "scale(1.04)" },
        },
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(1000%)" },
        },
      },
      animation: {
        glow: "glow 2s ease-in-out infinite",
        pulseCritical: "pulseCritical 1.5s ease-in-out infinite",
        scan: "scan 4s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
