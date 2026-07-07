"use client"

import { useEffect, useMemo, useState } from "react"
import { useI18n } from "@/lib/I18nProvider"
import type { TranslationKey } from "@/lib/i18n"
import { StatCard } from "@/components/StatCard"
import { DataTable, type ColumnDef } from "@/components/DataTable"
import { LineChart, DonutChart } from "@/components/Charts"
import { toast } from "@/components/Toast"
import { FileText, Download, TrendingUp, BarChart3, Mountain } from "lucide-react"
import { exportToCSV, exportToJSON, exportToPDF } from "@/lib/export"
import { fetchDecisionReadiness, type DecisionReadiness, type DecisionTimeSeriesRow } from "@/lib/api"

interface Report {
  date: string
  model: string
  f1: number
  dice: number
  iou: number
  status: "completed" | "draft"
}

const reportsData: Report[] = [
  { date: "2026-06-23", model: "U-Net ResNet50", f1: 0.94, dice: 0.95, iou: 0.90, status: "completed" },
  { date: "2026-06-22", model: "DeepLabV3+", f1: 0.92, dice: 0.93, iou: 0.87, status: "completed" },
  { date: "2026-06-21", model: "SegFormer-B5", f1: 0.93, dice: 0.94, iou: 0.88, status: "completed" },
  { date: "2026-06-20", model: "U-Net ResNet50", f1: 0.91, dice: 0.92, iou: 0.85, status: "completed" },
  { date: "2026-06-19", model: "DeepLabV3+", f1: 0.89, dice: 0.91, iou: 0.83, status: "completed" },
  { date: "2026-06-18", model: "SegFormer-B5", f1: 0.90, dice: 0.92, iou: 0.84, status: "completed" },
  { date: "2026-06-17", model: "U-Net ResNet50", f1: 0.88, dice: 0.90, iou: 0.81, status: "completed" },
  { date: "2026-06-16", model: "DeepLabV3+", f1: 0.86, dice: 0.89, iou: 0.79, status: "completed" },
  { date: "2026-06-15", model: "SegFormer-B5", f1: 0.87, dice: 0.90, iou: 0.80, status: "completed" },
  { date: "2026-06-14", model: "U-Net ResNet50", f1: 0.82, dice: 0.84, iou: 0.72, status: "draft" },
]

