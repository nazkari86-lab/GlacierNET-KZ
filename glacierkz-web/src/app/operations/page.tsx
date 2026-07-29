"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ClipboardCheck,
  Database,
  Download,
  Eye,
  FileCheck2,
  FlaskConical,
  Layers3,
  Map,
  RefreshCw,
  Satellite,
  Save,
  Search,
  ShieldCheck,
  WifiOff,
} from "lucide-react";
import {
  createFieldReport,
  createInspectionTask,
  fetchGlaciers,
  fetchOperationsOverview,
  fetchRegionalObservationScan,
  regionalObservationCandidateKey,
  type ChangeCandidate,
  type FieldReportInput,
  type GlacierRecord,
  type OperationsAsset,
  type OperationsObservation,
  type OperationsOverview,
  type RegionalObservationScan,
} from "@/lib/api";
import { riskTwinHref } from "@/lib/evidenceCase";
import { useI18n } from "@/lib/I18nProvider";

const OperationsInventoryMap = dynamic(() => import("@/components/OperationsInventoryMap"), { ssr: false });
const OperationsYearAnalysis = dynamic(() => import("@/components/OperationsYearAnalysis"), { ssr: false });

type DetailMode = "summary" | "compare" | "evidence" | "science";

const copy = {
  en: {
    title: "GlacierNET Operations",
    region: "Ile Alatau",
    attention: "What needs attention today",
    review: "Require review",
    insufficient: "Insufficient data",
    observations: "New observations",
    reviewed: "Human-reviewed cases",
    priorities: "Ranked observation queue",
    map: "Operational map",
    selected: "Selected object",
    change: "What changed",
    trust: "Can this be trusted?",
    why: "Why it was flagged",
    next: "What to do next",
    quality: "Observation quality",
    summary: "Decision brief",
    compare: "Before / after",
    evidence: "Evidence timeline",
    science: "Scientific details",
    assets: "Objects",
    inspections: "Inspections",
    reports: "Reports",
    monitor: "Monitor",
    overview: "Overview",
    research: "Research",
    save: "Save offline draft",
    saved: "Draft saved on this device",
    export: "Export audit snapshot",
    refresh: "Refresh",
    noData: "No operational records yet.",
    safety: "Priorities select observations. They are not event probabilities or official warnings.",
    strict: "Comparable observations only",
    all: "Show all observations",
    explain: "Why is this flagged?",
  },
  ru: {
    title: "GlacierNET Operations",
    region: "Иле Алатау",
    attention: "Что требует внимания сегодня",
    review: "Требуют проверки",
    insufficient: "Недостаточно данных",
    observations: "Новые наблюдения",
    reviewed: "Проверено человеком",
    priorities: "Очередь наблюдений",
    map: "Операционная карта",
    selected: "Выбранный объект",
    change: "Что изменилось",
    trust: "Насколько можно доверять",
    why: "Почему объект отмечен",
    next: "Что делать дальше",
    quality: "Качество наблюдения",
    summary: "Краткое решение",
    compare: "До / после",
    evidence: "Цепочка доказательств",
    science: "Научные детали",
    assets: "Объекты",
    inspections: "Проверки",
    reports: "Отчёты",
    monitor: "Карта",
    overview: "Обзор",
    research: "Наука",
    save: "Сохранить offline-черновик",
    saved: "Черновик сохранён на этом устройстве",
    export: "Экспорт audit snapshot",
    refresh: "Обновить",
    noData: "Операционных записей пока нет.",
    safety: "Приоритеты выбирают наблюдения. Это не вероятность события и не официальное предупреждение.",
    strict: "Только сопоставимые наблюдения",
    all: "Показать все наблюдения",
    explain: "Почему это отмечено?",
  },
  kk: {
    title: "GlacierNET Operations",
    region: "Іле Алатауы",
    attention: "Бүгін неге назар аудару керек",
    review: "Тексеру қажет",
    insufficient: "Дерек жеткіліксіз",
    observations: "Жаңа бақылаулар",
    reviewed: "Адам тексерген істер",
    priorities: "Бақылаулар кезегі",
    map: "Операциялық карта",
    selected: "Таңдалған нысан",
    change: "Не өзгерді",
    trust: "Қаншалықты сенімді",
    why: "Неге белгіленді",
    next: "Келесі әрекет",
    quality: "Бақылау сапасы",
    summary: "Шешім қысқаша",
    compare: "Бұрын / кейін",
    evidence: "Дәлелдер тізбегі",
    science: "Ғылыми мәліметтер",
    assets: "Нысандар",
    inspections: "Тексерулер",
    reports: "Есептер",
    monitor: "Карта",
    overview: "Шолу",
    research: "Ғылым",
    save: "Offline нобайды сақтау",
    saved: "Нобай осы құрылғыда сақталды",
    export: "Audit snapshot жүктеу",
    refresh: "Жаңарту",
    noData: "Операциялық жазбалар әлі жоқ.",
    safety: "Басымдықтар бақылауды таңдайды. Олар оқиға ықтималдығы немесе ресми ескерту емес.",
    strict: "Тек салыстырмалы бақылаулар",
    all: "Барлық бақылауларды көрсету",
    explain: "Неге белгіленді?",
  },
};

type OperationsCopy = { [Key in keyof (typeof copy)["en"]]: string };

const actionLabels: Record<string, string> = {
  acquire_clear_satellite_scene: "Acquire a clearer satellite scene",
  targeted_field_or_drone_inspection: "Inspect the disputed boundary in the field or by drone",
  refresh_stale_observation: "Refresh the stale observation",
  expert_review_and_local_calibration: "Run expert review and local calibration",
  routine_monitoring: "Continue routine monitoring",
};

function humanize(value: string): string {
  return actionLabels[value] ?? value.replaceAll("_", " ");
}

