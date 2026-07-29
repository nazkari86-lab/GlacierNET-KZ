import { expect, test } from "@playwright/test";

test.describe("Decision-first Operations workspace", () => {
  test("connects ranked observations to comparison and evidence", async ({ page }) => {
    await page.goto("/operations");

    await expect(
      page.getByRole("heading", { name: "What needs attention today" })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Критические объекты для следующей проверки" })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Real local Risk Twin screening")).toBeVisible();
    const riskTwinSelector = page.getByLabel("Выбрать любой реальный случай Risk Twin");
    await expect(riskTwinSelector).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("real-inventory-map")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(/RGI 7.0 boundaries/)).toBeVisible();
    await expect(page.getByRole("heading", { name: "Analysis by year" })).toBeVisible();
    await expect(page.getByTestId("analysis-year-select")).toBeVisible();
    await expect(page.getByTestId("year-area-chart")).toBeVisible();
    const annualLayer = page.getByRole("img", { name: "2024 segmentation screening layer" });
    const unavailable2024 = page.getByText(/2024 map layer unavailable/);
    await expect(annualLayer.or(unavailable2024)).toBeVisible({ timeout: 20_000 });
    if (await annualLayer.count()) {
      await expect.poll(() => annualLayer.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBeGreaterThan(0);
    }

    if (await page.getByText(/586 RGI 7.0 boundaries/).count()) {
      await page.getByText(/Find any glacier/).click();
      await page.getByTestId("map-glacier-search").fill("Туюксу");
      await page.getByRole("button", { name: /Ледник Центральный Туюксу/ }).click();
      await expect(page.getByText(/mean elevation/)).toBeVisible();
    } else {
      await expect(page.getByText(/RGI geometry unavailable/)).toBeVisible();
    }

    await page.getByTestId("analysis-year-select").selectOption("2000");
    await expect(
      page.getByRole("img", { name: "2000 segmentation screening layer" }).or(page.getByText(/2000 map layer unavailable/))
    ).toBeVisible({ timeout: 20_000 });
    const selectableCases = await riskTwinSelector.locator("option").allTextContents();
    expect(selectableCases.length).toBeGreaterThan(1);
    await riskTwinSelector.selectOption({ index: 1 });
    await expect(page.getByText("Выбранный реальный case")).toBeVisible();
    await expect(page.getByText(/Приоритет наблюдения/)).toBeVisible();
  });
});
