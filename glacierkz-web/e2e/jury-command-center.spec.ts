import { expect, test } from "@playwright/test";

test.describe("Command Center", () => {
  test("keeps the real Risk Twin case, comparisons, map and claim boundaries on one page", async ({ page }) => {
    await page.goto("/jury", { waitUntil: "domcontentloaded" });

    await expect(page.getByRole("heading", { name: /От спутникового слоя — к проверяемому следующему действию/i })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Навигация Command Center" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Skip to main content" })).toBeAttached();
    await expect(page.getByRole("region", { name: "Анимация ледника и ключевые факты" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Проверка похожих ледников/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /ПАСПОРТ 1/i })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(/Физически подобранные twin/i)).toBeVisible();

    const firstCase = page.getByRole("button", { name: /КЕЙС 1/i });
    await expect(firstCase).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(/Формула фиксирована и видима/i)).toBeVisible();
    await expect(page.locator(".risk-twin-map")).toBeVisible();
    await expect(page.locator("main [role=alert]")).toHaveCount(0);

    const routeMode = page.getByRole("button", { name: /Путь/i });
    await routeMode.click();
    await expect(routeMode).toHaveAttribute("aria-pressed", "true");

    await expect(page.getByRole("heading", { name: /Что GlacierNET‑KZ не будет обещать/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /Открыть полный Risk Twin/i })).toHaveAttribute("href", /\/risk-twin\?rgi=/);
  });
});
