import { test, expect } from "@playwright/test";

const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";

test.describe("API integration", () => {
  test.beforeEach(async ({ request }) => {
    const res = await request.get(`${API_URL}/health`);
    test.skip(!res.ok(), `API not running at ${API_URL} — start with: uvicorn app.main:app --app-dir glacierkz-api`);
  });

  test("health endpoint returns ok", async ({ request }) => {
    const res = await request.get(`${API_URL}/health`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.status).toMatch(/ok|healthy/i);
  });

  test("models endpoint lists available architectures", async ({ request }) => {
    const res = await request.get(`${API_URL}/api/models`);
    expect(res.ok()).toBeTruthy();
    const models = await res.json();
    expect(Array.isArray(models)).toBeTruthy();
    expect(models.length).toBeGreaterThan(0);
    const names = models.map((m: { name: string }) => m.name);
    expect(names).toContain("unet");
  });

  test("web settings page loads when API is up", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: /Settings/i })).toBeVisible();
  });
});
