import { expect, test } from "@playwright/test";

test.describe("Decision-first Operations workspace", () => {
  test("connects ranked observations to comparison and evidence", async ({ page }) => {
    await page.goto("/operations");

    await expect(
      page.getByRole("heading", { name: "What needs attention today" })
    ).toBeVisible();
    await expect(
      page.getByRole("img", { name: "Schematic map of monitored objects" })
    ).toBeVisible();
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