function parseValues(observation?: OperationsObservation): Record<string, unknown> {
  if (!observation) return {};
  try {
    return JSON.parse(observation.values_json) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function formatDate(value?: string): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function confidence(uncertainty: number): { label: string; description: string } {
  if (uncertainty <= 0.35) return { label: "High", description: "Usable" };
  if (uncertainty <= 0.65) return { label: "Medium", description: "Usable with limitations" };
  return { label: "Low", description: "Do not use without review" };
}

function changeLabel(candidate?: ChangeCandidate): string {
  if (!candidate) return "No change candidate";
  if (candidate.change_type.includes("stale")) return "Latest observation is not comparable";
  const amount = Math.abs(candidate.magnitude * 100).toFixed(1);
  return candidate.magnitude >= 0
    ? `Possible area increase of ${amount}%`
    : `Possible area decrease of ${amount}%`;
}

function downloadJson(name: string, value: unknown): void {
  const blob = new Blob([JSON.stringify(value, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

export default function OperationsPage() {
  const { locale } = useI18n();
  const text = copy[locale];
  const [data, setData] = useState<OperationsOverview | null>(null);
  const [glaciers, setGlaciers] = useState<GlacierRecord[]>([]);
  const [registryError, setRegistryError] = useState("");
  const [mapYear, setMapYear] = useState(2024);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastRefreshed, setLastRefreshed] = useState("");
  const [selectedAssetId, setSelectedAssetId] = useState("");
  const [detailMode, setDetailMode] = useState<DetailMode>("summary");
  const [saved, setSaved] = useState(false);
  const [assetQuery, setAssetQuery] = useState("");
  const [assetStatus, setAssetStatus] = useState("all");
  const [observer, setObserver] = useState("");
  const [waterLevel, setWaterLevel] = useState("");
  const [notes, setNotes] = useState("");
  const [signature, setSignature] = useState("");
  const [riskTwinScan, setRiskTwinScan] = useState<RegionalObservationScan | null>(null);
  const [riskTwinScanError, setRiskTwinScanError] = useState("");
  const [selectedRiskTwinKey, setSelectedRiskTwinKey] = useState("");
  const [locationVerification, setLocationVerification] = useState<"unverified" | "gps_verified" | "manually_confirmed">("unverified");
  const [locationMethod, setLocationMethod] = useState<"device_gps" | "map_selection" | "external_instrument">("map_selection");
  const [creatingInspection, setCreatingInspection] = useState(false);
  const [inspectionMessage, setInspectionMessage] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    setRegistryError("");
    try {
      const [live, registry, scan] = await Promise.all([
        fetchOperationsOverview(),
        fetchGlaciers("", false, 1000, true).catch((reason) => {
          setRegistryError(reason instanceof Error ? reason.message : "RGI registry unavailable");
          return { glaciers: [], total: 0 };
        }),
        fetchRegionalObservationScan(500, 10, 2023).catch((reason) => {
          setRiskTwinScanError(reason instanceof Error ? reason.message : "Risk Twin scan unavailable");
          return null;
        }),
      ]);
      setData(live);
      setGlaciers(registry.glaciers);
      setRiskTwinScan(scan);
      setLastRefreshed(
        new Intl.DateTimeFormat(locale, {
          hour: "2-digit",
          minute: "2-digit",
        }).format(new Date())
      );
      setSelectedAssetId((current) => current || live.observation_queue[0]?.asset_id || live.assets[0]?.id || "");
      setSelectedRiskTwinKey((current) => current || (scan?.candidates[0] ? regionalObservationCandidateKey(scan.candidates[0]) : ""));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Operations API unavailable");
    } finally {
      setLoading(false);
    }
  }, [locale]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    // Risk Twin handoffs return this stable URL. Honor it after the live
    // registry has loaded instead of silently selecting an unrelated queue item.
    const requestedAsset = new URLSearchParams(window.location.search).get("asset");
    if (requestedAsset && data?.assets.some((asset) => asset.id === requestedAsset)) {
      setSelectedAssetId(requestedAsset);
      document.getElementById("monitor")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [data?.assets]);

  const assetsById = useMemo(
    () => Object.fromEntries((data?.assets ?? []).map((asset) => [asset.id, asset])),
    [data]
  );
  const observationsByAsset = useMemo(
    () =>
      Object.fromEntries(
        (data?.assets ?? []).map((asset) => [
          asset.id,
          (data?.observations ?? []).filter((item) => item.asset_id === asset.id),
        ])
      ),
    [data]
  );
  const uniqueRiskTwinCandidates = useMemo(
    () => Array.from(
      new globalThis.Map(
        (riskTwinScan?.candidates ?? []).map((candidate) => [
          regionalObservationCandidateKey(candidate),
          candidate,
        ])
      ).values()
    ),
    [riskTwinScan]
  );
  const selectedAsset = assetsById[selectedAssetId];
  const selectedRiskTwinCandidate = uniqueRiskTwinCandidates.find((item) => regionalObservationCandidateKey(item) === selectedRiskTwinKey);
  const selectedRiskTwinHref = selectedRiskTwinCandidate
    ? riskTwinHref({
        rgiId: selectedRiskTwinCandidate.glacier.rgi_id,
        ...(selectedRiskTwinCandidate.lake_id ? { lakeId: selectedRiskTwinCandidate.lake_id } : {}),
        year: mapYear,
        lakeInventoryYear: selectedRiskTwinCandidate.inventory_year,
        sourceScope: "local_inventory",
      })
    : "/risk-twin";
  const selectedCandidate = data?.observation_queue.find((item) => item.asset_id === selectedAssetId);
  const selectedObservation = observationsByAsset[selectedAssetId]?.[0];
  const selectedTask = data?.inspection_tasks.find((item) => item.asset_id === selectedAssetId);
  const selectedCase = data?.evidence_cases.find((item) => item.asset_id === selectedAssetId);
  const observationValues = parseValues(selectedObservation);
  const trust = confidence(selectedCandidate?.uncertainty ?? 1);
  const qualityScore = Math.round((1 - (selectedCandidate?.uncertainty ?? 1)) * 100);

  const filteredAssets = (data?.assets ?? []).filter((asset) => {
    const matchesQuery = asset.name.toLowerCase().includes(assetQuery.toLowerCase());
    const matchesStatus = assetStatus === "all" || asset.status === assetStatus;
    return matchesQuery && matchesStatus;
  });
  const requiresReview = (data?.observation_queue ?? []).filter(
    (item) => item.status === "requires_review"
  ).length;
  const insufficientData = (data?.observation_queue ?? []).filter(
    (item) => item.status === "insufficient_data" || item.data_quality_gap >= 0.6
  ).length;

  const saveOffline = () => {
    if (!selectedTask || !selectedAsset) return;
    const draft: FieldReportInput = {
      task_id: selectedTask.id,
      asset_id: selectedAsset.id,
      observer,
      observed_at: new Date().toISOString(),
      latitude: selectedAsset.latitude,
      longitude: selectedAsset.longitude,
      measurements: { water_level_m: waterLevel ? Number(waterLevel) : null },
      checklist: {
        location_verified: locationVerification !== "unverified",
        location_verification_status: locationVerification,
        location_verification_method: locationMethod,
        shadow_mode: true,
      },
      notes,
      attachment_manifest: [],
      signature,
      sync_status: "offline_draft",
    };
    const storageKey = "glaciernet-operations-field-drafts.v2";
    const existing = JSON.parse(localStorage.getItem(storageKey) ?? "[]") as FieldReportInput[];
    localStorage.setItem(storageKey, JSON.stringify([...existing, draft]));
    setSaved(true);
  };

  const syncDraft = async () => {
    const storageKey = "glaciernet-operations-field-drafts.v2";
    const drafts = JSON.parse(localStorage.getItem(storageKey) ?? "[]") as FieldReportInput[];
    const draft = drafts.find((item) => item.task_id === selectedTask?.id);
    if (!draft) return;
    await createFieldReport({ ...draft, sync_status: "synced" });
    localStorage.setItem(storageKey, JSON.stringify(drafts.filter((item) => item !== draft)));
    setSaved(false);
    await load();
  };

  const startInspection = async () => {
    if (!selectedAsset || !selectedCandidate) return;
    setInspectionMessage("");
    setCreatingInspection(true);
    try {
      const task = await createInspectionTask({
        asset_id: selectedAsset.id,
        candidate_id: selectedCandidate.id,
        action_type: selectedCandidate.next_action,
        priority_score: selectedCandidate.priority_score,
        rationale: selectedCandidate.rationale,
      });
      setInspectionMessage(`Inspection ${task.id} created. Complete the field report below.`);
      await load();
      document.getElementById("inspections")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (reason) {
      setInspectionMessage(reason instanceof Error ? reason.message : "Could not create inspection");
    } finally {
      setCreatingInspection(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f4f6f8] text-slate-950">
      <a href="#main" aria-label="Skip to main content" className="sr-only rounded-lg bg-slate-950 px-4 py-3 text-sm font-semibold text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[1000]">Перейти к Operations</a>
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-[1500px] px-4 sm:px-6">
          <div className="flex min-h-16 flex-wrap items-center justify-between gap-3 py-3">
            <div>
              <Link href="/" className="inline-flex min-h-11 items-center font-semibold tracking-tight text-slate-950">
                {text.title}
              </Link>
              <p className="text-xs text-slate-500">{text.region} · shadow mode</p>
            </div>
            <nav aria-label="Operations navigation" className="order-3 flex w-full gap-1 overflow-x-auto md:order-2 md:w-auto">
              <NavLink href="#overview" icon={Eye} label={text.overview} />
              <NavLink href="#monitor" icon={Map} label={text.monitor} />
              <NavLink href="#years" icon={Layers3} label="Years" />
              <NavLink href="#assets" icon={Database} label={text.assets} />
              <NavLink href="#inspections" icon={ClipboardCheck} label={text.inspections} />
              <NavLink href="#reports" icon={FileCheck2} label={text.reports} />
            </nav>
            <details className="relative order-2 md:order-3">
              <summary className="flex cursor-pointer list-none items-center gap-1 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700">
                <FlaskConical className="h-4 w-4" aria-hidden="true" />
                {text.research}
                <ChevronDown className="h-4 w-4" aria-hidden="true" />
              </summary>
              <div className="absolute right-0 z-30 mt-2 w-52 rounded-xl border border-slate-200 bg-white p-2 shadow-xl">
                <Link className="block rounded-lg px-3 py-2 text-sm hover:bg-slate-100" href="/hub">Research hub</Link>
                <Link className="block rounded-lg px-3 py-2 text-sm hover:bg-slate-100" href="/datasets">Data</Link>
                <Link className="block rounded-lg px-3 py-2 text-sm hover:bg-slate-100" href="/compare">Models</Link>
                <Link className="block rounded-lg px-3 py-2 text-sm hover:bg-slate-100" href="/admin/system">System</Link>
              </div>
            </details>
          </div>
        </div>
      </header>

      <main id="main" className="mx-auto max-w-[1500px] space-y-6 px-4 py-6 sm:px-6">
        <section id="overview" aria-labelledby="attention-heading">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-blue-800">Decision workspace</p>
              <h1 id="attention-heading" className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
                {text.attention}
              </h1>
              <p className="mt-2 text-sm text-slate-500">
                Last refreshed {lastRefreshed || "—"}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => void load()}
                className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
              >
                <RefreshCw className="h-4 w-4" aria-hidden="true" />
                {text.refresh}
              </button>
              <button
                type="button"
                disabled={!data}
                onClick={() =>
                  data &&
                  downloadJson("glaciernet-operations-audit-snapshot.json", {
                    schema: "glaciernet-kz.operations-ui-snapshot.v2",
                    exported_at: new Date().toISOString(),
                    data,
                  })
                }
                className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
              >
                <Download className="h-4 w-4" aria-hidden="true" />
                {text.export}
              </button>
            </div>
          </div>

          <section id="risk-twin-priorities" aria-labelledby="risk-twin-priorities-heading" className="mt-5 rounded-2xl border border-cyan-200 bg-gradient-to-r from-cyan-50 via-white to-blue-50 p-5 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-cyan-800">Real local Risk Twin screening</p><h2 id="risk-twin-priorities-heading" className="mt-1 text-xl font-semibold">Критические объекты для следующей проверки</h2><p className="mt-1 max-w-3xl text-sm text-slate-600">Автоматически найдены в локальных инвентарях озёр: изменение 2020→2023, размер, близость к границе RGI и отсутствие надёжного геометрического совпадения. Это приоритет сбора доказательств, не прогноз опасности.</p></div>
              <Link href={selectedRiskTwinHref} className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-cyan-800 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-900">Открыть полный Risk Twin<ArrowRight className="h-4 w-4" /></Link>
            </div>
            {riskTwinScanError ? <p role="alert" aria-live="assertive" className="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">Risk Twin scan недоступен: {riskTwinScanError}</p> : !riskTwinScan ? <p className="mt-4 text-sm text-slate-600">Сканирование локальных геоданных…</p> : <>
              <div className="mt-4 grid gap-3 sm:grid-cols-4"><RiskTwinMetric label="Просканировано озёр" value={riskTwinScan.summary.scanned_lakes} /><RiskTwinMetric label="Кандидатов возле RGI" value={riskTwinScan.summary.candidates_with_nearby_rgi} /><RiskTwinMetric label="Крупных изменений площади" value={riskTwinScan.summary.large_change_screening} /><RiskTwinMetric label="Без надёжного match" value={riskTwinScan.summary.unmatched_previous} /></div>
              <label htmlFor="operations-risk-twin-case" className="mt-4 block max-w-3xl text-sm font-semibold text-slate-800">Выбрать любой реальный случай Risk Twin<select id="operations-risk-twin-case" value={selectedRiskTwinKey} onChange={(event) => setSelectedRiskTwinKey(event.target.value)} className="mt-1 min-h-11 w-full rounded-lg border border-cyan-300 bg-white px-3 text-sm font-normal"><option value="">Выберите объект</option>{uniqueRiskTwinCandidates.map((candidate) => { const key = regionalObservationCandidateKey(candidate); return <option key={key} value={key}>{candidate.glacier.name_ru || candidate.glacier.name} · озеро {candidate.lake_id ?? "без ID"} · приоритет {candidate.observation_priority_0_100.toFixed(0)}</option>; })}</select></label>
              {selectedRiskTwinCandidate && <article className="mt-4 rounded-xl border-2 border-cyan-500 bg-white p-4" aria-live="polite"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-cyan-800">Выбранный реальный case</p><h3 className="mt-1 text-lg font-semibold">{selectedRiskTwinCandidate.glacier.name_ru || selectedRiskTwinCandidate.glacier.name}</h3><p className="mt-1 text-sm text-slate-600">Озеро {selectedRiskTwinCandidate.lake_id ?? "без ID"} · {selectedRiskTwinCandidate.latitude.toFixed(5)}, {selectedRiskTwinCandidate.longitude.toFixed(5)}</p></div><span className="rounded-full bg-cyan-100 px-3 py-1 text-sm font-bold text-cyan-950">Приоритет наблюдения {selectedRiskTwinCandidate.observation_priority_0_100.toFixed(0)}/100</span></div><div className="mt-4 grid gap-3 sm:grid-cols-3"><DecisionFact label="Изменение площади" value={selectedRiskTwinCandidate.area_change_percent === null ? "Нет надёжного match" : `${selectedRiskTwinCandidate.area_change_percent > 0 ? "+" : ""}${selectedRiskTwinCandidate.area_change_percent.toFixed(1)}%`} /><DecisionFact label="До RGI" value={`${selectedRiskTwinCandidate.distance_to_rgi_boundary_m.toFixed(0)} м`} /><DecisionFact label="Архив событий в 10 км" value={String(selectedRiskTwinCandidate.historical_event_count_in_glacier_context)} /></div><div className="mt-3 flex flex-wrap gap-1">{selectedRiskTwinCandidate.flags.map((flag) => <span key={flag} className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">{flag.replaceAll("_", " ")}</span>)}</div><div className="mt-4"><Link href={selectedRiskTwinHref} className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-cyan-700 px-3 py-2 text-sm font-semibold text-cyan-900 hover:bg-cyan-50">Открыть этот проверяемый case <ArrowRight className="h-4 w-4" /></Link></div><p className="mt-3 text-xs text-slate-500">Откройте полный контекст и исходные слои для проверки; этот case не является утверждением об опасности.</p></article>}
              <div className="mt-4 grid gap-3 lg:grid-cols-2">{uniqueRiskTwinCandidates.slice(0, 6).map((candidate) => { const key = regionalObservationCandidateKey(candidate); return <button key={key} type="button" onClick={() => setSelectedRiskTwinKey(key)} className={`rounded-xl border bg-white p-4 text-left ${selectedRiskTwinKey === key ? "border-cyan-600 ring-2 ring-cyan-100" : "border-cyan-100 hover:border-cyan-400"}`}><div className="flex items-start justify-between gap-3"><div><p className="font-semibold">{candidate.glacier.name_ru || candidate.glacier.name}</p><p className="mt-1 text-xs text-slate-500">Озеро {candidate.lake_id ?? "без ID"} · {candidate.latitude.toFixed(4)}, {candidate.longitude.toFixed(4)}</p></div><span className="rounded-full bg-cyan-100 px-2.5 py-1 text-xs font-bold text-cyan-950">{candidate.observation_priority_0_100.toFixed(0)}/100</span></div><p className="mt-3 text-sm text-slate-800">{candidate.area_change_percent === null ? `Нет надёжного совпадения с ${riskTwinScan.previous_inventory_year ?? "предыдущим"} инвентарём` : `Изменение площади: ${candidate.area_change_percent > 0 ? "+" : ""}${candidate.area_change_percent.toFixed(1)}%`} · до RGI: {candidate.distance_to_rgi_boundary_m.toFixed(0)} м</p></button>; })}</div>
              <p className="mt-4 text-xs text-slate-500">Сравнение — геометрическая эвристика с порогом 300 м. Она не доказывает связь озера с ледником, состояние морены, вероятность события или основание для предупреждения.</p>
            </>}
          </section>
          {error && <div role="alert" aria-live="assertive" className="mt-5 rounded-xl border border-orange-300 bg-orange-50 p-4 text-orange-950">{error}</div>}

          <div aria-label="Attention summary" className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <AttentionCard icon={ClipboardCheck} label={text.review} value={requiresReview} tone="violet" />
            <AttentionCard icon={WifiOff} label={text.insufficient} value={insufficientData} tone="neutral" />
            <AttentionCard icon={Satellite} label={text.observations} value={data?.counts.observations ?? 0} tone="blue" />
            <AttentionCard icon={CheckCircle2} label={text.reviewed} value={(data?.evidence_cases ?? []).filter((item) => item.reviewer).length} tone="confirmed" />
          </div>
        </section>

        {loading ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-slate-500" aria-live="polite">
            Loading operations…
          </div>
        ) : (
          <>
            <section id="monitor" aria-label="Priority queue and operational map" className="grid overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm xl:grid-cols-[minmax(360px,0.7fr)_1.3fr]">
              <div className="border-b border-slate-200 p-5 xl:border-b-0 xl:border-r">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-800">Next Best Observation</p>
                    <h2 className="mt-1 text-xl font-semibold">{text.priorities}</h2>
                  </div>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium">
                    {data?.observation_queue.length ?? 0}
                  </span>
                </div>
                <div className="mt-4 space-y-3">
                  {(data?.observation_queue ?? []).map((candidate, index) => (
                    <QueueCard
                      key={candidate.id}
                      index={index}
                      candidate={candidate}
                      asset={assetsById[candidate.asset_id]}
                      observation={observationsByAsset[candidate.asset_id]?.[0]}
                      selected={candidate.asset_id === selectedAssetId}
                      onSelect={() => {
                        setSelectedAssetId(candidate.asset_id);
                        setDetailMode("summary");
                      }}
                    />
                  ))}
                  {!data?.observation_queue.length && <p className="rounded-xl bg-slate-50 p-6 text-center text-slate-500">{text.noData}</p>}
                </div>
              </div>
              <div className="relative min-h-[430px] overflow-hidden">
                <div className="pointer-events-none absolute left-4 right-4 top-4 z-[500] flex flex-wrap items-start justify-between gap-3">
                  <div className="rounded-xl border border-white/70 bg-white/90 px-4 py-3 shadow-sm backdrop-blur">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-800">Real spatial context</p>
                    <h2 className="mt-1 text-lg font-semibold">{text.map}</h2>
                    <p className="mt-1 text-xs text-slate-600">
                      {glaciers.length} RGI 7.0 boundaries · {mapYear} segmentation · {data?.assets.length ?? 0} shadow-mode objects
                    </p>
                  </div>
                  <span className="rounded-full border border-slate-300 bg-white/90 px-3 py-1 text-xs shadow-sm">Not a hazard map</span>
                </div>
                {registryError && (
                  <p role="alert" aria-live="assertive" className="absolute bottom-16 left-4 right-4 z-[500] rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
                    RGI geometry unavailable: {registryError}
                  </p>
                )}
                <OperationsInventoryMap
                  glaciers={glaciers}
                  assets={data?.assets ?? []}
                  candidates={data?.observation_queue ?? []}
                  selectedAssetId={selectedAssetId}
                  onSelectAsset={setSelectedAssetId}
                  riskTwinCandidates={uniqueRiskTwinCandidates}
                  selectedRiskTwinKey={selectedRiskTwinKey}
                  onSelectRiskTwin={setSelectedRiskTwinKey}
                  selectedYear={mapYear}
                />
              </div>
            </section>

            <OperationsYearAnalysis onYearChange={setMapYear} />

            {selectedAsset && (
              <section aria-labelledby="selected-object-heading" className="rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-200 p-5 sm:p-6">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{text.selected}</p>
                  <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 id="selected-object-heading" className="text-2xl font-semibold">{selectedAsset.name}</h2>
                        <StatusBadge status={selectedCandidate?.status ?? selectedAsset.status} />
                      </div>
                      <p className="mt-2 text-sm text-slate-500">
                        {humanize(selectedAsset.asset_type)} · Last observation {formatDate(selectedObservation?.observed_at)}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => void startInspection()}
                      disabled={creatingInspection}
                      className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-violet-700 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-700"
                    >
                      <ClipboardCheck className="h-4 w-4" aria-hidden="true" />
                      {creatingInspection ? "Creating…" : "Create inspection"}
                    </button>
                  </div>
                  {inspectionMessage && <p role="status" aria-live="polite" className="mt-3 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-950">{inspectionMessage}</p>}
                  <div className="mt-5 grid gap-3 lg:grid-cols-4">
                    <DecisionFact label={text.change} value={changeLabel(selectedCandidate)} />
                    <DecisionFact label={text.trust} value={`${trust.label} · ${trust.description}`} />
                    <DecisionFact label={text.why} value={selectedCandidate?.rationale ?? "No candidate rationale"} />
                    <DecisionFact label={text.next} value={humanize(selectedCandidate?.next_action ?? "routine_monitoring")} accent />
                  </div>
                </div>

                <div role="tablist" aria-label="Object detail level" className="flex gap-1 overflow-x-auto border-b border-slate-200 px-4 pt-3 sm:px-6">
                  {([
                    ["summary", text.summary],
                    ["compare", text.compare],
                    ["evidence", text.evidence],
                    ["science", text.science],
                  ] as [DetailMode, string][]).map(([mode, label]) => (
                    <button
                      key={mode}
                      type="button"
                      role="tab"
                      aria-selected={detailMode === mode}
                      onClick={() => setDetailMode(mode)}
                      className={`min-h-11 whitespace-nowrap border-b-2 px-3 text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 ${
                        detailMode === mode ? "border-blue-700 text-blue-800" : "border-transparent text-slate-500 hover:text-slate-900"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <div role="tabpanel" className="p-5 sm:p-6">
                  {detailMode === "summary" && (
                    <DecisionBrief
                      text={text}
                      candidate={selectedCandidate}
                      observation={selectedObservation}
                      values={observationValues}
                      qualityScore={qualityScore}
                    />
                  )}
                  {detailMode === "compare" && (
                    <ComparisonWorkspace />
                  )}
                  {detailMode === "evidence" && (
                    <EvidenceTimeline
                      observation={selectedObservation}
                      evidenceCase={selectedCase}
                      candidate={selectedCandidate}
                      auditEvents={(data?.audit_events ?? []).filter((item) =>
                        [selectedAssetId, selectedObservation?.id, selectedCandidate?.id, selectedCase?.id].includes(item.entity_id)
                      )}
                    />
                  )}
                  {detailMode === "science" && (
                    <ScientificDetails asset={selectedAsset} candidate={selectedCandidate} observation={selectedObservation} />
                  )}
                </div>
              </section>
            )}

            <section id="assets" aria-labelledby="assets-heading" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Operational inventory</p>
                  <h2 id="assets-heading" className="mt-1 text-xl font-semibold">{text.assets}</h2>
                </div>
                <div className="flex w-full flex-wrap gap-2 sm:w-auto">
                  <label className="relative flex-1 sm:w-64">
                    <span className="sr-only">Search objects</span>
                    <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" aria-hidden="true" />
                    <input
                      value={assetQuery}
                      onChange={(event) => setAssetQuery(event.target.value)}
                      placeholder="Search objects"
                      className="min-h-11 w-full rounded-lg border border-slate-300 pl-9 pr-3 text-sm focus:border-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
                    />
                  </label>
                  <label>
                    <span className="sr-only">Filter by status</span>
                    <select
                      value={assetStatus}
                      onChange={(event) => setAssetStatus(event.target.value)}
                      className="min-h-11 rounded-lg border border-slate-300 bg-white px-3 text-sm focus:border-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
                    >
                      <option value="all">All statuses</option>
                      <option value="requires_review">Requires review</option>
                      <option value="stale_observation">Stale observation</option>
                    </select>
                  </label>
                </div>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {filteredAssets.map((asset) => {
                  const candidate = data?.observation_queue.find((item) => item.asset_id === asset.id);
                  return (
                    <button
                      key={asset.id}
                      type="button"
                      onClick={() => {
                        setSelectedAssetId(asset.id);
                        document.getElementById("selected-object-heading")?.scrollIntoView({ behavior: "smooth" });
                      }}
                      className="grid min-h-32 grid-cols-[72px_1fr] gap-3 rounded-xl border border-slate-200 p-3 text-left hover:border-blue-400 hover:shadow-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
                    >
                      <MiniMap asset={asset} tone={candidate?.status === "requires_review" ? "violet" : "neutral"} />
                      <span>
                        <span className="block font-semibold">{asset.name}</span>
                        <span className="mt-1 block text-sm text-slate-600">{changeLabel(candidate)}</span>
                        <span className="mt-2 block text-xs text-slate-500">
                          {candidate ? `${confidence(candidate.uncertainty).label} confidence` : "No candidate"} · {humanize(candidate?.next_action ?? asset.status)}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </section>

            <section id="inspections" className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                <h2 className="text-xl font-semibold">{text.inspections}</h2>
                <div className="mt-4 space-y-3">
                  {(data?.inspection_tasks ?? []).map((task) => (
                    <article key={task.id} className="rounded-xl border border-slate-200 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <h3 className="font-semibold">{assetsById[task.asset_id]?.name ?? task.asset_id}</h3>
                        <StatusBadge status={task.status} />
                      </div>
                      <p className="mt-2 text-sm text-slate-600">{task.rationale}</p>
                      <p className="mt-3 text-sm font-medium text-violet-800">{humanize(task.action_type)}</p>
                    </article>
                  ))}
                </div>
              </div>
              <FieldDraft
                selectedTask={selectedTask}
                selectedAsset={selectedAsset}
                observer={observer}
                setObserver={setObserver}
                waterLevel={waterLevel}
                setWaterLevel={setWaterLevel}
                notes={notes}
                setNotes={setNotes}
                signature={signature}
                setSignature={setSignature}
                locationVerification={locationVerification}
                setLocationVerification={setLocationVerification}
                locationMethod={locationMethod}
                setLocationMethod={setLocationMethod}
                saved={saved}
                saveOffline={saveOffline}
                syncDraft={syncDraft}
                text={text}
              />
            </section>

            <section id="reports" className="grid gap-4 rounded-2xl bg-slate-950 p-5 text-white sm:grid-cols-[1fr_auto] sm:items-center sm:p-6">
              <div>
                <div className="flex items-center gap-3">
                  <ShieldCheck className="h-7 w-7 text-blue-300" aria-hidden="true" />
                  <div>
                    <h2 className="text-lg font-semibold">
                      {data?.audit_chain.valid ? "SHA-256 chain valid" : "Audit chain unavailable"}
                    </h2>
                    <p className="text-sm text-slate-300">{data?.audit_chain.events ?? 0} append-only events · {data?.counts.evidence_cases ?? 0} evidence cases</p>
                  </div>
                </div>
                <details className="mt-4">
                  <summary className="cursor-pointer text-sm text-blue-200">Show technical hash</summary>
                  <p className="mt-2 break-all font-mono text-[11px] text-slate-400">{data?.audit_chain.head_sha256 ?? "No persistent audit head in demo preview"}</p>
                </details>
              </div>
              <Link href="/reports" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-slate-100">
                Open reports
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

function NavLink({ href, icon: Icon, label }: { href: string; icon: typeof Eye; label: string }) {
  return (
    <a href={href} className="inline-flex min-h-11 items-center gap-1.5 rounded-lg px-3 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-950 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700">
      <Icon className="h-4 w-4" aria-hidden="true" />
      {label}
    </a>
  );
}

function AttentionCard({ icon: Icon, label, value, tone }: { icon: typeof Eye; label: string; value: number; tone: "violet" | "neutral" | "blue" | "confirmed" }) {
  const styles = {
    violet: "border-violet-200 bg-violet-50 text-violet-900",
    neutral: "border-slate-300 bg-white text-slate-900",
    blue: "border-blue-200 bg-blue-50 text-blue-950",
    confirmed: "border-emerald-200 bg-emerald-50 text-emerald-950",
  };
  return (
    <div className={`rounded-xl border p-4 ${styles[tone]}`}>
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium">{label}</span>
        <Icon className="h-5 w-5" aria-hidden="true" />
      </div>
      <p className="mt-3 text-3xl font-semibold">{value}</p>
    </div>
  );
}

function RiskTwinMetric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-xl border border-cyan-100 bg-white p-3"><p className="text-xs text-slate-600">{label}</p><p className="mt-1 text-2xl font-bold text-cyan-950">{value}</p></div>;
}

function StatusBadge({ status }: { status: string }) {
  const isConfirmed = status === "completed" || status === "approved" || status === "closed";
  const isAction = status === "requires_review" || status === "queued";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${
      isConfirmed ? "border-emerald-500 bg-white text-emerald-800" : isAction ? "border-violet-300 bg-violet-50 text-violet-900" : "border-slate-300 bg-slate-50 text-slate-700"
    }`}>
      <span className={`h-1.5 w-1.5 rounded-full ${isConfirmed ? "bg-emerald-600" : isAction ? "bg-violet-700" : "bg-slate-500"}`} aria-hidden="true" />
      {humanize(status)}
    </span>
  );
}

function QueueCard({ index, candidate, asset, observation, selected, onSelect }: { index: number; candidate: ChangeCandidate; asset?: OperationsAsset; observation?: OperationsObservation; selected: boolean; onSelect: () => void }) {
  const trust = confidence(candidate.uncertainty);
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={`grid w-full grid-cols-[64px_1fr] gap-3 rounded-xl border p-3 text-left transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 ${
        selected ? "border-blue-600 bg-blue-50 shadow-sm" : "border-slate-200 hover:border-blue-300 hover:bg-slate-50"
      }`}
    >
      {asset ? <MiniMap asset={asset} tone={candidate.status === "requires_review" ? "violet" : "neutral"} /> : <span />}
      <span>
        <span className="flex items-start justify-between gap-2">
          <span className="font-semibold">{index + 1}. {asset?.name ?? candidate.asset_id}</span>
          <span className="text-xs font-semibold text-slate-500">{Math.round(candidate.priority_score * 100)}</span>
        </span>
        <span className="mt-1 block text-sm text-slate-700">{changeLabel(candidate)}</span>
        <span className="mt-2 block text-xs text-slate-500">
          {trust.label} confidence · {formatDate(observation?.observed_at)}
        </span>
        <span className="mt-2 block text-xs font-medium text-violet-800">{humanize(candidate.next_action)}</span>
        <span className="sr-only">observation priority {Math.round(candidate.priority_score * 100)} percent</span>
      </span>
    </button>
  );
}

function MiniMap({ asset, tone }: { asset: OperationsAsset; tone: "violet" | "neutral" }) {
  return (
    <span className="relative block h-16 overflow-hidden rounded-lg border border-slate-200 bg-[#eaf0f2]" aria-hidden="true">
      <span className="absolute -left-3 top-5 h-14 w-20 rotate-12 rounded-[50%] border-2 border-slate-300 bg-white/70" />
      <span className="absolute left-4 top-1 h-12 w-16 -rotate-12 rounded-[40%] border border-slate-400/60" />
      <span className={`absolute left-7 top-6 h-3 w-3 rounded-full border-2 border-white shadow ${tone === "violet" ? "bg-violet-700" : "bg-blue-700"}`} />
      <span className="absolute bottom-1 right-1 font-mono text-[8px] text-slate-500">{asset.latitude.toFixed(2)}</span>
    </span>
  );
}

function DecisionFact({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={`rounded-xl border p-4 ${accent ? "border-violet-200 bg-violet-50" : "border-slate-200 bg-slate-50"}`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-sm font-medium ${accent ? "text-violet-950" : "text-slate-900"}`}>{value}</p>
    </div>
  );
}

function DecisionBrief({ text, candidate, observation, values, qualityScore }: { text: OperationsCopy; candidate?: ChangeCandidate; observation?: OperationsObservation; values: Record<string, unknown>; qualityScore: number }) {
  const factors = [
    { label: "Cloud / atmosphere", value: Math.max(0, 100 - Number(values.cloud_percent ?? 18)) },
    { label: "Seasonal snow separation", value: Number(values.seasonal_snow_score ?? Math.round((1 - (candidate?.data_quality_gap ?? 1)) * 100)) },
    { label: "Missing pixels", value: observation?.quality_status === "poor_quality" ? 68 : 96 },
    { label: "Cross-sensor comparability", value: Math.round((1 - (candidate?.model_disagreement ?? 1)) * 100) },
  ];
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
      <div>
        <h3 className="text-lg font-semibold">{text.explain}</h3>
        <ol className="mt-4 space-y-3">
          <Reason number={1}>The candidate differs from the latest usable observation by {Math.abs((candidate?.magnitude ?? 0) * 100).toFixed(1)}%.</Reason>
          <Reason number={2}>Data-quality gap is {Math.round((candidate?.data_quality_gap ?? 1) * 100)}%; poor years are not treated as confirmed change.</Reason>
          <Reason number={3}>Independent model disagreement is {Math.round((candidate?.model_disagreement ?? 1) * 100)}%.</Reason>
          <Reason number={4}>Domain-shift status is {humanize(candidate?.domain_shift_status ?? "unavailable")}.</Reason>
        </ol>
        <div className="mt-5 rounded-xl border border-violet-200 bg-violet-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-violet-700">{text.next}</p>
          <p className="mt-2 font-semibold text-violet-950">{humanize(candidate?.next_action ?? "routine_monitoring")}</p>
          <p className="mt-1 text-sm text-violet-900/75">This action is chosen for information gain, not because an event is predicted.</p>
        </div>
      </div>
      <details open className="rounded-xl border border-slate-200 p-4">
        <summary className="cursor-pointer font-semibold">
          {text.quality}: {qualityScore}/100 — {confidence(candidate?.uncertainty ?? 1).description}
        </summary>
        <div className="mt-4 space-y-4">
          {factors.map((factor) => <QualityBar key={factor.label} label={factor.label} value={factor.value} />)}
        </div>
        <p className="mt-4 rounded-lg bg-slate-100 p-3 text-sm text-slate-700">
          Main limitation: {candidate?.status === "insufficient_data" ? "seasonal snow makes the latest boundary incomparable." : "models disagree around the most informative boundary segment."}
        </p>
      </details>
    </div>
  );
}

function Reason({ number, children }: { number: number; children: React.ReactNode }) {
  return <li className="flex gap-3 text-sm text-slate-700"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-950 text-xs font-semibold text-white">{number}</span><span className="pt-0.5">{children}</span></li>;
}

function QualityBar({ label, value }: { label: string; value: number }) {
  const bounded = Math.max(0, Math.min(100, value));
  return (
    <div>
      <div className="flex justify-between gap-4 text-sm"><span>{label}</span><span className="font-medium">{bounded}</span></div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={bounded}>
        <div className="h-full rounded-full bg-blue-700" style={{ width: `${bounded}%` }} />
      </div>
    </div>
  );
}

function ComparisonWorkspace() {
  return <section className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-950"><h3 className="font-semibold">Сравнение требует связанных исходных артефактов</h3><p className="mt-2">В Operations не показываются искусственные изображения или графики. Откройте годовой screening layer на карте и полный Risk Twin case, чтобы проверить реальные локальные инвентари и ограничения данных.</p><Link href="/risk-twin" className="mt-3 inline-flex font-semibold text-blue-800 underline">Открыть Risk Twin</Link></section>;
}

function EvidenceTimeline({ observation, evidenceCase, candidate, auditEvents }: { observation?: OperationsObservation; evidenceCase?: OperationsOverview["evidence_cases"][number]; candidate?: ChangeCandidate; auditEvents: OperationsOverview["audit_events"] }) {
  const events = [
    observation && { title: `${humanize(observation.source)} received`, meta: `${formatDate(observation.observed_at)} · ${humanize(observation.quality_status)}`, status: "machine" },
    candidate && { title: "Change screen completed", meta: `${humanize(candidate.domain_shift_status)} · observation priority ${Math.round(candidate.priority_score * 100)}%`, status: "machine" },
    evidenceCase?.reviewer && { title: "Human review recorded", meta: `${evidenceCase.reviewer} · ${humanize(evidenceCase.status)}`, status: "human" },
    evidenceCase && { title: "Evidence case fixed", meta: `${evidenceCase.title} · ${formatDate(evidenceCase.updated_at)}`, status: "human" },
  ].filter(Boolean) as { title: string; meta: string; status: string }[];
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_0.8fr]">
      <div>
        <h3 className="text-lg font-semibold">Evidence timeline</h3>
        <ol className="mt-5">
          {events.map((event, index) => (
            <li key={`${event.title}-${index}`} className="relative grid grid-cols-[32px_1fr] gap-3 pb-6 last:pb-0">
              {index < events.length - 1 && <span className="absolute bottom-0 left-[15px] top-7 w-px bg-slate-300" aria-hidden="true" />}
              <span className={`relative z-10 flex h-8 w-8 items-center justify-center rounded-full border-2 bg-white ${event.status === "human" ? "border-emerald-600 text-emerald-700" : "border-blue-700 text-blue-700"}`}>
                {event.status === "human" ? <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> : <Layers3 className="h-4 w-4" aria-hidden="true" />}
              </span>
              <div><p className="font-medium">{event.title}</p><p className="mt-1 text-sm text-slate-500">{event.meta}</p></div>
            </li>
          ))}
          {!events.length && <p className="text-sm text-slate-500">No evidence events for this object.</p>}
        </ol>
      </div>
      <details className="rounded-xl border border-slate-200 p-4">
        <summary className="cursor-pointer font-semibold">Technical provenance</summary>
        <dl className="mt-4 space-y-3 text-sm">
          <div><dt className="text-slate-500">Artifact SHA-256</dt><dd className="mt-1 break-all font-mono text-xs">{observation?.artifact_sha256 ?? "not linked"}</dd></div>
          <div><dt className="text-slate-500">Audit events</dt><dd>{auditEvents.length}</dd></div>
          <div><dt className="text-slate-500">Evidence tier</dt><dd>{humanize(candidate?.evidence_tier ?? "unavailable")}</dd></div>
        </dl>
      </details>
    </div>
  );
}

function ScientificDetails({ asset, candidate, observation }: { asset: OperationsAsset; candidate?: ChangeCandidate; observation?: OperationsObservation }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <ScienceItem label="Model version" value={asset.model_version ?? "not recorded"} />
      <ScienceItem label="Data version" value={asset.data_version ?? "not recorded"} />
      <ScienceItem label="Input source" value={observation?.source ?? "not recorded"} />
      <ScienceItem label="Model disagreement" value={`${Math.round((candidate?.model_disagreement ?? 1) * 100)}%`} />
      <ScienceItem label="Expected information gain" value={`${Math.round((candidate?.expected_information_gain ?? 0) * 100)}%`} />
      <ScienceItem label="Domain shift" value={humanize(candidate?.domain_shift_status ?? "not assessed")} />
      <ScienceItem label="Allowed use" value={asset.allowed_use} />
      <ScienceItem label="Forbidden use" value={asset.forbidden_use} />
      <ScienceItem label="Coordinates" value={`${asset.latitude.toFixed(4)}, ${asset.longitude.toFixed(4)}`} />
    </div>
  );
}

function ScienceItem({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-slate-200 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p><p className="mt-2 break-words text-sm font-medium">{value}</p></div>;
}

function FieldDraft({ selectedTask, selectedAsset, observer, setObserver, waterLevel, setWaterLevel, notes, setNotes, signature, setSignature, locationVerification, setLocationVerification, locationMethod, setLocationMethod, saved, saveOffline, syncDraft, text }: {
  selectedTask?: OperationsOverview["inspection_tasks"][number];
  selectedAsset?: OperationsAsset;
  observer: string;
  setObserver: (value: string) => void;
  waterLevel: string;
  setWaterLevel: (value: string) => void;
  notes: string;
  setNotes: (value: string) => void;
  signature: string;
  setSignature: (value: string) => void;
  locationVerification: "unverified" | "gps_verified" | "manually_confirmed";
  setLocationVerification: (value: "unverified" | "gps_verified" | "manually_confirmed") => void;
  locationMethod: "device_gps" | "map_selection" | "external_instrument";
  setLocationMethod: (value: "device_gps" | "map_selection" | "external_instrument") => void;
  saved: boolean;
  saveOffline: () => void;
  syncDraft: () => Promise<void>;
  text: OperationsCopy;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex items-center gap-2"><WifiOff className="h-5 w-5 text-blue-700" aria-hidden="true" /><h2 className="text-xl font-semibold">Offline field report</h2></div>
      <p className="mt-2 text-sm text-slate-500">Drafts remain on this device until an analyst synchronises a persisted task. Location is unverified until you explicitly record how it was checked.</p>
      <div className="mt-5 space-y-4">
        <label htmlFor="field-task" className="block text-sm font-medium">Assigned task<input id="field-task" readOnly value={selectedTask?.id ?? ""} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-slate-50 px-3 text-sm" /></label>
        <label htmlFor="field-observer" className="block text-sm font-medium">Observer<input id="field-observer" value={observer} onChange={(event) => setObserver(event.target.value)} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-100" /></label>
        <label htmlFor="field-water-level" className="block text-sm font-medium">Water level, m<input id="field-water-level" type="number" inputMode="decimal" value={waterLevel} onChange={(event) => setWaterLevel(event.target.value)} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-100" /></label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label htmlFor="location-verification" className="block text-sm font-medium">Location verification<select id="location-verification" value={locationVerification} onChange={(event) => setLocationVerification(event.target.value as typeof locationVerification)} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"><option value="unverified">Unverified</option><option value="gps_verified">GPS verified</option><option value="manually_confirmed">Manually confirmed</option></select></label>
          <label htmlFor="location-method" className="block text-sm font-medium">Verification method<select id="location-method" value={locationMethod} onChange={(event) => setLocationMethod(event.target.value as typeof locationMethod)} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"><option value="map_selection">Map selection</option><option value="device_gps">Device GPS</option><option value="external_instrument">External instrument</option></select></label>
        </div>
        <label htmlFor="field-notes" className="block text-sm font-medium">Notes<textarea id="field-notes" rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-100" /></label>
        <label htmlFor="field-signature" className="block text-sm font-medium">Signature<input id="field-signature" value={signature} onChange={(event) => setSignature(event.target.value)} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-100" /></label>
        <button type="button" onClick={saveOffline} disabled={!selectedTask || !selectedAsset || !observer || !signature} className="flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40">
          <Save className="h-4 w-4" aria-hidden="true" />{text.save}
        </button>
        <div aria-live="polite">{saved && <p className="flex items-center gap-2 text-sm text-emerald-700"><CheckCircle2 className="h-4 w-4" aria-hidden="true" />{text.saved}</p>}</div>
        {saved && <button type="button" onClick={() => void syncDraft()} className="min-h-11 w-full rounded-lg border border-blue-700 px-4 py-2 text-sm font-semibold text-blue-800">Synchronise signed report</button>}
      </div>
    </section>
  );
}
