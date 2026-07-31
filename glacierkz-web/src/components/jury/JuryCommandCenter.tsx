"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  FileCheck2,
  GitCompareArrows,
  MapPinned,
  Route,
  ShieldCheck,
  UsersRound,
  Waves,
} from "lucide-react";
import ScientificEvidenceCockpit from "@/components/ScientificEvidenceCockpit";
import GlacierEvidenceIntro from "@/components/jury/GlacierEvidenceIntro";
import { riskTwinHref } from "@/lib/evidenceCase";
import { buildEvidenceMapObjects } from "@/lib/riskTwinEvidence";
import type { CryoGenesisDiscoverySummary, DiscoveryPassport } from "@/lib/cryogenesis";
import {
  fetchCryoGenesisDiscoveries,
  fetchCryoGenesisPassport,
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
  loading: () => <div className="flex h-[520px] items-center justify-center rounded-2xl bg-slate-950 text-sm text-slate-300">Загрузка интерактивной карты доказательств…</div>,
});

type MapMode = "evidence" | "route" | "people";

const MAP_MODES: Array<{ id: MapMode; label: string; detail: string; icon: typeof MapPinned }> = [
  { id: "evidence", label: "Доказательства", detail: "RGI, инвентарь озёр и локальные слои", icon: MapPinned },
  { id: "route", label: "Путь", detail: "HydroRIVERS NEXT_DOWN как планировочный контекст", icon: Route },
  { id: "people", label: "Люди и объекты", detail: "OSM/GHSL только как planning context", icon: UsersRound },
];

function readableFlag(flag: string) {
  return flag.replaceAll("_", " ").replaceAll("rgi", "RGI");
}

function compact(value: number | null | undefined, digits = 0) {
  return value === null || value === undefined || !Number.isFinite(value) ? "—" : value.toLocaleString("ru-RU", { maximumFractionDigits: digits });
}

