"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { BarChart3, Mountain, Layers, Activity, ArrowUpRight } from "lucide-react";
import { useI18n } from "@/lib/I18nProvider";
import { StatCard } from "@/components/StatCard";
import { LineChart, DonutChart } from "@/components/Charts";
import { DataTable, type ColumnDef } from "@/components/DataTable";
import { fetchDashboardStats, type DashboardStats } from "@/lib/api";

interface TaskRow {
  id: string;
  model: string;
  area_km2: number;
  date: string;
  status: "completed" | "processing" | "failed" | "queued";
}

export default function DashboardPage() {
  const { t } = useI18n();
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    fetchDashboardStats()
      .then(setStats)
      .catch(() => {});
  }, []);

  const statusColor: Record<string, string> = {
    completed: "text-emerald-600 bg-emerald-50",
    processing: "text-blue-600 bg-blue-50",
    failed: "text-red-600 bg-red-50",
    queued: "text-amber-600 bg-amber-50",
  };

  const statusLabel: Record<string, () => string> = {
    completed: () => t("dashboard.status_completed"),
    processing: () => t("dashboard.status_processing"),
    failed: () => t("dashboard.status_failed"),
    queued: () => t("dashboard.status_queued"),
  };

  const recentTasks: TaskRow[] = (stats?.recent_tasks || []) as TaskRow[];

  const columns: ColumnDef<TaskRow>[] = [
    { key: "id", header: t("dashboard.table_id"), sortable: true },
    { key: "model", header: t("dashboard.table_model"), sortable: true },
    {
      key: "area_km2",
      header: t("dashboard.table_area"),
      accessor: (row) => row.area_km2.toFixed(2),
      sortable: true,
      align: "right",
    },
    { key: "date", header: t("dashboard.table_date"), sortable: true },
    {
      key: "status",
      header: t("dashboard.table_status"),
      accessor: (row) => (
        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusColor[row.status]}`}>
          {statusLabel[row.status]?.() ?? row.status}
        </span>
      ),
      sortable: true,
    },
  ];

  const actions = [
    { href: "/predict", label: t("dashboard.action_predict"), color: "bg-blue-600 hover:bg-blue-700" },
    { href: "/compare", label: t("dashboard.action_compare"), color: "bg-purple-600 hover:bg-purple-700" },
    { href: "/trend", label: t("dashboard.action_trend"), color: "bg-emerald-600 hover:bg-emerald-700" },
    { href: "/analysis", label: t("dashboard.action_analysis"), color: "bg-amber-600 hover:bg-amber-700" },
  ];

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b bg-white" role="banner">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">{t("dashboard.title")}</h1>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        <section aria-label={t("dashboard.title")}>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label={t("dashboard.total_segments")}
              value={stats ? stats.total_segments.toLocaleString() : "—"}
              icon={<Layers className="h-5 w-5" aria-hidden="true" />}
              color="blue"
              trend="up"
              trendValue={t("dashboard.segments_trend")}
            />
            <StatCard
              label={t("dashboard.total_area")}
              value={stats ? `${stats.total_area_km2} km²` : "—"}
              icon={<Mountain className="h-5 w-5" aria-hidden="true" />}
              color="green"
              trend="up"
              trendValue={t("dashboard.area_trend")}
            />
            <StatCard
              label={t("dashboard.models_registered")}
              value={stats ? String(stats.models_registered) : "—"}
              icon={<BarChart3 className="h-5 w-5" aria-hidden="true" />}
              color="purple"
              trend="neutral"
              trendValue={t("dashboard.models_trend")}
            />
            <StatCard
              label={t("dashboard.active_tasks")}
              value={stats ? String(stats.active_tasks) : "—"}
              icon={<Activity className="h-5 w-5" aria-hidden="true" />}
              color="yellow"
              trend="down"
              trendValue={t("dashboard.tasks_trend")}
            />
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 lg:grid-cols-2" aria-label="Charts">
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-sm font-semibold text-gray-700">{t("dashboard.segments_over_time")}</h2>
            <LineChart
              data={stats?.segments_over_time || []}
              series={[{ name: t("dashboard.total_segments"), color: "#3b82f6" }]}
              height={220}
            />
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-sm font-semibold text-gray-700">{t("dashboard.model_usage")}</h2>
            <div className="flex justify-center">
              <DonutChart data={stats?.model_usage || []} size={180} innerRadius={65} />
            </div>
          </div>
        </section>

        <section aria-label={t("dashboard.recent_activity")}>
          <h2 className="mb-3 text-lg font-semibold text-gray-900">{t("dashboard.recent_activity")}</h2>
          <DataTable data={recentTasks} columns={columns} pageSize={10} emptyMessage={t("dashboard.recent_activity")} />
        </section>

        <section aria-label={t("dashboard.quick_actions")}>
          <h2 className="mb-3 text-lg font-semibold text-gray-900">{t("dashboard.quick_actions")}</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {actions.map((action) => (
              <Link
                key={action.href}
                href={action.href}
                className={`flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-medium text-white transition-colors ${action.color}`}
                aria-label={action.label}
              >
                {action.label}
                <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
