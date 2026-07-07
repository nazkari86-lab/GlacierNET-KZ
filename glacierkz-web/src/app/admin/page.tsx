"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import {
  Users,
  Database,
  Activity,
  Shield,
  Cpu,
  ArrowUpRight,
  ArrowDownRight,
  TrendingUp,
} from "lucide-react";
import RealTimeChart from "@/components/RealTimeChart";
import ActivityFeed from "@/components/ActivityFeed";
import { MetricGaugeBar } from "@/components/MetricGauge";
import { useI18n } from "@/lib/I18nProvider";
import {
  fetchAdminAlerts,
  fetchAdminRequestMetrics,
  fetchAdminStats,
  type AdminAlert,
  type AdminStats,
} from "@/lib/api";

interface SystemStats extends AdminStats {}

interface SystemAlert extends AdminAlert {}

export default function AdminOverviewPage() {
  const { t } = useI18n();
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [alerts, setAlerts] = useState<SystemAlert[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchStats = useCallback(async () => {
    try {
      const [statsData, alertsData] = await Promise.allSettled([
        fetchAdminStats(),
        fetchAdminAlerts(),
      ]);

      if (statsData.status === "fulfilled") setStats(statsData.value);
      if (alertsData.status === "fulfilled") setAlerts(alertsData.value);
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  const statCards = [
    {
      label: t("admin.total_users"),
      value: stats?.totalUsers ?? 0,
      change: "+12%",
      up: true,
      icon: Users,
      color: "bg-blue-50 text-blue-600",
    },
    {
      label: t("admin.datasets"),
      value: stats?.totalDatasets ?? 0,
      change: "+5%",
      up: true,
      icon: Database,
      color: "bg-green-50 text-green-600",
    },
    {
      label: t("admin.predictions"),
      value: stats?.totalPredictions ?? 0,
      change: "+23%",
      up: true,
      icon: Activity,
      color: "bg-purple-50 text-purple-600",
    },
    {
      label: t("admin.active_users"),
      value: stats?.activeUsers ?? 0,
      change: "+8%",
      up: true,
      icon: Shield,
      color: "bg-amber-50 text-amber-600",
    },
  ];

  const formatUptime = (seconds: number) => {
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    return `${d}d ${h}h`;
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(0)} MB`;
    return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-gray-900">{t("admin.system_overview")}</h1>
        <p className="text-sm text-gray-500 mt-0.5">{t("admin.system_overview_desc")}</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-white rounded-lg border border-gray-200 p-4 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-24 mb-3" />
              <div className="h-8 bg-gray-200 rounded w-16" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-4">
          {statCards.map((card) => (
            <div key={card.label} className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">{card.label}</span>
                <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center", card.color)}>
                  <card.icon className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-2 flex items-end gap-2">
                <span className="text-2xl font-bold text-gray-900">{card.value.toLocaleString()}</span>
                <span
                  className={cn(
                    "text-xs font-medium flex items-center gap-0.5 mb-1",
                    card.up ? "text-green-600" : "text-red-600"
                  )}
                >
                  {card.up ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                  {card.change}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">{t("admin.cpu_usage")}</h3>
          <MetricGaugeBar
            value={stats?.cpuUsage ?? 0}
            max={100}
            unit="%"
            color={stats && stats.cpuUsage > 80 ? "#ef4444" : "#3b82f6"}
          />
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-500">
            <div className="flex items-center gap-1">
              <Cpu className="w-3 h-3" /> {t("admin.uptime")}: {formatUptime(stats?.uptime ?? 0)}
            </div>
            <div className="flex items-center gap-1">
              <TrendingUp className="w-3 h-3" /> {t("admin.rpm")}: {stats?.requestsPerMinute ?? 0}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">{t("admin.memory_usage")}</h3>
          <MetricGaugeBar
            value={stats?.memoryUsage ?? 0}
            max={100}
            unit="%"
            color={stats && stats.memoryUsage > 80 ? "#ef4444" : "#8b5cf6"}
          />
          <div className="mt-3 text-xs text-gray-500">
            {t("admin.avg_response")}: {stats?.avgResponseTime ?? 0}ms
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">{t("admin.storage")}</h3>
          <MetricGaugeBar
            value={stats?.storageUsed ?? 0}
            max={stats?.storageTotal ?? 10737418240}
            unit=""
            color="#14b8a6"
            format={(v) => formatBytes(v)}
            showPercentage
          />
          <div className="mt-3 text-xs text-gray-500">
            {t("admin.error_rate")}: {(stats?.errorRate ?? 0).toFixed(2)}%
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <RealTimeChart
          title={t("admin.api_requests")}
          unit=" req/s"
          color="#3b82f6"
          variant="area"
          maxPoints={60}
          refreshInterval={3000}
          onDataFetch={fetchAdminRequestMetrics}
        />

        <ActivityFeed
          items={[
            ...alerts.map((a) => ({
              id: a.id,
              type: (a.level === "error" ? "alert" as const : "system" as const),
              title: a.message,
              timestamp: a.timestamp,
            })),
          ].slice(0, 8)}
          maxItems={8}
          compact
        />
      </div>
    </div>
  );
}
