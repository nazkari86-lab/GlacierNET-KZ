import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/dynamic", () => ({
  default: () => (props: { events: Array<{ id: string }>; onSelect: (id: string) => void }) => (
    <button type="button" data-testid="event-map" onClick={() => props.events[0] && props.onSelect(props.events[0].id)}>
      map · {props.events.length}
    </button>
  ),
}));

const event = vi.hoisted(() => ({
  id: "usgs:test",
  external_id: "test",
  source_id: "usgs_earthquakes",
  source_name: "USGS Earthquake Catalog",
  source_tier: "authoritative_sensor_catalog",
  title: "M 4.2 - Test Range",
  summary: "Catalogued magnitude 4.2 earthquake.",
  url: "https://earthquake.usgs.gov/test",
  published_at: "2026-07-31T08:00:00Z",
  event_type: "earthquake",
  matched_topics: ["earthquake"],
  latitude: 43.1,
  longitude: 77.1,
  location_name: "Test Range",
  geolocation_method: "source_coordinates",
  geolocation_uncertainty_km: null,
  magnitude: 4.2,
  severity_label: null,
  linked_glacier: {
    rgi_id: "RGI-test",
    name: "Test Glacier",
    name_ru: "Тестовый ледник",
    centroid: { latitude: 43.05, longitude: 77.05 },
  },
  distance_to_glacier_km: 7.1,
  link_scope: "near_glacier",
  link_rationale: "Source coordinate is 7.1 km from the selected RGI centroid; inspect local evidence now.",
  evidence_confidence_0_1: 0.91,
  observation_priority_0_100: 84,
  recommended_action: "Inspect the latest cloud-free optical/SAR scene.",
  hazard_probability: null,
  claim_status: "reported_signal_not_validated_hazard",
  content_sha256: "a".repeat(64),
}));

const api = vi.hoisted(() => ({
  fetchOsintEvents: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  api.fetchOsintEvents.mockResolvedValue({
    schema: "glaciernet-kz.osint-radar.v1",
    generated_at: "2026-07-31T08:00:00Z",
    region: { name: "Central Asia", bounds: { minlatitude: 40, maxlatitude: 47.5, minlongitude: 67, maxlongitude: 88 } },
    events: [event],
    source_health: [{ source_id: "usgs_earthquakes", status: "online", items: 1, error: null }],
    summary: { events_total: 1, near_glacier: 1, regional_trigger_context: 0, official_or_authoritative: 1, unresolved: 0 },
    method: {},
    claims_allowed: ["The source reported the event."],
    claims_not_allowed: ["The event caused glacier damage."],
    warnings: [],
    cache: { status: "memory_hit", ttl_seconds: 900 },
    returned: 1,
    matched: 1,
  });
  return {
    ...actual,
    fetchGlaciers: vi.fn().mockResolvedValue({
      glaciers: [{
        rgi_id: "RGI-test", name: "Test Glacier", name_ru: "Тестовый ледник", named: true,
        wgms_reference: false, centroid: { latitude: 43.05, longitude: 77.05 }, rgi_area_km2: 1,
        elevation: { min_m: 3000, mean_m: 3500, max_m: 4000 }, slope_deg: 20, aspect_deg: 5, maximum_length_m: 1000,
      }],
      total: 1,
    }),
    fetchOsintEvents: api.fetchOsintEvents,
    fetchOsintSources: vi.fn().mockResolvedValue({
      schema: "glaciernet-kz.osint-source-catalog.v1",
      sources: [{
        id: "usgs_earthquakes", name: "USGS Earthquake Catalog", tier: "authoritative_sensor_catalog",
        mode: "live_api", url: "https://earthquake.usgs.gov/", license_note: "Attribution",
        role: "Seismic context", configured: true,
      }],
      content_policy: "Metadata and canonical links only.",
    }),
    fetchOsintReadiness: vi.fn().mockResolvedValue({
      schema: "glaciernet-kz.osint-readiness.v1",
      status: "event_radar_ready_hazard_calibration_blocked",
      available: [],
      blocked: ["calibrated event-to-GLOF probability"],
      unlock_requires: [],
      safety_statement: "OSINT is not an official warning.",
    }),
  };
});

import EventRadarPage from "@/app/event-radar/page";

describe("OSINT Event Radar", () => {
  it("shows a source-backed event, object-specific action and claim boundary", async () => {
    render(<EventRadarPage />);

    expect(await screen.findByRole("heading", { name: /Сигнал → конкретный ледник/i })).toBeInTheDocument();
    expect(await screen.findByText("M 4.2 - Test Range")).toBeInTheDocument();
    expect(screen.getByText("7.1 км")).toBeInTheDocument();
    expect(screen.getByText("84/100")).toBeInTheDocument();
    expect(screen.getByText("Inspect the latest cloud-free optical/SAR scene.")).toBeInTheDocument();
    expect(screen.getByText(/hazard_probability = null/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Первоисточник" })).toHaveAttribute("href", event.url);
  });

  it("refreshes live sources explicitly without losing the evidence screen", async () => {
    const user = userEvent.setup();
    render(<EventRadarPage />);
    await screen.findByText("M 4.2 - Test Range");
    await user.click(screen.getByRole("button", { name: "Обновить источники" }));
    await waitFor(() => expect(api.fetchOsintEvents).toHaveBeenCalledWith(expect.objectContaining({ refresh: true })));
    expect(screen.getByText("USGS Earthquake Catalog")).toBeInTheDocument();
  });
});
