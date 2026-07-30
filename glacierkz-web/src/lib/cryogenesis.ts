export type CryoGenesisMatchStatus =
  | "matched"
  | "limited_match"
  | "no_valid_counterfactual";

export type CryoGenesisSurpriseClass =
  | "observation_inconclusive"
  | "comparison_inconclusive"
  | "trajectory_consistent"
  | "unexplained_divergence_candidate";

export interface CryoGenesisSourceAsset {
  source_id: string;
  relative_path: string;
  sha256: string;
  size_bytes: number;
}

export interface CryoGenesisTwinMatch {
  rgi_id: string;
  total_distance: number;
  component_distances: Record<string, number>;
  weight: number;
}

export interface CryoGenesisMatch {
  target_rgi_id: string;
  status: CryoGenesisMatchStatus;
  twins: CryoGenesisTwinMatch[];
  rejection_reasons: Record<string, string>;
}

export interface CryoGenesisDivergence {
  target_outcome: number;
  comparator_outcome: number;
  raw_divergence: number;
  standardized_divergence: number | null;
  comparator_interval: [number, number];
  leave_one_out_range: [number, number];
}

export interface DiscoveryPassport {
  schema: "glaciernet-kz.cryogenesis-passport.v1";
  cohort_id: string;
  target_rgi_id: string;
  claim_tier: string;
  match: CryoGenesisMatch;
  divergence: CryoGenesisDivergence | null;
  surprise_class: CryoGenesisSurpriseClass;
  claims_allowed: string[];
  claims_not_allowed: string[];
  provenance: CryoGenesisSourceAsset[];
  payload_sha256: string;
  download_url?: string;
}

export interface CryoGenesisDiscoveryList {
  status: "ready" | "unavailable" | "invalid_artifact";
  items: CryoGenesisDiscoverySummary[];
  count: number;
  invalid_artifact_count: number;
}

export interface CryoGenesisDiscoverySummary {
  schema: "glaciernet-kz.cryogenesis-discovery-summary.v1";
  cohort_id: string;
  target_rgi_id: string;
  claim_tier: string;
  match_status: CryoGenesisMatchStatus;
  twin_count: number;
  surprise_class: CryoGenesisSurpriseClass;
  raw_divergence: number | null;
  payload_sha256: string;
}
