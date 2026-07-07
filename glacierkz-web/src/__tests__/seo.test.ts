import { describe, it, expect } from "vitest";
import robots from "@/app/robots";
import sitemap from "@/app/sitemap";

describe("SEO metadata", () => {
  it("robots.txt allows public pages and blocks admin", () => {
    const config = robots();
    expect(config.rules).toBeDefined();
    const rule = Array.isArray(config.rules) ? config.rules[0] : config.rules;
    expect(rule.allow).toContain("/");
    expect(rule.disallow).toContain("/admin/");
    expect(config.sitemap).toContain("sitemap.xml");
  });

  it("sitemap includes main routes", () => {
    const entries = sitemap();
    const urls = entries.map((e) => e.url);
    expect(urls.some((u) => u.endsWith("GlacierNET-KZ") || u.endsWith("GlacierNET-KZ/"))).toBe(true);
    expect(urls.some((u) => u.includes("/predict"))).toBe(true);
    expect(urls.some((u) => u.includes("/trend"))).toBe(true);
    expect(entries.length).toBeGreaterThanOrEqual(10);
  });
});
