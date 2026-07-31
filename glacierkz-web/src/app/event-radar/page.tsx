"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  FileSearch,
  LocateFixed,
  Radar,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import {
  fetchGlaciers,
  fetchOsintEvents,
  fetchOsintReadiness,
  fetchOsintSources,
  type GlacierRecord,
  type OsintEvent,
  type OsintRadar,
  type OsintReadiness,
  type OsintSourceCatalog,
} from "@/lib/api";

const OsintEventMap = dynamic(() => import("@/components/OsintEventMap"), { ssr: false });

const SCOPE_LABELS: Record<string, string> = {
  near_glacier: "до 25 км",
  regional_trigger_context: "25–120 км",
  broad_context: "120–350 км",
  unresolved: "без координат",
};

function confidenceLabel(value: number): string {
  if (value >= 0.8) return "высокая полнота доказательства";
  if (value >= 0.6) return "средняя полнота доказательства";
  return "ограниченное доказательство";
}

export default function EventRadarPage() {
  const [radar, setRadar] = useState<OsintRadar | null>(null);
  const [sources, setSources] = useState<OsintSourceCatalog | null>(null);
  const [readiness, setReadiness] = useState<OsintReadiness | null>(null);
  const [glaciers, setGlaciers] = useState<GlacierRecord[]>([]);
  const [selectedRgi, setSelectedRgi] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [eventType, setEventType] = useState("all");
  const [scope, setScope] = useState("all");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const loadEvents = useCallback(async (refresh = false, rgiId = selectedRgi) => {
    if (refresh) setRefreshing(true);
    setError("");
    try {
      const payload = await fetchOsintEvents({
        rgiId: rgiId || undefined,
        eventType: eventType === "all" ? undefined : eventType,
        scope: scope as "all" | "near_glacier" | "regional_trigger_context" | "broad_context" | "unresolved",
        limit: 150,
        refresh,
      });
      setRadar(payload);
      setSelectedId((current) => payload.events.some((event) => event.id === current) ? current : payload.events[0]?.id ?? null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось получить OSINT-сигналы");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [eventType, scope, selectedRgi]);

  useEffect(() => {
    Promise.all([fetchGlaciers("", false, 1000, false), fetchOsintSources(), fetchOsintReadiness()])
      .then(([registry, sourceCatalog, status]) => {
        setGlaciers(registry.glaciers);
        setSources(sourceCatalog);
        setReadiness(status);
        const requestedRgi = new URLSearchParams(window.location.search).get("rgi");
        if (requestedRgi && registry.glaciers.some((glacier) => glacier.rgi_id === requestedRgi)) {
          setSelectedRgi(requestedRgi);
        }
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Не удалось загрузить каталог источников"));
  }, []);

  useEffect(() => {
    void loadEvents(false);
  }, [loadEvents]);

  const selected = useMemo(
    () => radar?.events.find((event) => event.id === selectedId) ?? null,
    [radar, selectedId],
  );
  const eventTypes = useMemo(
    () => Array.from(new Set(radar?.events.map((event) => event.event_type) ?? [])).sort(),
    [radar],
  );

  const selectEvent = useCallback((id: string) => {
    setSelectedId(id);
    document.getElementById("event-evidence")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, []);

  return (
    <main id="main-content" className="min-h-screen bg-slate-950 text-white">
      <section className="border-b border-slate-800 bg-[radial-gradient(circle_at_top_left,_rgba(8,145,178,0.25),_transparent_36%),radial-gradient(circle_at_top_right,_rgba(249,115,22,0.18),_transparent_30%)]">
        <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
          <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
            <div className="max-w-3xl">
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-cyan-200">
                <Radar className="h-4 w-4" />
                Source-backed Event Radar
              </div>
              <h1 className="text-4xl font-black tracking-tight sm:text-5xl">Сигнал → конкретный ледник → следующее наблюдение</h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300">
                Система получает реальные каталожные события, сохраняет источник и координаты, измеряет расстояние до выбранного RGI-ледника и предлагает проверяемое действие. Она не выдаёт новость за прогноз GLOF.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link href="/risk-twin" className="rounded-xl border border-slate-600 bg-slate-900 px-4 py-3 text-sm font-bold hover:border-cyan-400">
                Открыть Risk Twin
              </Link>
              <button
                type="button"
                onClick={() => void loadEvents(true)}
                disabled={refreshing}
                className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-4 py-3 text-sm font-black text-slate-950 disabled:opacity-60"
              >
                <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
                Обновить источники
              </button>
            </div>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-7xl space-y-7 px-4 py-8 sm:px-6">
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Сводка Event Radar">
          {[
            ["Сигналов в окне", radar?.summary.events_total ?? 0, "не событий GLOF"],
            ["Для выбранного фильтра", radar?.matched ?? 0, "до 350 км от RGI"],
            ["Официальные / каталожные", radar?.summary.official_or_authoritative ?? 0, "по типу источника"],
            ["Кэш", radar?.cache.status ?? "—", `${radar?.cache.ttl_seconds ?? 0} с TTL`],
          ].map(([label, value, note]) => (
            <div key={String(label)} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">{label}</p>
              <p className="mt-2 text-3xl font-black text-white">{value}</p>
              <p className="mt-1 text-xs text-slate-500">{note}</p>
            </div>
          ))}
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
          <div className="grid gap-3 md:grid-cols-3">
            <label className="text-xs font-bold uppercase tracking-wide text-slate-400">
              Ледник
              <select
                value={selectedRgi}
                onChange={(event) => setSelectedRgi(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-3 text-sm font-medium text-white"
              >
                <option value="">Ближайший ледник для каждого сигнала</option>
                {glaciers.map((glacier) => (
                  <option key={glacier.rgi_id} value={glacier.rgi_id}>{glacier.name_ru} · {glacier.rgi_id}</option>
                ))}
              </select>
            </label>
            <label className="text-xs font-bold uppercase tracking-wide text-slate-400">
              Тип события
              <select value={eventType} onChange={(event) => setEventType(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-3 text-sm text-white">
                <option value="all">Все типы</option>
                {eventTypes.map((type) => <option key={type} value={type}>{type}</option>)}
              </select>
            </label>
            <label className="text-xs font-bold uppercase tracking-wide text-slate-400">
              Пространственная связь
              <select value={scope} onChange={(event) => setScope(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-3 text-sm text-white">
                <option value="all">Все расстояния</option>
                <option value="near_glacier">до 25 км</option>
                <option value="regional_trigger_context">25–120 км</option>
                <option value="broad_context">120–350 км</option>
                <option value="unresolved">без координат</option>
              </select>
            </label>
          </div>
        </section>

        {error && <div role="alert" className="rounded-2xl border border-red-500/40 bg-red-950/50 px-5 py-4 text-sm text-red-100">{error}</div>}
        {loading && <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center text-slate-300">Получаем и проверяем метаданные источников…</div>}

        {!loading && radar && (
          <section className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(340px,0.8fr)]">
            <OsintEventMap events={radar.events} selectedId={selectedId} onSelect={selectEvent} />
            <div id="event-evidence" className="min-h-[480px] rounded-2xl border border-slate-800 bg-slate-900 p-5">
              {selected ? <EventEvidence event={selected} /> : (
                <div className="grid h-full place-items-center text-center text-slate-400">
                  <div><LocateFixed className="mx-auto mb-3 h-8 w-8" /><p>По этому фильтру нет пространственно допустимых сигналов.</p></div>
                </div>
              )}
            </div>
          </section>
        )}

        <section className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="flex items-center gap-2 text-lg font-black"><ShieldCheck className="h-5 w-5 text-emerald-400" />Состояние источников</h2>
            <div className="mt-4 space-y-3">
              {radar?.source_health.map((source) => (
                <div key={source.source_id} className="flex items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-950 px-4 py-3">
                  <div>
                    <p className="text-sm font-bold">{source.source_id}</p>
                    <p className="text-xs text-slate-500">{source.items} нормализованных записей{source.error ? ` · ${source.error}` : ""}</p>
                  </div>
                  <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${source.status === "online" ? "bg-emerald-400/10 text-emerald-300" : "bg-amber-400/10 text-amber-200"}`}>{source.status}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="flex items-center gap-2 text-lg font-black"><AlertTriangle className="h-5 w-5 text-amber-400" />Что система честно не утверждает</h2>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-300">
              {(radar?.claims_not_allowed ?? readiness?.blocked ?? []).slice(0, 5).map((claim) => (
                <li key={claim} className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" />{claim}</li>
              ))}
            </ul>
            <p className="mt-5 rounded-xl border border-amber-400/20 bg-amber-400/5 p-3 text-xs leading-5 text-amber-100">{readiness?.safety_statement}</p>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-lg font-black">Каталог источников и условия подключения</h2>
          <p className="mt-2 text-sm text-slate-400">{sources?.content_policy}</p>
          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {sources?.sources.map((source) => (
              <a key={source.id} href={source.url} target="_blank" rel="noreferrer" className="rounded-xl border border-slate-800 bg-slate-950 p-4 transition hover:border-cyan-500/60">
                <div className="flex items-start justify-between gap-3">
                  <p className="font-bold">{source.name}</p>
                  <ExternalLink className="h-4 w-4 shrink-0 text-slate-500" />
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-400">{source.role}</p>
                <div className="mt-3 flex flex-wrap gap-2 text-[10px] font-bold uppercase tracking-wide">
                  <span className="rounded-full bg-slate-800 px-2 py-1 text-slate-300">{source.tier}</span>
                  <span className={`rounded-full px-2 py-1 ${source.configured ? "bg-emerald-400/10 text-emerald-300" : "bg-amber-400/10 text-amber-200"}`}>{source.mode}</span>
                </div>
              </a>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

function EventEvidence({ event }: { event: OsintEvent }) {
  return (
    <div className="space-y-5">
      <div>
        <div className="flex flex-wrap items-center gap-2 text-[11px] font-bold uppercase tracking-[0.12em]">
          <span className="rounded-full bg-orange-400/10 px-2.5 py-1 text-orange-200">{event.event_type}</span>
          <span className="rounded-full bg-slate-800 px-2.5 py-1 text-slate-300">{SCOPE_LABELS[event.link_scope]}</span>
        </div>
        <h2 className="mt-3 text-xl font-black leading-7">{event.title}</h2>
        <p className="mt-2 text-xs text-slate-400">{event.source_name} · {new Date(event.published_at).toLocaleString("ru-RU")}</p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Metric label="До RGI" value={event.distance_to_glacier_km == null ? "—" : `${event.distance_to_glacier_km.toFixed(1)} км`} />
        <Metric label="Приоритет наблюдения" value={`${event.observation_priority_0_100}/100`} />
        <Metric label="Evidence confidence" value={`${Math.round(event.evidence_confidence_0_1 * 100)}%`} />
        <Metric label="Magnitude" value={event.magnitude == null ? "—" : String(event.magnitude)} />
      </div>
      <div className="rounded-xl border border-cyan-400/20 bg-cyan-400/5 p-4">
        <p className="text-xs font-bold uppercase tracking-wide text-cyan-200">Почему связано</p>
        <p className="mt-2 text-sm leading-6 text-slate-200">{event.link_rationale}</p>
        {event.linked_glacier && <p className="mt-2 text-xs font-bold text-cyan-300">{event.linked_glacier.name_ru} · {event.linked_glacier.rgi_id}</p>}
      </div>
      <div className="rounded-xl border border-emerald-400/20 bg-emerald-400/5 p-4">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-emerald-200"><CheckCircle2 className="h-4 w-4" />Следующее проверяемое действие</p>
        <p className="mt-2 text-sm leading-6 text-slate-200">{event.recommended_action}</p>
      </div>
      <div className="rounded-xl border border-amber-400/20 bg-amber-400/5 p-4 text-xs leading-5 text-amber-100">
        <strong>Граница вывода:</strong> {confidenceLabel(event.evidence_confidence_0_1)} относится к метаданным сигнала, а не к вероятности GLOF. hazard_probability = null.
      </div>
      <div className="flex flex-wrap gap-2">
        <a href={event.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-black text-slate-950">
          <ExternalLink className="h-4 w-4" />Первоисточник
        </a>
        {event.linked_glacier && (
          <Link href={`/risk-twin?rgi=${encodeURIComponent(event.linked_glacier.rgi_id)}`} className="inline-flex items-center gap-2 rounded-xl border border-slate-600 px-4 py-2.5 text-sm font-bold">
            <FileSearch className="h-4 w-4" />Evidence case
          </Link>
        )}
      </div>
      <p className="break-all font-mono text-[10px] text-slate-600">sha256 {event.content_sha256}</p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-slate-800 bg-slate-950 p-3"><p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{label}</p><p className="mt-1 text-lg font-black">{value}</p></div>;
}
