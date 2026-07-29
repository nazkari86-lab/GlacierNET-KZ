import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/dynamic", () => ({
  default: () => (props: { objects: Array<{ id: string; kind: string; name: string }>; selectedObjectId: string | null; onSelectObject: (id: string) => void }) => {
    const lake = props.objects.find((item) => item.kind === "lake") ?? props.objects[0];
    return <button type="button" data-testid="risk-twin-map-mock" data-selected={props.selectedObjectId ?? ""} onClick={() => lake && props.onSelectObject(lake.id)}>select-map-object</button>;
  },
}));

const fixtures = vi.hoisted(() => ({
  glacier: {
    rgi_id: "RGI2000-v7.0-G-13-33843", name: "Tsentralniy Tuyuksu Glacier", name_ru: "Ледник Центральный Туюксу", named: true, wgms_reference: true,
    centroid: { latitude: 43.05, longitude: 77.08 }, rgi_area_km2: 2.4, elevation: { min_m: 3400, mean_m: 3800, max_m: 4200 }, slope_deg: 22, aspect_deg: 5, maximum_length_m: 3200,
    geometry: { type: "Polygon", coordinates: [[[77.07, 43.04], [77.08, 43.04], [77.07, 43.04]]] },
  },
  context: {
    query: { year: 2024, buffer_km: 10, lake_inventory_year: 2023, previous_lake_inventory_year: 2020 },
    layers: {
      hma_gli_2015_2018: { type: "FeatureCollection", features: [] },
      tien_shan_lakes: { type: "FeatureCollection", features: [
        { type: "Feature", properties: { lake_id: "TS-001", area_m2: 120000, inventory_year: 2023 }, geometry: { type: "Point", coordinates: [77.081, 43.051] } },
        { type: "Feature", properties: { lake_id: "TS-002", area_m2: 36000, inventory_year: 2023 }, geometry: { type: "Point", coordinates: [77.084, 43.054] } },
      ] },
      historical_glof_events: { type: "FeatureCollection", features: [] }, hydrorivers: { type: "FeatureCollection", features: [] }, hydrobasins_level06: { type: "FeatureCollection", features: [] },
    },
    screening_candidates: [
      { lake_id: "TS-001", inventory_year: 2023, previous_inventory_year: 2020, latitude: 43.051, longitude: 77.081, area_current_m2: 120000, area_previous_m2: null, area_change_percent: null, geometric_match_distance_m: 650, distance_to_rgi_boundary_m: 400, elevation_m: 3650, observation_priority_0_100: 82, flags: ["no_reliable_2020_geometric_match"], interpretation: "screening only" },
      { lake_id: "TS-002", inventory_year: 2023, previous_inventory_year: 2020, latitude: 43.054, longitude: 77.084, area_current_m2: 36000, area_previous_m2: 11350, area_change_percent: 217.2, geometric_match_distance_m: 94, distance_to_rgi_boundary_m: 1200, elevation_m: 3670, observation_priority_0_100: 77, flags: ["large_area_change_screening"], interpretation: "screening only" },
    ], lake_timeseries: [], impact_assets: { available: false, planning_radius_km: 10, features: { type: "FeatureCollection", features: [] }, summary: {}, interpretation: "No local asset extract." },
    terrain: { available: false, path: "" }, sentinel1: { available: false, path: "" }, jrc_surface_water: { available: false, path: "" }, climate_context: { available: false, path: "" }, population_planning_context: { available: false, path: "" },
  },
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchGlaciers: vi.fn().mockResolvedValue({ total: 1, glaciers: [fixtures.glacier] }),
    fetchYears: vi.fn().mockResolvedValue([{ year: 2024 }]),
    fetchRiskTwinReadiness: vi.fn().mockResolvedValue({ status: "research_baseline", available: [], blocked: [], safety_statement: "screening evidence only; not an official warning" }),
    fetchYearMapLayer: vi.fn().mockResolvedValue({ year: 2024, method: "ndsi", image_url: "/static/year.png", bounds: [[43, 77], [43.1, 77.1]], source: "local", scope: "test", caveat: "test" }),
    fetchRiskTwinContext: vi.fn().mockResolvedValue(fixtures.context),
    fetchRegionalObservationScan: vi.fn().mockResolvedValue({ inventory_year: 2023, previous_inventory_year: 2020, summary: { scanned_lakes: 2, candidates_with_nearby_rgi: 2, unmatched_previous: 1, large_change_screening: 1 }, candidates: [{ lake_id: "TS-002", inventory_year: 2023, latitude: 43.054, longitude: 77.084, area_current_m2: 36000, previous_inventory_year: 2020, area_previous_m2: 11350, area_change_percent: 217.2, geometric_match_distance_m: 94, distance_to_rgi_boundary_m: 1200, observation_priority_0_100: 77, flags: ["large_area_change_screening"], glacier: { rgi_id: "RGI2000-v7.0-G-13-33843", name: "Tsentralniy Tuyuksu Glacier", name_ru: "Ледник Центральный Туюксу", centroid: { latitude: 43.05, longitude: 77.08 }, rgi_area_km2: 2.4 }, historical_event_count_in_glacier_context: 0, interpretation: "screening only" }], limitations: ["test", "test"] }),
    evaluateRiskTwin: vi.fn(),
  };
});

