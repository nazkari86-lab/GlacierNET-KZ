export const EVIDENCE_SOURCE_SCOPES = ["local_inventory", "annual_screening", "archive_context", "planning_context"] as const;
export type EvidenceSourceScope = typeof EVIDENCE_SOURCE_SCOPES[number];

export interface EvidenceCaseRef {
  rgiId: string;
  lakeId?: string;
  year?: number;
  sourceScope: EvidenceSourceScope;
}

export function isKnownSourceScope(value: string | null): value is EvidenceSourceScope {
  return value !== null && (EVIDENCE_SOURCE_SCOPES as readonly string[]).includes(value);
}

export function parseEvidenceCase(search: string | URLSearchParams): EvidenceCaseRef | null {
  const params = typeof search === "string" ? new URLSearchParams(search.startsWith("?") ? search.slice(1) : search) : search;
  const rgiId = params.get("rgi")?.trim();
  const lakeId = params.get("lake")?.trim();
  const scope = params.get("scope") ?? "local_inventory";
  const yearValue = params.get("year");
  if (!rgiId || !isKnownSourceScope(scope)) return null;
  const year = yearValue === null ? undefined : Number(yearValue);
  if (year !== undefined && (!Number.isInteger(year) || year < 1900 || year > 2100)) return null;
  return { rgiId, ...(lakeId ? { lakeId } : {}), ...(year !== undefined ? { year } : {}), sourceScope: scope };
}

export function serializeEvidenceCase(reference: EvidenceCaseRef): string {
  const params = new URLSearchParams({ rgi: reference.rgiId, scope: reference.sourceScope });
  if (reference.lakeId) params.set("lake", reference.lakeId);
  if (reference.year !== undefined) params.set("year", String(reference.year));
  return params.toString();
}

export function riskTwinHref(reference: EvidenceCaseRef): string {
  return `/risk-twin?${serializeEvidenceCase(reference)}`;
}
