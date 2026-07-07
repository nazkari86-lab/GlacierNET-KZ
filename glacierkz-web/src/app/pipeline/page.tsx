"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import PipelineStage from "@/components/PipelineStage";
import ActivityFeed from "@/components/ActivityFeed";
import type { ComponentProps } from "react";
import SearchBar from "@/components/SearchBar";
import {
  cancelPipelineRun,
  fetchPipelineRuns,
  rerunPipelineRun,
  type PipelineRun,
} from "@/lib/api";
import { RefreshCw, Plus, LayoutGrid, Rows3 } from "lucide-react";
import { useI18n } from "@/lib/I18nProvider";

const STATUS_KEYS = {
  all: "pipeline.status.all",
  running: "pipeline.status.running",
  success: "pipeline.status.success",
  failed: "pipeline.status.failed",
  pending: "pipeline.status.pending",
  cancelled: "pipeline.status.cancelled",
} as const;

export default function PipelinePage() {
  const { t } = useI18n();
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"compact" | "detailed">("detailed");
  const [expandedRun, setExpandedRun] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    try {
      setRuns(await fetchPipelineRuns(search, statusFilter));
    } catch {
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter]);

  useEffect(() => {
    fetchRuns();
    const interval = setInterval(fetchRuns, 10000);
    return () => clearInterval(interval);
  }, [fetchRuns]);

  const handleRerun = useCallback(async (runId: string) => {
    try {
      await rerunPipelineRun(runId);
      fetchRuns();
    } catch {
    }
  }, [fetchRuns]);

  const handleCancel = useCallback(async (runId: string) => {
    try {
      await cancelPipelineRun(runId);
      fetchRuns();
    } catch {
    }
  }, [fetchRuns]);

  const getStatusCount = (status: string) =>
    runs.filter((r) => status === "all" || r.status === status).length;

  const runningStages = runs
    .filter((r) => r.status === "running")
    .flatMap((r) => r.stages.filter((s) => s.status === "running"));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">{t("pipeline.title")}</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {t("pipeline.runs_summary", { runs: runs.length, active: runningStages.length })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode(viewMode === "compact" ? "detailed" : "compact")}
            className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
            title={viewMode === "compact" ? t("pipeline.detailed_view") : t("pipeline.compact_view")}
          >
            {viewMode === "compact" ? <LayoutGrid className="w-4 h-4" /> : <Rows3 className="w-4 h-4" />}
          </button>
          <button
            onClick={fetchRuns}
            className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
            <Plus className="w-4 h-4" />
            {t("pipeline.new_run")}
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <SearchBar
          placeholder={t("pipeline.search_placeholder")}
          value={search}
          onChange={setSearch}
          size="sm"
          className="w-64"
        />
        <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-0.5">
          {(["all", "running", "success", "failed"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={cn(
                "px-3 py-1 text-xs font-medium rounded-md transition-colors",
                statusFilter === s ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
              )}
            >
              {t(STATUS_KEYS[s])}
              <span className="ml-1 text-[10px] opacity-60">{getStatusCount(s)}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="bg-white rounded-lg border border-gray-200 p-5 animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-48 mb-3" />
                <div className="flex gap-3">
                  {Array.from({ length: 4 }).map((_, j) => (
                    <div key={j} className="h-20 flex-1 bg-gray-100 rounded-lg" />
                  ))}
                </div>
              </div>
            ))
          ) : runs.length === 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 p-12 text-center text-sm text-gray-500">
              {t("pipeline.no_runs")}
            </div>
          ) : (
            runs.map((run) => (
              <div
                key={run.id}
                className={cn(
                  "bg-white rounded-lg border border-gray-200 overflow-hidden transition-all",
                  expandedRun === run.id && "ring-2 ring-blue-500"
                )}
              >
                <div
                  className="flex items-center justify-between px-5 py-3 cursor-pointer hover:bg-gray-50/50"
                  onClick={() => setExpandedRun(expandedRun === run.id ? null : run.id)}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        "w-2 h-2 rounded-full",
                        run.status === "running" && "bg-blue-500 animate-pulse",
                        run.status === "success" && "bg-green-500",
                        run.status === "failed" && "bg-red-500",
                        run.status === "pending" && "bg-gray-300",
                        run.status === "cancelled" && "bg-gray-400"
                      )}
                    />
                    <div>
                      <p className="text-sm font-semibold text-gray-900">{run.name}</p>
                      <p className="text-[10px] text-gray-400">
                        {run.branch} · {run.triggeredBy} · {new Date(run.createdAt).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "px-2 py-0.5 text-[10px] font-medium rounded-full",
                        run.status === "running" && "bg-blue-100 text-blue-700",
                        run.status === "success" && "bg-green-100 text-green-700",
                        run.status === "failed" && "bg-red-100 text-red-700",
                        run.status === "pending" && "bg-gray-100 text-gray-500",
                        run.status === "cancelled" && "bg-gray-100 text-gray-500"
                      )}
                    >
                      {t(STATUS_KEYS[run.status as keyof typeof STATUS_KEYS] ?? "pipeline.status.pending")}
                    </span>
                    {run.status === "running" && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCancel(run.id);
                        }}
                        className="text-xs text-red-600 hover:text-red-700 transition-colors"
                      >
                        {t("pipeline.cancel")}
                      </button>
                    )}
                  </div>
                </div>

                {expandedRun === run.id && (
                  <div className="px-5 pb-4 border-t border-gray-100 pt-4 space-y-4">
                    <PipelineStage
                      stages={run.stages as ComponentProps<typeof PipelineStage>["stages"]}
                      orientation="horizontal"
                    />

                    {run.commit && (
                      <div className="text-xs text-gray-500">
                        {t("pipeline.commit")}: <span className="font-mono">{run.commit.slice(0, 8)}</span>
                      </div>
                    )}

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleRerun(run.id)}
                        className="px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        {t("pipeline.rerun")}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        <div className="lg:col-span-1">
          <ActivityFeed
            title={t("pipeline.activity")}
            items={runs.slice(0, 10).map((r) => ({
              id: r.id,
              type: r.status === "running" ? "system" : r.status === "failed" ? "alert" : "update",
              title: `${r.name}: ${r.status}`,
              description: r.branch,
              timestamp: r.createdAt,
            }))}
            maxItems={10}
            compact
          />
        </div>
      </div>
    </div>
  );
}
