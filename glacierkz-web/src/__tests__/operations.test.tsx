import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import OperationsPage from "@/app/operations/page";
import { I18nProvider, LOCALE_STORAGE_KEY } from "@/lib/I18nProvider";

const overview = vi.hoisted(() => ({
  counts: {
    basins: 1,
    assets: 2,
    observations: 1,
    change_candidates: 1,
    inspection_tasks: 1,
    field_reports: 0,
    evidence_cases: 0,
    decisions: 0,
  },
  observation_queue: [
    {
      id: "candidate-1",
      asset_id: "lake-1",
      change_type: "candidate_area_change",
      magnitude: 0.08,
      uncertainty: 0.6,
      data_quality_gap: 0.3,
      model_disagreement: 0.7,
      expected_information_gain: 0.8,
      domain_shift_status: "review_required",
      priority_score: 0.64,
      next_action: "targeted_field_or_drone_inspection",
      rationale: "Independent model outputs disagree materially.",
      status: "requires_review",
      evidence_tier: "synthetic_demo",
      detected_at: "2026-07-21T00:00:00Z",
    },
  ],
  inspection_tasks: [
    {
      id: "task-1",
      asset_id: "lake-1",
      candidate_id: "candidate-1",
      action_type: "targeted_field_or_drone_inspection",
      priority_score: 0.64,
      rationale: "Independent model outputs disagree materially.",
      status: "queued",
      offline_package_status: "not_built",
    },
  ],
  observations: [
    {
      id: "observation-1",
      asset_id: "lake-1",
      observation_type: "satellite_change_screen",
      observed_at: "2026-07-20T00:00:00Z",
      source: "synthetic Sentinel-2 demonstration",
      values_json: JSON.stringify({ area_change_percent: 8, cloud_percent: 18 }),
      quality_status: "review_required",
      uncertainty: 0.6,
      artifact_sha256: "b".repeat(64),
      created_by: "demo_seed",
      created_at: "2026-07-20T00:00:00Z",
    },
  ],
  field_reports: [],
  assets: [
    {
      id: "lake-1",
      basin_id: "basin-1",
      asset_type: "moraine_lake",
      name: "Demo Lake A (synthetic)",
      latitude: 43.04,
      longitude: 77.27,
      status: "requires_review",
      evidence_tier: "synthetic_demo",
      allowed_use: "workflow demonstration",
      forbidden_use: "hazard inference",
    },
  ],
  evidence_cases: [
    {
      id: "case-1",
      asset_id: "lake-1",
      title: "Synthetic review",
      status: "under_review",
      summary: "Synthetic review.",
      limitations: "No hazard inference.",
      allowed_use: "demonstration",
      forbidden_use: "warning",
      reviewer: "Demo Analyst",
      updated_at: "2026-07-21T00:00:00Z",
    },
  ],
  decisions: [],
  audit_events: [
    {
      sequence: 1,
      entity_type: "assets",
      entity_id: "lake-1",
      action: "created",
      actor: "demo_seed",
      payload_sha256: "c".repeat(64),
      previous_event_sha256: null,
      event_sha256: "d".repeat(64),
      created_at: "2026-07-20T00:00:00Z",
    },
  ],
  audit_chain: { valid: true, events: 5, head_sha256: "a".repeat(64) },
  safety_statement: "Priorities are not hazard probabilities.",
  demo_only: true,
  persistence: "none",
}));

