import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/dynamic", () => ({
  default: () => () => <div data-testid="ml-evidence-map">map</div>,
}));

const fixture = vi.hoisted(() => ({
  glacier: {
    rgi_id: "RGI2000-v7.0-G-13-33843",
    name: "Tsentralniy Tuyuksu Glacier",
    name_ru: "Ледник Центральный Туюксу",
    named: true,
    wgms_reference: true,
    centroid: { latitude: 43.05, longitude: 77.08 },
    rgi_area_km2: 2.838,
    elevation: { min_m: 3400, mean_m: 3800, max_m: 4200 },
    slope_deg: 22,
    aspect_deg: 5,
    maximum_length_m: 3200,
  },
  readiness: {
    status: "ready",
    recommended_model: "temporal_s2_terrain_s1",
    years: [
      { year: 2016, sentinel2: true, terrain: true, sentinel1: false, compatible_models: ["temporal_s2_terrain"], recommended_model: "temporal_s2_terrain" },
      { year: 2024, sentinel2: true, terrain: true, sentinel1: true, compatible_models: ["temporal_s2_terrain_s1", "temporal_s2_terrain"], recommended_model: "temporal_s2_terrain_s1" },
    ],
    models: [
      {
        name: "temporal_s2_terrain_s1", display_name: "Multimodal U-Net", description: "best", supports_tta: true, supports_crf: false, supports_uncertainty: true,
        available: true, trusted_artifact: true, recommended: true, benchmark: { test_years: [2024], hard_dice: 0.903, hard_iou: 0.823, label_quality_tier: "silver" },
      },
      {
        name: "temporal_s2_terrain", display_name: "Temporal U-Net", description: "broad", supports_tta: true, supports_crf: false, supports_uncertainty: true,
        available: true, trusted_artifact: true, benchmark: { test_years: [2024], hard_dice: 0.88, hard_iou: 0.79, label_quality_tier: "silver" },
      },
    ],
    training_dataset: {
      status: "ready",
      dataset_id: "enhanced_provisional_spatial_holdout",
      schema: "glaciernet-kz.enhanced-provisional-training.v1",
      annotation_status: "provisional_not_gold",
      dataset_role: "machine_assisted_training_only_not_gold_benchmark",
      split_strategy: "glacier_group_spatial_holdout",
      channel_count: 11,
      patch_size: 256,
      eligible_tasks: 25,
      patch_count: 45,
      storage_bytes: 74_000_000,
      minimum_geometry_coverage: 1,
      excluded_tasks: {
        total: 29,
        by_confidence: { medium_provisional: 16, low_provisional: 13 },
        handling: "retained in active-review queue",
      },
      splits: {
        train: { patch_count: 33, glacier_count: 5, glaciers: ["RGI2000-v7.0-G-13-33843"], years: [2022, 2023, 2024] },
        val: { patch_count: 6, glacier_count: 2, glaciers: [], years: [2022, 2023, 2024] },
        test: { patch_count: 6, glacier_count: 2, glaciers: [], years: [2022, 2023, 2024] },
      },
      membership: { "RGI2000-v7.0-G-13-33843": "train" },
      review_queue: [
        {
          glacier_id: "RGI2000-v7.0-G-13-33843",
          year: 2022,
          confidence: "low_provisional",
          quality_score: 10,
          review_priority: 100,
          flags: ["empty_candidate"],
          next_action: "Inspect the source composite and redraw the glacier candidate.",
        },
      ],
      spatial_evaluation: {
        status: "completed_provisional_not_gold",
        epochs_requested: 40,
        epochs_completed: 13,
        glacier_counts: { train: 5, val: 2, test: 2 },
        baseline_test: { hard_dice: 0.6827, hard_iou: 0.5182 },
        candidate_test: { hard_dice: 0.6932, hard_iou: 0.5305 },
        candidate_minus_baseline_hard_iou: 0.0123,
        model_artifact_present: true,
      },
      preview_url: "/api/ml/training-dataset/preview",
      manifest_url: "/api/ml/training-dataset",
      training_command: "python -m src.train --patches-dir data/processed/patches/enhanced_provisional_spatial_holdout",
      limitations: ["not independently adjudicated gold"],
    },
    workflow: [],
    interpretation: "screening",
  },
  evidence: {
    schema: "glaciernet-kz.ml-case.v1",
    case_id: "e855ed7d973b159ff4fb",
    created_at: "2026-07-29T00:00:00Z",
    glacier: null as unknown,
    year: 2024,
    model: { name: "temporal_s2_terrain_s1", display_name: "Multimodal U-Net", description: "best", supports_tta: true, supports_crf: false, supports_uncertainty: true },
    inference: { variant: "flip_tta_4", use_tta: true, decision_threshold: 0.5, duration_seconds: 23.5, window_shape: [512, 512], context_m: 400, feature_schema: Array(16).fill("band") },
    source: { sentinel2_file: "sentinel2_2024.tif", sentinel2_size_bytes: 1, source_crop_sha256: "a".repeat(64), terrain_file: "terrain.tif", sentinel1_file: "s1.tif" },
    metrics: { predicted_area_km2: 2.6063, rgi_rasterized_area_km2: 2.8666, area_delta_percent: -9.08, rgi_overlap_iou: 0.8239, mean_probability_in_selected_component: 0.9349, uncertain_fraction_in_review_zone: 0.0679, mean_boundary_entropy_nats: 0.5223, review_priority_0_100: 31 },
    map: { bounds: [[43.02, 77.04], [43.07, 77.11]], rgi_geometry: { type: "Polygon", coordinates: [] }, model_geometry: { type: "Polygon", coordinates: [] } },
    artifacts: { selected_mask_url: "/mask.tif", probability_url: "/prob.tif", entropy_url: "/entropy.tif", boundary_url: "/boundary.geojson", manifest_url: "/manifest.json" },
    review: { status: "expert_review_required", next_action: "Inspect high-entropy boundary sectors.", risk_twin_url: "/risk-twin?ml_case=e855ed7d973b159ff4fb" },
    claims_allowed: ["model-screened glacier boundary"],
    claims_not_allowed: ["independent expert accuracy"],
    warnings: [],
    cache: { hit: false, case_id: "e855ed7d973b159ff4fb" },
  },
}));

