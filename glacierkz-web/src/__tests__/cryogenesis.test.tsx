import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import DiscoveryPassportPanel from "@/components/DiscoveryPassportPanel";
import type { DiscoveryPassport } from "@/lib/cryogenesis";

const passport: DiscoveryPassport = {
  schema: "glaciernet-kz.cryogenesis-passport.v1",
  cohort_id: "ile-2020-2024-v1",
  target_rgi_id: "RGI-A",
  claim_tier: "divergence_measured",
  match: {
    target_rgi_id: "RGI-A",
    status: "matched",
    twins: [
      {
        rgi_id: "RGI-B",
        total_distance: 0.2,
        component_distances: { area_km2: 0.1 },
        weight: 1,
      },
    ],
    rejection_reasons: {},
  },
  divergence: {
    target_outcome: -0.2,
    comparator_outcome: -0.1,
    raw_divergence: -0.1,
    standardized_divergence: -2,
    comparator_interval: [-0.12, -0.08],
    leave_one_out_range: [-0.1, -0.1],
  },
  surprise_class: "unexplained_divergence_candidate",
  claims_allowed: ["retrospective mapped-area comparison"],
  claims_not_allowed: ["causal effect identification"],
  provenance: [],
  payload_sha256: "a".repeat(64),
};

describe("DiscoveryPassportPanel", () => {
  it("shows measured divergence next to the causal boundary", () => {
    render(<DiscoveryPassportPanel passport={passport} />);
    expect(
      screen.getByText(/Unexplained divergence candidate/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/causal effect identification/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/retrospective mapped-area comparison/i),
    ).toBeInTheDocument();
  });
});
