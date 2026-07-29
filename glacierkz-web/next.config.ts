import type { NextConfig } from "next";

const apiOrigin = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  // Lets CI or a local verification build run alongside the developer server
  // without touching its active .next cache or HMR state.
  distDir: process.env.NEXT_DIST_DIR || ".next",
  turbopack: {
    root: __dirname,
  },
  allowedDevOrigins: [
    // Next.js compares the request origin host in development. Keep the
    // hostname variants as well as legacy URL entries so HMR works whether the
    // local UI is opened as localhost or 127.0.0.1 on a non-default port.
    "localhost",
    "127.0.0.1",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3100",
    "http://127.0.0.1:3100",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
  ],
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${apiOrigin}/api/:path*` },
      { source: "/static/:path*", destination: `${apiOrigin}/static/:path*` },
      { source: "/mcp/:path*", destination: `${apiOrigin}/mcp/:path*` },
      { source: "/docs", destination: `${apiOrigin}/docs` },
      { source: "/docs/:path*", destination: `${apiOrigin}/docs/:path*` },
      { source: "/redoc", destination: `${apiOrigin}/redoc` },
      { source: "/openapi.json", destination: `${apiOrigin}/openapi.json` },
      { source: "/health", destination: `${apiOrigin}/health` },
      { source: "/health/:path*", destination: `${apiOrigin}/health/:path*` },
      { source: "/metrics", destination: `${apiOrigin}/metrics` },
      { source: "/info", destination: `${apiOrigin}/info` },
      { source: "/status", destination: `${apiOrigin}/status` },
      { source: "/legacy", destination: `${apiOrigin}/` },
      { source: "/legacy/:path*", destination: `${apiOrigin}/:path*` },
    ];
  },
};

export default nextConfig;
