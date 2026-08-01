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
    await expect(page.getByRole("heading", { name: /Покажите, что проверить рядом с объектом компании/i })).toBeVisible();

    await page.getByLabel("Название объекта").fill("Тестовый водозабор");
    await page.getByLabel("Широта").fill("42.9753");
    await page.getByLabel("Долгота").fill("76.9723");
    await page.getByRole("button", { name: /Добавить и проверить/i }).click();
    await expect(page.getByRole("button", { name: /Тестовый водозабор Инфраструктура/i })).toBeVisible();
    await page.getByRole("button", { name: /Показать маршрут на карте/i }).first().click();
    await expect(page.getByText(/Контекст HydroRIVERS/i)).toBeVisible({ timeout: 20_000 });

    const firstCase = page.getByRole("button", { name: /ОБЪЕКТ №1/i });
    await expect(firstCase).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(/заметное изменение площади/i)).toBeVisible();
    await expect(page.locator(".risk-twin-map")).toBeVisible();
    await expect(page.getByText("Что проверить по маршруту", { exact: true })).toBeVisible();
    await expect(page.getByText(/Это не зона затопления/i)).toBeVisible();
    await page.getByRole("button", { name: "Показать весь маршрут" }).click();
    await expect(page.locator("main [role=alert]")).toHaveCount(0);

    await expect(page.getByRole("link", { name: /Полный паспорт/i })).toHaveAttribute("href", /\/risk-twin\?rgi=/);
    await expect(page.getByRole("link", { name: /Похожие ледники/i })).toHaveAttribute("href", "/discovery");
  });
});
