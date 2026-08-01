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
    await expect(page.getByText("Для Тестовый водозабор", { exact: true })).toBeVisible();
    await expect(page.getByText(/Линия — не зона затопления/i)).toBeVisible();
    await page.getByRole("button", { name: "Показать весь маршрут" }).click();
    await expect(page.locator("main [role=alert]")).toHaveCount(0);

    await expect(page.getByRole("link", { name: /Полный паспорт/i })).toHaveAttribute("href", /\/risk-twin\?rgi=/);
    await expect(page.getByRole("link", { name: /Похожие ледники/i })).toHaveAttribute("href", "/discovery");
  });

  test("turns the public AlES HPP-2 example into a specific operator action", async ({ page }) => {
    await page.goto("/jury", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("button", { name: /Показать кейс АлЭС/i })).toBeVisible({ timeout: 20_000 });
    await page.getByRole("button", { name: /Показать кейс АлЭС/i }).click();

    await expect(page.getByRole("heading", { name: /Проверять сначала озеро GL43050789E76985293N/i })).toBeVisible({ timeout: 20_000 });
    const connectedRoute = page.getByText("ТОЧКА В PLANNING‑CORRIDOR", { exact: true });
    const routeUnavailable = page.getByText(/для выбранного RGI локальный маршрут недоступен/i);
    await expect(connectedRoute.or(routeUnavailable)).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Подтвердить контур озера", { exact: true })).toBeVisible();
    await expect(page.getByText(/Подтвердить гидрологическую связь/i)).toBeVisible();
    await expect(page.getByText(/Подключить телеметрию объекта/i)).toBeVisible();
    await expect(page.getByText(/Не обоснованы остановка ГЭС/i)).toBeVisible();
    await expect(page.locator(".risk-twin-map")).toBeVisible();
    await expect(page.locator(".risk-twin-map .leaflet-popup")).toHaveCount(0);
    await expect(page.getByText("Для ГЭС‑2 Каскада Алматинских ГЭС", { exact: true })).toBeVisible();
    if (await connectedRoute.isVisible()) {
      await expect(page.getByText("До оси HydroRIVERS: 16 м", { exact: true })).toBeVisible();
    } else {
      await expect(routeUnavailable).toBeVisible();
    }
    await expect(page.locator("main [role=alert]")).toHaveCount(0);
  });
});
