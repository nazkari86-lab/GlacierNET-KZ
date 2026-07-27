import { expect, test } from "@playwright/test";

test.describe("Decision-first Operations workspace", () => {
  test("connects ranked observations to comparison and evidence", async ({ page }) => {
    await page.goto("/operations");

    await expect(
      page.getByRole("heading", { name: "What needs attention today" })
    ).toBeVisible();
    await expect(page.getByTestId("real-inventory-map")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(/RGI 7.0 boundaries/)).toBeVisible();
    await expect(page.getByRole("heading", { name: "Analysis by year" })).toBeVisible();
    await expect(page.getByTestId("analysis-year-select")).toBeVisible();
    await expect(page.getByTestId("year-area-chart")).toBeVisible();
    const annualLayer = page.getByRole("img", { name: "2024 segmentation screening layer" });
    await expect(annualLayer).toBeVisible({ timeout: 20_000 });
    await expect.poll(() => annualLayer.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBeGreaterThan(0);

    await page.getByText(/Find any glacier/).click();
    await page.getByTestId("map-glacier-search").fill("Туюксу");
    await page.getByRole("button", { name: /Ледник Центральный Туюксу/ }).click();
    await expect(page.getByText(/mean elevation/)).toBeVisible();

    await page.getByTestId("analysis-year-select").selectOption("2000");
    await expect(page.getByRole("img", { name: "2000 segmentation screening layer" })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Next Best Observation")).toBeVisible();
    await expect(page.getByText("What changed")).toBeVisible();
    await expect(page.getByText("Can this be trusted?")).toBeVisible();

    await page.getByRole("tab", { name: "Before / after" }).click();
    await expect(
      page.getByRole("img", { name: /Synthetic difference map/ })
    ).toBeVisible();
    await expect(page.getByText("Model agreement")).toBeVisible();

    await page.getByText("2. Demo Lake A (synthetic)").click();
    await page.getByRole("tab", { name: "Evidence timeline" }).click();
    await expect(page.getByText("Human review recorded")).toBeVisible();
    await expect(page.getByText("Evidence case fixed")).toBeVisible();
  });
});
