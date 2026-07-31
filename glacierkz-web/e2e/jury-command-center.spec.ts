import { expect, test } from "@playwright/test";

test.describe("Command Center", () => {
  test("turns real inventory evidence into one clear next action", async ({ page }) => {
    await page.goto("/jury", { waitUntil: "domcontentloaded" });

    await expect(page.getByRole("heading", { name: /Какое ледниковое озеро проверить первым/i })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Навигация Command Center" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Skip to main content" })).toBeAttached();
    await expect(page.getByRole("region", { name: "Анимация ледника и ключевые факты" })).toBeVisible();
    await expect(page.getByText(/Просмотрено 317 озёр/i)).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("heading", { name: /Следующее действие: проверить контур воды/i })).toBeVisible();

    const firstCase = page.getByRole("button", { name: /ОБЪЕКТ №1/i });
    await expect(firstCase).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(/заметное изменение площади/i)).toBeVisible();
    await expect(page.locator(".risk-twin-map")).toBeVisible();
    await expect(page.locator("main [role=alert]")).toHaveCount(0);

    await expect(page.getByRole("link", { name: /Полный паспорт/i })).toHaveAttribute("href", /\/risk-twin\?rgi=/);
    await expect(page.getByRole("link", { name: /Похожие ледники/i })).toHaveAttribute("href", "/discovery");
  });
});
