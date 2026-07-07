"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import UserAvatar from "@/components/UserAvatar";
import SearchBar from "@/components/SearchBar";
import { Download, Clock, AlertTriangle, Info, Shield } from "lucide-react";
import { useI18n } from "@/lib/I18nProvider";
import { exportAdminAuditCsv, fetchAdminAudit, type AuditEntry } from "@/lib/api";

const LEVEL_ICONS = {
  info: { icon: Info, color: "text-blue-500 bg-blue-50" },
  warning: { icon: AlertTriangle, color: "text-amber-500 bg-amber-50" },
  error: { icon: Shield, color: "text-red-500 bg-red-50" },
};

export default function AuditLogPage() {
  const { t } = useI18n();
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [levelFilter, setLevelFilter] = useState<string>("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null);
  const pageSize = 25;

  const fetchEntries = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchAdminAudit({
        page,
        limit: pageSize,
        q: search || undefined,
        level: levelFilter,
        from: dateFrom || undefined,
        to: dateTo || undefined,
      });
      setEntries(data.entries);
      setTotalPages(data.totalPages);
    } catch {
    } finally {
      setLoading(false);
    }
  }, [page, search, levelFilter, dateFrom, dateTo]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  const handleExport = useCallback(async () => {
    try {
      const blob = await exportAdminAuditCsv({
        q: search || undefined,
        level: levelFilter,
        from: dateFrom || undefined,
        to: dateTo || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit-log-${new Date().toISOString().split("T")[0]}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
    }
  }, [search, levelFilter, dateFrom, dateTo]);

  const formatTimestamp = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleString();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">{t("admin.audit_title")}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{t("admin.audit_desc")}</p>
        </div>
        <button
          onClick={handleExport}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <SearchBar
          placeholder="Search audit log..."
          value={search}
          onChange={setSearch}
          size="sm"
          className="w-64"
        />
        <select
          value={levelFilter}
          onChange={(e) => setLevelFilter(e.target.value)}
          className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">All Levels</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="error">Error</option>
        </select>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">From</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">To</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/50">
              <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500 w-8" />
              <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">User</th>
              <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">Action</th>
              <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">Resource</th>
              <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">IP Address</th>
              <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">Time</th>
              <th className="w-8 px-4 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i} className="border-b border-gray-50 animate-pulse">
                  <td colSpan={7} className="px-4 py-3">
                    <div className="h-6 bg-gray-100 rounded w-full" />
                  </td>
                </tr>
              ))
            ) : entries.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-sm text-gray-500">
                  No audit entries found
                </td>
              </tr>
            ) : (
              entries.map((entry) => {
                const levelInfo = LEVEL_ICONS[entry.level];
                const LevelIcon = levelInfo.icon;
                return (
                  <tr
                    key={entry.id}
                    className="border-b border-gray-50 hover:bg-gray-50/50 cursor-pointer transition-colors"
                    onClick={() => setSelectedEntry(selectedEntry?.id === entry.id ? null : entry)}
                  >
                    <td className="px-4 py-3">
                      <div className={cn("w-6 h-6 rounded-full flex items-center justify-center", levelInfo.color)}>
                        <LevelIcon className="w-3 h-3" />
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <UserAvatar name={entry.userName} size="xs" />
                        <span className="text-sm text-gray-700">{entry.userName}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm font-medium text-gray-900">{entry.action}</span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {entry.resource}
                      {entry.resourceId && (
                        <span className="text-gray-400 ml-1">#{entry.resourceId}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500 font-mono">
                      {entry.ipAddress}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 text-xs text-gray-500">
                        <Clock className="w-3 h-3" />
                        {formatTimestamp(entry.timestamp)}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {selectedEntry?.id === entry.id && entry.details && (
                        <div className="absolute right-4 mt-1 p-3 bg-white border border-gray-200 rounded-lg shadow-lg z-10 max-w-sm text-xs text-gray-600">
                          {entry.details}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">
            Page {page} of {totalPages}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 text-xs border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 transition-colors"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1 text-xs border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
