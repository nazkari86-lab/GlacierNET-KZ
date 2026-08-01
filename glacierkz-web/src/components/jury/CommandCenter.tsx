"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  MapPinned,
  ShieldCheck,
} from "lucide-react";
import GlacierEvidenceIntro from "@/components/jury/GlacierEvidenceIntro";
import CompanyAssetMode, { type CompanyAsset } from "@/components/jury/CompanyAssetMode";
import { riskTwinHref } from "@/lib/evidenceCase";
import { distanceToRouteMeters } from "@/lib/geoDistance";
import { buildEvidenceMapObjects, type EvidenceMapObject } from "@/lib/riskTwinEvidence";
import {
  fetchGlaciers,
  fetchJuryEvidence,
  fetchRegionalObservationScan,
  fetchRiskTwinContext,
  fetchYearMapLayer,
  regionalObservationCandidateKey,
  type GlacierRecord,
  type JuryEvidence,
  type RegionalObservationScan,
  type RiskTwinSpatialContext,
  type YearMapLayer,
} from "@/lib/api";

const RiskTwinMap = dynamic(() => import("@/components/RiskTwinMap"), {
  ssr: false,
  loading: () => <div className="flex h-[500px] items-center justify-center rounded-2xl bg-slate-950 text-sm text-slate-300">Загружаем карту выбранного объекта…</div>,
});

