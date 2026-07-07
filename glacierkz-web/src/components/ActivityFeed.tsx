"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import {
  User,
  Upload,
  Download,
  Settings,
  AlertTriangle,
  Database,
  BarChart3,
  FileText,
  Clock,
  RefreshCw,
} from "lucide-react";

interface ActivityItem {
  id: string;
  type: "upload" | "download" | "process" | "alert" | "settings" | "user" | "report" | "system" | "update";
  title: string;
  description?: string;
  user?: string;
  timestamp: string;
  metadata?: Record<string, string>;
}

interface ActivityFeedProps {
  items: ActivityItem[];
  title?: string;
  maxItems?: number;
  showFilter?: boolean;
  onItemClick?: (item: ActivityItem) => void;
  className?: string;
  compact?: boolean;
}

const TYPE_CONFIG: Record<string, { icon: typeof User; color: string; bg: string }> = {
  upload: { icon: Upload, color: "text-blue-600", bg: "bg-blue-100" },
  download: { icon: Download, color: "text-green-600", bg: "bg-green-100" },
  process: { icon: BarChart3, color: "text-purple-600", bg: "bg-purple-100" },
  alert: { icon: AlertTriangle, color: "text-amber-600", bg: "bg-amber-100" },
  settings: { icon: Settings, color: "text-gray-600", bg: "bg-gray-100" },
  user: { icon: User, color: "text-indigo-600", bg: "bg-indigo-100" },
  report: { icon: FileText, color: "text-teal-600", bg: "bg-teal-100" },
  system: { icon: Database, color: "text-orange-600", bg: "bg-orange-100" },
  update: { icon: RefreshCw, color: "text-teal-600", bg: "bg-teal-100" },
};

function formatRelativeTime(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(timestamp).toLocaleDateString();
}

export default function ActivityFeed({
  items,
  title,
  maxItems = 20,
  showFilter = true,
  onItemClick,
  className,
  compact = false,
}: ActivityFeedProps) {
  const [filter, setFilter] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  const filteredItems = items.filter((item) => !filter || item.type === filter);
  const visibleItems = showAll ? filteredItems : filteredItems.slice(0, maxItems);
  const typeCounts = items.reduce(
    (acc, item) => {
      acc[item.type] = (acc[item.type] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className={cn("bg-white rounded-lg border border-gray-200 overflow-hidden", className)}>
      <div className="flex items-center justify-between p-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-gray-500" />
          <h3 className="text-sm font-semibold text-gray-900">{title || "Activity"}</h3>
          <span className="text-[10px] text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded-full">
            {items.length}
          </span>
        </div>
        {showFilter && (
          <div className="flex items-center gap-1">
            {Object.entries(typeCounts)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 4)
              .map(([type, count]) => {
                const config = TYPE_CONFIG[type];
                return (
                  <button
                    key={type}
                    onClick={() => setFilter(filter === type ? null : type)}
                    className={cn(
                      "flex items-center gap-1 px-1.5 py-0.5 text-[10px] rounded-full transition-colors",
                      filter === type ? "bg-gray-800 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    )}
                  >
                    <config.icon className="w-2.5 h-2.5" />
                    {count}
                  </button>
                );
              })}
          </div>
        )}
      </div>

      <div className="overflow-y-auto max-h-[400px]">
        {visibleItems.length === 0 ? (
          <div className="px-3 py-8 text-center text-sm text-gray-500">No activity</div>
        ) : (
          <div className="divide-y divide-gray-50">
            {visibleItems.map((item) => {
              const config = TYPE_CONFIG[item.type] || TYPE_CONFIG.system;
              const Icon = config.icon;
              return (
                <div
                  key={item.id}
                  className={cn(
                    "flex items-start gap-3 px-3 hover:bg-gray-50 cursor-pointer transition-colors",
                    compact ? "py-2" : "py-3"
                  )}
                  onClick={() => onItemClick?.(item)}
                >
                  <div className={cn("w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0", config.bg)}>
                    <Icon className={cn("w-3.5 h-3.5", config.color)} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-900 truncate">{item.title}</p>
                    {item.description && !compact && (
                      <p className="text-[11px] text-gray-500 mt-0.5 line-clamp-2">{item.description}</p>
                    )}
                    <div className="flex items-center gap-2 mt-1">
                      {item.user && (
                        <span className="text-[10px] text-gray-400">{item.user}</span>
                      )}
                      <span className="text-[10px] text-gray-400">{formatRelativeTime(item.timestamp)}</span>
                    </div>
                    {item.metadata && !compact && (
                      <div className="flex items-center gap-2 mt-1">
                        {Object.entries(item.metadata).map(([k, v]) => (
                          <span key={k} className="text-[10px] text-gray-400">
                            {k}: {v}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {filteredItems.length > maxItems && !showAll && (
        <div className="px-3 py-2 border-t border-gray-100">
          <button
            onClick={() => setShowAll(true)}
            className="w-full text-xs text-blue-600 hover:text-blue-700 font-medium"
          >
            Show {filteredItems.length - maxItems} more
          </button>
        </div>
      )}
    </div>
  );
}

export type { ActivityFeedProps, ActivityItem };