function readableSurpriseClass(value: CryoGenesisDiscoverySummary["surprise_class"]) {
  return {
    observation_inconclusive: "наблюдение неполно",
    comparison_inconclusive: "сравнение неполно",
    trajectory_consistent: "траектория согласована",
    unexplained_divergence_candidate: "кандидат на расхождение",
  }[value];
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

function ClaimValue({ value }: { value: JuryEvidence["supported_now"][number]["value"] }) {
  if (typeof value === "string") {
    return <p className="mt-3 rounded-lg bg-white/80 p-3 text-sm leading-6 text-emerald-950">{value}</p>;
  }
  return <dl className="mt-3 grid gap-2 sm:grid-cols-2">
    {Object.entries(value).map(([key, item]) => <div key={key} className="rounded-lg bg-white/80 px-3 py-2">
      <dt className="text-[11px] font-medium uppercase tracking-wide text-emerald-800">{key.replaceAll("_", " ")}</dt>
      <dd className="mt-1 break-words font-mono text-sm font-bold text-slate-950">{item === null ? "—" : String(item)}</dd>
    </div>)}
  </dl>;
}

export default function JuryCommandCenter() {
  const [evidence, setEvidence] = useState<JuryEvidence | null>(null);
  const [scan, setScan] = useState<RegionalObservationScan | null>(null);
  const [glaciers, setGlaciers] = useState<GlacierRecord[]>([]);
  const [selectedCaseKey, setSelectedCaseKey] = useState("");
  const [context, setContext] = useState<RiskTwinSpatialContext | null>(null);
  const [yearLayer, setYearLayer] = useState<YearMapLayer | null>(null);
  const [discoveries, setDiscoveries] = useState<CryoGenesisDiscoverySummary[]>([]);
  const [selectedDiscoveryId, setSelectedDiscoveryId] = useState("");
  const [passport, setPassport] = useState<DiscoveryPassport | null>(null);
  const [discoveryError, setDiscoveryError] = useState("");
  const [discoveriesLoading, setDiscoveriesLoading] = useState(true);
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);
  const [mapMode, setMapMode] = useState<MapMode>("evidence");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([
      fetchJuryEvidence(),
      fetchRegionalObservationScan(6, 10, 2023),
      fetchGlaciers("", false, 1000, true),
      fetchYearMapLayer(2024).catch(() => null),
    ])
      .then(([jury, regional, registry, layer]) => {
        if (!active) return;
        setEvidence(jury);
        setScan(regional);
        setGlaciers(registry.glaciers);
        setYearLayer(layer);
        const first = regional.candidates[0];
        if (first) setSelectedCaseKey(regionalObservationCandidateKey(first));
      })
      .catch((cause) => {
        if (active) setError(cause instanceof Error ? cause.message : "Не удалось загрузить единый пакет доказательств.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    fetchCryoGenesisDiscoveries()
      .then((payload) => {
        if (!active) return;
        setDiscoveries(payload.items);
        setSelectedDiscoveryId(payload.items[0]?.target_rgi_id ?? "");
        if (payload.status !== "ready") setDiscoveryError("Сохранённый cohort CryoGenesis пока не готов к показу.");
      })
      .catch(() => {
        if (active) setDiscoveryError("CryoGenesis сейчас недоступен; Risk Twin продолжает работать независимо.");
      })
      .finally(() => {
        if (active) setDiscoveriesLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedDiscoveryId) {
      setPassport(null);
      return;
    }
    let active = true;
    setPassport(null);
    fetchCryoGenesisPassport(selectedDiscoveryId)
      .then((next) => {
        if (active) setPassport(next);
      })
      .catch(() => {
        if (active) setDiscoveryError("Паспорт выбранного сравнительного кейса недоступен.");
      });
    return () => {
      active = false;
    };
  }, [selectedDiscoveryId]);

  const selectedCase = useMemo(
    () => scan?.candidates.find((candidate) => regionalObservationCandidateKey(candidate) === selectedCaseKey) ?? scan?.candidates[0] ?? null,
    [scan, selectedCaseKey],
  );
  const selectedGlacier = useMemo(
    () => glaciers.find((glacier) => glacier.rgi_id === selectedCase?.glacier.rgi_id) ?? null,
    [glaciers, selectedCase],
  );

  useEffect(() => {
    if (!selectedCase || !selectedGlacier) return;
    let active = true;
    setContext(null);
    setSelectedObjectId(selectedCase.lake_id ? `lake:${selectedCase.lake_id}` : `glacier:${selectedGlacier.rgi_id}`);
    fetchRiskTwinContext(selectedGlacier.rgi_id, 2024, 10, selectedCase.inventory_year)
      .then((next) => {
        if (active) setContext(next);
      })
      .catch((cause) => {
        if (active) setError(cause instanceof Error ? cause.message : "Не удалось загрузить локальный контекст Risk Twin.");
      });
    return () => {
      active = false;
    };
  }, [selectedCase, selectedGlacier]);

  const mapObjects = useMemo(
    () => buildEvidenceMapObjects(selectedGlacier, yearLayer, context, []),
    [context, selectedGlacier, yearLayer],
  );
  const selectedObject = useMemo(
    () => mapObjects.find((object) => object.id === selectedObjectId) ?? null,
    [mapObjects, selectedObjectId],
  );
  const priorityComponents = selectedCase?.priority_components;
  const priorityDrivers: Array<[string, number]> = priorityComponents
    ? ([
      ["Изменение площади", priorityComponents.area_change],
      ["Размер озера", priorityComponents.lake_size],
      ["Близость к RGI", priorityComponents.rgi_proximity],
      ["Нет надёжного предыдущего match", priorityComponents.no_reliable_previous_match],
    ] as Array<[string, number]>).filter(([, value]) => value > 0)
    : [];

  const scrollToLiveCase = () => {
    document.getElementById("live-case")?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      block: "start",
    });
  };

  return <>
    <a href="#main" aria-label="Skip to main content" className="sr-only z-[1000] rounded-md bg-slate-950 px-4 py-3 font-semibold text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-4">Перейти к содержанию Command Center</a>
    <main id="main" className="min-h-screen bg-slate-50 text-slate-900">
      <nav aria-label="Навигация Command Center" className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 px-4 py-3 shadow-sm backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
          <a href="#overview" className="flex items-center gap-2 font-bold tracking-tight text-slate-950"><span className="grid h-8 w-8 place-items-center rounded-lg bg-cyan-500 text-sm text-slate-950">G</span>GlacierNET‑KZ <span className="hidden text-slate-400 sm:inline">/ Command Center</span></a>
          <div className="flex flex-wrap gap-1 text-xs font-semibold text-slate-700">
            <a href="#overview" className="rounded-full px-3 py-2 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-cyan-700">Суть</a>
            <a href="#live-case" className="rounded-full px-3 py-2 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-cyan-700">Живой кейс</a>
            <a href="#comparisons" className="rounded-full px-3 py-2 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-cyan-700">Похожие ледники</a>
            <a href="#science" className="rounded-full px-3 py-2 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-cyan-700">Наука</a>
            <a href="#limits" className="rounded-full px-3 py-2 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-cyan-700">Границы</a>
          </div>
        </div>
      </nav>

      <div className="mx-auto max-w-7xl space-y-8 px-4 py-6 sm:py-8">
        <header id="overview" className="overflow-hidden rounded-3xl bg-slate-950 p-6 text-white shadow-[0_28px_70px_-35px_rgba(8,47,73,0.9)] sm:p-9">
          <div className="grid gap-8 xl:grid-cols-[1.15fr_0.8fr_0.55fr] xl:items-center">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-200">Active Cryosphere Evidence System</p>
              <h1 className="mt-3 max-w-4xl text-3xl font-bold tracking-tight sm:text-5xl">От спутникового слоя — к проверяемому следующему действию.</h1>
              <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-300 sm:text-base">GlacierNET‑KZ не выдаёт «магический риск». Он связывает локальные артефакты, ML‑screening, реальные озёрные инвентари и карту контекста, чтобы показать: <strong className="text-white">что известно, что проверить следующим и чего пока нельзя утверждать.</strong></p>
              <div className="mt-6 flex flex-wrap gap-3">
                <button type="button" onClick={scrollToLiveCase} className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-cyan-400 px-4 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-cyan-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">Показать живой кейс <ArrowRight className="h-4 w-4" /></button>
                {selectedCase && <Link href={caseHref(selectedCase)} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-white/25 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">Открыть полный Risk Twin <ChevronRight className="h-4 w-4" /></Link>}
              </div>
            </div>
            <GlacierEvidenceIntro
              comparableYears={evidence?.strict_trend.n_years ?? null}
              scannedLakes={scan?.summary.scanned_lakes ?? null}
              selectedPriority={selectedCase ? Math.round(selectedCase.observation_priority_0_100) : null}
            />
            <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-cyan-100">Локальный пакет</p><p className="mt-2 text-2xl font-bold">{evidence ? (evidence.release_checks.local_package_complete ? "готов" : "неполный") : "…"}</p><p className="mt-1 text-xs leading-5 text-slate-300">{evidence ? `${evidence.release_checks.required_artifact_count} обязательных артефактов` : "Проверяем артефакты"}</p></div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-cyan-100">Поддержано сейчас</p><p className="mt-2 text-2xl font-bold">{evidence?.claim_status_counts.supported_silver ?? "…"}</p><p className="mt-1 text-xs leading-5 text-slate-300">silver‑утверждений с ограниченной областью</p></div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-cyan-100">Честные стоп‑сигналы</p><p className="mt-2 text-2xl font-bold">{evidence?.blocked_until_external_work.length ?? "…"}</p><p className="mt-1 text-xs leading-5 text-slate-300">утверждений не будут показаны как доказанные</p></div>
            </div>
          </div>
        </header>

        {error && <p role="alert" aria-live="assertive" className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-900">{error}</p>}
        {loading && <p role="status" aria-live="polite" className="rounded-2xl border border-cyan-200 bg-cyan-50 p-4 text-sm font-medium text-cyan-950">Собираем локальные артефакты и реальный Risk Twin‑кейс…</p>}

        <section aria-labelledby="jury-flow-title" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-800">Как читать проект за 60 секунд</p>
          <h2 id="jury-flow-title" className="mt-1 text-2xl font-bold tracking-tight text-slate-950">Одна проверяемая цепочка вместо набора несвязанных страниц</h2>
          <ol className="mt-5 grid gap-3 md:grid-cols-4">
            {[
              ["01", "Локальные данные", "Спутниковые артефакты, RGI и инвентари с явным источником."],
              ["02", "ML‑screening", "Годовой слой показывает, что можно визуально сопоставить, а не готовый прогноз."],
              ["03", "Risk Twin", "Сам находит объекты с высокой ценностью следующей проверки и объясняет каждый балл."],
              ["04", "Решение с границей", "Выдаёт проверяемое действие и одновременно запрещает неподтверждённый вывод."],
            ].map(([number, title, detail]) => <li key={number} className="relative rounded-xl border border-slate-200 bg-slate-50 p-4"><span className="text-xs font-black tracking-widest text-cyan-700">{number}</span><h3 className="mt-2 font-bold text-slate-950">{title}</h3><p className="mt-2 text-sm leading-5 text-slate-600">{detail}</p></li>)}
          </ol>
        </section>

        <section id="comparisons" aria-labelledby="comparisons-title" className="scroll-mt-20 rounded-2xl border border-violet-200 bg-violet-50 p-5 shadow-sm sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-4"><div className="max-w-4xl"><p className="text-xs font-bold uppercase tracking-[0.16em] text-violet-800">CryoGenesis · matched physical comparisons</p><h2 id="comparisons-title" className="mt-1 text-2xl font-bold tracking-tight text-violet-950">Проверка похожих ледников: контрольная группа до результата</h2><p className="mt-2 text-sm leading-6 text-violet-950">Это отдельный исследовательский слой: для целевого ледника заранее подбираются физически похожие ледники по площади, высоте, склону, экспозиции, климату и снегу. Затем видимое расхождение траекторий становится <strong>гипотезой для проверки</strong>, а не заявлением о причине.</p></div><Link href="/discovery" className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-violet-700 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-violet-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-800">Открыть все сравнения <ChevronRight className="h-4 w-4" /></Link></div>

          {discoveriesLoading && <p role="status" aria-live="polite" className="mt-5 rounded-xl bg-white/80 p-4 text-sm text-violet-900">Загружаем сохранённые паспорта похожих ледников…</p>}
          {discoveryError && <p role="status" aria-live="polite" className="mt-5 rounded-xl border border-violet-200 bg-white/80 p-4 text-sm text-violet-900">{discoveryError}</p>}
          {discoveries.length > 0 && <><div className="mt-5 grid gap-3 lg:grid-cols-3">{discoveries.slice(0, 3).map((item, index) => {
            const active = item.target_rgi_id === selectedDiscoveryId;
            return <button key={item.target_rgi_id} type="button" onClick={() => setSelectedDiscoveryId(item.target_rgi_id)} aria-pressed={active} className={`min-w-0 rounded-2xl border p-4 text-left transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-800 ${active ? "border-violet-500 bg-white shadow-sm" : "border-violet-200 bg-violet-50/40 hover:border-violet-400 hover:bg-white/70"}`}><div className="flex items-start justify-between gap-2"><span className="text-xs font-black text-violet-800">ПАСПОРТ {index + 1}</span><span className="rounded-full bg-violet-100 px-2 py-1 text-[10px] font-bold text-violet-950">{item.twin_count} twin</span></div><p className="mt-2 break-all font-mono text-xs font-bold text-slate-950">{item.target_rgi_id}</p><p className="mt-2 text-xs leading-5 text-slate-600">{readableSurpriseClass(item.surprise_class)} · {item.match_status.replaceAll("_", " ")}</p></button>;
          })}</div>
          {passport && <div className="mt-4 grid gap-3 lg:grid-cols-[0.72fr_1.28fr]"><article className="rounded-2xl bg-slate-950 p-5 text-white"><div className="flex items-start gap-2"><GitCompareArrows className="mt-0.5 h-5 w-5 shrink-0 text-violet-200" /><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-violet-200">Выбранное сравнение</p><h3 className="mt-1 break-all font-mono text-sm font-bold">{passport.target_rgi_id}</h3></div></div><dl className="mt-4 grid grid-cols-2 gap-2 text-sm"><div className="rounded-xl bg-white/10 p-3"><dt className="text-xs text-violet-100">Подобрано twin</dt><dd className="mt-1 text-xl font-bold">{passport.match.twins.length}</dd></div><div className="rounded-xl bg-white/10 p-3"><dt className="text-xs text-violet-100">Cohort</dt><dd className="mt-1 break-all font-mono text-xs font-bold">{passport.cohort_id}</dd></div>{passport.divergence && <><div className="rounded-xl bg-white/10 p-3"><dt className="text-xs text-violet-100">Raw divergence</dt><dd className="mt-1 text-xl font-bold">{passport.divergence.raw_divergence.toFixed(3)}</dd></div><div className="rounded-xl bg-white/10 p-3"><dt className="text-xs text-violet-100">Standardised</dt><dd className="mt-1 text-xl font-bold">{passport.divergence.standardized_divergence?.toFixed(2) ?? "—"}</dd></div></>}</dl><p className="mt-4 text-xs leading-5 text-slate-300">Наблюдаемое расхождение в сохранённом cohort; не причинный эффект и не прогноз.</p></article><article className="rounded-2xl border border-violet-200 bg-white p-5"><p className="text-xs font-bold uppercase tracking-[0.16em] text-violet-800">Физически подобранные twin</p><ol className="mt-3 space-y-2">{passport.match.twins.slice(0, 5).map((twin, index) => <li key={twin.rgi_id} className="flex min-w-0 items-center justify-between gap-3 rounded-xl bg-violet-50 px-3 py-2.5"><div className="min-w-0"><span className="mr-2 text-xs font-black text-violet-700">{index + 1}</span><span className="break-all font-mono text-xs font-bold text-slate-950">{twin.rgi_id}</span></div><span className="shrink-0 rounded-full bg-white px-2 py-1 text-xs font-bold text-violet-950">d={twin.total_distance.toFixed(3)}</span></li>)}</ol><p className="mt-4 rounded-xl bg-violet-50 p-3 text-xs leading-5 text-violet-950"><strong>Можно:</strong> {passport.claims_allowed[0]}. <strong>Нельзя:</strong> {passport.claims_not_allowed[0]}.</p></article></div>}</>}
        </section>

        <section id="live-case" aria-labelledby="live-case-title" className="scroll-mt-20 space-y-5">
          <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-800">Live Risk Twin · real inventory screening</p><h2 id="live-case-title" className="mt-1 text-2xl font-bold tracking-tight text-slate-950">Живой кейс: объект найден автоматически, а не добавлен для демонстрации</h2><p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">Выберите любой из первых реальных кандидатов. Приоритет — это ценность проверки инвентарного объекта, <strong>не вероятность прорыва, не уровень угрозы и не официальное предупреждение.</strong></p></div><span className="rounded-full bg-cyan-100 px-3 py-1.5 text-xs font-bold text-cyan-950">{scan ? `${scan.returned} кандидатов из ${scan.summary.scanned_lakes.toLocaleString("ru-RU")} озёр` : "Загрузка scan…"}</span></div>

          {scan && <div className="grid gap-3 lg:grid-cols-3">{scan.candidates.slice(0, 3).map((candidate, index) => {
            const key = regionalObservationCandidateKey(candidate);
            const active = key === regionalObservationCandidateKey(selectedCase ?? candidate);
            return <button key={key} type="button" onClick={() => setSelectedCaseKey(key)} aria-pressed={active} className={`min-h-24 rounded-2xl border p-4 text-left transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-700 ${active ? "border-cyan-500 bg-cyan-50 shadow-sm" : "border-slate-200 bg-white hover:border-cyan-300 hover:bg-slate-50"}`}><div className="flex items-start justify-between gap-3"><span className="text-xs font-black text-cyan-800">КЕЙС {index + 1}</span><span className="rounded-full bg-slate-950 px-2 py-1 text-xs font-bold text-white">{candidate.observation_priority_0_100.toFixed(0)}/100</span></div><p className="mt-2 truncate font-mono text-sm font-bold text-slate-950">{candidate.lake_id ?? "озеро без ID"}</p><p className="mt-1 text-xs leading-5 text-slate-600">{candidate.glacier.name_ru || candidate.glacier.name} · {candidate.distance_to_rgi_boundary_m.toFixed(0)} м до RGI</p></button>;
          })}</div>}

          {!selectedCase || !selectedGlacier ? <div className="rounded-2xl bg-slate-950 p-6 text-sm text-slate-300">Загрузка выбранного географического контекста…</div> : <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
            <div className="min-w-0 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><div><p className="text-xs font-bold uppercase tracking-[0.14em] text-cyan-800">Карта реальных слоёв</p><p className="mt-1 text-sm text-slate-600">Нажмите объект на карте: его источник, допустимое и запрещённое утверждение откроются в popup.</p></div><div className="flex flex-wrap gap-2">{MAP_MODES.map((mode) => { const Icon = mode.icon; return <button key={mode.id} type="button" onClick={() => setMapMode(mode.id)} aria-pressed={mapMode === mode.id} className={`inline-flex min-h-10 items-center gap-2 rounded-lg px-3 py-2 text-xs font-bold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-700 ${mapMode === mode.id ? "bg-slate-950 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}><Icon className="h-4 w-4" />{mode.label}</button>; })}</div></div>
              <RiskTwinMap glacier={selectedGlacier} objects={mapObjects} selectedObjectId={selectedObjectId} onSelectObject={setSelectedObjectId} mode={mapMode} yearLayer={yearLayer} comparisonLayer={null} />
            </div>

            <aside aria-label="Паспорт выбранного Risk Twin кейса" className="space-y-4">
              <article className="rounded-2xl bg-slate-950 p-5 text-white shadow-sm"><p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-200">Выбранный объект</p><h3 className="mt-2 break-all font-mono text-lg font-bold">{selectedCase.lake_id ?? "Lake ID unavailable"}</h3><p className="mt-2 text-sm text-slate-300">Контекст ледника: {selectedGlacier.name_ru || selectedGlacier.name} · {selectedGlacier.rgi_id}</p><dl className="mt-4 grid grid-cols-2 gap-2 text-sm"><div className="rounded-xl bg-white/10 p-3"><dt className="text-xs text-cyan-100">Площадь 2023</dt><dd className="mt-1 font-bold">{(selectedCase.area_current_m2 / 1_000_000).toFixed(3)} км²</dd></div><div className="rounded-xl bg-white/10 p-3"><dt className="text-xs text-cyan-100">Изменение к {selectedCase.previous_inventory_year ?? "—"}</dt><dd className="mt-1 font-bold">{selectedCase.area_change_percent === null ? "нет match" : `${selectedCase.area_change_percent > 0 ? "+" : ""}${selectedCase.area_change_percent.toFixed(1)}%`}</dd></div><div className="rounded-xl bg-white/10 p-3"><dt className="text-xs text-cyan-100">До RGI</dt><dd className="mt-1 font-bold">{selectedCase.distance_to_rgi_boundary_m.toFixed(0)} м</dd></div><div className="rounded-xl bg-white/10 p-3"><dt className="text-xs text-cyan-100">Записи в контексте</dt><dd className="mt-1 font-bold">{selectedCase.historical_event_count_in_glacier_context}</dd></div></dl></article>

              <article className="rounded-2xl border border-cyan-200 bg-cyan-50 p-5"><p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-900">Почему очередь {selectedCase.observation_priority_0_100.toFixed(0)}/100</p><p className="mt-2 text-sm leading-6 text-cyan-950">Формула фиксирована и видима. Она ранжирует ценность последующей проверки, а не опасность.</p><div className="mt-4 space-y-2">{priorityDrivers.map(([label, value]) => <div key={label} className="flex items-center justify-between rounded-xl bg-white px-3 py-2 text-sm"><span>{label}</span><strong>+{value.toFixed(0)}</strong></div>)}</div><p className="mt-3 text-xs text-cyan-900">База +{compact(priorityComponents?.base_follow_up)} · сумма до ограничения {compact(priorityComponents?.total_before_cap)}.</p></article>

              <article className="rounded-2xl border border-amber-200 bg-amber-50 p-5"><div className="flex items-start gap-2"><AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" /><div><h3 className="font-bold text-amber-950">Следующее проверяемое действие</h3><p className="mt-1 text-sm leading-6 text-amber-900">Получить чистую спутниковую сцену и проверить контур воды; затем при необходимости проверить границу в поле или БПЛА.</p></div></div><div className="mt-3 flex flex-wrap gap-1.5">{selectedCase.flags.map((flag) => <span key={flag} className="rounded-full bg-white px-2 py-1 text-[11px] font-semibold text-amber-950">{readableFlag(flag)}</span>)}</div></article>
            </aside>
          </div>}

          {context && <div className="grid gap-3 md:grid-cols-3"><article className="rounded-xl border border-sky-100 bg-sky-50 p-4"><Waves className="h-5 w-5 text-sky-700" /><h3 className="mt-2 font-bold text-sky-950">Путь и вода</h3><p className="mt-2 text-sm leading-6 text-sky-900">{context.downstream_route.available ? `${context.downstream_route.route_length_km?.toFixed(1) ?? "—"} км · ${context.downstream_route.route_segment_count ?? 0} сегментов HydroRIVERS NEXT_DOWN.` : "Доступен только локальный гидрографический контекст."}</p><p className="mt-2 text-xs text-sky-800">Не является моделированием потока, временем добегания или зоной затопления.</p></article><article className="rounded-xl border border-violet-100 bg-violet-50 p-4"><UsersRound className="h-5 w-5 text-violet-700" /><h3 className="mt-2 font-bold text-violet-950">Люди и объекты</h3><p className="mt-2 text-sm leading-6 text-violet-900">{context.impact_assets.available ? `OSM planning context: ${context.impact_assets.nearby_asset_count ?? context.impact_assets.returned_feature_count ?? 0} объектов в локальном окне.` : "Локальный атрибутированный OSM extract недоступен — объекты не выдумываются."}</p><p className="mt-2 text-xs text-violet-800">Не является числом затронутых людей или подтверждённой экспозицией.</p></article><article className="rounded-xl border border-rose-100 bg-rose-50 p-4"><Route className="h-5 w-5 text-rose-700" /><h3 className="mt-2 font-bold text-rose-950">Архивный контекст</h3><p className="mt-2 text-sm leading-6 text-rose-900">{context.layers.historical_glof_events.features.length} записей HMAGLOFDB в выбранном пространственном контексте; каждая требует проверки первоисточника.</p><p className="mt-2 text-xs text-rose-800">Архивная близость не доказывает повторение или вероятность события.</p></article></div>}

          {selectedObject && <p role="status" aria-live="polite" className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700"><strong>Выбрано на карте:</strong> {selectedObject.name}. {selectedObject.visibleFact}</p>}
        </section>

        {evidence && <section aria-labelledby="evidence-now-title" className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 sm:p-6"><div className="flex items-start gap-3"><CheckCircle2 className="mt-0.5 h-6 w-6 shrink-0 text-emerald-700" /><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-800">Что подтверждено локально</p><h2 id="evidence-now-title" className="mt-1 text-2xl font-bold tracking-tight text-emerald-950">Проверяемые результаты, а не декларации</h2><p className="mt-2 max-w-4xl text-sm leading-6 text-emerald-900">Каждый блок связывает число с локальным артефактом и областью, в которой оно допустимо.</p></div></div><div className="mt-5 grid gap-3 lg:grid-cols-2">{evidence.supported_now.map((item) => <article key={item.title} className="rounded-xl border border-emerald-100 bg-emerald-50/60 p-4"><h3 className="font-bold text-emerald-950">{item.title}</h3><ClaimValue value={item.value} /><p className="mt-3 rounded-lg bg-white/80 p-3 text-xs leading-5 text-emerald-950"><strong>Scope:</strong> {item.scope}</p></article>)}</div></section>}

        {evidence && <section id="science" aria-labelledby="science-title" className="scroll-mt-20 space-y-4"><div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]"><article className="rounded-2xl border border-amber-200 bg-amber-50 p-5"><p className="text-xs font-bold uppercase tracking-[0.16em] text-amber-800">Проверка на прочность</p><h2 id="science-title" className="mt-1 text-xl font-bold text-amber-950">Сложный внешний результат показан, а не спрятан</h2><p className="mt-3 text-sm leading-6 text-amber-900">{evidence.honest_negative_result.meaning}</p><div className="mt-4 grid grid-cols-2 gap-2"><div className="rounded-xl bg-white p-3"><p className="text-xs text-slate-500">Hard Dice</p><p className="mt-1 text-xl font-mono font-bold">{evidence.honest_negative_result.hard_dice.estimate.toFixed(3)}</p><p className="text-xs text-slate-600">95% CI {evidence.honest_negative_result.hard_dice.ci_lower.toFixed(3)}–{evidence.honest_negative_result.hard_dice.ci_upper.toFixed(3)}</p></div><div className="rounded-xl bg-white p-3"><p className="text-xs text-slate-500">Area error</p><p className="mt-1 text-xl font-mono font-bold">{evidence.honest_negative_result.area_error_percent.estimate.toFixed(0)}%</p><p className="text-xs text-slate-600">Внешняя генерализация не доказана</p></div></div></article><article className="rounded-2xl border border-cyan-200 bg-cyan-50 p-5"><p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-800">Строгий временной тренд</p><h3 className="mt-1 text-xl font-bold text-cyan-950">{evidence.strict_trend.n_years} сопоставимых лет в проверяемом ряду</h3><p className="mt-3 text-3xl font-mono font-bold text-cyan-950">{evidence.strict_trend.slope_km2_per_year.toFixed(2)} км²/год</p><p className="mt-2 text-sm leading-6 text-cyan-900">p={evidence.strict_trend.p_value.toFixed(4)} · {evidence.strict_trend.significant ? "статистически значимо в заданном протоколе" : "не заявляется как значимый"}. {evidence.strict_trend.meaning}</p><p className="mt-4 rounded-xl bg-white p-3 text-xs leading-5 text-cyan-950">Это анализ доступного строгого ряда; он не превращается автоматически в прогноз к 2050 году или доказательство для другого региона.</p></article></div><details className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><summary className="cursor-pointer list-none font-bold text-slate-950 focus-visible:outline-2 focus-visible:outline-cyan-700"><span className="inline-flex items-center gap-2"><FileCheck2 className="h-5 w-5 text-cyan-700" />Открыть полный Scientific Evidence Cockpit: метрики, CI, артефакты и registry утверждений</span></summary><div className="mt-4"><ScientificEvidenceCockpit science={evidence.scientific_evidence} /></div></details></section>}

        {evidence && <section id="limits" aria-labelledby="limits-title" className="scroll-mt-20 rounded-2xl border border-slate-300 bg-slate-100 p-5 sm:p-6"><div className="flex items-start gap-3"><ShieldCheck className="mt-0.5 h-6 w-6 shrink-0 text-slate-700" /><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-600">Научная честность — часть продукта</p><h2 id="limits-title" className="mt-1 text-2xl font-bold tracking-tight text-slate-950">Что GlacierNET‑KZ не будет обещать без внешней проверки</h2></div></div><ul className="mt-5 grid gap-3 lg:grid-cols-3">{evidence.blocked_until_external_work.map((item) => <li key={item.id} className="min-w-0 rounded-xl border border-slate-200 bg-white p-4"><div className="flex min-w-0 gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" /><div className="min-w-0"><h3 className="font-bold text-slate-950">{item.claim}</h3><p className="mt-2 text-sm leading-5 text-slate-600">{item.scope}</p><p className="mt-3 break-all text-xs font-medium text-slate-700">Нужно: {item.evidence.join(" · ")}</p></div></div></li>)}</ul></section>}

        <footer className="rounded-2xl bg-slate-950 p-5 text-slate-200 sm:p-6"><div className="flex flex-wrap items-center justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-200">Один экран для показа — глубокие инструменты по ссылке</p><p className="mt-2 text-sm text-slate-300">На защите начните с «Живого кейса», покажите сравнение физических twin, кликните объект на карте и завершите блоком границ.</p></div><div className="flex flex-wrap gap-2"><Link href="/risk-twin" className="rounded-lg bg-cyan-400 px-3 py-2 text-sm font-bold text-slate-950 hover:bg-cyan-300">Полный Risk Twin</Link><Link href="/discovery" className="rounded-lg border border-violet-300/50 px-3 py-2 text-sm font-semibold text-violet-100 hover:bg-violet-500/20">CryoGenesis</Link><Link href="/operations" className="rounded-lg border border-white/20 px-3 py-2 text-sm font-semibold text-white hover:bg-white/10">Operations</Link><Link href="/analysis" className="rounded-lg border border-white/20 px-3 py-2 text-sm font-semibold text-white hover:bg-white/10">AI Evidence</Link></div></div></footer>
      </div>
    </main>
  </>;
}