export default function ReportsPage() {
  const { t } = useI18n()
  const [decisionReadiness, setDecisionReadiness] = useState<DecisionReadiness | null>(null)

  useEffect(() => {
    fetchDecisionReadiness()
      .then(setDecisionReadiness)
      .catch(() => {})
  }, [])

  const stats = useMemo(() => {
    const totalReports = reportsData.length
    const modelsCompared = new Set(reportsData.map((r) => r.model)).size
    const bestF1 = Math.max(...reportsData.map((r) => r.f1))
    const latestDate = reportsData[0]?.date ?? ""
    return { totalReports, modelsCompared, bestF1, latestDate }
  }, [])

  const donutData = useMemo(() => {
    const counts = reportsData.reduce<Record<string, number>>((acc, r) => {
      acc[r.model] = (acc[r.model] || 0) + 1
      return acc
    }, {})
    return Object.entries(counts).map(([label, value], i) => ({
      label,
      value,
      color: ["#2563eb", "#16a34a", "#ea580c"][i % 3],
    }))
  }, [])

  const lineData = useMemo(() => {
    const models = ["U-Net ResNet50", "DeepLabV3+", "SegFormer-B5"]
    return models.map((model) => ({
      label: model,
      values: reportsData
        .filter((r) => r.model === model)
        .reverse()
        .map((r) => r.f1),
    }))
  }, [])

  const handleExport = (format: string) => {
    const rows = decisionReadiness?.timeseries || []
    const columns = [
      { key: "year", header: "Year" },
      { key: "area_km2", header: "Area km2" },
      { key: "primary_method", header: "Method" },
      { key: "sensor", header: "Sensor" },
      { key: "source_flag", header: "Source flag" },
      { key: "quality_score", header: "Quality" },
      { key: "confidence", header: "Confidence" },
      { key: "include_in_strict_trend", header: "Strict trend" },
      { key: "caveat", header: "Caveat" },
    ]
    if (rows.length > 0) {
      if (format === "CSV") {
        exportToCSV(rows as unknown as Record<string, unknown>[], columns, "glaciernet_kz_decision_ready_timeseries")
      } else if (format === "JSON") {
        exportToJSON([decisionReadiness], "glaciernet_kz_decision_readiness")
      } else if (format === "PDF") {
        void exportToPDF(
          rows as unknown as Record<string, unknown>[],
          columns,
          "glaciernet_kz_decision_report",
          "GlacierNET-KZ Decision Report"
        )
      }
    }
    const labels: Record<string, string> = {
      JSON: t("reports.export_json"),
      CSV: t("reports.export_csv"),
      PDF: "Decision PDF exported",
      Markdown: t("reports.export_markdown"),
      HTML: t("reports.export_html"),
    }
    toast.success(labels[format] || format)
  }

  const columns: ColumnDef<Report>[] = [
    { key: "date", header: t("reports.date"), sortable: true },
    { key: "model", header: "Model", sortable: true },
    { key: "f1", header: t("reports.f1_score"), sortable: true, render: (v) => Number(v).toFixed(2) },
    { key: "dice", header: t("reports.dice"), sortable: true, render: (v) => Number(v).toFixed(2) },
    { key: "iou", header: t("reports.iou"), sortable: true, render: (v) => Number(v).toFixed(2) },
    {
      key: "status",
      header: "Status",
      sortable: true,
      render: (v) => {
        const status = String(v);
        return (
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
            status === "completed"
              ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
              : "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300"
          }`}
        >
          {status === "completed" ? t("reports.status_completed") : t("reports.status_draft")}
        </span>
        );
      },
    },
  ]

  const decisionRows = decisionReadiness?.timeseries || []
  const strictRows = decisionRows.filter((r) => r.include_in_strict_trend === "True")
  const excludedRows = decisionRows.filter((r) => r.include_in_strict_trend !== "True")
  const trend = decisionReadiness?.summary.strict_trend
  const avgQuality =
    decisionRows.length > 0
      ? decisionRows.reduce((sum, r) => sum + Number(r.quality_score || 0), 0) / decisionRows.length
      : 0

  const decisionColumns: ColumnDef<DecisionTimeSeriesRow>[] = [
    { key: "year", header: "Year", sortable: true },
    { key: "area_km2", header: "Area km2", sortable: true },
    { key: "primary_method", header: "Method", sortable: true },
    { key: "sensor", header: "Sensor", sortable: true },
    {
      key: "quality_score",
      header: "Quality",
      sortable: true,
      render: (v) => `${v}/100`,
      align: "right",
    },
    {
      key: "confidence",
      header: "Confidence",
      sortable: true,
      render: (v) => {
        const confidence = String(v)
        const className =
          confidence === "high"
            ? "bg-emerald-100 text-emerald-800"
            : confidence === "medium"
              ? "bg-amber-100 text-amber-800"
              : "bg-red-100 text-red-800"
        return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${className}`}>{confidence}</span>
      },
    },
    {
      key: "include_in_strict_trend",
      header: "Strict",
      render: (v) => (String(v) === "True" ? "yes" : "excluded"),
    },
  ]

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-blue-500/10 p-2.5">
          <FileText className="h-6 w-6 text-blue-500" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          {t("reports.results_title")}
        </h1>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label={t("reports.total_reports")} value={stats.totalReports} icon={<FileText className="h-5 w-5" />} color="blue" />
        <StatCard label={t("reports.models_compared")} value={stats.modelsCompared} icon={<BarChart3 className="h-5 w-5" />} color="emerald" />
        <StatCard label={t("reports.best_f1")} value={stats.bestF1.toFixed(2)} icon={<TrendingUp className="h-5 w-5" />} color="violet" />
        <StatCard label={t("reports.latest_report_date")} value={stats.latestDate} icon={<Mountain className="h-5 w-5" />} color="amber" />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Strict trend years"
          value={trend?.n_years ?? strictRows.length}
          icon={<FileText className="h-5 w-5" />}
          color="blue"
        />
        <StatCard
          label="Avg data quality"
          value={decisionRows.length ? `${avgQuality.toFixed(0)}/100` : "—"}
          icon={<BarChart3 className="h-5 w-5" />}
          color="emerald"
        />
        <StatCard
          label="Trend slope"
          value={trend?.slope_km2_per_year !== undefined ? `${trend.slope_km2_per_year} km²/yr` : "—"}
          icon={<TrendingUp className="h-5 w-5" />}
          color="violet"
        />
        <StatCard
          label="2050 forecast"
          value={trend?.forecast_2050_km2 !== undefined ? `${trend.forecast_2050_km2} km²` : "—"}
          icon={<Mountain className="h-5 w-5" />}
          color="amber"
        />
      </div>

      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-6 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold text-emerald-950">Decision readiness view</h2>
        <div className="grid gap-3 text-sm text-emerald-900 md:grid-cols-3">
          <p>
            Strict trend excludes caveat years and uses the preferred available method order: RF, U-Net, then NDSI.
          </p>
          <p>
            Excluded years: {excludedRows.length ? excludedRows.map((r) => `${r.year} (${r.source_flag})`).join(", ") : "none"}.
          </p>
          <p>
            p-value: {trend?.p_value ?? "—"}; R²: {trend?.r_squared ?? "—"}; significant: {trend?.significant ? "yes" : "no"}.
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-white">Decision-ready area time series</h2>
        <DataTable data={decisionRows} columns={decisionColumns} sortable pagination pageSize={8} emptyMessage="Decision tables not generated yet" />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-white">{t("reports.model_distribution")}</h2>
        <div className="flex justify-center">
          <DonutChart data={donutData} size={240} />
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-white">{t("reports.f1_over_time")}</h2>
        <LineChart data={lineData} height={300} />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-white">Recent Reports</h2>
        <DataTable data={reportsData} columns={columns} sortable pagination pageSize={5} />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-white">{t("reports.export_section")}</h2>
        <div className="flex flex-wrap gap-3">
          {(["JSON", "CSV", "PDF", "Markdown", "HTML"] as const).map((fmt) => (
            <button
              key={fmt}
              onClick={() => handleExport(fmt)}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
            >
              <Download className="h-4 w-4" />
              {t(`reports.export_${fmt.toLowerCase()}` as TranslationKey)}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
