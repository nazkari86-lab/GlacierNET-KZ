import { expect, test, type Page } from "@playwright/test";

const PUBLIC_ROUTES = [
  "/",
  "/hub",
  "/ml",
  "/risk-twin",
  "/benchmark",
  "/discovery",
  "/operations",
  "/jury",
  "/analysis",
  "/glaciers",
  "/explore",
  "/predict",
  "/compare",
  "/dashboard",
  "/datasets",
  "/history",
  "/demo",
  "/pilot",
  "/pipeline",
  "/reports",
  "/settings",
  "/training",
  "/trend",
] as const;

const MOBILE_CRITICAL_ROUTES = [
  "/",
  "/ml",
  "/risk-twin",
  "/benchmark",
  "/operations",
  "/analysis",
  "/glaciers",
  "/jury",
] as const;

function observeRuntimeIssues(page: Page) {
  let currentRoute = "/";
  const issues: string[] = [];

  page.on("pageerror", (error) => {
    issues.push(`${currentRoute}: page error: ${error.message}`);
  });
  page.on("console", (message) => {
    if (message.type() !== "error" && message.type() !== "warning") return;
    const text = message.text();
    // Browser extensions and optional external basemap tiles are outside the
    // application runtime. Application warnings and errors remain failures.
    if (/Download the React DevTools|favicon\.ico/i.test(text)) return;
    issues.push(`${currentRoute}: console ${message.type()}: ${text}`);
  });
  page.on("requestfailed", (request) => {
    const url = request.url();
    if (!/^https?:\/\/(127\.0\.0\.1|localhost)(?::\d+)?\//.test(url)) return;
    const failure = request.failure()?.errorText ?? "unknown";
    // A route transition intentionally aborts in-flight fetches owned by the
    // page being left. Connection errors and server failures are still caught.
    if (failure === "net::ERR_ABORTED") return;
    issues.push(`${currentRoute}: local request failed: ${url} (${failure})`);
  });
  page.on("response", (response) => {
    const url = response.url();
    if (response.status() < 500 || !/^https?:\/\/(127\.0\.0\.1|localhost)(?::\d+)?\//.test(url)) return;
    issues.push(`${currentRoute}: HTTP ${response.status()}: ${url}`);
  });

  return {
    issues,
    setRoute(route: string) {
      currentRoute = route;
    },
  };
}

async function horizontalOverflowReport(page: Page) {
  return page.evaluate(() => {
    const viewportWidth = document.documentElement.clientWidth;
    const overflow = document.documentElement.scrollWidth - viewportWidth;
    const offenders = Array.from(document.querySelectorAll<HTMLElement>("body *"))
      .map((element) => ({ element, rect: element.getBoundingClientRect() }))
      .filter(({ rect }) => rect.right > viewportWidth + 1 || rect.left < -1)
      .sort((a, b) => b.rect.right - a.rect.right)
      .slice(0, 5)
      .map(({ element, rect }) => ({
        tag: element.tagName.toLowerCase(),
        className: element.className,
        text: element.textContent?.trim().slice(0, 100) ?? "",
        left: Math.round(rect.left),
        right: Math.round(rect.right),
        width: Math.round(rect.width),
      }));
    return { overflow, offenders };
  });
}

test.describe("Public page runtime regression", () => {
  test("every public route renders without runtime, network, or layout errors", async ({ page }) => {
    const observer = observeRuntimeIssues(page);

    for (const route of PUBLIC_ROUTES) {
      observer.setRoute(route);
      const response = await page.goto(route, { waitUntil: "domcontentloaded" });
      expect(response?.status(), `${route} document response`).toBeLessThan(400);
      await expect(page.locator("body"), `${route} body`).toBeVisible();
      await page.waitForTimeout(500);

      const report = await horizontalOverflowReport(page);
      expect(
        report.overflow,
        `${route} horizontal overflow\n${JSON.stringify(report.offenders, null, 2)}`
      ).toBeLessThanOrEqual(1);
    }

    expect(observer.issues, observer.issues.join("\n")).toEqual([]);
  });

  test("critical workflows fit a mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const observer = observeRuntimeIssues(page);

    for (const route of MOBILE_CRITICAL_ROUTES) {
      observer.setRoute(route);
      const response = await page.goto(route, { waitUntil: "domcontentloaded" });
      expect(response?.status(), `${route} mobile document response`).toBeLessThan(400);
      await expect(page.locator("body"), `${route} mobile body`).toBeVisible();
      await page.waitForTimeout(500);

      const report = await horizontalOverflowReport(page);
      expect(
        report.overflow,
        `${route} mobile horizontal overflow\n${JSON.stringify(report.offenders, null, 2)}`
      ).toBeLessThanOrEqual(1);
    }

    expect(observer.issues, observer.issues.join("\n")).toEqual([]);
  });
});
