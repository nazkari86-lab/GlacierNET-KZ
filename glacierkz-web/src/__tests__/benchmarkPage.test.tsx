import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchCentralAsiaBenchmark: vi.fn().mockResolvedValue({
      schema: "centralasia-glacierbench.report.v2",
      benchmark_name: "CentralAsia-GlacierBench",
      status: "ready",
      summary: {
        sources_total: 1,
        sources_local: 1,
        sources_verified: 1,
        sources_metadata_only: 0,
        sources_missing: 0,
        tracks_total: 1,
        model_evaluations_total: 1,
        model_evaluations_measured: 1,
        reference_evidence_total: 0,
        reference_evidence_available: 0,
        decision_support_evaluations_total: 0,
        decision_support_evaluations_ready: 0,
        tracks_data_ready: 0,
        tracks_blocked: 0,
      },
      sources: [
        {
          id: "rgi",
          title: "RGI 7.0",
          role: "silver geometry",
          citation_url: "https://example.test/rgi",
          license: "data policy",
          evidence_tier: "silver_reference_not_independent_gold",
          state: "verified_local",
          available: true,
          size_bytes: 1024,
          integrity: "computed_without_upstream_digest",
        },
      ],
      tracks: [
        {
          id: "external_transfer",
          title: "Frozen cross-region transfer",
          category: "model_evaluation",
          status: "measured_provisional",
          scope: "untouched replay",
          metrics: {},
          headline_metrics: { candidate_hard_dice: 0.5433, n_external_glaciers: 9 },
          claim_allowed: "frozen provisional external replay",
          claim_not_allowed: "independent external accuracy",
          artifacts: [],
        },
      ],
      claims_not_unlocked: ["independent expert gold-label accuracy"],
    }),
  };
});

import BenchmarkPage from "@/app/benchmark/page";

describe("CentralAsia-GlacierBench page", () => {
  it("shows measured evidence and its claim boundary", async () => {
    render(<BenchmarkPage />);
    expect(await screen.findByText("Frozen cross-region transfer")).toBeInTheDocument();
    expect(screen.getByText("0.5433")).toBeInTheDocument();
    expect(screen.getByText("independent external accuracy")).toBeInTheDocument();
    expect(screen.getByText("RGI 7.0")).toBeInTheDocument();
  });
});
