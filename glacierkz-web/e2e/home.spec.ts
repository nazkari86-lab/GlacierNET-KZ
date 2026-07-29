import { test, expect } from "@playwright/test";

test.describe("Home page", () => {
  test("loads with English title by default", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1, name: "Analyze a real glacier and see where the model can be trusted." })).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
  });

  test("switches locale to Russian", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("radio", { name: "RU" }).click();
    await expect(page.locator("html")).toHaveAttribute("lang", "ru");
    await expect(page.getByRole("heading", { level: 1, name: "Спутниктік бақылауларды тексерілетін дәлелдерге айналдырамыз." })).not.toBeVisible();
    await expect(page.getByRole("heading", { level: 1, name: "Проанализируйте реальный ледник и увидьте, где модели можно доверять." })).toBeVisible();
  });

  test("navigates to the glacier-first ML workspace", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Open ML Workspace" }).click();
    await expect(page).toHaveURL(/\/ml/);
    await expect(
      page.getByRole("heading", { name: /От спутникового композита/i })
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
