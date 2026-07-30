import { expect, test } from "@playwright/test";

test.describe("Active Cryosphere Risk Twin", () => {
  test("shows a real year-specific screening case and keeps the map usable offline", async ({ page }) => {
    test.setTimeout(60_000);
    await page.goto("/risk-twin");

    await expect(page.getByRole("heading", { level: 1, name: "Active Cryosphere Risk Twin" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Система сама нашла объекты, которые стоит проверить" })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByLabel("Risk Twin evidence map")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("button", { name: "Локально" })).toHaveAttribute("aria-pressed", "true");

    const inventoryYear = page.getByLabel("Год инвентаря озёр");
    await expect(inventoryYear).toBeVisible();
    const refreshedScan = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return url.pathname.endsWith("/api/risk-twin/regional-scan")
        && url.searchParams.get("inventory_year") === "2010"
        && response.ok();
    });
    await inventoryYear.selectOption("2010");
    await refreshedScan;
    await expect(inventoryYear).toHaveValue("2010");
    await expect(page.locator("#observation-queue").getByText(/Период сравнения:/)).toContainText("2010");

    const caseButton = page.locator("#observation-queue button").filter({ hasText: "Lake" }).first();
    await expect(caseButton).toBeVisible({ timeout: 20_000 });
    await caseButton.click();
    await expect(page).toHaveURL(/\/risk-twin\?.*lake=.*lake_year=2010/);
    await expect(
      page.getByRole("heading", { name: "Что этот объект позволяет утверждать сейчас" })
    ).toBeVisible({ timeout: 20_000 });
    await expect(page.locator("[data-nextjs-dialog]")).toHaveCount(0);
  });
});
