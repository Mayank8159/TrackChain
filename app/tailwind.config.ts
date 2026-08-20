// Tailwind CSS theme and content globs.

import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        scada: {
          bg: "#0B0F19",
          panel: "#111827",
          "panel-header": "#151E32",
          border: "#1E293B",
          "border-bright": "#334155",
          cyan: "#00F0FF",
          green: "#00E676",
          amber: "#FFB300",
          red: "#FF1744",
          text: "#E2E8F0",
          muted: "#94A3B8",
        },
      },
      fontFamily: {
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
      keyframes: {
        glow: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.6" },
        },
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(1000%)" },
        },
        radar: {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
      },
      animation: {
        glow: "glow 2s ease-in-out infinite",
        scan: "scan 4s linear infinite",
        radar: "radar 8s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