function areaKm2(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return (value / 1_000_000).toLocaleString("ru-RU", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
}

function coordinate(value: number) {
  return value.toLocaleString("ru-RU", { minimumFractionDigits: 4, maximumFractionDigits: 4 });
}

function caseHref(candidate: RegionalObservationScan["candidates"][number]) {
  return riskTwinHref({
    rgiId: candidate.glacier.rgi_id,
    lakeId: candidate.lake_id ?? undefined,
    year: 2024,
    lakeInventoryYear: candidate.inventory_year,
    sourceScope: "local_inventory",
  });
}

export default function CommandCenter() {
  const [evidence, setEvidence] = useState<JuryEvidence | null>(null);
  const [scan, setScan] = useState<RegionalObservationScan | null>(null);
  const [glaciers, setGlaciers] = useState<GlacierRecord[]>([]);
  const [yearLayer, setYearLayer] = useState<YearMapLayer | null>(null);
  const [selectedCaseKey, setSelectedCaseKey] = useState("");
  const [context, setContext] = useState<RiskTwinSpatialContext | null>(null);
  const [contextStatus, setContextStatus] = useState<"idle" | "loading" | "ready" | "unavailable">("idle");
  const [companyAsset, setCompanyAsset] = useState<CompanyAsset | null>(null);
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([
      fetchJuryEvidence(),
      fetchRegionalObservationScan(500, 10, 2023),
      fetchGlaciers("", false, 1000, true),
      fetchYearMapLayer(2024).catch(() => null),
    ])
      .then(([nextEvidence, regional, registry, layer]) => {
        if (!active) return;
        setEvidence(nextEvidence);
        setScan(regional);
        setGlaciers(registry.glaciers);
        setYearLayer(layer);
        const first = regional.candidates[0];
        if (first) setSelectedCaseKey(regionalObservationCandidateKey(first));
      })
      .catch((cause) => {
        if (active) setError(cause instanceof Error ? cause.message : "Не удалось загрузить локальный пакет доказательств.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  const selectedCase = useMemo(
    () => scan?.candidates.find((candidate) => regionalObservationCandidateKey(candidate) === selectedCaseKey) ?? scan?.candidates[0] ?? null,
    [scan, selectedCaseKey],
  );
  const selectedCaseIndex = useMemo(
    () => selectedCase && scan ? scan.candidates.findIndex((candidate) => regionalObservationCandidateKey(candidate) === regionalObservationCandidateKey(selectedCase)) + 1 : 0,
    [scan, selectedCase],
  );
  const selectedGlacier = useMemo(
    () => glaciers.find((glacier) => glacier.rgi_id === selectedCase?.glacier.rgi_id) ?? null,
    [glaciers, selectedCase],
  );

  useEffect(() => {
    if (!selectedCase || !selectedGlacier) return;
    let active = true;
    setContext(null);
    setContextStatus("loading");
    setSelectedObjectId(selectedCase.lake_id ? `lake:${selectedCase.lake_id}` : `glacier:${selectedGlacier.rgi_id}`);
    fetchRiskTwinContext(selectedGlacier.rgi_id, 2024, 10, selectedCase.inventory_year)
      .then((next) => {
        if (!active) return;
        setContext(next);
        setContextStatus("ready");
      })
      .catch((cause) => {
        if (!active) return;
        setContextStatus("unavailable");
        setError(cause instanceof Error ? cause.message : "Не удалось загрузить пространственный контекст выбранного объекта.");
      });
    return () => { active = false; };
  }, [selectedCase, selectedGlacier]);

  const companyAssetMapObject = useMemo<EvidenceMapObject | null>(() => {
    if (!companyAsset) return null;
    return {
      id: `company-asset:${companyAsset.id}`,
      kind: "asset",
      name: companyAsset.name,
      geometry: { type: "Point", coordinates: [companyAsset.longitude, companyAsset.latitude] },
      source: companyAsset.sourceLabel ?? "Координата, введённая пользователем в этом браузере",
      temporalCoverage: companyAsset.isPublicExample ? "публичная картографическая точка; проверено 2026-08-01" : "пользовательский ввод; не отправляется API",
      maturity: "requires_verification",
      visibleFact: `${companyAsset.type}${companyAsset.operator ? ` · ${companyAsset.operator}` : ""}. Используется только для пространственной проверки рядом с инвентарными объектами.`,
      allowedClaim: "Можно показать координату объекта рядом с локальными справочными слоями и измерить расстояние до planning‑route.",
      prohibitedClaim: "Координата объекта не доказывает воздействие, зону затопления, ущерб или необходимость эвакуации.",
      inspectorFacts: [
        { label: "Тип", value: companyAsset.type },
        { label: "Широта", value: coordinate(companyAsset.latitude) },
        { label: "Долгота", value: coordinate(companyAsset.longitude) },
        { label: "Источник", value: companyAsset.sourceLabel ?? "ввод пользователя" },
        { label: "Хранение", value: companyAsset.isPublicExample ? "встроенный публичный пример" : "только в этом браузере" },
      ],
    };
  }, [companyAsset]);
  const mapObjects = useMemo(
    () => [...buildEvidenceMapObjects(selectedGlacier, yearLayer, context, []), ...(companyAssetMapObject ? [companyAssetMapObject] : [])],
    [companyAssetMapObject, context, selectedGlacier, yearLayer],
  );
  const pinnedObjectIds = useMemo(
    () => companyAssetMapObject ? [companyAssetMapObject.id] : [],
    [companyAssetMapObject],
  );
  const selectedObject = useMemo(
    () => mapObjects.find((object) => object.id === selectedObjectId) ?? null,
    [mapObjects, selectedObjectId],
  );
  const companyAssetDistanceToRouteM = useMemo(
    () => companyAsset && context?.downstream_route.available
      ? distanceToRouteMeters(companyAsset.latitude, companyAsset.longitude, context.downstream_route.features)
      : null,
    [companyAsset, context],
  );

  const scrollToMap = () => document.getElementById("map")?.scrollIntoView({
    behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
    block: "start",
  });

  return <>
    <a href="#main" aria-label="Skip to main content" className="sr-only z-[1000] rounded-md bg-slate-950 px-4 py-3 font-semibold text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-4">Перейти к содержанию Command Center</a>
    <main id="main" className="min-h-screen bg-[linear-gradient(180deg,#f8fafc_0%,#ecfeff_48%,#f8fafc_100%)] text-slate-900">
      <nav aria-label="Навигация Command Center" className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 px-4 py-3 shadow-sm backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
          <a href="#decision" className="flex items-center gap-2 font-bold tracking-tight text-slate-950"><span className="grid h-8 w-8 place-items-center rounded-lg bg-cyan-500 text-sm text-slate-950">G</span>GlacierNET‑KZ <span className="hidden text-slate-400 sm:inline">/ Command Center</span></a>
          <div className="flex gap-1 text-xs font-semibold text-slate-700"><a href="#decision" className="rounded-full px-3 py-2 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-cyan-700">Решение</a><a href="#asset-mode" className="rounded-full px-3 py-2 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-emerald-700">Объект компании</a><a href="#map" className="rounded-full px-3 py-2 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-cyan-700">Карта</a><a href="#details" className="rounded-full px-3 py-2 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-cyan-700">Доказательства</a></div>
        </div>
      </nav>

      <div className="mx-auto max-w-6xl space-y-8 px-4 py-6 sm:py-9">
        {error && <p role="alert" aria-live="assertive" className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-900">{error}</p>}
        {loading && <p role="status" aria-live="polite" className="rounded-2xl border border-cyan-200 bg-cyan-50 p-4 text-sm font-medium text-cyan-950">Проверяем реальные инвентари и локальные артефакты…</p>}

        <section id="decision" aria-labelledby="decision-title" className="scroll-mt-20 overflow-hidden rounded-3xl bg-slate-950 p-6 text-white shadow-[0_28px_70px_-35px_rgba(8,47,73,0.9)] sm:p-9">
          <div className="grid gap-7 lg:grid-cols-[1.08fr_0.92fr] lg:items-center">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-200">Реальная очередь проверки · локальный инвентарь</p>
              <h1 id="decision-title" className="mt-3 max-w-2xl text-3xl font-bold tracking-tight sm:text-5xl">Какое ледниковое озеро проверить первым?</h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300">GlacierNET‑KZ просматривает реальный инвентарь, отбирает объект для проверки и показывает <strong className="text-white">измеримые причины решения</strong>. Это не прогноз катастрофы.</p>
              {scan && <p className="mt-5 inline-flex rounded-full bg-white/10 px-3 py-2 text-sm font-semibold text-cyan-100">Просмотрено {scan.summary.scanned_lakes.toLocaleString("ru-RU")} озёр → показана объяснимая очередь</p>}
              <div className="mt-6 flex flex-wrap gap-3"><button type="button" onClick={scrollToMap} className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-cyan-400 px-4 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-cyan-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">Проверить на карте <ArrowRight className="h-4 w-4" /></button>{selectedCase && <Link href={caseHref(selectedCase)} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-white/25 px-4 py-2.5 text-sm font-semibold text-white hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">Полный паспорт <ChevronRight className="h-4 w-4" /></Link>}</div>
            </div>
            <GlacierEvidenceIntro comparableYears={evidence?.strict_trend.n_years ?? null} scannedLakes={scan?.summary.scanned_lakes ?? null} selectedPriority={selectedCase ? Math.round(selectedCase.observation_priority_0_100) : null} />
          </div>
        </section>

        {!selectedCase || !selectedGlacier ? <section className="rounded-3xl bg-white p-6 shadow-sm"><p className="text-sm text-slate-600">Загружаем первый объект из очереди…</p></section> : <>
          <section aria-labelledby="answer-title" className="rounded-3xl border border-cyan-200 bg-white p-5 shadow-sm sm:p-7">
            <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-800">Ответ системы</p><h2 id="answer-title" className="mt-1 text-2xl font-bold tracking-tight text-slate-950">Да — начать с объекта №{selectedCaseIndex || 1}</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Ледниковое озеро в координатах {coordinate(selectedCase.latitude)}° N · {coordinate(selectedCase.longitude)}° E. Инвентарный идентификатор и RGI‑контекст доступны ниже как доказательство, а не как название для пользователя.</p></div><div className="rounded-2xl bg-slate-950 px-5 py-4 text-center text-white"><p className="text-xs font-bold uppercase tracking-wide text-cyan-200">Приоритет проверки</p><p className="mt-1 text-4xl font-black">{selectedCase.observation_priority_0_100.toFixed(0)}<span className="text-lg text-slate-300">/100</span></p></div></div>

            <div className="mt-6 grid gap-3 md:grid-cols-[1fr_auto_1fr]"><article className="rounded-2xl border border-slate-200 bg-slate-50 p-5"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Инвентарь {selectedCase.previous_inventory_year ?? "до"}</p><p className="mt-2 text-3xl font-black text-slate-950">{areaKm2(selectedCase.area_previous_m2)} <span className="text-base font-semibold text-slate-500">км²</span></p><p className="mt-2 text-sm text-slate-600">Ранее сопоставленный контур озера.</p></article><div className="grid place-items-center"><div className="rounded-full bg-cyan-100 p-3 text-center"><ArrowRight className="h-7 w-7 text-cyan-800" /></div><p className="mt-2 text-center text-xl font-black text-cyan-900">{selectedCase.area_change_percent === null ? "изменение не вычислено" : `${selectedCase.area_change_percent > 0 ? "+" : ""}${selectedCase.area_change_percent.toFixed(1)}%`}</p></div><article className="rounded-2xl border border-cyan-200 bg-cyan-50 p-5"><p className="text-xs font-bold uppercase tracking-wide text-cyan-800">Инвентарь {selectedCase.inventory_year}</p><p className="mt-2 text-3xl font-black text-cyan-950">{areaKm2(selectedCase.area_current_m2)} <span className="text-base font-semibold text-cyan-800">км²</span></p><p className="mt-2 text-sm text-cyan-900">Текущий контур из локального инвентаря.</p></article></div>

            <div className="mt-5 grid gap-3 md:grid-cols-3"><article className="rounded-2xl border border-slate-200 p-4"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Почему в очереди</p><p className="mt-2 text-2xl font-black text-slate-950">+{selectedCase.priority_components?.area_change.toFixed(0) ?? "—"}</p><p className="mt-1 text-sm leading-5 text-slate-600">баллов за заметное изменение площади.</p></article><article className="rounded-2xl border border-slate-200 p-4"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Ледниковый контекст</p><p className="mt-2 text-2xl font-black text-slate-950">{selectedCase.distance_to_rgi_boundary_m.toFixed(0)} м</p><p className="mt-1 text-sm leading-5 text-slate-600">до границы RGI‑инвентаря.</p></article><article className="rounded-2xl border border-slate-200 p-4"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Архивный контекст</p><p className="mt-2 text-2xl font-black text-slate-950">{selectedCase.historical_event_count_in_glacier_context}</p><p className="mt-1 text-sm leading-5 text-slate-600">записей в пределах 10 км; это не прогноз повторения.</p></article></div>
          </section>

          <section aria-labelledby="action-title" className="rounded-3xl border border-amber-200 bg-amber-50 p-5 shadow-sm sm:p-7"><div className="flex items-start gap-3"><AlertTriangle className="mt-0.5 h-6 w-6 shrink-0 text-amber-700" /><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-amber-800">Практический результат</p><h2 id="action-title" className="mt-1 text-2xl font-bold tracking-tight text-amber-950">Следующее действие: проверить контур воды</h2><p className="mt-2 max-w-4xl text-sm leading-6 text-amber-950">Получить чистую спутниковую сцену, сопоставить границу воды с контуром инвентаря и только при расхождении направлять полевую или БПЛА‑проверку. Так сотни объектов превращаются в объяснимую очередь задач.</p></div></div><ol className="mt-5 grid gap-3 md:grid-cols-3"><li className="rounded-xl bg-white/80 p-4"><span className="text-xs font-black text-amber-700">01</span><p className="mt-2 font-bold text-slate-950">Чистый снимок</p><p className="mt-1 text-sm text-slate-600">Исключить облачность и сезонные помехи.</p></li><li className="rounded-xl bg-white/80 p-4"><span className="text-xs font-black text-amber-700">02</span><p className="mt-2 font-bold text-slate-950">Проверка контура</p><p className="mt-1 text-sm text-slate-600">Сравнить воду с контуром 2020 и 2023.</p></li><li className="rounded-xl bg-white/80 p-4"><span className="text-xs font-black text-amber-700">03</span><p className="mt-2 font-bold text-slate-950">Только при необходимости — поле</p><p className="mt-1 text-sm text-slate-600">БПЛА или выезд нужны после дистанционной проверки.</p></li></ol></section>

          <CompanyAssetMode
            candidates={scan?.candidates ?? []}
            scannedLakes={scan?.summary.scanned_lakes ?? 0}
            routeContext={companyAsset ? {
              assetId: companyAsset.id,
              status: contextStatus === "loading" ? "loading" : context?.downstream_route.available ? "available" : "unavailable",
              routeLengthKm: context?.downstream_route.route_length_km ?? null,
              corridorWidthM: context?.downstream_route.corridor_width_m ?? null,
              routeSegmentCount: context?.downstream_route.route_segment_count ?? null,
              planningAssetCount: context?.downstream_route.planning_asset_count ?? null,
              assetDistanceToRouteM: companyAssetDistanceToRouteM,
              candidateKey: regionalObservationCandidateKey(selectedCase),
            } : null}
            onSelectCandidate={(candidate, asset) => {
              setCompanyAsset(asset);
              setSelectedCaseKey(regionalObservationCandidateKey(candidate));
              window.requestAnimationFrame(scrollToMap);
            }}
          />

          {scan && <section aria-labelledby="queue-title" className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7"><div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Прозрачная очередь</p><h2 id="queue-title" className="mt-1 text-xl font-bold text-slate-950">Можно сравнить следующие реальные кандидаты</h2></div><p className="text-sm text-slate-600">Выбор меняет только объект проверки, а не формулу.</p></div><div className="mt-4 grid gap-3 lg:grid-cols-3">{scan.candidates.slice(0, 3).map((candidate, index) => { const key = regionalObservationCandidateKey(candidate); const active = key === regionalObservationCandidateKey(selectedCase); return <button key={key} type="button" onClick={() => setSelectedCaseKey(key)} aria-pressed={active} className={`min-w-0 rounded-2xl border p-4 text-left transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-700 ${active ? "border-cyan-500 bg-cyan-50" : "border-slate-200 hover:border-cyan-300 hover:bg-slate-50"}`}><div className="flex items-center justify-between gap-2"><span className="text-xs font-black text-cyan-800">ОБЪЕКТ №{index + 1}</span><span className="rounded-full bg-slate-950 px-2 py-1 text-xs font-bold text-white">{candidate.observation_priority_0_100.toFixed(0)}/100</span></div><p className="mt-3 text-sm font-bold text-slate-950">{areaKm2(candidate.area_current_m2)} км² · {candidate.area_change_percent === null ? "нет сравнения" : `${candidate.area_change_percent > 0 ? "+" : ""}${candidate.area_change_percent.toFixed(1)}%`}</p><p className="mt-1 text-xs text-slate-600">{coordinate(candidate.latitude)}° N · {coordinate(candidate.longitude)}° E</p></button>; })}</div></section>}

          <section id="map" aria-labelledby="map-title" className="scroll-mt-20 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-800">Проверка на карте</p><h2 id="map-title" className="mt-1 text-2xl font-bold tracking-tight text-slate-950">Контур озера, ледник и локальный слой — в одном месте</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Нажмите на геометрию, чтобы увидеть её источник и измерение. После выбора объекта компании карта добавляет его координату, HydroRIVERS‑маршрут и planning‑corridor — это контекст проверки, не зона воздействия.</p></div><MapPinned className="h-7 w-7 text-cyan-700" /></div><div className="mt-4"><RiskTwinMap glacier={selectedGlacier} objects={mapObjects} selectedObjectId={selectedObjectId} focusObjectId={selectedCase.lake_id ? `lake:${selectedCase.lake_id}` : `glacier:${selectedGlacier.rgi_id}`} onSelectObject={setSelectedObjectId} mode={companyAsset ? "route" : "evidence"} yearLayer={yearLayer} comparisonLayer={null} compact pinnedObjectIds={pinnedObjectIds} decisionContext={companyAsset ? { title: `Для ${companyAsset.name}`, instruction: "1) подтвердить контур озера; 2) сверить речную связь с инженерной схемой; 3) подключить телеметрию. Линия — не зона затопления.", metric: companyAssetDistanceToRouteM === null ? "Расстояние до маршрута вычисляется…" : `До оси HydroRIVERS: ${companyAssetDistanceToRouteM < 1000 ? `${companyAssetDistanceToRouteM.toFixed(0)} м` : `${(companyAssetDistanceToRouteM / 1000).toFixed(1)} км`}` } : null} /></div>{selectedObject && <p role="status" aria-live="polite" className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700"><strong>Выбрано на карте:</strong> {selectedObject.name}. {selectedObject.visibleFact}</p>}</section>

          <section id="details" aria-labelledby="details-title" className="scroll-mt-20 rounded-3xl border border-slate-200 bg-slate-100 p-5 shadow-sm sm:p-7"><div className="flex items-start gap-3"><ShieldCheck className="mt-0.5 h-6 w-6 shrink-0 text-slate-700" /><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-600">Всё исследование сохранено</p><h2 id="details-title" className="mt-1 text-2xl font-bold tracking-tight text-slate-950">Подробные доказательства — после основного решения</h2><p className="mt-2 text-sm leading-6 text-slate-600">Эти инструменты важны для проверки, но не нужны, чтобы понять главный результат за первые 30 секунд.</p></div></div><div className="mt-5 grid gap-3 md:grid-cols-3"><Link href={caseHref(selectedCase)} className="rounded-2xl bg-slate-950 p-5 text-white transition hover:bg-slate-800"><p className="text-xs font-bold uppercase tracking-wide text-cyan-200">Полный Risk Twin</p><p className="mt-2 font-bold">Все локальные слои, контекст маршрута и паспорт объекта.</p><span className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-cyan-200">Открыть <ChevronRight className="h-4 w-4" /></span></Link><Link href="/discovery" className="rounded-2xl bg-violet-700 p-5 text-white transition hover:bg-violet-600"><p className="text-xs font-bold uppercase tracking-wide text-violet-100">Похожие ледники</p><p className="mt-2 font-bold">100 сохранённых CryoGenesis‑паспортов и физически подобранные twin‑ледники.</p><span className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-violet-100">Открыть <ChevronRight className="h-4 w-4" /></span></Link><Link href="/analysis" className="rounded-2xl bg-white p-5 text-slate-950 transition hover:bg-slate-50"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Научная проверка</p><p className="mt-2 font-bold">ML‑метрики, uncertainty, строгий ряд и реестр утверждений.</p><span className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-cyan-800">Открыть <ChevronRight className="h-4 w-4" /></span></Link></div>{evidence && <details className="mt-4 rounded-2xl border border-slate-200 bg-white p-4"><summary className="cursor-pointer font-bold text-slate-950 focus-visible:outline-2 focus-visible:outline-cyan-700">Научные границы утверждений</summary><div className="mt-4 grid gap-3 md:grid-cols-2"><p className="rounded-xl bg-emerald-50 p-4 text-sm leading-6 text-emerald-950"><CheckCircle2 className="mr-2 inline h-4 w-4 text-emerald-700" />Локальный пакет: {evidence.release_checks.local_package_complete ? "готов" : "неполный"}; {evidence.release_checks.required_artifact_count} обязательных артефактов.</p><p className="rounded-xl bg-amber-50 p-4 text-sm leading-6 text-amber-950"><AlertTriangle className="mr-2 inline h-4 w-4 text-amber-700" />Не заявляются: вероятность GLOF, официальное предупреждение, независимая внешняя точность или прогноз до 2050 года.</p></div></details>}</section>
        </>}
      </div>
    </main>
  </>;
}
