"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Database,
  ExternalLink,
  FlaskConical,
  HardDriveDownload,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import {
  fetchCentralAsiaBenchmark,
  type BenchmarkSource,
  type BenchmarkTrack,
  type CentralAsiaBenchmarkReport,
} from "@/lib/api";

function statusTone(status: string) {
  if (status.startsWith("measured") || status === "verified_local") {
    return "border-emerald-200 bg-emerald-50 text-emerald-900";
  }
  if (status.includes("ready") || status === "local_unverified") {
    return "border-amber-200 bg-amber-50 text-amber-950";
  }
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function readableStatus(status: string) {
  return status.replaceAll("_", " ");
}

function metricRows(metrics: Record<string, unknown>) {
  return Object.entries(metrics).flatMap(([key, value]) => {
    if (value === null || value === undefined) return [];
    if (typeof value === "object") return [];
    const rendered = typeof value === "number"
      ? Math.abs(value) < 10 ? value.toFixed(4) : value.toFixed(2)
      : String(value);
    return [{ key, value: rendered }];
  });
}

function TrackCard({ track }: { track: BenchmarkTrack }) {
  const metrics = metricRows(track.headline_metrics ?? track.metrics);
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">{track.id}</p>
          <h2 className="mt-1 text-xl font-semibold">{track.title}</h2>
          {track.scope && <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{track.scope}</p>}
        </div>
        <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusTone(track.status)}`}>
          {readableStatus(track.status)}
        </span>
      </div>
      {metrics.length > 0 ? (
        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => (
            <div key={metric.key} className="rounded-xl bg-slate-950 p-4 text-white">
              <p className="break-words text-xs text-slate-400">{readableStatus(metric.key)}</p>
              <p className="mt-2 text-2xl font-bold text-cyan-300">{metric.value}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-5 flex items-start gap-2 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
          Метрика не показывается, пока реальный frozen test не выполнен.
        </div>
      )}
      <div className="mt-5 grid gap-3 text-sm md:grid-cols-2">
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-950">
          <p className="font-semibold">Что уже можно утверждать</p>
          <p className="mt-1 leading-6">{track.claim_allowed ?? "Пока только готовность данных и протокола."}</p>
        </div>
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-950">
          <p className="font-semibold">Что нельзя утверждать</p>
          <p className="mt-1 leading-6">{track.claim_not_allowed ?? "Нет дополнительных ограничений."}</p>
        </div>
      </div>
      {track.blockers && track.blockers.length > 0 && (
        <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
          <p className="font-semibold">Release blockers measured from persisted evidence</p>
          <ul className="mt-2 space-y-1">{track.blockers.map((blocker) => <li key={blocker}>• {readableStatus(blocker)}</li>)}</ul>
        </div>
      )}
    </article>
  );
}

function SourceRow({ source }: { source: BenchmarkSource }) {
  return (
    <div className="grid gap-2 border-b border-slate-100 px-4 py-4 last:border-0 lg:grid-cols-[1.2fr_1.5fr_0.7fr_auto] lg:items-center">
      <div>
        <p className="font-semibold">{source.title}</p>
        <p className="mt-1 text-xs text-slate-500">{source.evidence_tier}</p>
      </div>
      <p className="text-sm leading-6 text-slate-600">{source.role}</p>
      <div className="text-sm text-slate-600">
        <p>{source.size_bytes ? `${(source.size_bytes / 1e6).toFixed(1)} MB` : "not local"}</p>
        <p className="text-xs">{source.integrity}</p>
      </div>
      <div className="flex items-center gap-2">
        <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${statusTone(source.state)}`}>
          {readableStatus(source.state)}
        </span>
        <a href={source.citation_url} target="_blank" rel="noreferrer" aria-label={`Source: ${source.title}`} className="rounded-lg p-2 text-blue-700 hover:bg-blue-50">
          <ExternalLink className="h-4 w-4" />
        </a>
      </div>
    </div>
  );
}

