import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchIntegratedRiskTwinCase } from "@/lib/api";

describe("integrated Risk Twin API client", () => {
  afterEach(() => vi.restoreAllMocks());

  it("requests opt-in ML and normalizes the nested spatial context", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      schema: "glaciernet-kz.integrated-risk-twin-case.v1",
      query: { rgi_id: "RGI-test", year: 2024, lake_inventory_year: 2023, lake_id: "GL-test" },
      context: {
        query: { year: 2024, buffer_km: 10, lake_inventory_year: 2023, previous_lake_inventory_year: 2020 },
        layers: {}, screening_candidates: [], lake_timeseries: [],
        downstream_route: { available: false, status: "not_available" },
      },
      selected_candidate: null,
      ml_evidence: null,
      ml_status_reason: null,
      decision: { workflow_priority_0_100: 50, priority_formula: "max", lake_observation_priority_0_100: 50, ml_boundary_review_priority_0_100: null, driver: "missing_ml_evidence", title: "Run ML", next_action: "Run ML", ml_changed_next_action: false, meaning: "not hazard", gate: { status: "not_available", usable_for_boundary_screening: false, usable_for_temporal_change: false, reasons: ["missing"] } },
      evidence_route: [], claims_allowed: [], claims_not_allowed: [],
    }), { status: 200 }));

    const result = await fetchIntegratedRiskTwinCase("RGI-test", { lakeId: "GL-test", runMlIfMissing: true });

    expect(result.context.layers.tien_shan_lakes.features).toEqual([]);
    expect(result.context.downstream_route.features.features).toEqual([]);
    const request = fetchMock.mock.calls[0][1] as RequestInit;
    expect(JSON.parse(String(request.body))).toMatchObject({ lake_id: "GL-test", run_ml_if_missing: true, year: 2024 });
  });
});