const years = vi.hoisted(() => [
  {
    year: 2000,
    sensor: "Landsat 7",
    source_flag: "local",
    source_file: "data/landsat_2000.tif",
    source_available: true,
    quality_score: 88,
    confidence: "high",
    include_in_strict_trend: true,
    caveat: "",
    primary_method: "ndsi",
    primary_area_km2: 12.4,
    reported_methods: ["ndsi"],
    artifact_methods: ["ndsi"],
    methods: {},
    overlay_url: "/static/predictions/2000/overlay.png",
    provenance_url: "/static/predictions/2000/provenance.json",
    provenance_available: true,
    artifact_status: "ready" as const,
  },
  {
    year: 2024,
    sensor: "Sentinel-2",
    source_flag: "local",
    source_file: "data/sentinel2_2024.tif",
    source_available: true,
    quality_score: 96,
    confidence: "high",
    include_in_strict_trend: true,
    caveat: "Fixed inventory scope.",
    primary_method: "ndsi",
    primary_area_km2: 10.8,
    reported_methods: ["ndsi", "rf", "unet"],
    artifact_methods: ["ndsi", "rf", "unet"],
    methods: {},
    overlay_url: "/static/predictions/2024/overlay.png",
    provenance_url: "/static/predictions/2024/provenance.json",
    provenance_available: true,
    artifact_status: "ready" as const,
  },
]);

vi.mock("@/components/OperationsInventoryMap", () => ({
  default: ({ glaciers }: { glaciers: unknown[] }) => (
    <div role="application" aria-label={`Interactive map with ${glaciers.length} real RGI glacier boundaries`} data-testid="real-inventory-map" />
  ),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchOperationsOverview: vi.fn().mockResolvedValue({
      ...overview,
      counts: { ...overview.counts, assets: 0 },
      assets: [],
      observation_queue: [],
      inspection_tasks: [],
    }),
    fetchOperationsDemo: vi.fn().mockResolvedValue(overview),
    fetchGlaciers: vi.fn().mockResolvedValue({
      total: 1,
      glaciers: [{
        rgi_id: "RGI2000-v7.0-G-13-33843",
        name: "Tsentralniy Tuyuksu Glacier",
        name_ru: "Ледник Центральный Туюксу",
        named: true,
        wgms_reference: true,
        centroid: { longitude: 77.08, latitude: 43.05 },
        rgi_area_km2: 2.4,
        elevation: { min_m: 3400, mean_m: 3800, max_m: 4200 },
        slope_deg: 22,
        aspect_deg: 5,
        maximum_length_m: 3200,
        geometry: { type: "Polygon", coordinates: [] },
      }],
    }),
    fetchYears: vi.fn().mockResolvedValue(years),
    compareLocalYears: vi.fn().mockResolvedValue({
      from: years[0],
      to: years[1],
      change_km2: -1.6,
      change_percent: -12.9,
      comparable_in_strict_trend: true,
      warnings: [],
      method: "decision-ready primary area table",
    }),
  };
});

describe("OperationsPage", () => {
  beforeEach(() => {
    localStorage.setItem(LOCALE_STORAGE_KEY, "en");
  });

  it("renders a fail-closed observation workflow from the safe demo", async () => {
    render(
      <I18nProvider>
        <OperationsPage />
      </I18nProvider>
    );

    expect(
      (await screen.findAllByText("Demo Lake A (synthetic)")).length
    ).toBeGreaterThan(0);
    expect(screen.getByText("Next Best Observation")).toBeInTheDocument();
    expect(
      screen.getByText(/Synthetic shadow-mode demo/)
    ).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Operations navigation" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "What needs attention today" })).toBeInTheDocument();
    expect(await screen.findByTestId("real-inventory-map")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Analysis by year" })).toBeInTheDocument();
    expect(screen.getByText("2000–2024")).toBeInTheDocument();
    expect(screen.getByTestId("year-area-chart")).toBeInTheDocument();
    expect(screen.getByText("What changed")).toBeInTheDocument();
    expect(screen.getByText("Can this be trusted?")).toBeInTheDocument();
    expect(screen.getAllByText(/observation priority/i).length).toBeGreaterThan(0);
    expect(screen.getByText("SHA-256 chain valid")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Before / after" }));
    expect(screen.getByRole("img", { name: /Synthetic difference map/ })).toBeInTheDocument();
    expect(screen.getByText("Model agreement")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Evidence timeline" }));
    expect(screen.getByText("Human review recorded")).toBeInTheDocument();
  });
});
