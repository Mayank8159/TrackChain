// Environment-Aware API Resolution for TrackChain (tc.v1).
// Resolves between local development, Vercel deployments, and custom production environments.

export interface EnvironmentConfig {
  apiUrl: string;
  sseUrl: string;
  wsUrl: string;
  isProduction: boolean;
  isDevelopment: boolean;
  corsOrigin: string;
}

function resolveEnvironment(): EnvironmentConfig {
  // 1. Explicitly configured public URL (highest priority: NEXT_PUBLIC_API_URL, NEXT_PUBLIC_BACKEND_URL, NEXT_PUBLIC_API_BASE_URL)
  const explicitUrl =
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL;

  if (explicitUrl && explicitUrl.trim()) {
    const cleanUrl = explicitUrl.trim().replace(/\/$/, "");
    const isProd = cleanUrl.startsWith("https://");
    const isDev = cleanUrl.includes("localhost") || cleanUrl.includes("127.0.0.1");
    const wsScheme = isProd ? "wss" : "ws";
    const hostPart = cleanUrl.replace(/^https?:\/\//, "");

    return {
      apiUrl: cleanUrl,
      sseUrl: `${cleanUrl}/api/alerts/stream`,
      wsUrl: `${wsScheme}://${hostPart}/ws/live`,
      isProduction: isProd,
      isDevelopment: isDev,
      corsOrigin: typeof window !== "undefined" ? window.location.origin : cleanUrl,
    };
  }

  // 2. Vercel deployment auto-detection
  if (process.env.NEXT_PUBLIC_VERCEL_URL || process.env.VERCEL_URL) {
    const host = process.env.NEXT_PUBLIC_VERCEL_URL || process.env.VERCEL_URL;
    const cleanHost = host?.replace(/^https?:\/\//, "").replace(/\/$/, "");
    const url = `https://${cleanHost}`;
    return {
      apiUrl: url,
      sseUrl: `${url}/api/alerts/stream`,
      wsUrl: `wss://${cleanHost}/ws/live`,
      isProduction: true,
      isDevelopment: false,
      corsOrigin: url,
    };
  }

  // 3. Fallback: Local development environment
  return {
    apiUrl: "http://localhost:8000",
    sseUrl: "http://localhost:8000/api/alerts/stream",
    wsUrl: "ws://localhost:8000/ws/live",
    isProduction: false,
    isDevelopment: true,
    corsOrigin: "http://localhost:3000",
  };
}

export const env = resolveEnvironment();
