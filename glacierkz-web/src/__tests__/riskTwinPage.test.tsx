import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

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
    query: { year: 2024, buffer_km: 10 },
    layers: {
      hma_gli_2015_2018: { type: "FeatureCollection", features: [] },
      tien_shan_lakes_2023: { type: "FeatureCollection", features: [{ type: "Feature", properties: { lake_id: "TS-001", area_m2: 120000, inventory_year: 2023 }, geometry: { type: "Point", coordinates: [77.081, 43.051] } }] },
      historical_glof_events: { type: "FeatureCollection", features: [] }, hydrorivers: { type: "FeatureCollection", features: [] }, hydrobasins_level06: { type: "FeatureCollection", features: [] },
    },
    screening_candidates: [], lake_timeseries: [], impact_assets: { available: false, planning_radius_km: 10, features: { type: "FeatureCollection", features: [] }, summary: {}, interpretation: "No local asset extract." },
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
    fetchRegionalObservationScan: vi.fn().mockResolvedValue({ inventory_year: 2023, previous_inventory_year: 2020, summary: { scanned_lakes: 1, candidates_with_nearby_rgi: 1, unmatched_previous: 0, large_change_screening: 0 }, candidates: [], limitations: ["test", "test"] }),
    evaluateRiskTwin: vi.fn(),
  };
});

import RiskTwinPage from "@/app/risk-twin/page";

describe("Risk Twin evidence workspace", () => {
  it("connects map selection and an evidence gap to the same inspector and map focus", async () => {
    const user = userEvent.setup();
    render(<RiskTwinPage />);

    await user.click(await screen.findByTestId("risk-twin-map-mock"));
    expect(await screen.findByRole("status")).toHaveTextContent("Lake ID: TS-001");
    expect(screen.getByText(/инвентарная близость не подтверждает связь с ледником/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /пропускная способность выпуска/i }));
    expect(screen.getByTestId("risk-twin-map-mock")).toHaveAttribute("data-selected", "lake:TS-001");
    expect(screen.getAllByText(/снять геометрию выпуска/i)).toHaveLength(2);
  });
});
