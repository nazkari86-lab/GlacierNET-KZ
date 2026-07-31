"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Database, MapPinned, Mountain, Plus, Radar, RefreshCw, ShieldAlert, Waves } from "lucide-react";
import EvidenceInspector from "@/components/risk-twin/EvidenceInspector";
import EvidenceIssueQueue from "@/components/risk-twin/EvidenceIssueQueue";
import EvidenceRouteRibbon from "@/components/risk-twin/EvidenceRouteRibbon";
import CaseActionPlan from "@/components/risk-twin/CaseActionPlan";
import { parseEvidenceCase, serializeEvidenceCase, type EvidenceCaseRef, type EvidenceSourceScope } from "@/lib/evidenceCase";
import { buildEvidenceIssues, buildEvidenceMapObjects } from "@/lib/riskTwinEvidence";
import {
  evaluateRiskTwin,
  fetchGlaciers,
  fetchMlCase,
  fetchRiskTwinContext,
  fetchRiskTwinReadiness,
  fetchRegionalObservationScan,
  fetchYearMapLayer,
  regionalObservationCandidateKey,
  fetchYears,
  type GlacierRecord,
  type MlEvidenceCase,
  type RiskTwinObservationInput,
  type RiskTwinReadiness,
  type RiskTwinResult,
  type RiskTwinSpatialContext,
  type RegionalObservationScan,
  type YearMapLayer,
} from "@/lib/api";

const RiskTwinMap = dynamic(() => import("@/components/RiskTwinMap"), { ssr: false });
const PRIMARY_RGI_ID = "RGI2000-v7.0-G-13-33843"; // Central Tuyuksu: present in the local study-area subset.
const LAKE_INVENTORY_YEARS = [1990, 2000, 2010, 2020, 2023];

const REQUIRED = [
  "lake_area_m2",
  "water_level_m",
  "freeboard_m",
  "dam_stability_index",
  "outlet_capacity_fraction",
  "channel_capacity_m3_s",
  "exposed_asset_count",
];

const LABELS: Record<string, string> = {
  glacier_area_m2: "Glacier area (m²)",
  lake_area_m2: "Lake area (m²)",
  water_level_m: "Water level (m)",
  freeboard_m: "Freeboard (m)",
  dam_stability_index: "Dam stability index",
  outlet_capacity_fraction: "Outlet capacity fraction",
  channel_capacity_m3_s: "Channel capacity (m³/s)",
  exposed_asset_count: "Exposed asset count",
};

function observationFromGlacier(glacier: GlacierRecord, year: number): RiskTwinObservationInput {
  return {
    observation_id: `rgi-${glacier.rgi_id}-${year}`,
    variable: "glacier_area_m2",
    value: glacier.rgi_area_km2 * 1_000_000,
    uncertainty_std: Math.max(glacier.rgi_area_km2 * 50_000, 1),
    timestamp: `${year}-09-01T00:00:00Z`,
    sensor: "RGI 7.0 inventory geometry",
    quality_flags: ["inventory_reference", "not_a_lake_observation"],
    spatial_support: "glacier_inventory",
  };
}

