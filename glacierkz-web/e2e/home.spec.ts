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
    await expect(page.getByRole("link", { name: "Предсказание" })).toBeVisible();
  });

  test("navigates to predict page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Predict" }).first().click();
    await expect(page).toHaveURL(/\/predict/);
    await expect(page.getByRole("heading", { name: /Predict/i })).toBeVisible();
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
