"use client";

import { cn } from "@/lib/utils";
import { Check, Loader2, AlertCircle, Clock, ChevronRight, RotateCcw, Download } from "lucide-react";

interface Stage {
  id: string;
  name: string;
  description?: string;
  status: "pending" | "running" | "completed" | "waiting" | "failed" | "skipped" | "success";
  startedAt?: string;
  completedAt?: string;
  error?: string;
  progress?: number;
  artifacts?: Array<{ name: string; url: string; size?: number }>;
}

interface PipelineStageProps {
  stages: Stage[];
  currentStageId?: string;
  orientation?: "horizontal" | "vertical";
  onRetry?: (stageId: string) => void;
  onDownloadArtifact?: (url: string) => void;
  showArtifacts?: boolean;
  showTimestamps?: boolean;
  compact?: boolean;
  className?: string;
}

const STATUS_CONFIG = {
  pending: { color: "bg-gray-200", icon: Clock, label: "Pending", textColor: "text-gray-500" },
  running: { color: "bg-blue-500", icon: Loader2, label: "Running", textColor: "text-blue-600" },
  waiting: { color: "bg-yellow-300", icon: Clock, label: "Waiting", textColor: "text-yellow-600" },
  completed: { color: "bg-green-500", icon: Check, label: "Completed", textColor: "text-green-600" },
  success: { color: "bg-green-500", icon: Check, label: "Success", textColor: "text-green-600" },
  failed: { color: "bg-red-500", icon: AlertCircle, label: "Failed", textColor: "text-red-600" },
  skipped: { color: "bg-gray-300", icon: ChevronRight, label: "Skipped", textColor: "text-gray-400" },
} as const;

