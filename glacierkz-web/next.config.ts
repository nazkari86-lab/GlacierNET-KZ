import type { NextConfig } from "next";

const apiOrigin = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  turbopack: {
    root: __dirname,
  },
  allowedDevOrigins: [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
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
