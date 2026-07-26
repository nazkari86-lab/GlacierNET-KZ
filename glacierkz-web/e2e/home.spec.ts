import { test, expect } from "@playwright/test";

test.describe("Home page", () => {
  test("loads with English title by default", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1, name: "GlacierNET-KZ" })).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
  });

  test("switches locale to Russian", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("radio", { name: "RU" }).click();
    await expect(page.locator("html")).toHaveAttribute("lang", "ru");
    const navigation = page.getByLabel("Main navigation");
    await expect(navigation.getByRole("link", { name: "Обзор" })).toBeVisible();
    await expect(navigation.getByRole("link", { name: "Карта" })).toBeVisible();
    await expect(navigation.getByRole("link", { name: "Объекты" })).toBeVisible();
    await expect(navigation.getByRole("link", { name: "Проверки" })).toBeVisible();
    await expect(navigation.getByRole("link", { name: "Отчёты" })).toBeVisible();
  });

  test("navigates to the decision-first Operations workspace", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Open Operations" }).click();
    await expect(page).toHaveURL(/\/operations/);
    await expect(
      page.getByRole("heading", { name: "What needs attention today" })
    ).toBeVisible();
  });

  test("skip link targets main content", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: /Skip to content/i });
    await expect(skip).toBeFocused();
    await skip.click();
    await expect(page.locator("#main-content")).toBeVisible();
  });
});
