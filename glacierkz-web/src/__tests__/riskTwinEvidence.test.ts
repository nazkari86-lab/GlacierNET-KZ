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
    tien_shan_lakes_2023: {
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

  it("does not create a population object when local population context is unavailable", () => {
    const objects = buildEvidenceMapObjects(glacier, null, lakeContext, []);

    expect(objects).toHaveLength(2);
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