export default function BenchmarkPage() {
  const [report, setReport] = useState<CentralAsiaBenchmarkReport | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchCentralAsiaBenchmark()
      .then(setReport)
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Benchmark could not be loaded"));
  }, []);

  const verifiedSources = useMemo(
    () => report?.summary.sources_verified
      ?? report?.sources.filter((source) => source.state === "verified_local").length
      ?? 0,
    [report]
  );
  const modelTracks = useMemo(
    () => report?.tracks.filter((track) => track.category === "model_evaluation") ?? [],
    [report]
  );
  const referenceTracks = useMemo(
    () => report?.tracks.filter((track) => track.category === "reference_evidence") ?? [],
    [report]
  );
  const decisionTracks = useMemo(
    () => report?.tracks.filter((track) => track.category === "decision_support_evaluation") ?? [],
    [report]
  );
  const summaryCards = report
    ? [
        { label: "Verified sources", value: verifiedSources, Icon: Database },
        { label: "Local sources", value: report.summary.sources_local, Icon: HardDriveDownload },
        { label: "Measured model tests", value: report.summary.model_evaluations_measured, Icon: CheckCircle2 },
        { label: "Reference layers", value: report.summary.reference_evidence_available, Icon: FlaskConical },
        { label: "Blocked honestly", value: report.summary.tracks_blocked, Icon: AlertTriangle },
        { label: "Missing sources", value: report.summary.sources_missing ?? 0, Icon: AlertTriangle },
      ]
    : [];

  if (!report && !error) {
    return <main className="flex min-h-screen items-center justify-center gap-3 bg-slate-950 text-white"><Loader2 className="h-6 w-6 animate-spin text-cyan-300" />Loading evidence-bound benchmark…</main>;
  }

  return (
    <div className="min-h-screen bg-[#f4f7fb] text-slate-950">
      <header className="border-b border-slate-800 bg-slate-950 text-white">
        <div className="mx-auto flex max-w-[1500px] items-center gap-3 px-4 py-4 sm:px-6">
          <Link href="/" aria-label="Back" className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"><ArrowLeft className="h-5 w-5" /></Link>
          <div className="rounded-xl bg-cyan-400/10 p-2 text-cyan-300"><FlaskConical className="h-6 w-6" /></div>
          <div>
            <p className="font-semibold">CentralAsia-GlacierBench</p>
            <p className="text-xs text-slate-400">Frozen splits · real sources · no synthetic scores</p>
          </div>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-[1500px] space-y-6 px-4 py-6 sm:px-6">
        {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-900">{error}</p>}
        {report && (
          <>
            <section className="overflow-hidden rounded-3xl bg-slate-950 px-6 py-8 text-white shadow-xl sm:px-10">
              <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.18em] text-cyan-300"><ShieldCheck className="h-4 w-4" />Scientific release gate</p>
              <h1 className="mt-4 max-w-5xl text-3xl font-bold tracking-tight sm:text-5xl">Одна панель показывает не только результат модели, но и силу доказательства.</h1>
              <p className="mt-4 max-w-4xl text-base leading-7 text-slate-300">Каждый track отделяет наблюдения, inventory labels и физические модельные сценарии. Отсутствующая проверка остаётся заблокированной — нулевой или синтетический результат не подставляется.</p>
              <div className="mt-7 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
                {summaryCards.map(({ label, value, Icon }) => (
                  <div key={label} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <Icon className="h-5 w-5 text-cyan-300" />
                    <p className="mt-3 text-xs text-slate-400">{label}</p>
                    <p className="mt-1 text-3xl font-bold">{value}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="space-y-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.14em] text-blue-700">Model evaluation</p>
                <h2 className="mt-1 text-2xl font-bold">Что действительно измеряет качество алгоритмов</h2>
                <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">Dice, IoU и paired deltas относятся только к явно указанным frozen test и silver-label протоколам. Наблюдательные datasets не повышают эти оценки.</p>
              </div>
              {modelTracks.map((track) => <TrackCard key={track.id} track={track} />)}
            </section>

            <section className="space-y-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.14em] text-violet-700">Reference evidence</p>
                <h2 className="mt-1 text-2xl font-bold">Независимый физический и событийный контекст</h2>
                <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">ITS_LIVE, Hugonnet, lake inventories и HMAGLOFDB показывают доступность реальных наблюдений. Это доказательства контекста, а не accuracy модели и не вероятность опасного события.</p>
              </div>
              {referenceTracks.map((track) => <TrackCard key={track.id} track={track} />)}
            </section>

            <section className="space-y-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.14em] text-amber-700">Decision-support evaluation</p>
                <h2 className="mt-1 text-2xl font-bold">Политика следующего наблюдения — только через реальный replay</h2>
                <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">Gate считает только source-reviewed события, проверенные non-event controls, immutable pre-event snapshots и фактически измеренное снижение decision loss. Пустые таблицы не превращаются в нулевой score.</p>
              </div>
              {decisionTracks.map((track) => <TrackCard key={track.id} track={track} />)}
            </section>

            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-200 px-5 py-4">
                <p className="text-sm font-semibold uppercase tracking-[0.14em] text-blue-700">Source ledger</p>
                <h2 className="mt-1 text-2xl font-bold">Реальные источники и их фактическое состояние</h2>
              </div>
              {report.sources.map((source) => <SourceRow key={source.id} source={source} />)}
            </section>

            <section className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-rose-950">
              <h2 className="font-semibold">Даже этот benchmark не разрешает заявлять</h2>
              <ul className="mt-3 space-y-2 text-sm">
                {(report.claims_not_unlocked ?? []).map((claim) => <li key={claim}>• {claim}</li>)}
              </ul>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
