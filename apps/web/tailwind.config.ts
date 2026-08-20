import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        scada: {
          bg: "#0a0e17",
          panel: "#111827",
          border: "#1e293b",
          cyan: "#06d6a0",
          blue: "#3b82f6",
          amber: "#f59e0b",
          red: "#ef4444",
          green: "#10b981",
          muted: "#64748b",
          text: "#e2e8f0",
        },
      },
      boxShadow: {
        glass: "0 0 30px rgba(6, 214, 160, 0.05)",
        "glass-lg": "0 0 60px rgba(6, 214, 160, 0.08)",
        gauge: "0 0 40px rgba(6, 214, 160, 0.12)",
      },
      backgroundImage: {
        "grid-pattern":
          "linear-gradient(rgba(6, 214, 160, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(6, 214, 160, 0.03) 1px, transparent 1px)",
      },
      backgroundSize: {
        grid: "40px 40px",
      },
      animation: {
        pulse_slow: "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "scan-line": "scan 4s ease-in-out infinite",
        "fade-in": "fadeIn 0.3s ease-out",
      },
      keyframes: {
        scan: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(100%)" },
        },
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
