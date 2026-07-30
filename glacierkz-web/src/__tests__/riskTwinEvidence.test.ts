import { describe, expect, it } from "vitest";
import { buildEvidenceIssues, buildEvidenceMapObjects } from "@/lib/riskTwinEvidence";
import type { GlacierRecord, RiskTwinSpatialContext } from "@/lib/api";

const glacier: GlacierRecord = {
  rgi_id: "RGI2000-v7.0-G-13-33843",
  name: "Tsentralniy Tuyuksu Glacier",
  name_ru: "Ледник Центральный Туюксу",
  named: true,
  wgms_reference: true,
  centroid: { latitude: 43.05, longitude: 77.08 },
  rgi_area_km2: 2.4,
  elevation: { min_m: 3400, mean_m: 3800, max_m: 4200 },
  slope_deg: 22,
  aspect_deg: 5,
  maximum_length_m: 3200,
  geometry: {
    type: "Polygon",
    coordinates: [[[77.07, 43.04], [77.08, 43.04], [77.07, 43.04]]],
  },
};

const lakeContext = {
  layers: {
    hma_gli_2015_2018: { type: "FeatureCollection", features: [] },
    tien_shan_lakes: {
      type: "FeatureCollection",
      features: [{
        type: "Feature",
        properties: { lake_id: "TS-001", area_m2: 120000, inventory_year: 2023 },
        geometry: { type: "Point", coordinates: [77.081, 43.051] },
      }],
    },
    historical_glof_events: { type: "FeatureCollection", features: [] },
    hydrorivers: { type: "FeatureCollection", features: [] },
    hydrobasins_level06: { type: "FeatureCollection", features: [] },
  },
  query: { year: 2024, buffer_km: 10, lake_inventory_year: 2023, previous_lake_inventory_year: 2020 },
  impact_assets: {
    available: false,
    planning_radius_km: 10,
    features: { type: "FeatureCollection", features: [] },
    summary: {},
    interpretation: "No local asset extract is available.",
  },
  population_planning_context: { available: false, path: "" },
} as unknown as RiskTwinSpatialContext;

describe("Risk Twin evidence model", () => {
  it("turns only supplied context features into source-aware objects", () => {
    const objects = buildEvidenceMapObjects(glacier, null, null, []);

    expect(objects).toHaveLength(1);
    expect(objects[0]).toMatchObject({
      kind: "glacier",
      name: "Ледник Центральный Туюксу",
      maturity: "inventory_reference",
    });
    expect(objects[0]?.prohibitedClaim).toMatch(/hazard|опас/i);
  });

  it("keeps an unnamed supplied lake identifiable by its source ID", () => {
    const objects = buildEvidenceMapObjects(glacier, null, lakeContext, []);

    expect(objects.find((item) => item.kind === "lake")?.name).toContain("Lake ID: TS-001");
  });

  it("attaches exact local screening measurements to a matching 2023 lake", () => {
    const context = {
      ...lakeContext,
      screening_candidates: [{
        lake_id: "TS-001", inventory_year: 2023, previous_inventory_year: 2020, latitude: 43.051,
        longitude: 77.081,
        area_current_m2: 120000, area_previous_m2: 100000, area_change_percent: 20,
        geometric_match_distance_m: 40,
        distance_to_rgi_boundary_m: 510,
        elevation_m: 3600,
        observation_priority_0_100: 72,
        flags: ["within_1km_of_rgi_boundary"],
        interpretation: "screening only",
      }],
    } as RiskTwinSpatialContext;

    const lake = buildEvidenceMapObjects(glacier, null, context, []).find((item) => item.kind === "lake");

    expect(lake).toMatchObject({
      name: expect.stringContaining("72/100"),
      screening: { rank: 1, distanceToRgiBoundaryM: 510, areaChangePercent: 20 },
    });
    expect(lake?.inspectorFacts).toContainEqual({ label: "До границы RGI", value: "510 м" });
  });

  it("preserves a missing 2020 match instead of turning it into a false zero-percent change", () => {
    const context = {
      ...lakeContext,
      screening_candidates: [{
        lake_id: "TS-001", inventory_year: 2023, previous_inventory_year: 2020, latitude: 43.051, longitude: 77.081,
        area_current_m2: 120000, area_previous_m2: null, area_change_percent: null,
        geometric_match_distance_m: 900, distance_to_rgi_boundary_m: 510, elevation_m: 3600,
        observation_priority_0_100: 72, flags: ["no_reliable_2020_geometric_match"], interpretation: "screening only",
      }],
    } as RiskTwinSpatialContext;

    const lake = buildEvidenceMapObjects(glacier, null, context, []).find((item) => item.kind === "lake");

    expect(lake?.screening?.areaChangePercent).toBeNull();
  });

  it("does not create a population object when local population context is unavailable", () => {
    const objects = buildEvidenceMapObjects(glacier, null, lakeContext, []);

    expect(objects).toHaveLength(2);
  });

  it("distinguishes a NEXT_DOWN route and planning corridor from nearby hydrography", () => {
    const context = {
      ...lakeContext,
      downstream_route: {
        available: true,
        status: "distance_cap_reached",
        route_length_km: 42.5,
        route_segment_count: 3,
        corridor_width_m: 750,
        planning_asset_count: 1,
        interpretation: "Planning route only.",
        features: {
          type: "FeatureCollection",
          features: [{
            type: "Feature",
            properties: {
              hyriv_id: 10,
              next_downstream_id: 11,
              route_sequence: 1,
              relation: "graph_derived_downstream_planning_route",
            },
            geometry: { type: "LineString", coordinates: [[77.08, 43.05], [77.1, 43.0]] },
          }],
        },
        corridor: {
          type: "Feature",
          properties: { width_m: 750 },
          geometry: { type: "Polygon", coordinates: [[[77, 43], [77.2, 43], [77.2, 42.9], [77, 43]]] },
        },
        planning_assets: { type: "FeatureCollection", features: [] },
      },
    } as unknown as RiskTwinSpatialContext;

    const objects = buildEvidenceMapObjects(glacier, null, context, []);
    const route = objects.find((item) => item.kind === "river" && item.isRoute);
    const corridor = objects.find((item) => item.kind === "corridor");

    expect(route?.name).toContain("Route segment 1");
    expect(route?.prohibitedClaim).toMatch(/гидродинамический|warning/i);
    expect(corridor?.visibleFact).toContain("42.5 km");
  });

  it("marks an outlet-data gap as a decision gap rather than a hazard", () => {
    const issues = buildEvidenceIssues([], ["outlet_capacity_fraction"], []);

    expect(issues[0]).toMatchObject({
      id: "gap-outlet_capacity_fraction",
      decisionImpact: "high",
    });
    expect(issues[0]?.title).not.toMatch(/risk score|danger/i);
  });
});
