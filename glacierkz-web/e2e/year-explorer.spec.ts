import { test, expect } from "@playwright/test";

const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";

test.describe("Local year explorer", () => {
  test.beforeEach(async ({ request }) => {
    const response = await request.get(`${API_URL}/api/years`);
    test.skip(!response.ok(), `Year API is not running at ${API_URL}`);
  });

  test("shows a real local year and compares without an upload", async ({ page }) => {
    await page.goto("/explore");

    await expect(page.getByRole("heading", { name: "Local Year Explorer" })).toBeVisible();
    await expect(page.getByText("450.47 km²").first()).toBeVisible();
    await expect(page.getByTestId("selected-sensor")).toHaveText("Sentinel-2");
    await expect(page.getByText("100/100 · high")).toBeVisible();

    await page.getByLabel("Compare with").selectOption("2000");
    await page.getByRole("button", { name: "Compare years" }).click();

    await expect(page.getByRole("heading", { name: "2000 → 2024" })).toBeVisible();
    await expect(page.getByText("-128.61 km²")).toBeVisible();
    await expect(page.getByText("Comparable")).toBeVisible();
  });

  test("labels the 2015 result as excluded from strict comparison", async ({ page }) => {
    await page.goto("/explore");
    await page.getByLabel("View year").selectOption("2015");

    await expect(page.getByText("57/100 · low")).toBeVisible();
    await expect(page.getByText(/Late-2015 annual TOA fallback/)).toBeVisible();
  });

  test("passes verified year context to the AI analysis page", async ({ page }) => {
    await page.goto("/explore");
    await page.getByRole("link", { name: "Ask AI about this verified year" }).click();

    await expect(page).toHaveURL(/\/analysis\?year=2024/);
    await expect(page.getByLabel("Prompt")).toHaveValue(/2024/);
    await expect(page.getByText("Загружено проверенных контекстов: 1")).toBeVisible();
  });
});
