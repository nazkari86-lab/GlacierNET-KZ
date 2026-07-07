"use client";

import React, { useState, useMemo } from "react";

interface TableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  sortable?: boolean;
  pagination?: boolean;
  pageSize?: number;
  selectable?: boolean;
  onSelectionChange?: (selected: T[]) => void;
  emptyMessage?: string;
  loading?: boolean;
}

export interface ColumnDef<T> {
  key: string;
  header: string;
  accessor?: (row: T) => React.ReactNode;
  render?: (value: unknown) => React.ReactNode;
  sortable?: boolean;
  width?: string;
  align?: "left" | "center" | "right";
  className?: string;
}

export function DataTable<T extends object>({
  data,
  columns,
  sortable = true,
  pagination = true,
  pageSize = 10,
  selectable = false,
  onSelectionChange,
  emptyMessage = "No data available",
  loading = false,
}: TableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const sorted = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const aVal = (a as Record<string, unknown>)[sortKey];
      const bVal = (b as Record<string, unknown>)[sortKey];
      if (aVal === bVal) return 0;
      const cmp = aVal == null ? -1 : bVal == null ? 1 : aVal < bVal ? -1 : 1;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  const paged = useMemo(() => {
    if (!pagination) return sorted;
    const start = page * pageSize;
    return sorted.slice(start, start + pageSize);
  }, [sorted, page, pageSize, pagination]);

  const totalPages = Math.ceil(data.length / pageSize);

  const handleSort = (key: string) => {
    if (!sortable) return;
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const toggleRow = (idx: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      if (onSelectionChange) onSelectionChange(Array.from(next).map((i) => sorted[i]));
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === paged.length) {
      setSelected(new Set());
      onSelectionChange?.([]);
    } else {
      const all = new Set(paged.map((_, i) => page * pageSize + i));
      setSelected(all);
      onSelectionChange?.(paged);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
        <div className="animate-pulse">
          <div className="h-10 bg-gray-100 border-b" />
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-12 border-b border-gray-50 flex items-center px-4 gap-4">
              {columns.map((_, j) => (
                <div key={j} className="h-4 bg-gray-100 rounded flex-1" />
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              {selectable && (
                <th className="w-10 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selected.size === paged.length && paged.length > 0}
                    onChange={toggleAll}
                    className="rounded border-gray-300"
                  />
                </th>
              )}
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`px-4 py-3 text-left font-medium text-gray-600 ${sortable && col.sortable !== false ? "cursor-pointer hover:text-gray-900 select-none" : ""} ${col.className || ""}`}
                  style={{ width: col.width }}
                  onClick={() => col.sortable !== false && handleSort(col.key)}
                >
                  <span className="flex items-center gap-1">
                    {col.header}
                    {sortKey === col.key && (
                      <span className="text-blue-500">{sortDir === "asc" ? "↑" : "↓"}</span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length + (selectable ? 1 : 0)}
                  className="px-4 py-12 text-center text-gray-400"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              paged.map((row, rowIdx) => {
                const globalIdx = page * pageSize + rowIdx;
                return (
                  <tr
                    key={rowIdx}
                    className={`border-b border-gray-50 hover:bg-gray-50 transition-colors ${selected.has(globalIdx) ? "bg-blue-50" : ""}`}
                  >
                    {selectable && (
                      <td className="w-10 px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selected.has(globalIdx)}
                          onChange={() => toggleRow(globalIdx)}
                          className="rounded border-gray-300"
                        />
                      </td>
                    )}
                    {columns.map((col) => (
                      <td key={col.key} className={`px-4 py-3 ${col.align === "right" ? "text-right" : col.align === "center" ? "text-center" : ""} ${col.className || ""}`}>
                        {col.render
                          ? col.render((row as Record<string, unknown>)[col.key])
                          : col.accessor
                            ? col.accessor(row)
                            : String((row as Record<string, unknown>)[col.key] ?? "")}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      {pagination && totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
          <span className="text-xs text-gray-500">
            Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, data.length)} of {data.length}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="px-3 py-1 text-xs rounded border border-gray-200 disabled:opacity-50 hover:bg-gray-50"
            >
              Prev
            </button>
            {Array.from({ length: Math.min(5, totalPages) }).map((_, i) => {
              const p = page < 3 ? i : page - 2 + i;
              if (p >= totalPages) return null;
              return (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`px-3 py-1 text-xs rounded border ${p === page ? "bg-blue-500 text-white border-blue-500" : "border-gray-200 hover:bg-gray-50"}`}
                >
                  {p + 1}
                </button>
              );
            })}
            <button
              onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
              disabled={page >= totalPages - 1}
              className="px-3 py-1 text-xs rounded border border-gray-200 disabled:opacity-50 hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