function distanceKm(latitudeA: number, longitudeA: number, latitudeB: number, longitudeB: number): number {
  const radians = (value: number) => (value * Math.PI) / 180;
  const dLat = radians(latitudeB - latitudeA);
  const dLon = radians(longitudeB - longitudeA);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(radians(latitudeA)) * Math.cos(radians(latitudeB)) * Math.sin(dLon / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export default function RiskTwinPage() {
  const [glaciers, setGlaciers] = useState<GlacierRecord[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [year, setYear] = useState(2024);
  const [years, setYears] = useState<number[]>([]);
  const [yearLayer, setYearLayer] = useState<YearMapLayer | null>(null);
  const [context, setContext] = useState<RiskTwinSpatialContext | null>(null);
  const [regionalScan, setRegionalScan] = useState<RegionalObservationScan | null>(null);
  const [regionalScanError, setRegionalScanError] = useState("");
  const [scanInventoryYear, setScanInventoryYear] = useState(2023);
  const [readiness, setReadiness] = useState<RiskTwinReadiness | null>(null);
  const [observations, setObservations] = useState<RiskTwinObservationInput[]>([]);
  const [result, setResult] = useState<RiskTwinResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ variable: "lake_area_m2", value: "", uncertainty: "", sensor: "Field / remote observation" });
  const [coordinateQuery, setCoordinateQuery] = useState("");
  const [coordinateMessage, setCoordinateMessage] = useState("");
  const [mapMode, setMapMode] = useState<"evidence" | "route" | "people">("evidence");
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);
  const [comparisonYear, setComparisonYear] = useState<number | null>(null);
  const [comparisonLayer, setComparisonLayer] = useState<YearMapLayer | null>(null);
  const [comparisonError, setComparisonError] = useState("");
  const [sourceScope, setSourceScope] = useState<EvidenceSourceScope>("local_inventory");
  const [mlEvidence, setMlEvidence] = useState<MlEvidenceCase | null>(null);

  const selected = useMemo(() => glaciers.find((item) => item.rgi_id === selectedId) ?? null, [glaciers, selectedId]);
  const gaps = result?.state.data_gaps ?? REQUIRED;
  const evidenceObjects = useMemo(() => buildEvidenceMapObjects(selected, yearLayer, context, observations), [context, observations, selected, yearLayer]);
  const evidenceIssues = useMemo(() => buildEvidenceIssues(evidenceObjects, gaps, result?.observation_ranking ?? []), [evidenceObjects, gaps, result]);
  const selectedEvidenceObject = useMemo(() => evidenceObjects.find((item) => item.id === selectedEvidenceId) ?? null, [evidenceObjects, selectedEvidenceId]);
  const selectedEvidenceIssue = useMemo(() => evidenceIssues.find((item) => item.id === selectedIssueId) ?? null, [evidenceIssues, selectedIssueId]);
  const selectedCandidate = useMemo(() => {
    const lakeId = selectedEvidenceObject?.kind === "lake" ? selectedEvidenceObject.id.slice("lake:".length) : null;
    return lakeId ? context?.screening_candidates.find((candidate) => candidate.lake_id === lakeId) ?? null : null;
  }, [context, selectedEvidenceObject]);

  const replaceMapQuery = useCallback((updates: Record<string, string | null>) => {
    const url = new URL(window.location.href);
    for (const [key, value] of Object.entries(updates)) {
      if (value) url.searchParams.set(key, value);
      else url.searchParams.delete(key);
    }
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
  }, []);

  const replaceEvidenceCaseQuery = useCallback((reference: EvidenceCaseRef) => {
    const url = new URL(window.location.href);
    for (const key of ["rgi", "lake", "year", "lake_year", "scope"]) url.searchParams.delete(key);
    const canonical = new URLSearchParams(serializeEvidenceCase(reference));
    canonical.forEach((value, key) => url.searchParams.set(key, value));
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
  }, []);

  const caseForSelection = useCallback((rgiId: string, lakeId?: string, scope = sourceScope, lakeInventoryYear = scanInventoryYear): EvidenceCaseRef => ({
    rgiId,
    ...(lakeId ? { lakeId } : {}),
    year,
    lakeInventoryYear,
    sourceScope: scope,
  }), [scanInventoryYear, sourceScope, year]);

  const selectEvidence = useCallback((id: string) => {
    const object = evidenceObjects.find((item) => item.id === id);
    const lakeId = object?.kind === "lake" ? id.slice("lake:".length) : undefined;
    const scope: EvidenceSourceScope = object?.kind === "annual_segmentation" ? "annual_screening" : "local_inventory";
    setSelectedEvidenceId(id);
    setSelectedIssueId(null);
    setSourceScope(scope);
    replaceMapQuery({ object: id, issue: null });
    if (selectedId) replaceEvidenceCaseQuery(caseForSelection(selectedId, lakeId, scope));
  }, [caseForSelection, evidenceObjects, replaceEvidenceCaseQuery, replaceMapQuery, selectedId]);

  const selectIssue = useCallback((id: string) => {
    const issue = evidenceIssues.find((item) => item.id === id);
    setSelectedIssueId(id);
    setSelectedEvidenceId(issue?.objectId ?? null);
    if (issue?.objectId) {
      const object = evidenceObjects.find((item) => item.id === issue.objectId);
      const lakeId = object?.kind === "lake" ? issue.objectId.slice("lake:".length) : undefined;
      const scope: EvidenceSourceScope = object?.kind === "annual_segmentation" ? "annual_screening" : "local_inventory";
      setSourceScope(scope);
      if (selectedId) replaceEvidenceCaseQuery(caseForSelection(selectedId, lakeId, scope));
    }
    replaceMapQuery({ object: issue?.objectId ?? null, issue: id });
  }, [caseForSelection, evidenceIssues, evidenceObjects, replaceEvidenceCaseQuery, replaceMapQuery, selectedId]);

  useEffect(() => {
    const requestedCase = parseEvidenceCase(window.location.search);
    // The regional scanner can legitimately identify unnamed RGI features, so
    // the selector must include the entire local study-area registry.
    Promise.all([fetchGlaciers("", false, 1000, true), fetchYears(), fetchRiskTwinReadiness()])
      .then(([registry, annual, readinessPayload]) => {
        setGlaciers(registry.glaciers);
        const preferredRgiId = requestedCase && registry.glaciers.some((item) => item.rgi_id === requestedCase.rgiId)
          ? requestedCase.rgiId
          : registry.glaciers.find((item) => item.rgi_id === PRIMARY_RGI_ID)?.rgi_id ?? registry.glaciers[0]?.rgi_id ?? "";
        setSelectedId(preferredRgiId);
        const availableYears = annual.map((item) => item.year).sort((a, b) => a - b);
        setYears(availableYears);
        if (requestedCase?.year && availableYears.includes(requestedCase.year)) setYear(requestedCase.year);
        else if (availableYears.length) setYear(availableYears.at(-1) ?? 2024);
        if (requestedCase?.lakeInventoryYear && LAKE_INVENTORY_YEARS.includes(requestedCase.lakeInventoryYear)) setScanInventoryYear(requestedCase.lakeInventoryYear);
        if (requestedCase) {
          setSourceScope(requestedCase.sourceScope);
          setSelectedEvidenceId(requestedCase.lakeId ? `lake:${requestedCase.lakeId}` : null);
        }
        setReadiness(readinessPayload);
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Risk Twin data could not be loaded"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const mode = params.get("mode");
    const object = params.get("object");
    const issue = params.get("issue");
    const compare = Number(params.get("compare"));
    if (mode === "evidence" || mode === "route" || mode === "people") setMapMode(mode);
    if (object) setSelectedEvidenceId(object);
    if (issue) setSelectedIssueId(issue);
    if (Number.isInteger(compare) && compare > 0) setComparisonYear(compare);
    const mlCase = params.get("ml_case");
    if (mlCase) {
      fetchMlCase(mlCase)
        .then(setMlEvidence)
        .catch((cause) => setError(cause instanceof Error ? cause.message : "ML evidence case could not be loaded"));
    }
  }, []);

  const selectGlacier = useCallback((rgiId: string) => {
    setSelectedId(rgiId);
    setSelectedEvidenceId(null);
    setSelectedIssueId(null);
    setSourceScope("local_inventory");
    replaceMapQuery({ object: null, issue: null });
    replaceEvidenceCaseQuery(caseForSelection(rgiId, undefined, "local_inventory"));
  }, [caseForSelection, replaceEvidenceCaseQuery, replaceMapQuery]);

  /** Open a concrete lake case, not merely the glacier around it.  The URL is
   * shareable and the map/action plan converge on the same object after the
   * asynchronous local context arrives. */
  const openLakeCase = useCallback((rgiId: string, lakeId: string | null, inventoryYear?: number) => {
    const caseInventoryYear = inventoryYear && LAKE_INVENTORY_YEARS.includes(inventoryYear) ? inventoryYear : scanInventoryYear;
    if (caseInventoryYear !== scanInventoryYear) setScanInventoryYear(caseInventoryYear);
    const objectId = lakeId ? `lake:${lakeId}` : null;
    setSelectedId(rgiId);
    setSelectedEvidenceId(objectId);
    setSelectedIssueId(null);
    setSourceScope("local_inventory");
    replaceMapQuery({ object: objectId, issue: null });
    replaceEvidenceCaseQuery(caseForSelection(rgiId, lakeId ?? undefined, "local_inventory", caseInventoryYear));
  }, [caseForSelection, replaceEvidenceCaseQuery, replaceMapQuery, scanInventoryYear]);

  const selectYear = useCallback((nextYear: number) => {
    setYear(nextYear);
    if (selectedId) replaceEvidenceCaseQuery({
      rgiId: selectedId,
      ...(selectedEvidenceObject?.kind === "lake" ? { lakeId: selectedEvidenceObject.id.slice("lake:".length) } : {}),
      year: nextYear,
      sourceScope,
    });
  }, [replaceEvidenceCaseQuery, selectedEvidenceObject, selectedId, sourceScope]);

  useEffect(() => {
    setRegionalScan(null);
    setRegionalScanError("");
    fetchRegionalObservationScan(100, 10, scanInventoryYear).then(setRegionalScan).catch((cause) => setRegionalScanError(cause instanceof Error ? cause.message : "Regional scan could not be loaded"));
  }, [scanInventoryYear]);

  useEffect(() => {
    if (!selected) return;
    setObservations([observationFromGlacier(selected, year)]);
    setResult(null);
  }, [selected, year]);

  useEffect(() => {
    fetchYearMapLayer(year).then(setYearLayer).catch(() => setYearLayer(null));
  }, [year]);

  useEffect(() => {
    if (!comparisonYear || comparisonYear === year) {
      setComparisonLayer(null);
      setComparisonError("");
      return;
    }
    setComparisonError("");
    fetchYearMapLayer(comparisonYear).then(setComparisonLayer).catch(() => {
      setComparisonLayer(null);
      setComparisonError("Сравнение годов недоступно: для выбранного года нет локального проверенного слоя.");
    });
  }, [comparisonYear, year]);

  useEffect(() => {
    // A canonical lake deep link arrives before the asynchronous local context.
    // Do not discard it during that loading window; only clear it after the
    // context has had a chance to provide (or genuinely omit) the feature.
    if (selectedEvidenceId && context && !evidenceObjects.some((item) => item.id === selectedEvidenceId)) {
      setSelectedEvidenceId(null);
    }
    if (selectedIssueId && !evidenceIssues.some((item) => item.id === selectedIssueId)) setSelectedIssueId(null);
  }, [context, evidenceIssues, evidenceObjects, selectedEvidenceId, selectedIssueId]);

  useEffect(() => {
    if (!selected) return;
    setContext(null);
    fetchRiskTwinContext(selected.rgi_id, year, 10, scanInventoryYear).then(setContext).catch((cause) => {
      setContext(null);
      setError(cause instanceof Error ? cause.message : "Local spatial context could not be loaded");
    });
  }, [selected, year, scanInventoryYear]);

  useEffect(() => {
    if (!selected || selectedEvidenceId || !context) return;
    const suggested = context.screening_candidates.find((candidate) => candidate.lake_id);
    if (!suggested?.lake_id) return;
    const objectId = `lake:${suggested.lake_id}`;
    setSelectedEvidenceId(objectId);
    setSelectedIssueId(null);
    setSourceScope("local_inventory");
    replaceMapQuery({ object: objectId, issue: null });
    replaceEvidenceCaseQuery(caseForSelection(selected.rgi_id, suggested.lake_id, "local_inventory", suggested.inventory_year));
  }, [caseForSelection, context, replaceEvidenceCaseQuery, replaceMapQuery, selected, selectedEvidenceId]);

  const addObservation = () => {
    const value = Number(form.value);
    const uncertainty = Number(form.uncertainty);
    if (!Number.isFinite(value) || !Number.isFinite(uncertainty) || uncertainty <= 0) {
      setError("Enter a finite value and a positive uncertainty before adding an observation.");
      return;
    }
    setError("");
    setObservations((items) => [
      ...items.filter((item) => item.variable !== form.variable),
      {
        observation_id: `manual-${form.variable}-${Date.now()}`,
        variable: form.variable,
        value,
        uncertainty_std: uncertainty,
        timestamp: new Date().toISOString(),
        sensor: form.sensor.trim() || "user supplied observation",
        quality_flags: ["user_supplied", "requires_provenance_review"],
        spatial_support: "basin_screening",
      },
    ]);
    setForm((current) => ({ ...current, value: "", uncertainty: "" }));
    setResult(null);
  };

  const evaluate = async () => {
    if (!selected) return;
    setEvaluating(true);
    setError("");
    try {
      const next = await evaluateRiskTwin({
        basin_id: selected.rgi_id,
        observations,
        required_variables: REQUIRED,
        actions: [
          { action_id: "satellite-lake-area", label: "Acquire a clear lake-area scene", target_variables: ["lake_area_m2"], expected_observation_variance: { lake_area_m2: 2500 }, cost: 0.2, latency_hours: 24 },
          { action_id: "field-water-level", label: "Measure water level and freeboard", target_variables: ["water_level_m", "freeboard_m"], expected_observation_variance: { water_level_m: 0.04, freeboard_m: 0.04 }, cost: 1, latency_hours: 48 },
          { action_id: "dam-channel-survey", label: "Survey dam, outlet and channel", target_variables: ["dam_stability_index", "outlet_capacity_fraction", "channel_capacity_m3_s"], expected_observation_variance: { dam_stability_index: 0.03, outlet_capacity_fraction: 0.03, channel_capacity_m3_s: 4 }, cost: 2, latency_hours: 72 },
          { action_id: "exposure-survey", label: "Update downstream exposure inventory", target_variables: ["exposed_asset_count"], expected_observation_variance: { exposed_asset_count: 4 }, cost: 1, latency_hours: 48 },
        ],
        priority_inputs: { current_anomaly: 0.5, potential_consequence: 0.5, staleness: 0.4 },
      });
      setResult(next);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Risk Twin evaluation failed");
    } finally {
      setEvaluating(false);
    }
  };

  const selectByCoordinates = () => {
    const [latitudeText, longitudeText] = coordinateQuery.trim().split(/[\s,;]+/);
    const latitude = Number(latitudeText);
    const longitude = Number(longitudeText);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
      setCoordinateMessage("Введите две координаты: широта, долгота. Например: 43.0512, 77.0814.");
      return;
    }
    const nearest = glaciers.reduce<GlacierRecord | null>((best, glacier) => !best || distanceKm(latitude, longitude, glacier.centroid.latitude, glacier.centroid.longitude) < distanceKm(latitude, longitude, best.centroid.latitude, best.centroid.longitude) ? glacier : best, null);
    if (!nearest) return;
    const distance = distanceKm(latitude, longitude, nearest.centroid.latitude, nearest.centroid.longitude);
    selectGlacier(nearest.rgi_id);
    setCoordinateMessage(`Выбран ближайший RGI-ледник: ${nearest.name_ru || nearest.name} (${distance.toFixed(1)} км от центра контура). Проверьте геометрию на карте.`);
    document.getElementById("risk-twin-map")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <main id="main" className="risk-twin-page min-h-screen px-4 py-5 text-slate-900 sm:px-6 sm:py-8">
      <a href="#main" aria-label="Skip to main content" className="sr-only rounded-lg bg-slate-950 px-4 py-3 text-sm font-semibold text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[1000]">Перейти к рабочей области Risk Twin</a>
      <div className="mx-auto max-w-7xl space-y-5">
        <header className="risk-twin-grid relative overflow-hidden rounded-3xl border border-cyan-100 bg-gradient-to-br from-slate-950 via-cyan-950 to-blue-950 p-6 text-white shadow-[0_28px_90px_-38px_rgba(8,47,73,0.95)] sm:p-9">
          <div className="absolute -right-20 -top-24 h-72 w-72 rounded-full bg-cyan-300/15 blur-3xl" />
          <div className="absolute -bottom-32 left-1/3 h-64 w-64 rounded-full bg-blue-500/15 blur-3xl" />
          <div className="relative">
            <nav aria-label="Risk Twin sections" className="mb-7 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-cyan-100">
              <a href="#risk-twin-workspace" className="inline-flex min-h-11 items-center rounded-full bg-white/10 px-4 py-2 font-medium transition hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">Карта</a>
              <a href="#observation-queue" className="inline-flex min-h-11 items-center rounded-full bg-white/10 px-4 py-2 font-medium transition hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">Очередь наблюдений</a>
              <a href="#evidence-ledger" className="inline-flex min-h-11 items-center rounded-full bg-white/10 px-4 py-2 font-medium transition hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">Evidence ledger</a>
              <Link href="/event-radar" className="inline-flex min-h-11 items-center rounded-full bg-cyan-300/20 px-4 py-2 font-bold text-cyan-50 transition hover:bg-cyan-300/30 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">Live Event Radar</Link>
            </nav>
            <div className="flex flex-wrap items-start justify-between gap-6">
              <div className="max-w-3xl">
                <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-200/25 bg-emerald-300/15 px-3 py-1.5 text-xs font-bold uppercase tracking-[0.12em] text-emerald-100"><CheckCircle2 className="h-4 w-4" />Local evidence workspace</p>
                <h1 className="text-3xl font-black tracking-tight sm:text-5xl">Active Cryosphere<br className="hidden sm:block" /> Risk Twin</h1>
                <p className="mt-4 max-w-2xl text-sm leading-6 text-cyan-50 sm:text-base">Прозрачная рабочая область для исследования ледников: карта объединяет локальные снимки, озёра, гидрографию, климатический каталог и evidence gaps. Она помогает выбрать следующую проверку, но не имитирует официальное предупреждение.</p>
              </div>
              <div className="flex flex-wrap gap-2"><Link href="/event-radar" className="inline-flex min-h-11 items-center rounded-xl bg-cyan-300 px-4 text-sm font-black text-slate-950 shadow-sm transition hover:-translate-y-0.5 hover:bg-cyan-200">Проверить текущие сигналы</Link><Link href="/operations" className="inline-flex min-h-11 items-center rounded-xl border border-white/30 bg-white/10 px-4 text-sm font-semibold shadow-sm transition hover:-translate-y-0.5 hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">Открыть Operations workflow</Link></div>
            </div>
            <div className="mt-7 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-slate-950/25 p-4 backdrop-blur-sm"><p className="text-xs font-semibold uppercase tracking-wider text-cyan-200">Spatial sources</p><p className="mt-1 text-2xl font-bold">9+</p><p className="mt-1 text-xs text-slate-200">RGI, lakes, rivers, basins, JRC, DEM, S1, ERA5, GHSL/OSM</p></div>
              <div className="rounded-2xl border border-white/10 bg-slate-950/25 p-4 backdrop-blur-sm"><p className="text-xs font-semibold uppercase tracking-wider text-cyan-200">Selected context</p><p className="mt-1 text-2xl font-bold">10 km</p><p className="mt-1 text-xs text-slate-200">Explicit proximity window around the RGI geometry</p></div>
              <div className="rounded-2xl border border-amber-200/20 bg-amber-300/10 p-4 backdrop-blur-sm"><p className="text-xs font-semibold uppercase tracking-wider text-amber-100">Claim boundary</p><p className="mt-1 text-sm font-bold leading-5">{readiness?.safety_statement ?? "Screening evidence only; not an official warning."}</p></div>
            </div>
          </div>
        </header>

        {error && <div role="alert" aria-live="assertive" className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-900 shadow-sm">{error}</div>}
        {mlEvidence && (
          <section aria-label="Linked ML evidence" className="grid gap-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm md:grid-cols-[1fr_auto] md:items-center">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-emerald-800">Linked model evidence · {mlEvidence.case_id}</p>
              <h2 className="mt-1 text-lg font-bold">{mlEvidence.glacier.name_ru} · {mlEvidence.year} multimodal boundary</h2>
              <p className="mt-2 text-sm text-emerald-950">
                ML area {mlEvidence.metrics.predicted_area_km2.toFixed(4)} km² · RGI agreement {(mlEvidence.metrics.rgi_overlap_iou * 100).toFixed(1)}% · uncertain review zone {(mlEvidence.metrics.uncertain_fraction_in_review_zone * 100).toFixed(1)}%.
                These values are screening evidence, not an event probability.
              </p>
            </div>
            <Link href={`/ml?case=${encodeURIComponent(mlEvidence.case_id)}`} className="inline-flex min-h-11 items-center justify-center rounded-xl border border-emerald-700 px-4 text-sm font-bold text-emerald-900 hover:bg-white">
              Inspect ML layers
            </Link>
          </section>
        )}
        {loading ? <div className="rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-600 shadow-sm">Загружаем реестр, годовые слои и контекст Risk Twin…</div> : (
          <>
            <section id="risk-twin-workspace" aria-label="Risk Twin workspace controls" className="grid gap-4 rounded-2xl border border-slate-200/80 bg-white/95 p-5 shadow-[0_16px_40px_-26px_rgba(15,23,42,0.45)] backdrop-blur md:grid-cols-4">
              <label htmlFor="risk-twin-glacier" className="text-sm font-bold text-slate-800">Ледник / бассейн
                <select id="risk-twin-glacier" value={selectedId} onChange={(event) => selectGlacier(event.target.value)} className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-medium shadow-sm outline-none transition focus:border-cyan-700 focus:ring-4 focus:ring-cyan-100">
                  {glaciers.map((glacier) => <option key={glacier.rgi_id} value={glacier.rgi_id}>{glacier.name_ru || glacier.name} · {glacier.rgi_id}</option>)}
                </select>
              </label>
              <label htmlFor="risk-twin-year" className="text-sm font-bold text-slate-800">Годовой слой карты
                <select id="risk-twin-year" value={year} onChange={(event) => selectYear(Number(event.target.value))} className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-medium shadow-sm outline-none transition focus:border-cyan-700 focus:ring-4 focus:ring-cyan-100">
                  {years.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </label>
              <div className="text-sm font-bold text-slate-800"><label htmlFor="risk-twin-coordinates">Поиск по координатам</label>
                <div className="mt-2 flex gap-2"><input id="risk-twin-coordinates" value={coordinateQuery} onChange={(event) => setCoordinateQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") selectByCoordinates(); }} placeholder="43.0512, 77.0814" className="min-h-11 w-full rounded-xl border border-slate-300 px-3 text-sm font-normal shadow-sm outline-none transition focus:border-cyan-700 focus:ring-4 focus:ring-cyan-100" /><button type="button" onClick={selectByCoordinates} className="min-h-11 rounded-xl bg-cyan-700 px-4 text-sm font-bold text-white shadow-sm transition hover:bg-cyan-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-700">Найти</button></div>
                {coordinateMessage && <p role="status" aria-live="polite" className="mt-2 text-xs font-normal leading-5 text-cyan-800">{coordinateMessage}</p>}
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm leading-5 text-slate-700"><span className="font-bold text-slate-900">Как читать:</span> выбранные слои показаны в 10-км контексте. Близость не доказывает причинную связь, путь потока или прогноз.</div>
            </section>

            <section aria-label="Risk Twin evidence route" className="rounded-3xl border border-cyan-100 bg-gradient-to-r from-cyan-50 via-white to-blue-50 p-5 shadow-[0_16px_40px_-30px_rgba(8,145,178,0.45)] sm:p-6">
              <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wider text-cyan-800">Real evidence route</p><h2 className="mt-1 text-lg font-semibold">Полный путь Risk Twin для {selected?.name_ru || selected?.name || "выбранного ледника"}</h2></div><p className="max-w-md text-xs text-slate-600">Каждый шаг кликабелен на карте или раскрывается ниже. Красные и жёлтые элементы — необходимость проверки, не прогноз.</p></div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-8">
                <div className="rounded-2xl border border-cyan-100 bg-white p-3 shadow-sm"><MapPinned className="h-5 w-5 text-cyan-700" /><p className="mt-2 text-sm font-semibold">1. RGI ледник</p><p className="mt-1 text-xs text-slate-600">{selected ? `${selected.rgi_area_km2.toFixed(2)} км² inventory area` : "Загрузка…"}</p></div>
                <div className="rounded-xl border border-indigo-100 bg-white p-3"><Radar className="h-5 w-5 text-indigo-700" /><p className="mt-2 text-sm font-semibold">2. {year} сегментация</p><p className="mt-1 text-xs text-slate-600">{mlEvidence ? `multimodal ML · ${(mlEvidence.metrics.rgi_overlap_iou * 100).toFixed(1)}% RGI agreement` : yearLayer ? "локальный raster-слой" : "слой недоступен"}</p></div>
                <div className="rounded-xl border border-blue-100 bg-white p-3"><Waves className="h-5 w-5 text-blue-700" /><p className="mt-2 text-sm font-semibold">3. Озёра рядом</p><p className="mt-1 text-xs text-slate-600">{context ? `${context.layers?.tien_shan_lakes?.features?.length ?? 0} polygons · ${context.query.lake_inventory_year}` : "Загрузка…"}</p></div>
                <div className="rounded-xl border border-red-100 bg-white p-3"><AlertTriangle className="h-5 w-5 text-red-700" /><p className="mt-2 text-sm font-semibold">4. Архив событий</p><p className="mt-1 text-xs text-slate-600">{context ? `${context.layers?.historical_glof_events?.features?.length ?? 0} HMAGLOFDB records` : "Загрузка…"}</p></div>
                <div className="rounded-xl border border-emerald-100 bg-white p-3"><Mountain className="h-5 w-5 text-emerald-700" /><p className="mt-2 text-sm font-semibold">5. Рельеф и S1</p><p className="mt-1 text-xs text-slate-600">DEM + Sentinel‑1 {year}</p></div>
                <div className="rounded-xl border border-cyan-100 bg-white p-3"><Waves className="h-5 w-5 text-cyan-700" /><p className="mt-2 text-sm font-semibold">6. Реки и бассейны</p><p className="mt-1 text-xs text-slate-600">{context ? `${context.layers?.hydrorivers?.features?.length ?? 0} reaches · ${context.layers?.hydrobasins_level06?.features?.length ?? 0} basins` : "Загрузка…"}</p></div>
                <div className="rounded-xl border border-violet-100 bg-white p-3"><Database className="h-5 w-5 text-violet-700" /><p className="mt-2 text-sm font-semibold">7. Люди: context</p><p className="mt-1 text-xs text-slate-600">GHSL + OSM, без «пострадавших»</p></div>
                <div className="rounded-xl border border-teal-100 bg-white p-3"><Radar className="h-5 w-5 text-teal-700" /><p className="mt-2 text-sm font-semibold">8. Water & climate</p><p className="mt-1 text-xs text-slate-600">JRC water + ERA5 catalog</p></div>
                <div className="rounded-xl border border-amber-100 bg-white p-3"><ShieldAlert className="h-5 w-5 text-amber-700" /><p className="mt-2 text-sm font-semibold">9. Чего не знаем</p><p className="mt-1 text-xs text-slate-600">{gaps.length} данных нужны для вывода</p></div>
                <Link href={`/event-radar?rgi=${encodeURIComponent(selected?.rgi_id ?? "")}`} className="rounded-xl border border-orange-100 bg-white p-3 transition hover:border-orange-300 hover:shadow-sm"><Radar className="h-5 w-5 text-orange-700" /><p className="mt-2 text-sm font-semibold">10. Текущие OSINT-сигналы</p><p className="mt-1 text-xs text-slate-600">Источник, расстояние, точное следующее наблюдение</p></Link>
              </div>
            </section>

            <section id="observation-queue" aria-label="Automatic regional observation scan" className="relative overflow-hidden rounded-3xl bg-slate-950 p-5 text-white shadow-[0_24px_60px_-30px_rgba(15,23,42,0.9)] sm:p-6">
              <div className="absolute right-0 top-0 h-48 w-48 rounded-full bg-cyan-400/10 blur-3xl" />
              <div className="relative flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.14em] text-cyan-200">Automatic regional scan</p><h2 className="mt-2 text-xl font-bold">Система сама нашла объекты, которые стоит проверить</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">Выберите год инвентаря озёр: он сравнивается только с предыдущим доступным инвентарём. Год сегментации ледника выше — отдельный слой и не подменяет это сравнение.</p></div><div className="flex items-center gap-3"><label htmlFor="risk-twin-scan-year" className="text-xs font-semibold text-cyan-100">Год инвентаря озёр<select id="risk-twin-scan-year" value={scanInventoryYear} onChange={(event) => setScanInventoryYear(Number(event.target.value))} className="mt-1 block min-h-11 rounded-xl border border-white/20 bg-slate-900 px-3 py-2 text-sm font-bold text-white outline-none focus:border-cyan-200 focus:ring-4 focus:ring-cyan-300/20">{LAKE_INVENTORY_YEARS.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><span className="rounded-full border border-amber-200/20 bg-amber-300/15 px-3 py-1.5 text-xs font-bold text-amber-100">Не карта опасности</span></div></div>
              {regionalScanError ? <p className="mt-4 rounded-lg bg-red-500/20 p-3 text-sm text-red-100">Regional scan unavailable: {regionalScanError}</p> : !regionalScan ? <p className="mt-4 text-sm text-slate-300">Сканирование локальных инвентарей…</p> : <><p className="mt-4 rounded-lg bg-cyan-300/10 p-3 text-sm text-cyan-50">Период сравнения: <strong>{regionalScan.inventory_year}</strong>{regionalScan.previous_inventory_year ? <> против <strong>{regionalScan.previous_inventory_year}</strong></> : " — базовый инвентарь без более раннего сравнения"}.</p><div className="mt-4 grid gap-3 sm:grid-cols-4"><div className="rounded-xl bg-white/10 p-3"><p className="text-xs text-slate-300">Просканировано озёр {regionalScan.inventory_year}</p><p className="mt-1 text-2xl font-bold">{regionalScan.summary.scanned_lakes}</p></div><div className="rounded-xl bg-white/10 p-3"><p className="text-xs text-slate-300">Реальных кандидатов</p><p className="mt-1 text-2xl font-bold">{regionalScan.summary.candidates_with_nearby_rgi}</p></div><div className="rounded-xl bg-white/10 p-3"><p className="text-xs text-slate-300">Крупное изм. площади</p><p className="mt-1 text-2xl font-bold">{regionalScan.summary.large_change_screening}</p></div><div className="rounded-xl bg-white/10 p-3"><p className="text-xs text-slate-300">Без match предыдущего года</p><p className="mt-1 text-2xl font-bold">{regionalScan.summary.unmatched_previous}</p></div></div><div className="mt-4 grid gap-2 lg:grid-cols-2">{regionalScan.candidates.slice(0, 8).map((item) => <button key={regionalObservationCandidateKey(item)} type="button" onClick={() => { openLakeCase(item.glacier.rgi_id, item.lake_id, item.inventory_year); document.getElementById("risk-twin-map")?.scrollIntoView({ behavior: "smooth", block: "start" }); }} className="rounded-xl border border-white/10 bg-white/5 p-3 text-left transition hover:bg-white/10"><div className="flex items-start justify-between gap-3"><div><p className="font-semibold">{item.glacier.name_ru || item.glacier.name}</p><p className="mt-1 text-xs text-slate-300">Lake {item.lake_id ?? "without ID"} · {item.latitude.toFixed(4)}, {item.longitude.toFixed(4)}</p></div><span className="rounded-full bg-cyan-300/20 px-2 py-1 text-xs font-bold text-cyan-100">{item.observation_priority_0_100.toFixed(0)}/100</span></div><p className="mt-2 text-sm text-amber-100">{item.area_change_percent === null ? `Нет надёжного match с ${regionalScan.previous_inventory_year ?? "предыдущим годом"}` : `Изменение площади: ${item.area_change_percent > 0 ? "+" : ""}${item.area_change_percent.toFixed(1)}%`} · до RGI: {item.distance_to_rgi_boundary_m.toFixed(0)} м</p>{item.priority_components && <p className="mt-1 text-xs text-cyan-100">Очередь: изменение +{item.priority_components.area_change.toFixed(0)} · размер +{item.priority_components.lake_size.toFixed(0)} · близость +{item.priority_components.rgi_proximity.toFixed(0)} · нет match +{item.priority_components.no_reliable_previous_match.toFixed(0)}</p>}<p className="mt-1 text-xs text-slate-300">Нажмите, чтобы открыть этот объект на карте и конкретный план проверки.</p></button>)}</div><p className="mt-4 text-xs text-slate-400">{regionalScan.limitations[0]} {regionalScan.limitations[1]}</p></>}
            </section>

            <section className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1.65fr)_minmax(340px,0.85fr)]">
              <div id="risk-twin-map" className="min-w-0 space-y-3 rounded-3xl border border-slate-200/90 bg-white p-4 shadow-[0_20px_50px_-30px_rgba(15,23,42,0.45)] sm:p-5">
                <div className="flex flex-wrap items-end justify-between gap-3"><div className="min-w-0"><p className="text-xs font-bold uppercase tracking-[0.14em] text-cyan-700">Interactive evidence canvas</p><h2 className="mt-1 text-xl font-bold tracking-tight text-slate-950">Карта выбранного ледника</h2><p className="mt-1 max-w-2xl text-sm text-slate-600">На карте показаны все локальные объекты выбранного 10-км контекста. Выбор на карте и в очереди открывает один и тот же проверяемый кейс.</p></div><div className="max-w-full rounded-xl bg-slate-950 px-3 py-2 text-right text-xs text-slate-100"><p className="truncate font-semibold">{selected?.name_ru || selected?.name || "Выберите ледник"}</p><p className="mt-0.5 text-slate-300">{year} сегментация · озёра {scanInventoryYear}{context?.query.previous_lake_inventory_year ? ` → ${context.query.previous_lake_inventory_year}` : ""}</p></div></div>
                <div className="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 sm:grid-cols-[1fr_auto]">
                  <div className="flex flex-wrap gap-2" aria-label="Map modes">
                    {(["evidence", "route", "people"] as const).map((mode) => <button key={mode} type="button" aria-pressed={mapMode === mode} onClick={() => { setMapMode(mode); replaceMapQuery({ mode }); }} className={`min-h-10 rounded-xl border px-3 text-sm font-bold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-700 ${mapMode === mode ? "border-cyan-700 bg-cyan-700 text-white" : "border-slate-300 bg-white text-slate-700 hover:bg-cyan-50"}`}>{mode === "evidence" ? "Доказательства" : mode === "route" ? "Пространственный путь" : "Люди и объекты"}</button>)}
                  </div>
                  <label className="text-sm font-bold text-slate-800">Сравнить с годом
                    <select aria-label="Сравнить карту с годом" value={comparisonYear ?? ""} onChange={(event) => { const next = event.target.value ? Number(event.target.value) : null; setComparisonYear(next); replaceMapQuery({ compare: next ? String(next) : null }); }} className="ml-2 min-h-10 rounded-xl border border-slate-300 bg-white px-3 text-sm font-medium outline-none focus:border-cyan-700 focus:ring-4 focus:ring-cyan-100"><option value="">Без сравнения</option>{years.filter((item) => item !== year).map((item) => <option key={item} value={item}>{item}</option>)}</select>
                  </label>
                </div>
                {comparisonError && <p role="status" aria-live="polite" className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-900">{comparisonError}</p>}
                {!context && <p role="status" aria-live="polite" className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">Локальный пространственный контекст недоступен. Граница RGI и годовой слой остаются доступны.</p>}
                <RiskTwinMap glacier={selected} objects={evidenceObjects} selectedObjectId={selectedEvidenceId} onSelectObject={selectEvidence} mode={mapMode} yearLayer={yearLayer} comparisonLayer={comparisonLayer} mlEvidence={mlEvidence} />
                <EvidenceRouteRibbon objects={evidenceObjects} mode={mapMode} />
              </div>
              <aside className="min-w-0 space-y-4">
                <EvidenceIssueQueue issues={evidenceIssues} selectedId={selectedIssueId} onSelect={selectIssue} />
                <EvidenceInspector object={selectedEvidenceObject} issue={selectedEvidenceIssue} />
                <div id="evidence-ledger" className="rounded-3xl border border-slate-200 bg-white p-5 shadow-[0_20px_50px_-32px_rgba(15,23,42,0.42)]">
                  <p className="text-xs font-bold uppercase tracking-[0.14em] text-cyan-700">Evidence ledger</p><h2 className="mt-1 flex items-center gap-2 text-xl font-bold tracking-tight"><Database className="h-5 w-5 text-cyan-700" />Данные для проверки</h2>
                  <p className="mt-2 text-xs leading-5 text-slate-600">Добавляйте только известные значения. Введённые вручную данные остаются в этом браузере и требуют проверки источника.</p>
                  <div className="mt-4 space-y-2">
                    {observations.map((item) => <div key={item.observation_id} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 p-3 text-sm"><div><strong>{LABELS[item.variable] ?? item.variable}</strong><span className="ml-2 text-slate-600">{item.value.toLocaleString(undefined, { maximumFractionDigits: 2 })} ± {item.uncertainty_std.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span><p className="mt-1 text-xs text-slate-500">Источник: {item.sensor}</p></div><button type="button" aria-label={`Удалить ${LABELS[item.variable] ?? item.variable}`} onClick={() => { setObservations((rows) => rows.filter((row) => row.observation_id !== item.observation_id)); setResult(null); }} className="min-h-11 rounded-lg px-3 text-xs font-medium text-red-700 underline hover:bg-red-50">Удалить</button></div>)}
                  </div>
                  <div className="mt-4 space-y-2 border-t border-slate-200 pt-4">
                    <label htmlFor="risk-twin-observation-variable" className="text-sm font-bold">Добавить измерение</label><select id="risk-twin-observation-variable" value={form.variable} onChange={(e) => setForm({ ...form, variable: e.target.value })} className="min-h-11 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm shadow-sm outline-none focus:border-cyan-700 focus:ring-4 focus:ring-cyan-100">{REQUIRED.map((item) => <option key={item} value={item}>{LABELS[item]}</option>)}</select>
                    <div className="grid grid-cols-2 gap-2"><label className="sr-only" htmlFor="risk-twin-observation-value">Значение наблюдения</label><input id="risk-twin-observation-value" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} inputMode="decimal" placeholder="Значение" className="min-h-11 rounded-xl border border-slate-300 px-3 py-2 text-sm shadow-sm outline-none focus:border-cyan-700 focus:ring-4 focus:ring-cyan-100" /><label className="sr-only" htmlFor="risk-twin-observation-uncertainty">Погрешность наблюдения</label><input id="risk-twin-observation-uncertainty" value={form.uncertainty} onChange={(e) => setForm({ ...form, uncertainty: e.target.value })} inputMode="decimal" placeholder="Погрешность" className="min-h-11 rounded-xl border border-slate-300 px-3 py-2 text-sm shadow-sm outline-none focus:border-cyan-700 focus:ring-4 focus:ring-cyan-100" /></div>
                    <label className="sr-only" htmlFor="risk-twin-observation-source">Источник или метод</label><input id="risk-twin-observation-source" value={form.sensor} onChange={(e) => setForm({ ...form, sensor: e.target.value })} placeholder="Источник или метод" className="min-h-11 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm shadow-sm outline-none focus:border-cyan-700 focus:ring-4 focus:ring-cyan-100" />
                    <button onClick={addObservation} className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-cyan-700 px-3 py-2 text-sm font-bold text-cyan-800 transition hover:bg-cyan-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-700"><Plus className="h-4 w-4" />Добавить в ledger</button>
                  </div>
                  <button onClick={() => void evaluate()} disabled={evaluating || !selected} className="mt-4 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-cyan-700 px-4 py-3 text-sm font-bold text-white shadow-lg shadow-cyan-900/15 transition hover:bg-cyan-800 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-700"><RefreshCw className={`h-4 w-4 ${evaluating ? "animate-spin" : ""}`} />{evaluating ? "Проверяем…" : "Показать пробелы данных"}</button>
                </div>
              </aside>
            </section>

            <CaseActionPlan glacier={selected} candidate={selectedCandidate} object={selectedEvidenceObject} year={year} />

            <section className="grid gap-4 lg:grid-cols-3">
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-5"><h2 className="flex items-center gap-2 font-semibold text-amber-950"><AlertTriangle className="h-5 w-5" />Data gaps ({gaps.length})</h2><ul className="mt-3 space-y-1 text-sm text-amber-900">{gaps.map((gap) => <li key={gap}>• {LABELS[gap] ?? gap}</li>)}</ul></div>
              <div className="rounded-xl bg-white p-5 shadow-sm"><h2 className="font-semibold">Next evidence actions</h2><ol className="mt-3 space-y-2 text-sm">{result?.observation_ranking?.slice(0, 4).map((action) => <li key={action.action_id}><strong>{action.label}</strong>{action.model_based_uncertainty_reduction_fraction !== undefined && <span className="block text-slate-500">Expected uncertainty reduction: {(action.model_based_uncertainty_reduction_fraction * 100).toFixed(0)}%</span>}</li>) ?? <li className="text-slate-500">Evaluate the ledger to rank evidence collection.</li>}</ol></div>
              <div className="rounded-xl bg-white p-5 shadow-sm"><h2 className="font-semibold">Decision status</h2>{result ? <div className="mt-3 text-sm"><p className="flex items-center gap-2 font-medium text-amber-800"><AlertTriangle className="h-4 w-4" />{result.decision_support.abstain ? "Abstaining: evidence is insufficient for a decision claim." : "Screening support available."}</p><p className="mt-3 text-slate-600">Not allowed: {result.claims_not_allowed.join(", ")}.</p></div> : <p className="mt-3 text-sm text-slate-500">No evaluation has been run for this session.</p>}</div>
            </section>

            <section className="grid gap-4 lg:grid-cols-3">
              <div className="rounded-xl bg-white p-5 shadow-sm"><h2 className="font-semibold">Nearby lake inventories</h2><p className="mt-3 text-3xl font-bold text-blue-700">{context?.layers?.tien_shan_lakes?.features?.length ?? "—"}</p><p className="mt-1 text-sm text-slate-600">Полигоны {context?.query.lake_inventory_year ?? scanInventoryYear} внутри 10-км контекста. HMA GLI 2015–2018: {context?.layers?.hma_gli_2015_2018?.features?.length ?? "—"}. Это географическая близость, не подтверждённая связь с ледником.</p></div>
              <div className="rounded-xl bg-white p-5 shadow-sm"><h2 className="font-semibold">Historical records</h2><p className="mt-3 text-3xl font-bold text-red-700">{context?.layers?.historical_glof_events?.features?.length ?? "—"}</p><p className="mt-1 text-sm text-slate-600">HMAGLOFDB records in the spatial context; all remain pending primary-source review.</p></div>
              <div className="rounded-xl bg-white p-5 shadow-sm"><h2 className="font-semibold">Local raster context</h2><dl className="mt-3 space-y-1 text-sm text-slate-700"><div><dt className="inline font-medium">Mean elevation:</dt> <dd className="inline">{context?.terrain.bands?.elevation_m ?? "not available"} m</dd></div><div><dt className="inline font-medium">Mean slope:</dt> <dd className="inline">{context?.terrain.bands?.slope_degrees ?? "not available"}°</dd></div><div><dt className="inline font-medium">Sentinel‑1 VV/VH:</dt> <dd className="inline">{context?.sentinel1.bands ? `${context.sentinel1.bands.VV_x100 ?? "—"} / ${context.sentinel1.bands.VH_x100 ?? "—"}` : "not available"}</dd></div></dl></div>
            </section>

            <section className="grid gap-4 lg:grid-cols-3">
              <div className="rounded-xl border border-cyan-100 bg-cyan-50 p-5"><h2 className="font-semibold text-cyan-950">Hydrographic route</h2>{context?.downstream_route?.available ? <><p className="mt-2 text-3xl font-bold text-cyan-800">{context.downstream_route.route_length_km?.toFixed(1) ?? "—"} км</p><p className="mt-1 text-sm text-cyan-900">{context.downstream_route.route_segment_count} сегментов по реальным связям HydroRIVERS NEXT_DOWN · стартовый reach в {context.downstream_route.start_distance_to_rgi_boundary_m?.toFixed(0) ?? "—"} м от RGI.</p><p className="mt-2 text-sm font-medium text-orange-900">В коридоре проверки: {context.downstream_route.planning_asset_count ?? 0} публичных объектов OSM. Откройте режим «Путь», затем нажмите сегмент или объект.</p><p className="mt-2 text-xs text-cyan-800">{context.downstream_route.interpretation}</p></> : <><p className="mt-2 text-3xl font-bold text-cyan-800">{context?.layers?.hydrorivers?.features?.length ?? "—"}</p><p className="mt-1 text-sm text-cyan-900">Доступен только локальный гидрографический контекст.</p></>}</div>
              <div className="rounded-xl border border-teal-100 bg-teal-50 p-5"><h2 className="font-semibold text-teal-950">JRC surface-water context</h2>{context?.jrc_surface_water.available ? <><p className="mt-2 text-sm text-teal-900">Occurrence: <strong>{context.jrc_surface_water.bands?.occurrence_percent ?? "—"}%</strong> · seasonality: <strong>{context.jrc_surface_water.bands?.seasonality_months ?? "—"} months</strong> · recurrence: <strong>{context.jrc_surface_water.bands?.recurrence_percent ?? "—"}%</strong>.</p><p className="mt-2 text-xs text-teal-800">{context.jrc_surface_water.scope}</p></> : <p className="mt-2 text-sm text-teal-900">Local JRC water artifact unavailable: {context?.jrc_surface_water.reason ?? "loading"}.</p>}</div>
              <div className="rounded-xl border border-sky-100 bg-sky-50 p-5"><h2 className="font-semibold text-sky-950">ERA5-Land catalog</h2>{context?.climate_context.available ? <><p className="mt-2 text-sm text-sky-900">{context.climate_context.years?.[0]}–{context.climate_context.years?.at(-1)} · {context.climate_context.variables?.join(", ")}.</p><p className="mt-2 text-xs text-sky-800">{context.climate_context.interpretation}</p></> : <p className="mt-2 text-sm text-sky-900">Local climate catalog unavailable: {context?.climate_context.reason ?? "loading"}.</p>}</div>
              <div className="rounded-xl border border-cyan-100 bg-cyan-50 p-5"><h2 className="font-semibold text-cyan-950">Physical evidence · CentralAsia-GlacierBench</h2>{context?.benchmark_physical_context?.available ? <div className="mt-2 space-y-2 text-sm text-cyan-950">{context.benchmark_physical_context.itslive_point_sample ? <p>NASA ITS_LIVE: <strong>{context.benchmark_physical_context.itslive_point_sample.velocity_m_per_year_median ?? "—"} m/year median</strong> · p90 {context.benchmark_physical_context.itslive_point_sample.velocity_m_per_year_p90 ?? "—"} · {context.benchmark_physical_context.itslive_point_sample.observations_valid.toLocaleString()} valid image pairs.</p> : <p>ITS_LIVE exact point sample is not materialised for this glacier; matching cloud cubes: {context.benchmark_physical_context.itslive_cloud_coverage.length}.</p>}{context.benchmark_physical_context.oggm && <p>OGGM inventory-based volume: <strong>{context.benchmark_physical_context.oggm.inventory_based_volume_km3?.toFixed(4) ?? "—"} km³</strong>. This is physics-model context, not a field measurement.</p>}<p className="text-xs text-cyan-800">No instability, discharge or event probability is inferred from these values.</p></div> : <p className="mt-2 text-sm text-cyan-900">No exact benchmark physical context is available for the selected RGI object.</p>}</div>
            </section>

            <section className="rounded-xl border border-violet-100 bg-violet-50 p-5"><h2 className="font-semibold text-violet-950">Люди и инфраструктура: planning context</h2>{context?.impact_assets.available ? <><p className="mt-2 text-sm text-violet-900">Публичные OSM-объекты в радиусе {context.impact_assets.planning_radius_km} км: {Object.entries(context.impact_assets.summary).map(([kind, count]) => `${kind}: ${count}`).join(" · ") || "нет объектов в extract"}.</p>{context.population_planning_context.available && <p className="mt-2 text-sm text-violet-900">GHSL modelled population-grid sum в {context.population_planning_context.planning_radius_km} км: <strong>{Math.round(context.population_planning_context.modelled_population_grid_sum ?? 0).toLocaleString()}</strong> (reference year {context.population_planning_context.reference_year}).</p>}<p className="mt-2 text-xs text-violet-800">{context.impact_assets.interpretation} {context.population_planning_context.scope}</p></> : <><p className="mt-2 text-sm text-violet-900">Локальный атрибутированный OSM extract ещё не загружен, поэтому Twin не показывает вымышленные населённые пункты или инфраструктуру.</p><code className="mt-3 block rounded bg-white px-3 py-2 text-xs text-slate-700">python scripts/fetch_osm_critical_assets.py</code></>}</section>

            <section className="rounded-xl bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wider text-cyan-800">Where to inspect next</p><h2 className="mt-1 text-lg font-semibold">Реальные кандидаты для проверки озёр</h2><p className="mt-1 max-w-3xl text-sm text-slate-600">Полигоны озёр {context?.query.lake_inventory_year ?? scanInventoryYear} в 10 км от выбранного ледника: сравнение с {context?.query.previous_lake_inventory_year ?? "более ранним выбранным"} инвентарём, расстояние до RGI-границы и причины приоритета.</p></div><span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">Приоритет наблюдения ≠ риск GLOF</span></div>
              {!context ? <p className="mt-4 text-sm text-slate-500">Загрузка кандидатов…</p> : context.screening_candidates.length === 0 ? <p className="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-600">В текущем 10-км контексте нет полигонов выбранного инвентаря.</p> : <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200"><table className="min-w-[920px] w-full text-left text-sm"><caption className="sr-only">Реальные кандидаты озёр для проверки: площадь, изменение к предыдущему инвентарю, расстояние до RGI и причина приоритета.</caption><thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-600"><tr><th scope="col" className="px-3 py-3">Кандидат</th><th scope="col" className="px-3 py-3">Площадь {context.query.lake_inventory_year}</th><th scope="col" className="px-3 py-3">Изм. к {context.query.previous_lake_inventory_year ?? "—"}</th><th scope="col" className="px-3 py-3">До границы RGI</th><th scope="col" className="px-3 py-3">Почему проверить</th><th scope="col" className="px-3 py-3">Приоритет</th></tr></thead><tbody>{context.screening_candidates.map((item) => <tr key={item.lake_id ?? `${item.latitude}-${item.longitude}`} className="border-b border-slate-100 align-top transition hover:bg-cyan-50/40 focus-within:bg-cyan-50"><td className="px-3 py-3 font-medium"><button type="button" onClick={() => item.lake_id && openLakeCase(selected?.rgi_id ?? "", item.lake_id, item.inventory_year)} className="min-h-11 rounded-lg px-2 text-left underline decoration-cyan-300 underline-offset-4 hover:bg-cyan-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-700">{item.lake_id ?? "ID отсутствует"}</button><span className="mt-1 block text-xs font-normal text-slate-500">{item.latitude.toFixed(4)}, {item.longitude.toFixed(4)} · {item.elevation_m ?? "—"} м</span></td><td className="px-3 py-3">{(item.area_current_m2 / 1_000_000).toFixed(3)} км²</td><td className="px-3 py-3">{item.area_change_percent === null ? <span className="text-amber-700">нет надёжного match</span> : <span className={item.area_change_percent >= 20 ? "font-semibold text-amber-700" : "text-slate-700"}>{item.area_change_percent > 0 ? "+" : ""}{item.area_change_percent.toFixed(1)}%<span className="block text-xs text-slate-500">match {item.geometric_match_distance_m?.toFixed(0)} м</span></span>}</td><td className="px-3 py-3">{item.distance_to_rgi_boundary_m.toFixed(0)} м</td><td className="px-3 py-3"><div className="flex max-w-xs flex-wrap gap-1">{item.flags.map((flag) => <span key={flag} className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">{flag.replaceAll("_", " ")}</span>)}</div></td><td className="px-3 py-3"><span className="rounded-full bg-cyan-100 px-2 py-1 font-semibold text-cyan-900">{item.observation_priority_0_100.toFixed(0)}/100</span></td></tr>)}</tbody></table></div>}
              <p className="mt-4 text-xs text-slate-500">Сопоставление — геометрическая эвристика с порогом 300 м, потому что идентификаторы инвентарей различаются. Изменение площади требует проверки по исходным снимкам; оно не доказывает связь с ледником, состояние морены или вероятность события.</p>
            </section>

            <section className="rounded-xl border border-blue-100 bg-blue-50 p-5 text-sm text-blue-950"><h2 className="font-semibold">Lake-context time series</h2><div className="mt-3 grid grid-cols-5 gap-2">{context?.lake_timeseries.map((point) => <div key={point.year} className="rounded-lg bg-white p-3"><strong>{point.year}</strong><span className="mt-1 block">{point.lake_count} lakes</span><span className="block text-xs text-slate-600">{(point.total_area_m2 / 1_000_000).toFixed(3)} km²</span></div>)}</div><p className="mt-3 text-xs">Counts and areas are inventory summaries within the selected glacier’s spatial buffer. They do not prove that a lake is glacier-connected or quantify its hazard.</p></section>

            <section className="rounded-xl bg-white p-6 shadow-sm"><h2 className="flex items-center gap-2 text-lg font-semibold"><MapPinned className="h-5 w-5 text-cyan-700" />Research capability and boundary</h2><div className="mt-4 grid gap-4 md:grid-cols-2"><div><h3 className="font-medium text-emerald-800">Available now</h3><ul className="mt-2 space-y-1 text-sm text-slate-700">{readiness?.available.map((item) => <li key={item}><CheckCircle2 className="mr-2 inline h-4 w-4 text-emerald-600" />{item}</li>)}</ul></div><div><h3 className="font-medium text-amber-800">Blocked until data/validation exist</h3><ul className="mt-2 space-y-1 text-sm text-slate-700">{readiness?.blocked.map((item) => <li key={item}><AlertTriangle className="mr-2 inline h-4 w-4 text-amber-600" />{item}</li>)}</ul></div></div></section>
          </>
        )}
      </div>
    </main>
  );
}
