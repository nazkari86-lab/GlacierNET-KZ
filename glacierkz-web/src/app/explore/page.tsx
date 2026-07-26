"use client";

/* eslint-disable @next/next/no-img-element -- local scientific overlays are served by the API. */

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  Bot,
  CheckCircle2,
  Download,
  GitCompareArrows,
  Loader2,
  Mountain,
} from "lucide-react";
import {
  compareLocalYears,
  fetchYears,
  type YearComparison,
  type YearResult,
} from "@/lib/api";
import { useI18n } from "@/lib/I18nProvider";

function QualityBadge({ year }: { year: YearResult }) {
  const good = year.include_in_strict_trend;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${
        good ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
      }`}
    >
      {good ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
      {year.quality_score}/100 · {year.confidence}
    </span>
  );
}

export default function ExplorePage() {
  const { t } = useI18n();
  const [years, setYears] = useState<YearResult[]>([]);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [compareYear, setCompareYear] = useState<number | null>(null);
  const [comparison, setComparison] = useState<YearComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchYears()
      .then((records) => {
        setYears(records);
        if (records.length) {
          setSelectedYear(records[records.length - 1].year);
          setCompareYear(records[0].year);
        }
      })
      .catch((cause) => setError(String(cause)))
      .finally(() => setLoading(false));
  }, []);

  const selected = useMemo(
    () => years.find((item) => item.year === selectedYear) ?? null,
    [years, selectedYear]
  );

  const runComparison = async () => {
    if (selectedYear === null || compareYear === null || selectedYear === compareYear) return;
    setLoading(true);
    setError("");
    try {
      setComparison(await compareLocalYears(compareYear, selectedYear));
    } catch (cause) {
      setError(String(cause));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
          <Link href="/" className="text-zinc-400 hover:text-zinc-700" aria-label={t("nav.back")}>
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <Mountain className="h-5 w-5 text-blue-600" aria-hidden="true" />
          <span className="font-bold">{t("explore.title")}</span>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900">{t("explore.title")}</h1>
          <p className="mt-2 max-w-3xl text-zinc-600">{t("explore.subtitle")}</p>
        </div>

        {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</p>}

        <section className="grid gap-4 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm md:grid-cols-[1fr_1fr_auto] md:items-end">
          <label className="space-y-1">
            <span className="text-sm font-medium text-zinc-700">{t("explore.view_year")}</span>
            <select
              value={selectedYear ?? ""}
              onChange={(event) => {
                setSelectedYear(Number(event.target.value));
                setComparison(null);
              }}
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2"
            >
              {years.map((item) => (
                <option key={item.year} value={item.year}>
                  {item.year} · {item.sensor} · {item.quality_score}/100
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1">
            <span className="text-sm font-medium text-zinc-700">{t("explore.compare_with")}</span>
            <select
              value={compareYear ?? ""}
              onChange={(event) => setCompareYear(Number(event.target.value))}
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2"
            >
              {years.map((item) => (
                <option key={item.year} value={item.year}>{item.year} · {item.sensor}</option>
              ))}
            </select>
          </label>
          <button
            onClick={runComparison}
            disabled={loading || selectedYear === compareYear}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <GitCompareArrows className="h-4 w-4" />}
            {t("explore.compare")}
          </button>
        </section>

        {loading && !selected && (
          <div className="flex items-center justify-center gap-2 rounded-xl bg-white p-16 text-zinc-500">
            <Loader2 className="h-5 w-5 animate-spin" />
            {t("explore.loading")}
          </div>
        )}

        {selected && (
          <>
            <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl bg-white p-5 shadow-sm">
                <p className="text-sm text-zinc-500">{t("explore.primary_area")}</p>
                <p className="mt-1 text-3xl font-bold text-blue-700">{selected.primary_area_km2.toFixed(2)} km²</p>
                <p className="mt-1 text-xs text-zinc-400">{selected.primary_method}</p>
              </div>
              <div className="rounded-xl bg-white p-5 shadow-sm">
                <p className="text-sm text-zinc-500">{t("explore.sensor")}</p>
                <p className="mt-1 text-xl font-semibold" data-testid="selected-sensor">{selected.sensor}</p>
                <p className="mt-1 text-xs text-zinc-400">{selected.source_flag}</p>
              </div>
              <div className="rounded-xl bg-white p-5 shadow-sm">
                <p className="text-sm text-zinc-500">{t("explore.quality")}</p>
                <div className="mt-2"><QualityBadge year={selected} /></div>
              </div>
              <div className="rounded-xl bg-white p-5 shadow-sm">
                <p className="text-sm text-zinc-500">{t("explore.artifacts")}</p>
                <p className="mt-1 text-xl font-semibold">{selected.artifact_methods.length}</p>
                <p className="mt-1 text-xs text-zinc-400">{selected.artifact_status}</p>
              </div>
            </section>

            {selected.caveat && (
              <section className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
                <div><strong>{t("explore.limit")}:</strong> {selected.caveat}</div>
              </section>
            )}

            <section className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
              <div className="rounded-xl bg-white p-5 shadow-sm">
                <h2 className="mb-4 text-lg font-semibold">{selected.year} · {t("explore.overlay")}</h2>
                {selected.overlay_url ? (
                  <img
                    src={selected.overlay_url}
                    alt={`Glacier segmentation overlay for ${selected.year}`}
                    className="max-h-[620px] w-full rounded-lg bg-zinc-100 object-contain"
                  />
                ) : (
                  <div className="flex min-h-80 items-center justify-center rounded-lg bg-zinc-100 p-8 text-center text-zinc-500">
                    {t("explore.metadata_only")}
                  </div>
                )}
              </div>

              <div className="space-y-4">
                <Link
                  href={`/analysis?year=${selected.year}`}
                  className="flex items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 py-3 font-medium text-white hover:bg-violet-700"
                >
                  <Bot className="h-5 w-5" />
                  {t("explore.ask_ai")}
                </Link>
                <section className="rounded-xl bg-white p-5 shadow-sm">
                  <h2 className="font-semibold">{t("explore.methods")}</h2>
                  <div className="mt-3 space-y-3">
                    {Object.values(selected.methods).map((method) => (
                      <div key={method.name} className="rounded-lg border border-zinc-200 p-3">
                        <div className="flex items-center justify-between">
                          <span className="font-medium uppercase">{method.name}</span>
                          <span className="text-sm font-semibold">{method.area_km2.toFixed(2)} km²</span>
                        </div>
                        {method.mask_url && (
                          <a className="mt-2 inline-flex items-center gap-1 text-xs text-blue-600 hover:underline" href={method.mask_url}>
                            <Download className="h-3.5 w-3.5" /> {t("explore.download_mask")}
                          </a>
                        )}
                      </div>
                    ))}
                    {!Object.keys(selected.methods).length && (
                      <p className="text-sm text-zinc-500">{t("explore.metadata_only")}</p>
                    )}
                  </div>
                </section>

                <section className="rounded-xl bg-white p-5 shadow-sm">
                  <h2 className="font-semibold">{t("explore.provenance")}</h2>
                  <p className="mt-2 break-all text-xs text-zinc-500">{selected.source_file}</p>
                  {selected.source_size_mb && <p className="mt-1 text-xs text-zinc-500">{selected.source_size_mb} MB</p>}
                  {selected.provenance_url && (
                    <a className="mt-3 inline-flex items-center gap-1 text-sm text-blue-600 hover:underline" href={selected.provenance_url}>
                      <Download className="h-4 w-4" /> JSON provenance
                    </a>
                  )}
                </section>
              </div>
            </section>
          </>
        )}

        {comparison && (
          <section className="rounded-xl border border-blue-200 bg-blue-50 p-6">
            <h2 className="text-xl font-semibold text-blue-950">
              {comparison.from.year} → {comparison.to.year}
            </h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              <div><p className="text-sm text-blue-700">{t("explore.change")}</p><p className="text-2xl font-bold">{comparison.change_km2.toFixed(2)} km²</p></div>
              <div><p className="text-sm text-blue-700">{t("explore.change_percent")}</p><p className="text-2xl font-bold">{comparison.change_percent?.toFixed(2) ?? "—"}%</p></div>
              <div><p className="text-sm text-blue-700">{t("explore.comparability")}</p><p className="text-lg font-semibold">{comparison.comparable_in_strict_trend ? t("explore.comparable") : t("explore.not_comparable")}</p></div>
            </div>
            {comparison.warnings.length > 0 && (
              <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-blue-900">
                {comparison.warnings.map((warning) => <li key={warning}>{warning}</li>)}
              </ul>
            )}
            <Link
              href={`/analysis?from=${comparison.from.year}&to=${comparison.to.year}`}
              className="mt-5 inline-flex items-center gap-2 rounded-lg bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800"
            >
              <Bot className="h-4 w-4" />
              {t("explore.ask_ai_comparison")}
            </Link>
          </section>
        )}
      </main>
    </div>
  );
}
