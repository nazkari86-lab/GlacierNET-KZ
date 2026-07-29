import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ScientificEvidenceCockpit from "@/components/ScientificEvidenceCockpit";
import type { ScientificEvidence } from "@/lib/api";

const science: ScientificEvidence = {
  schema: "glaciernet-kz.scientific-evidence.v1",
  claim_policy: "Claims are scoped.",
  claim_registry: [
    { id: "C1", status: "supported_silver", claim: "One-AOI silver result", scope: "one AOI", artifacts: [{ path: "results/a.json", exists: true, sha256: "a".repeat(64) }] },
    { id: "C5", status: "blocked_external_evidence", claim: "External generalisation", scope: "Needs labels", artifacts: [{ path: "benchmarks/cross.json", exists: true, sha256: "b".repeat(64) }] },
  ],
  temporal_holdout: {
    evaluation_protocol: "untouched temporal test-year holdout", generalisation_scope: "one AOI", label_quality_tier: "silver", label_provenance: "RGI-derived masks",
    splits: { train_years: [2016, 2022], validation_years: [2023], test_years: [2024] },
    hard_metrics: { hard_dice: 0.87, hard_iou: 0.77, precision: 0.95, recall: 0.8, threshold: 0.2 },
    threshold_calibration: { selection_split: "validation", objective: "test", selected_threshold: 0.2 },
    glacier_level_ci_status: "blocked: glacier_id is absent", boundary_metrics_status: "blocked: geometry needed",
    claims_allowed: ["temporal holdout benchmark"], claims_not_allowed: ["field accuracy"], artifacts: [{ path: "results/temporal.json", exists: true, sha256: "c".repeat(64) }],
  },
  paired_glacier_diagnostic: {
    label_quality_tier: "provisional_silver_rgi", evaluation_status: "post_hoc_non_independent_not_a_holdout", cohort_selection: { n_glaciers: 18 },
    metrics: { hard_iou: { estimate: 0.025, ci_lower: 0.01, ci_upper: 0.04, confidence: 0.95, n_glaciers: 18 } }, paired_tests: {},
    claims_not_allowed: ["gold-label accuracy"], artifacts: [{ path: "benchmarks/paired.json", exists: true, sha256: "d".repeat(64) }],
  },
  external_generalisation: { status: "blocked_external_evidence", test_region: "Zhetysu Alatau", label_quality_tier_required: "gold", blocked_reason: "No labels", artifact: { path: "benchmarks/cross.json", exists: true, sha256: "e".repeat(64) } },
};

describe("ScientificEvidenceCockpit", () => {
  it("renders measured metrics and explicit scientific blocks together", () => {
    render(<ScientificEvidenceCockpit science={science} />);

    expect(screen.getByRole("heading", { name: /Scientific evidence cockpit/i })).toBeInTheDocument();
    expect(screen.getByText(/2016–2022/)).toBeInTheDocument();
    expect(screen.getByText(/Glacier-level CI unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/post-hoc, non-independent/i)).toBeInTheDocument();
    expect(screen.getAllByText(/External generalisation/).length).toBeGreaterThan(0);
    expect(screen.getByText("results/a.json")).toBeInTheDocument();
  });
});
