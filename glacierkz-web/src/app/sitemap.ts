import type { MetadataRoute } from "next";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://github.com/nazkari86-lab/GlacierNET-KZ";

const ROUTES = [
  "",
  "/dashboard",
  "/predict",
  "/compare",
  "/trend",
  "/datasets",
  "/training",
  "/reports",
  "/history",
  "/analysis",
  "/settings",
  "/pipeline",
] as const;

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date("2026-06-27");

  return ROUTES.map((path) => ({
    url: `${BASE_URL}${path}`,
    lastModified,
    changeFrequency: path === "" ? "weekly" : "monthly",
    priority: path === "" ? 1 : 0.8,
  }));
}