function formatDuration(start?: string, end?: string): string {
  if (!start) return "";
  const ms = (end ? new Date(end) : new Date()).getTime() - new Date(start).getTime();
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

export default function PipelineStage({
  stages,
  currentStageId,
  orientation = "horizontal",
  onRetry,
  onDownloadArtifact,
  showArtifacts = false,
  showTimestamps = true,
  compact = false,
  className,
}: PipelineStageProps) {
  const completedCount = stages.filter((s) => s.status === "completed" || s.status === "success").length;
  const overallProgress = stages.length > 0 ? (completedCount / stages.length) * 100 : 0;

  if (orientation === "horizontal") {
    return (
      <div className={cn("bg-white rounded-lg border border-gray-200 p-4", className)}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Pipeline Progress</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {completedCount}/{stages.length} stages completed
            </p>
          </div>
          <span className="text-xs font-medium text-gray-700">{overallProgress.toFixed(0)}%</span>
        </div>

        <div className="w-full h-2 bg-gray-100 rounded-full mb-6">
          <div
            className="h-full bg-blue-500 rounded-full transition-all duration-500"
            style={{ width: `${overallProgress}%` }}
          />
        </div>

        <div className="flex items-start gap-0 overflow-x-auto pb-2">
          {stages.map((stage, i) => {
            const config = STATUS_CONFIG[stage.status];
            const Icon = config.icon;
            const isLast = i === stages.length - 1;
            return (
              <div key={stage.id} className="flex items-start flex-shrink-0">
                <div className={cn("flex flex-col items-center", compact ? "w-20" : "w-28")}>
                  <div
                    className={cn(
                      "w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all",
                      config.color,
                      stage.status === "running" && "animate-pulse",
                      stage.status === "completed" && "border-green-500 bg-green-50",
                      stage.status === "failed" && "border-red-500 bg-red-50"
                    )}
                  >
                    <Icon
                      className={cn(
                        "w-4 h-4 text-white",
                        stage.status === "running" && "animate-spin"
                      )}
                    />
                  </div>
                  <span className={cn("text-[11px] font-medium mt-2 text-center leading-tight", config.textColor)}>
                    {stage.name}
                  </span>
                  {showTimestamps && stage.startedAt && !compact && (
                    <span className="text-[10px] text-gray-400 mt-1">
                      {formatDuration(stage.startedAt, stage.completedAt)}
                    </span>
                  )}
                  {stage.error && !compact && (
                    <span className="text-[10px] text-red-500 mt-1 text-center leading-tight max-w-full truncate">
                      {stage.error}
                    </span>
                  )}
                  {onRetry && stage.status === "failed" && (
                    <button
                      onClick={() => onRetry(stage.id)}
                      className="flex items-center gap-0.5 mt-1 text-[10px] text-blue-600 hover:text-blue-700"
                    >
                      <RotateCcw className="w-2.5 h-2.5" /> Retry
                    </button>
                  )}
                  {showArtifacts && stage.artifacts && stage.artifacts.length > 0 && !compact && (
                    <div className="mt-1.5 space-y-0.5">
                      {stage.artifacts.map((a, j) => (
                        <button
                          key={j}
                          onClick={() => onDownloadArtifact?.(a.url)}
                          className="flex items-center gap-0.5 text-[10px] text-blue-600 hover:underline"
                        >
                          <Download className="w-2.5 h-2.5" />
                          <span className="truncate max-w-[80px]">{a.name}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                {!isLast && (
                  <div className="flex items-center mt-4">
                    <div
                      className={cn(
                        "w-12 h-0.5 transition-colors",
                        stage.status === "completed" || stage.status === "success" ? "bg-green-400" : "bg-gray-200"
                      )}
                    />
                    <ChevronRight className="w-3 h-3 text-gray-300 -ml-0.5" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className={cn("bg-white rounded-lg border border-gray-200 overflow-hidden", className)}>
      <div className="p-3 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">Pipeline Stages</h3>
          <span className="text-xs text-gray-500">{completedCount}/{stages.length}</span>
        </div>
        <div className="w-full h-1.5 bg-gray-100 rounded-full mt-2">
          <div
            className="h-full bg-blue-500 rounded-full transition-all"
            style={{ width: `${overallProgress}%` }}
          />
        </div>
      </div>

      <div className="divide-y divide-gray-50">
        {stages.map((stage) => {
          const config = STATUS_CONFIG[stage.status];
          const Icon = config.icon;
          return (
            <div
              key={stage.id}
              className={cn(
                "flex items-start gap-3 px-3",
                compact ? "py-2" : "py-3",
                currentStageId === stage.id && "bg-blue-50/50"
              )}
            >
              <div
                className={cn(
                  "w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5",
                  config.color,
                  stage.status === "running" && "animate-pulse"
                )}
              >
                <Icon className={cn("w-3.5 h-3.5 text-white", stage.status === "running" && "animate-spin")} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-gray-900">{stage.name}</span>
                  <span className={cn("text-[10px] font-medium", config.textColor)}>{config.label}</span>
                </div>
                {stage.description && !compact && (
                  <p className="text-[11px] text-gray-500 mt-0.5">{stage.description}</p>
                )}
                {stage.error && (
                  <p className="text-[11px] text-red-600 mt-1 bg-red-50 rounded px-2 py-1">{stage.error}</p>
                )}
                {stage.progress !== undefined && stage.status === "running" && (
                  <div className="w-full h-1 bg-gray-200 rounded-full mt-2">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all"
                      style={{ width: `${stage.progress}%` }}
                    />
                  </div>
                )}
                {showTimestamps && stage.startedAt && (
                  <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-400">
                    <span>Started {new Date(stage.startedAt).toLocaleTimeString()}</span>
                    {stage.completedAt && (
                      <span>Duration: {formatDuration(stage.startedAt, stage.completedAt)}</span>
                    )}
                  </div>
                )}
              </div>
              <div className="flex-shrink-0 flex items-center gap-1">
                {onRetry && stage.status === "failed" && (
                  <button
                    onClick={() => onRetry(stage.id)}
                    className="p-1 rounded hover:bg-gray-100"
                    aria-label="Retry"
                  >
                    <RotateCcw className="w-3.5 h-3.5 text-gray-400" />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export type { PipelineStageProps, Stage };
