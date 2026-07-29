import { describe, expect, it } from "vitest";
import { buildCaseActionPlan, buildSelectedObjectAdvice } from "@/lib/caseActionPlan";
import type { EvidenceMapObject } from "@/lib/riskTwinEvidence";
import type { GlacierRecord, RiskTwinSpatialContext } from "@/lib/api";

const glacier: GlacierRecord = {
  rgi_id: "RGI2000-v7.0-G-13-33843", name: "Tuyuksu", name_ru: "Ледник Туюксу", named: true, wgms_reference: true,
  centroid: { latitude: 43.05, longitude: 77.08 }, rgi_area_km2: 2.4,
  elevation: { min_m: 3400, mean_m: 3800, max_m: 4200 }, slope_deg: 22, aspect_deg: 5, maximum_length_m: 3200,
};

const candidate: RiskTwinSpatialContext["screening_candidates"][number] = {
  lake_id: "GL43055541E77098579N", inventory_year: 2023, previous_inventory_year: 2020, latitude: 43.055541, longitude: 77.09858,
  area_current_m2: 118123.2, area_previous_m2: null, area_change_percent: null,
  geometric_match_distance_m: 2218.1, distance_to_rgi_boundary_m: 511.6, elevation_m: 3639,
  observation_priority_0_100: 80, flags: ["no_reliable_2020_geometric_match", "within_1km_of_rgi_boundary"], interpretation: "screening only",
};

describe("case action plan", () => {
  it("turns a missing geometric match into a concrete validation task instead of a zero-percent trend", () => {
    const plan = buildCaseActionPlan(glacier, candidate, 2024);

    expect(plan.facts.find((fact) => fact.label === "К 2020")?.value).toMatch(/не установлено/);
    expect(plan.actions.satellite[0]).toMatchObject({ title: "Создать подтверждённую пару контуров" });
    expect(plan.actions.satellite[0]?.blockedClaim).toMatch(/нельзя заявлять рост/);
  });

  it("keeps field and decision work bounded by concrete acceptance criteria", () => {
    const plan = buildCaseActionPlan(glacier, candidate, 2024);

    expect(plan.actions.field[0]?.acceptance).toMatch(/неопределённость/);
    expect(plan.actions.decision[0]?.blockedClaim).toMatch(/GLOF-предупреждение/);
    expect(plan.caseId).toContain(candidate.lake_id!);
  });

  it("explains why this exact lake was selected before listing the whole workflow", () => {
    const plan = buildCaseActionPlan(glacier, candidate, 2024);

    expect(plan.focus.headline).toBe("Создать подтверждённую пару контуров");
    expect(plan.focus.reasons.join(" ")).toMatch(/2218/);
    expect(plan.focus.reasons.join(" ")).toMatch(/80\/100/);
    expect(plan.focus.nextStep.acceptance).toMatch(/match ≤300 м/);
    expect(plan.decisionGates.find((gate) => gate.label === "Изменение площади 2020–2023")).toMatchObject({ status: "blocked" });
    expect(plan.decisionGates.find((gate) => gate.label === "Последствия для людей и инфраструктуры")?.detail).toMatch(/модель распространения/);
  });

  it("still gives a bounded, object-specific next step for a raw map object", () => {
    const lake: EvidenceMapObject = {
      id: "lake:inventory-only",
      kind: "lake",
      name: "Lake ID: inventory-only",
      geometry: { type: "Point", coordinates: [77.1, 43.05] } as GeoJSON.Point,
      source: "Tien Shan lake inventory 2023",
      temporalCoverage: "2023 inventory",
      maturity: "spatial_context",
      visibleFact: "Inventory contour available.",
      allowedClaim: "The inventory contour can be shown.",
      prohibitedClaim: "The contour does not prove a hazard.",
      inspectorFacts: [{ label: "Площадь 2023", value: "118123 м²" }],
    };

    const advice = buildSelectedObjectAdvice(lake, 2024);

    expect(advice.title).toMatch(/инвентарный контур/);
    expect(advice.nextStep.instruction).toMatch(/исходную сцену/);
    expect(advice.nextStep.blockedClaim).toMatch(/нельзя делать выводы/);
    expect(advice.guardrails.join(" ")).toMatch(/официальным предупреждением/);
  });
});
