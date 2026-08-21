// Environment-Aware API Resolution for TrackChain (tc.v1).
// Resolves between local development, Vercel deployments, and custom production environments.

export interface EnvironmentConfig {
  apiUrl: string;
  sseUrl: string;
  isProduction: boolean;
  isDevelopment: boolean;
  corsOrigin: string;
}

function resolveEnvironment(): EnvironmentConfig {
  // 1. Explicitly configured public URL (highest priority)
  const explicitUrl = process.env.NEXT_PUBLIC_API_URL;
  if (explicitUrl && explicitUrl.trim()) {
    const cleanUrl = explicitUrl.trim().replace(/\/$/, "");
    return {
      apiUrl: cleanUrl,
      sseUrl: `${cleanUrl}/api/alerts/stream`,
      isProduction: cleanUrl.startsWith("https://"),
      isDevelopment: cleanUrl.includes("localhost") || cleanUrl.includes("127.0.0.1"),
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
      isProduction: true,
      isDevelopment: false,
      corsOrigin: url,
    };
  }

  // 3. Fallback: Local development environment
  return {
    apiUrl: "http://localhost:8000",
    sseUrl: "http://localhost:8000/api/alerts/stream",
    isProduction: false,
    isDevelopment: true,
    corsOrigin: "http://localhost:3000",
  };
}

export const env = resolveEnvironment();