const apiMocks = vi.hoisted(() => ({
  analyzeMlGlacier: vi.fn(),
  fetchMlCase: vi.fn(),
  verifyMlTrainingDataset: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchMlReadiness: vi.fn().mockResolvedValue(fixture.readiness),
    fetchGlaciers: vi.fn().mockResolvedValue({ total: 1, glaciers: [fixture.glacier] }),
    analyzeMlGlacier: apiMocks.analyzeMlGlacier,
    fetchMlCase: apiMocks.fetchMlCase,
    verifyMlTrainingDataset: apiMocks.verifyMlTrainingDataset,
  };
});

import MlWorkspacePage from "@/app/ml/page";

describe("ML Workspace", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/ml");
    apiMocks.analyzeMlGlacier.mockReset();
    apiMocks.fetchMlCase.mockReset();
    apiMocks.verifyMlTrainingDataset.mockReset();
    fixture.evidence.glacier = fixture.glacier;
  });

  it("makes glacier-first inference the primary workflow", async () => {
    render(<MlWorkspacePage />);

    expect(await screen.findByRole("heading", { name: /От спутникового композита/i })).toBeInTheDocument();
    expect(screen.getByLabelText("Glacier")).toHaveValue(fixture.glacier.rgi_id);
    expect(screen.getByRole("button", { name: "2024" })).toBeInTheDocument();
    expect(screen.getByText(/16-channel inference/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Leakage-safe weighted annotations/i })).toBeInTheDocument();
    expect(screen.getByText("45")).toBeInTheDocument();
    expect(screen.getByText(/Training dataset role: TRAIN/i)).toBeInTheDocument();
    expect(screen.getByAltText(/pixel reliability maps/i)).toHaveAttribute(
      "src",
      expect.stringContaining("/api/ml/training-dataset/preview")
    );
    expect(screen.getByText(/Real weighted training command/i)).toBeInTheDocument();
  });

  it("renders map, diagnostics and Risk Twin handoff after real-case response", async () => {
    apiMocks.analyzeMlGlacier.mockResolvedValue(fixture.evidence);
    const user = userEvent.setup();
    render(<MlWorkspacePage />);

    await user.click(await screen.findByRole("button", { name: /Analyze glacier/i }));
    await waitFor(() => expect(apiMocks.analyzeMlGlacier).toHaveBeenCalledWith(
      fixture.glacier.rgi_id,
      expect.objectContaining({ year: 2024, model_name: "temporal_s2_terrain_s1", use_tta: true })
    ));
    expect(await screen.findByTestId("ml-evidence-map")).toBeInTheDocument();
    expect(screen.getByText("2.6063 km²")).toBeInTheDocument();
    expect(screen.getByText("82.4%")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open same case in Risk Twin/i })).toHaveAttribute(
      "href",
      fixture.evidence.review.risk_twin_url
    );
    expect(new URLSearchParams(window.location.search).get("case")).toBe(fixture.evidence.case_id);
  });

  it("runs a real weighted pipeline check and labels it as compatibility evidence", async () => {
    apiMocks.verifyMlTrainingDataset.mockResolvedValue({
      schema: "glaciernet-kz.weighted-training-check.v1",
      status: "verified",
      created_at: "2026-07-30T00:00:00Z",
      dataset_id: "enhanced_provisional_spatial_holdout",
      dataset_manifest_sha256: "a".repeat(64),
      purpose: "Pipeline compatibility check; one batch is not model training or accuracy evidence.",
      architecture: "unet",
      batch: {
        features: [1, 256, 256, 11],
        labels: [1, 256, 256, 1],
        weights: [1, 256, 256],
        weight_min: 0,
        weight_max: 0.97,
        nonzero_weight_fraction: 0.99,
      },
      metrics: { loss: 0.33 },
      runtime: { duration_seconds: 7.2, tensorflow: "2.13.0", python: "3.10", devices: ["CPU"] },
      claims_allowed: ["weighted optimization step"],
      claims_not_allowed: ["accuracy"],
      cache: { hit: true },
    });
    const user = userEvent.setup();
    render(<MlWorkspacePage />);

    await user.click(await screen.findByRole("button", { name: /Verify weighted pipeline/i }));

    await waitFor(() => expect(apiMocks.verifyMlTrainingDataset).toHaveBeenCalledWith(false));
    expect(screen.getByText(/Verified · cache/i)).toBeInTheDocument();
    expect(screen.getByText(/7.20 s · TF 2.13.0/i)).toBeInTheDocument();
    expect(screen.getByText("1×256×256×11")).toBeInTheDocument();
    expect(screen.getByText(/not model accuracy/i)).toBeInTheDocument();
  });
});