import RiskTwinPage from "@/app/risk-twin/page";

describe("Risk Twin evidence workspace", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/risk-twin");
    HTMLElement.prototype.scrollIntoView = vi.fn();
  });

  it("connects map selection and an evidence gap to the same inspector and map focus", async () => {
    const user = userEvent.setup();
    render(<RiskTwinPage />);

    await user.click(await screen.findByTestId("risk-twin-map-mock"));
    expect(await screen.findByRole("status")).toHaveTextContent("Озеро TS-001");
    expect(screen.getByText(/инвентарная близость не подтверждает связь с ледником/i)).toBeInTheDocument();
    const canonicalCase = new URLSearchParams(window.location.search);
    expect(canonicalCase.get("rgi")).toBe("RGI2000-v7.0-G-13-33843");
    expect(canonicalCase.get("lake")).toBe("TS-001");
    expect(canonicalCase.get("year")).toBe("2024");
    expect(canonicalCase.get("scope")).toBe("local_inventory");

    await user.click(screen.getByRole("button", { name: /пропускная способность выпуска/i }));
    expect(screen.getByTestId("risk-twin-map-mock")).toHaveAttribute("data-selected", "lake:TS-001");
    expect(screen.getAllByText(/снять геометрию выпуска/i)).toHaveLength(2);
  });

  it("restores a canonical lake case from its URL", async () => {
    window.history.replaceState({}, "", "/risk-twin?rgi=RGI2000-v7.0-G-13-33843&lake=TS-001&year=2024&scope=local_inventory");

    render(<RiskTwinPage />);

    await screen.findByTestId("risk-twin-map-mock");
    await waitFor(() => expect(screen.getByTestId("risk-twin-map-mock")).toHaveAttribute("data-selected", "lake:TS-001"));
  });

  it("keeps the exact regional-scan lake selected instead of falling back to its parent glacier", async () => {
    const user = userEvent.setup();
    render(<RiskTwinPage />);

    await waitFor(() => expect(screen.getByTestId("risk-twin-map-mock")).toHaveAttribute("data-selected", "lake:TS-001"));
    await user.click(await screen.findByRole("button", { name: /Lake TS-002/i }));

    await waitFor(() => expect(new URLSearchParams(window.location.search).get("lake")).toBe("TS-002"));
    expect(screen.getByTestId("risk-twin-map-mock")).toHaveAttribute("data-selected", "lake:TS-002");
    expect(screen.getByText("Что сделать с этим объектом сейчас")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Что этот объект позволяет утверждать сейчас" })).toBeInTheDocument();
    expect(screen.getByText("Наблюдаемый факт")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Перейти к журналу доказательств" })).toHaveAttribute("href", "#evidence-ledger");
  });
});
