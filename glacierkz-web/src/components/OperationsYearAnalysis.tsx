"use client";

/* eslint-disable @next/next/no-img-element -- verified local scientific overlays are served by the API. */

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  GitCompareArrows,
  Loader2,
} from "lucide-react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  compareLocalYears,
  fetchYears,
  type YearComparison,
  type YearResult,
} from "@/lib/api";

export default function OperationsYearAnalysis({
  onYearChange,
}: {
  onYearChange?: (year: number) => void;
}) {
  const [years, setYears] = useState<YearResult[]>([]);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [compareYear, setCompareYear] = useState<number | null>(null);
  const [comparison, setComparison] = useState<YearComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const chartElementRef = useRef<HTMLDivElement>(null);
  const [chartWidth, setChartWidth] = useState(0);

  useEffect(() => {
    const element = chartElementRef.current;
    if (!element) return;
    const update = () => setChartWidth(Math.max(0, Math.floor(element.getBoundingClientRect().width)));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, [years.length]);

  useEffect(() => {
    fetchYears()
      .then((records) => {
        setYears(records);
        const latest = records.at(-1)?.year ?? null;
        setSelectedYear(latest);
        if (latest !== null) onYearChange?.(latest);
        setCompareYear(records.find((record) => record.include_in_strict_trend)?.year ?? records[0]?.year ?? null);
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : String(cause)))
      .finally(() => setLoading(false));
  }, [onYearChange]);

  const selected = useMemo(
    () => years.find((record) => record.year === selectedYear) ?? null,
    [selectedYear, years]
  );
  const before = useMemo(
    () => years.find((record) => record.year === compareYear) ?? null,
    [compareYear, years]
  );
  const strictCount = years.filter((record) => record.include_in_strict_trend).length;
  const chartData = years.map((record) => ({
    year: record.year,
    area: record.primary_area_km2,
    strictArea: record.include_in_strict_trend ? record.primary_area_km2 : null,
  }));

  const compare = async () => {
    if (selectedYear === null || compareYear === null || selectedYear === compareYear) return;
    setLoading(true);
    setError("");
    try {
      setComparison(await compareLocalYears(compareYear, selectedYear));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section id="years" aria-labelledby="years-heading" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-800">Verified local results</p>
          <h2 id="years-heading" className="mt-1 text-2xl font-semibold">Analysis by year</h2>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">
            Select any locally analyzed year, inspect its real segmentation artifact, and compare only with explicit quality warnings.
          </p>
        </div>
        {years.length > 0 && (
          <div className="rounded-xl bg-slate-100 px-4 py-3 text-sm">
            <strong>{years[0].year}–{years.at(-1)?.year}</strong>
            <span className="ml-2 text-slate-600">{years.length} analyzed · {strictCount} strict-comparable</span>
          </div>
        )}
      </div>

      {error && <p role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      {loading && years.length === 0 && (
        <div className="mt-5 flex min-h-40 items-center justify-center gap-2 text-slate-500">
          <Loader2 className="h-5 w-5 animate-spin" /> Loading year analysis…
        </div>
      )}

      {years.length > 0 && (
        <>
          <div className="mt-5 grid gap-3 lg:grid-cols-[1fr_1fr_auto] lg:items-end">
            <label className="space-y-1">
              <span className="text-sm font-medium">Analyze year</span>
              <select
                value={selectedYear ?? ""}
                onChange={(event) => {
                  const nextYear = Number(event.target.value);
                  setSelectedYear(nextYear);
                  onYearChange?.(nextYear);
                  setComparison(null);
                }}
                className="min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3"
                data-testid="analysis-year-select"
              >
                {years.map((record) => (
                  <option key={record.year} value={record.year}>
                    {record.year} · {record.sensor} · quality {record.quality_score}/100
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-1">
              <span className="text-sm font-medium">Compare with</span>
              <select
                value={compareYear ?? ""}
                onChange={(event) => {
                  setCompareYear(Number(event.target.value));
                  setComparison(null);
                }}
                className="min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3"
                data-testid="compare-year-select"
              >
                {years.map((record) => (
                  <option key={record.year} value={record.year}>
                    {record.year} · {record.sensor} {record.include_in_strict_trend ? "· comparable" : "· caution"}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={() => void compare()}
              disabled={loading || selectedYear === compareYear}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-blue-700 px-5 font-semibold text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <GitCompareArrows className="h-4 w-4" />}
              Compare years
            </button>
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-xl border border-slate-200 p-4">
              <h3 className="font-semibold">Measured area across available years</h3>
              <p className="mt-1 text-xs text-slate-500">Gray includes every metadata year; blue highlights strict-comparable observations.</p>
              <div ref={chartElementRef} className="mt-4 h-72 w-full" data-testid="year-area-chart">
                {chartWidth > 0 ? (
                  <LineChart width={chartWidth} height={288} data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="year" />
                    <YAxis unit=" km²" width={78} domain={["auto", "auto"]} />
                    <Tooltip formatter={(value) => [`${Number(value).toFixed(2)} km²`, "Area"]} />
                    <Legend />
                    <Line type="monotone" dataKey="area" name="All analyzed years" stroke="#94a3b8" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="strictArea" name="Strict-comparable" stroke="#1d4ed8" strokeWidth={3} connectNulls={false} dot={{ r: 4 }} />
                  </LineChart>
                ) : (
                  <div className="h-full animate-pulse rounded-lg bg-slate-100" aria-hidden="true" />
                )}
              </div>
            </div>

            {selected && (
              <div className="grid gap-3 sm:grid-cols-2">
                <Metric label="Selected year" value={String(selected.year)} detail={`${selected.sensor} · ${selected.source_flag}`} />
                <Metric label="Primary area" value={`${selected.primary_area_km2.toFixed(2)} km²`} detail={selected.primary_method.toUpperCase()} />
                <Metric label="Quality" value={`${selected.quality_score}/100`} detail={selected.confidence} />
                <Metric
                  label="Comparability"
                  value={selected.include_in_strict_trend ? "Strict-ready" : "Use with caution"}
                  detail={selected.artifact_status}
                  good={selected.include_in_strict_trend}
                />
                <div className="sm:col-span-2">
                  <Link
                    href={`/analysis?year=${selected.year}`}
                    className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-violet-700 px-4 font-semibold text-white hover:bg-violet-800"
                  >
                    <Bot className="h-4 w-4" /> Explain {selected.year} with AI
                  </Link>
                </div>
              </div>
            )}
          </div>

          {selected?.caveat && (
            <div className="mt-5 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
              <p><strong>Limitation for {selected.year}:</strong> {selected.caveat}</p>
            </div>
          )}

          {selected && (
            <div className="mt-6 grid gap-5 lg:grid-cols-2">
              <ArtifactCard year={before} label="Comparison year" />
              <ArtifactCard year={selected} label="Selected year" />
            </div>
          )}

          {comparison && (
            <div className={`mt-6 rounded-xl border p-5 ${comparison.comparable_in_strict_trend ? "border-emerald-200 bg-emerald-50" : "border-amber-300 bg-amber-50"}`} data-testid="year-comparison-result">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">{comparison.from.year} → {comparison.to.year}</p>
                  <p className="mt-1 text-3xl font-semibold">
                    {comparison.change_km2 > 0 ? "+" : ""}{comparison.change_km2.toFixed(2)} km²
                  </p>
                  <p className="text-sm">{comparison.change_percent == null ? "Percent unavailable" : `${comparison.change_percent > 0 ? "+" : ""}${comparison.change_percent.toFixed(2)}%`}</p>
                </div>
                <span className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-2 text-sm font-medium">
                  {comparison.comparable_in_strict_trend ? <CheckCircle2 className="h-4 w-4 text-emerald-700" /> : <AlertTriangle className="h-4 w-4 text-amber-700" />}
                  {comparison.comparable_in_strict_trend ? "Strict comparison allowed" : "Not strict-comparable"}
                </span>
              </div>
              {comparison.warnings.length > 0 && (
                <ul className="mt-4 list-disc space-y-1 pl-5 text-sm">
                  {comparison.warnings.map((warning) => <li key={warning}>{warning}</li>)}
                </ul>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}

function Metric({ label, value, detail, good }: { label: string; value: string; detail: string; good?: boolean }) {
  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-xl font-semibold ${good === false ? "text-amber-800" : "text-slate-950"}`}>{value}</p>
      <p className="mt-1 text-xs text-slate-500">{detail}</p>
    </div>
  );
}

function ArtifactCard({ year, label }: { year: YearResult | null; label: string }) {
  return (
    <figure className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
      <figcaption className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3">
        <span className="font-semibold">{label}</span>
        <span className="text-sm text-slate-600">{year ? `${year.year} · ${year.sensor}` : "Not selected"}</span>
      </figcaption>
      {year?.overlay_url ? (
        <img
          src={year.overlay_url}
          alt={`Verified glacier segmentation overlay for ${year.year}`}
          className="h-72 w-full object-contain"
        />
      ) : (
        <div className="flex h-72 items-center justify-center p-6 text-center text-sm text-slate-500">
          {year ? `No physical overlay is available for ${year.year}; metadata is shown without inventing imagery.` : "Choose a comparison year."}
        </div>
      )}
    </figure>
  );
}
