import { expect, test } from "@playwright/test";

test.describe("Source-backed Event Radar", () => {
  test("links a real-format event to a selected glacier without inventing hazard probability", async ({ page }) => {
    await page.route("**/api/osint/events?*", async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          schema: "glaciernet-kz.osint-radar.v1",
          generated_at: "2026-07-31T08:00:00Z",
          region: { name: "Central Asia", bounds: { minlatitude: 40, maxlatitude: 47.5, minlongitude: 67, maxlongitude: 88 } },
          events: [{
            id: "usgs:test", external_id: "test", source_id: "usgs_earthquakes",
            source_name: "USGS Earthquake Catalog", source_tier: "authoritative_sensor_catalog",
            title: "M 4.2 - Test Range", summary: "Catalogued magnitude 4.2 earthquake.",
            url: "https://earthquake.usgs.gov/test", published_at: "2026-07-31T08:00:00Z",
            event_type: "earthquake", matched_topics: ["earthquake"], latitude: 43.1, longitude: 77.1,
            location_name: "Test Range", geolocation_method: "source_coordinates",
            geolocation_uncertainty_km: null, magnitude: 4.2, severity_label: null,
            linked_glacier: { rgi_id: "RGI-test", name: "Test Glacier", name_ru: "Тестовый ледник", centroid: { latitude: 43.05, longitude: 77.05 } },
            distance_to_glacier_km: 7.1, link_scope: "near_glacier",
            link_rationale: "Source coordinate is 7.1 km from the selected RGI centroid; inspect local evidence now.",
            evidence_confidence_0_1: 0.91, observation_priority_0_100: 84,
            recommended_action: "Inspect the latest cloud-free optical/SAR scene.",
            hazard_probability: null, claim_status: "reported_signal_not_validated_hazard",
            content_sha256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          }],
          source_health: [{ source_id: "usgs_earthquakes", status: "online", items: 1, error: null }],
          summary: { events_total: 1, near_glacier: 1, regional_trigger_context: 0, official_or_authoritative: 1, unresolved: 0 },
          method: {}, claims_allowed: [], claims_not_allowed: ["The event caused glacier damage."],
          warnings: [], cache: { status: "memory_hit", ttl_seconds: 900 }, returned: 1, matched: 1,
        }),
      });
    });
    await page.route("**/api/osint/sources", async (route) => {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify({ schema: "v1", sources: [], content_policy: "Metadata only." }) });
    });
    await page.route("**/api/osint/readiness", async (route) => {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify({ schema: "v1", status: "ready", available: [], blocked: [], unlock_requires: [], safety_statement: "Not an official warning." }) });
    });

    await page.goto("/event-radar");
    await expect(page.getByRole("heading", { name: /Сигнал → конкретный ледник/i })).toBeVisible();
    await expect(page.getByText("M 4.2 - Test Range")).toBeVisible();
    await expect(page.getByText("7.1 км")).toBeVisible();
    await expect(page.getByText("84/100")).toBeVisible();
    await expect(page.getByText(/hazard_probability = null/i)).toBeVisible();
    await expect(page.getByRole("link", { name: "Первоисточник" })).toHaveAttribute("href", "https://earthquake.usgs.gov/test");
  });
});
