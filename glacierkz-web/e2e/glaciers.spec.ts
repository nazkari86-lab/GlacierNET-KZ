import { test, expect } from "@playwright/test";

const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";

test.describe("Individual glacier registry", () => {
  test.beforeEach(async ({ request }) => {
    const response = await request.get(`${API_URL}/api/glaciers?named_only=true`);
    test.skip(!response.ok(), `Glacier registry API is not running at ${API_URL}`);
  });

  test("shows Tuyuksu inventory evidence and a physical time series", async ({ page }) => {
    await page.goto("/glaciers");

    await expect(page.getByRole("heading", { name: "Individual Glacier Registry" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Ледник Центральный Туюксу" })).toBeVisible();
    await expect(page.getByText("WGMS reference")).toBeVisible();
    await expect(page.getByText("2.838 km²").last()).toBeVisible();
    await expect(page.getByText("-0.3937 km²")).toBeVisible();
    await expect(page.getByText("-13.83%")).toBeVisible();
    await expect(page.getByTestId("glacier-series-chart")).toBeVisible();
    await expect(page.getByLabel("RGI boundary map for Ледник Центральный Туюксу")).toBeVisible();
    await expect(page.getByText(/fixed RGI 2000 outline/)).toBeVisible();
  });

  test("passes the selected glacier evidence to AI analysis", async ({ page }) => {
    await page.goto("/glaciers");
    await page.getByRole("link", { name: "Analyze with AI" }).click();

    await expect(page).toHaveURL(/\/analysis\?glacier=RGI2000-v7.0-G-13-33843/);
    await expect(page.getByLabel("Prompt")).toHaveValue(/Центральный Туюксу/);
    await expect(page.getByText("Загружено проверенных контекстов: 1")).toBeVisible();
  });
});
