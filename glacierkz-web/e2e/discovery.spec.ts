import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

test("CryoGenesis shows physical twins and never promotes a causal claim", async ({
  page,
}) => {
  const passportRoot = resolve(
    process.cwd(),
    "../results/cryogenesis/current/passports",
  );
  const passportFile = readdirSync(passportRoot)
    .filter((name) => name.endsWith(".json"))
    .sort()[0];
  const passport = JSON.parse(
    readFileSync(resolve(passportRoot, passportFile), "utf8"),
  );

  await page.route("**/api/cryogenesis/discoveries", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        status: "ready",
        items: [passport],
        count: 1,
        invalid_artifact_count: 0,
      }),
    });
  });
  await page.route(
    "**/api/cryogenesis/glaciers/*/passport",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(passport),
      });
    },
  );

  await page.goto("/discovery");
  await expect(
    page.getByRole("heading", { level: 1, name: /CryoGenesis/i }),
  ).toBeVisible();
  await expect(
    page.getByText(/retrospective mapped-area comparison/i),
  ).toBeVisible();
  await expect(page.getByText(/causal effect identification/i)).toBeVisible();
  await expect(
    page.getByLabel(/CryoGenesis target and matched twins/i),
  ).toBeVisible();
  await expect(
    page.locator('[data-evidence-tier="synthetic"]'),
  ).toHaveCount(0);
});

