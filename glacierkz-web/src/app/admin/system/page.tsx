"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import {
  Server,
  HardDrive,
  Cpu,
  MemoryStick,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Globe,
} from "lucide-react";
import { MetricGaugeBar } from "@/components/MetricGauge";
import {
  fetchAdminServices,
  fetchAdminSystemInfo,
  type AdminServiceHealth,
  type AdminSystemInfo,
} from "@/lib/api";

interface ServiceHealth extends AdminServiceHealth {}

interface SystemInfo extends AdminSystemInfo {}

const STATUS_ICON = {
  healthy: { icon: CheckCircle, color: "text-green-500 bg-green-50" },
  degraded: { icon: AlertTriangle, color: "text-amber-500 bg-amber-50" },
  down: { icon: XCircle, color: "text-red-500 bg-red-50" },
};

export default function AdminSystemPage() {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [services, setServices] = useState<ServiceHealth[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [sysInfo, services] = await Promise.allSettled([
        fetchAdminSystemInfo(),
        fetchAdminServices(),
      ]);

      if (sysInfo.status === "fulfilled") setSystemInfo(sysInfo.value);
      if (services.status === "fulfilled") setServices(services.value);
    } catch {
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(0)} KB`;
    if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(0)} MB`;
    return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
  };

  const formatUptime = (seconds: number) => {
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${d}d ${h}h ${m}m`;
  };

  const allHealthy = services.every((s) => s.status === "healthy");
  const anyDown = services.some((s) => s.status === "down");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">System</h1>
          <p className="text-sm text-gray-500 mt-0.5">Infrastructure health and service status</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} />
          Refresh
        </button>
      </div>

      <div
        className={cn(
          "flex items-center gap-3 px-4 py-3 rounded-lg border",
          allHealthy
            ? "bg-green-50 border-green-200 text-green-800"
            : anyDown
              ? "bg-red-50 border-red-200 text-red-800"
              : "bg-amber-50 border-amber-200 text-amber-800"
        )}
      >
        {allHealthy ? (
          <CheckCircle className="w-4 h-4" />
        ) : anyDown ? (
          <XCircle className="w-4 h-4" />
        ) : (
          <AlertTriangle className="w-4 h-4" />
        )}
        <span className="text-sm font-medium">
          {allHealthy
            ? "All services operational"
            : anyDown
              ? "Some services are down"
              : "Some services degraded"}
        </span>
        <span className="text-xs opacity-70 ml-auto">
          {services.filter((s) => s.status === "healthy").length}/{services.length} healthy
        </span>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
              <Cpu className="w-4 h-4 text-blue-600" />
            </div>
            <span className="text-xs text-gray-500">CPU</span>
          </div>
          <div className="flex items-end gap-1">
            <span className="text-xl font-bold text-gray-900">
              {systemInfo?.cpu.usage ?? 0}%
            </span>
          </div>
          <p className="text-[10px] text-gray-400 mt-1 truncate">
            {systemInfo?.cpu.model ?? "Unknown"} · {systemInfo?.cpu.cores ?? 0} cores
          </p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center">
              <MemoryStick className="w-4 h-4 text-purple-600" />
            </div>
            <span className="text-xs text-gray-500">Memory</span>
          </div>
          <div className="flex items-end gap-1">
            <span className="text-xl font-bold text-gray-900">
              {systemInfo ? formatBytes(systemInfo.memory.used) : "0 GB"}
            </span>
          </div>
          <p className="text-[10px] text-gray-400 mt-1">
            of {systemInfo ? formatBytes(systemInfo.memory.total) : "0 GB"}
          </p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-teal-50 flex items-center justify-center">
              <HardDrive className="w-4 h-4 text-teal-600" />
            </div>
            <span className="text-xs text-gray-500">Disk</span>
          </div>
          <div className="flex items-end gap-1">
            <span className="text-xl font-bold text-gray-900">
              {systemInfo ? formatBytes(systemInfo.disk.used) : "0 GB"}
            </span>
          </div>
          <p className="text-[10px] text-gray-400 mt-1">
            of {systemInfo ? formatBytes(systemInfo.disk.total) : "0 GB"} on {systemInfo?.disk.mount ?? "/"}
          </p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center">
              <Globe className="w-4 h-4 text-amber-600" />
            </div>
            <span className="text-xs text-gray-500">Network</span>
          </div>
          <div className="flex items-end gap-1">
            <span className="text-xl font-bold text-gray-900">
              {systemInfo?.network.connections ?? 0}
            </span>
          </div>
          <p className="text-[10px] text-gray-400 mt-1">active connections</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Resource Usage</h3>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-500">CPU</span>
                <span className="text-xs font-medium text-gray-700">{systemInfo?.cpu.usage ?? 0}%</span>
              </div>
              <MetricGaugeBar
                value={systemInfo?.cpu.usage ?? 0}
                max={100}
                unit="%"
                color="#3b82f6"
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-500">Memory</span>
                <span className="text-xs font-medium text-gray-700">
                  {systemInfo ? ((systemInfo.memory.used / systemInfo.memory.total) * 100).toFixed(0) : 0}%
                </span>
              </div>
              <MetricGaugeBar
                value={systemInfo?.memory.used ?? 0}
                max={systemInfo?.memory.total ?? 1073741824}
                unit=""
                color="#8b5cf6"
                format={formatBytes}
                showPercentage
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-500">Disk</span>
                <span className="text-xs font-medium text-gray-700">
                  {systemInfo ? ((systemInfo.disk.used / systemInfo.disk.total) * 100).toFixed(0) : 0}%
                </span>
              </div>
              <MetricGaugeBar
                value={systemInfo?.disk.used ?? 0}
                max={systemInfo?.disk.total ?? 1073741824}
                unit=""
                color="#14b8a6"
                format={formatBytes}
                showPercentage
              />
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 grid grid-cols-2 gap-2 text-xs text-gray-500">
            <div className="flex items-center gap-1">
              <Server className="w-3 h-3" /> {systemInfo?.hostname ?? "Unknown"}
            </div>
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" /> Uptime: {formatUptime(systemInfo?.uptime ?? 0)}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Services</h3>
          <div className="space-y-3">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="h-10 bg-gray-100 rounded-lg" />
                  </div>
                ))
              : services.map((svc) => {
                  const info = STATUS_ICON[svc.status];
                  const StatusIcon = info.icon;
                  return (
                    <div
                      key={svc.name}
                      className="flex items-center gap-3 p-2.5 rounded-lg bg-gray-50/50 border border-gray-100"
                    >
                      <div className={cn("w-7 h-7 rounded-full flex items-center justify-center", info.color)}>
                        <StatusIcon className="w-3.5 h-3.5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{svc.name}</p>
                        <p className="text-[10px] text-gray-400">{svc.latency}ms</p>
                      </div>
                      <span
                        className={cn(
                          "px-2 py-0.5 text-[10px] font-medium rounded-full",
                          svc.status === "healthy" && "bg-green-100 text-green-700",
                          svc.status === "degraded" && "bg-amber-100 text-amber-700",
                          svc.status === "down" && "bg-red-100 text-red-700"
                        )}
                      >
                        {svc.status}
                      </span>
                    </div>
                  );
                })}
          </div>
        </div>
      </div>
    </div>
  );
}
