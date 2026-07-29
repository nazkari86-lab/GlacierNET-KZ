"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { BarChart3, Download, FileText, Mountain, TrendingUp } from "lucide-react";
import { DataTable, type ColumnDef } from "@/components/DataTable";
import { StatCard } from "@/components/StatCard";
import { toast } from "@/components/Toast";
import { downloadFile, exportToCSV, exportToJSON, exportToPDF } from "@/lib/export";
import { fetchDecisionReadiness, type DecisionReadiness, type DecisionTimeSeriesRow } from "@/lib/api";
import { riskTwinHref } from "@/lib/evidenceCase";

const columns = [
  { key: "year", header: "Year" },
  { key: "area_km2", header: "Area km²" },
  { key: "primary_method", header: "Method" },
  { key: "sensor", header: "Sensor" },
  { key: "source_flag", header: "Source flag" },
  { key: "quality_score", header: "Quality /100" },
  { key: "confidence", header: "Confidence" },
  { key: "include_in_strict_trend", header: "Strict trend" },
  { key: "caveat", header: "Caveat" },
] as const;

function reportMarkdown(data: DecisionReadiness): string {
  const trend = data.summary.strict_trend;
  const header = "# GlacierNET-KZ decision-readiness report\n\n" +
    `Generated from: ${data.updated_from}\n\n` +
    `Strict trend years: ${trend?.n_years ?? "not available"}\n\n` +
    `Slope: ${trend?.slope_km2_per_year ?? "not available"} km²/year\n\n`;
  const rows = data.timeseries.map((row) => `| ${row.year} | ${row.area_km2} | ${row.primary_method} | ${row.sensor} | ${row.quality_score} | ${row.confidence} | ${row.include_in_strict_trend} |`).join("\n");
  return `${header}## Time series\n\n| Year | Area km² | Method | Sensor | Quality | Confidence | Strict trend |\n|---|---:|---|---|---:|---|---|\n${rows}\n`;
}

export default function ReportsPage() {
  const [data, setData] = useState<DecisionReadiness | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchDecisionReadiness().then(setData).catch((cause) => setError(cause instanceof Error ? cause.message : "Decision readiness data unavailable"));
  }, []);

  const rows = useMemo(() => data?.timeseries ?? [], [data]);
  const strictRows = rows.filter((row) => row.include_in_strict_trend === "True");
  const excludedRows = rows.filter((row) => row.include_in_strict_trend !== "True");
  const trend = data?.summary.strict_trend;
  const averageQuality = useMemo(() => rows.length ? rows.reduce((total, row) => total + Number(row.quality_score || 0), 0) / rows.length : 0, [rows]);
  const decisionColumns: ColumnDef<DecisionTimeSeriesRow>[] = columns.map((column) => ({ ...column, sortable: true }));
  const latestYear = Number(rows.at(-1)?.year);
  const riskTwinCaseHref = riskTwinHref({
    rgiId: "RGI2000-v7.0-G-13-33843",
    year: Number.isInteger(latestYear) ? latestYear : 2024,
    sourceScope: "annual_screening",
  });

  const exportReport = (format: "CSV" | "JSON" | "PDF" | "Markdown" | "HTML") => {
    if (!data || !rows.length) { toast.error("No decision-readiness table is available to export."); return; }
    const name = "glaciernet_kz_decision_readiness";
    if (format === "CSV") exportToCSV(rows as unknown as Record<string, unknown>[], [...columns], name);
    if (format === "JSON") exportToJSON([data], name);
    if (format === "PDF") void exportToPDF(rows as unknown as Record<string, unknown>[], [...columns], name, "GlacierNET-KZ decision-readiness report");
    if (format === "Markdown") downloadFile(reportMarkdown(data), `${name}.md`, "text/markdown;charset=utf-8;");
    if (format === "HTML") {
      const body = reportMarkdown(data).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll("\n", "<br>");
      downloadFile(`<!doctype html><html><head><meta charset="utf-8"><title>GlacierNET-KZ report</title></head><body><main>${body}</main></body></html>`, `${name}.html`, "text/html;charset=utf-8;");
    }
    toast.success(`${format} report exported`);
  };

  return <main id="main-content" className="min-h-screen bg-slate-50 px-4 py-8"><div className="mx-auto max-w-7xl space-y-6"><header className="flex flex-wrap items-center gap-3"><div className="rounded-xl bg-blue-500/10 p-2.5"><FileText className="h-6 w-6 text-blue-600" /></div><div><h1 className="text-2xl font-bold">Decision-readiness reports</h1><p className="text-sm text-slate-600">Only locally generated annual evidence is shown. No model benchmark metrics are fabricated here.</p></div><Link href={riskTwinCaseHref} className="ml-auto inline-flex min-h-10 items-center rounded-lg border border-blue-700 px-3 py-2 text-sm font-semibold text-blue-900 hover:bg-blue-50">Открыть годовой Risk Twin case</Link></header>{error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}<section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><StatCard label="Years with evidence" value={rows.length || "—"} icon={<FileText className="h-5 w-5" />} color="blue" /><StatCard label="Strict trend years" value={trend?.n_years ?? strictRows.length} icon={<BarChart3 className="h-5 w-5" />} color="emerald" /><StatCard label="Average data quality" value={rows.length ? `${averageQuality.toFixed(0)}/100` : "—"} icon={<TrendingUp className="h-5 w-5" />} color="violet" /><StatCard label="2050 screening forecast" value={trend?.forecast_2050_km2 !== undefined ? `${trend.forecast_2050_km2} km²` : "—"} icon={<Mountain className="h-5 w-5" />} color="amber" /></section><section className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 text-sm text-emerald-950"><h2 className="font-semibold">Strict trend interpretation</h2><p className="mt-2">Preferred available method order: RF, U-Net, then NDSI. Excluded years: {excludedRows.length ? excludedRows.map((row) => `${row.year} (${row.source_flag})`).join(", ") : "none"}. p-value: {trend?.p_value ?? "—"}; R²: {trend?.r_squared ?? "—"}; significant: {trend?.significant ? "yes" : "no"}.</p></section><section className="rounded-xl bg-white p-5 shadow-sm"><h2 className="mb-4 text-lg font-semibold">Decision-ready area time series</h2><DataTable data={rows} columns={decisionColumns} sortable pagination pageSize={10} emptyMessage="Decision tables have not been generated yet." /></section><section className="rounded-xl bg-white p-5 shadow-sm"><h2 className="mb-4 text-lg font-semibold">Export the actual table</h2><div className="flex flex-wrap gap-3">{(["CSV", "JSON", "PDF", "Markdown", "HTML"] as const).map((format) => <button key={format} onClick={() => exportReport(format)} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-50"><Download className="h-4 w-4" />{format}</button>)}</div></section></div></main>;
}
