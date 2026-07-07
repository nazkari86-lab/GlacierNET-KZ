"use client";

import { useState, useMemo, useCallback } from "react";
import { cn } from "@/lib/utils";
import {
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  Search,
  Download,
  RefreshCw,
  MoreHorizontal,
  Eye,
  Check,
  X,
} from "lucide-react";

interface Column<T> {
  key: string;
  label: string;
  sortable?: boolean;
  filterable?: boolean;
  width?: string;
  align?: "left" | "center" | "right";
  render?: (value: unknown, row: T, index: number) => React.ReactNode;
  editable?: boolean;
  type?: "text" | "number" | "select" | "date";
  options?: string[];
}

interface BulkAction<T> {
  label: string;
  icon?: React.ReactNode;
  onClick: (selectedRows: T[]) => void;
  variant?: "default" | "danger";
}

interface AdminDataTableProps<T extends { id: string | number }> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  searchable?: boolean;
  searchPlaceholder?: string;
  bulkActions?: BulkAction<T>[];
  selectable?: boolean;
  pagination?: boolean;
  pageSize?: number;
  exportable?: boolean;
  onExport?: (data: T[]) => void;
  onRefresh?: () => void;
  onRowClick?: (row: T) => void;
  onRowEdit?: (row: T, key: string, value: unknown) => void;
  emptyMessage?: string;
  className?: string;
  striped?: boolean;
  compact?: boolean;
}

export default function AdminDataTable<T extends { id: string | number }>({
  columns,
  data,
  loading = false,
  searchable = true,
  searchPlaceholder = "Search...",
  bulkActions = [],
  selectable = false,
  pagination = true,
  pageSize = 20,
  exportable = false,
  onExport,
  onRefresh,
  onRowClick,
  onRowEdit,
  emptyMessage = "No data available",
  className,
  striped = false,
  compact = false,
}: AdminDataTableProps<T>) {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<Set<string | number>>(new Set());
  const [filters] = useState<Record<string, string>>({});
  const [editingCell, setEditingCell] = useState<{ rowId: string | number; key: string } | null>(null);
  const [editValue, setEditValue] = useState<string>("");

  const filteredData = useMemo(() => {
    let result = [...data];
    if (search) {
      const q = search.toLowerCase();
      result = result.filter((row) =>
        columns.some((col) => {
          const val = row[col.key as keyof T];
          return String(val).toLowerCase().includes(q);
        })
      );
    }
    Object.entries(filters).forEach(([key, val]) => {
      if (val) {
        result = result.filter((row) => String(row[key as keyof T]).toLowerCase().includes(val.toLowerCase()));
      }
    });
    return result;
  }, [data, search, columns, filters]);

  const sortedData = useMemo(() => {
    if (!sortKey) return filteredData;
    return [...filteredData].sort((a, b) => {
      const aVal = a[sortKey as keyof T];
      const bVal = b[sortKey as keyof T];
      const cmp = String(aVal).localeCompare(String(bVal), undefined, { numeric: true });
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [filteredData, sortKey, sortDir]);

  const totalPages = Math.ceil(sortedData.length / pageSize);
  const paginatedData = useMemo(() => {
    if (!pagination) return sortedData;
    const start = (currentPage - 1) * pageSize;
    return sortedData.slice(start, start + pageSize);
  }, [sortedData, currentPage, pageSize, pagination]);

  const handleSort = useCallback(
    (key: string) => {
      if (sortKey === key) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortKey(key);
        setSortDir("asc");
      }
    },
    [sortKey]
  );

  const handleSelectAll = useCallback(() => {
    if (selectedIds.size === paginatedData.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(paginatedData.map((r) => r.id)));
    }
  }, [paginatedData, selectedIds]);

  const handleSelectRow = useCallback((id: string | number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const startEdit = useCallback((rowId: string | number, key: string, currentValue: unknown) => {
    setEditingCell({ rowId, key });
    setEditValue(String(currentValue ?? ""));
  }, []);

  const saveEdit = useCallback(() => {
    if (!editingCell) return;
    const numVal = Number(editValue);
    onRowEdit?.(
      data.find((r) => r.id === editingCell.rowId) as T,
      editingCell.key,
      isNaN(numVal) ? editValue : numVal
    );
    setEditingCell(null);
    setEditValue("");
  }, [editingCell, editValue, onRowEdit, data]);

  const cancelEdit = useCallback(() => {
    setEditingCell(null);
    setEditValue("");
  }, []);

  const handleExport = useCallback(() => {
    if (onExport) {
      onExport(selectedIds.size > 0 ? sortedData.filter((r) => selectedIds.has(r.id)) : sortedData);
    } else {
      const csv = [
        columns.map((c) => c.label).join(","),
        ...sortedData.map((row) =>
          columns.map((c) => `"${String(row[c.key as keyof T] ?? "").replace(/"/g, '""')}"`).join(",")
        ),
      ].join("\n");
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `export-${Date.now()}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    }
  }, [sortedData, columns, onExport, selectedIds]);

  const SortIcon = ({ colKey }: { colKey: string }) => {
    if (sortKey !== colKey) return <ChevronsUpDown className="w-3 h-3 text-gray-400" />;
    return sortDir === "asc" ? (
      <ChevronUp className="w-3 h-3 text-blue-600" />
    ) : (
      <ChevronDown className="w-3 h-3 text-blue-600" />
    );
  };

  return (
    <div className={cn("bg-white rounded-lg border border-gray-200 overflow-hidden", className)}>
      <div className="flex items-center justify-between p-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          {searchable && (
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setCurrentPage(1);
                }}
                placeholder={searchPlaceholder}
                className="pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 w-56"
              />
            </div>
          )}
          {selectedIds.size > 0 && (
            <span className="text-xs text-gray-500">{selectedIds.size} selected</span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {bulkActions.length > 0 && selectedIds.size > 0 && (
            <div className="relative group">
              <button className="flex items-center gap-1 px-2.5 py-1.5 text-xs bg-gray-100 rounded-md hover:bg-gray-200">
                Actions <MoreHorizontal className="w-3 h-3" />
              </button>
              <div className="absolute right-0 mt-1 w-44 bg-white border border-gray-200 rounded-lg shadow-lg z-50 hidden group-hover:block">
                {bulkActions.map((action, i) => (
                  <button
                    key={i}
                    onClick={() => action.onClick(sortedData.filter((r) => selectedIds.has(r.id)))}
                    className={cn(
                      "flex items-center gap-2 w-full px-3 py-2 text-xs text-left hover:bg-gray-50",
                      action.variant === "danger" ? "text-red-600" : "text-gray-700"
                    )}
                  >
                    {action.icon}
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          )}
          {exportable && (
            <button
              onClick={handleExport}
              className="flex items-center gap-1 px-2.5 py-1.5 text-xs bg-gray-100 rounded-md hover:bg-gray-200"
            >
              <Download className="w-3 h-3" /> Export
            </button>
          )}
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="p-1.5 text-gray-500 hover:bg-gray-100 rounded-md"
              aria-label="Refresh"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100">
              {selectable && (
                <th className="w-10 px-3 py-2">
                  <input
                    type="checkbox"
                    checked={selectedIds.size === paginatedData.length && paginatedData.length > 0}
                    onChange={handleSelectAll}
                    className="rounded border-gray-300"
                  />
                </th>
              )}
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    "px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider",
                    col.sortable && "cursor-pointer select-none hover:text-gray-700",
                    col.align === "center" && "text-center",
                    col.align === "right" && "text-right"
                  )}
                  style={{ width: col.width }}
                  onClick={() => col.sortable && handleSort(col.key)}
                >
                  <div className="flex items-center gap-1">
                    {col.label}
                    {col.sortable && <SortIcon colKey={col.key} />}
                  </div>
                </th>
              ))}
              <th className="w-10 px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="animate-pulse border-b border-gray-50">
                  {columns.map((col) => (
                    <td key={col.key} className={cn("px-3", compact ? "py-1.5" : "py-2.5")}>
                      <div className="h-4 bg-gray-200 rounded" />
                    </td>
                  ))}
                </tr>
              ))
            ) : paginatedData.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length + (selectable ? 1 : 0) + 1}
                  className="px-3 py-12 text-center text-sm text-gray-500"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              paginatedData.map((row, rowIdx) => (
                <tr
                  key={row.id}
                  className={cn(
                    "border-b border-gray-50 hover:bg-gray-50/50 transition-colors",
                    striped && rowIdx % 2 === 1 && "bg-gray-50/30",
                    onRowClick && "cursor-pointer"
                  )}
                  onClick={() => onRowClick?.(row)}
                >
                  {selectable && (
                    <td className="px-3 py-2">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(row.id)}
                        onChange={() => handleSelectRow(row.id)}
                        onClick={(e) => e.stopPropagation()}
                        className="rounded border-gray-300"
                      />
                    </td>
                  )}
                  {columns.map((col) => {
                    const val = row[col.key as keyof T];
                    const isEditing =
                      editingCell?.rowId === row.id && editingCell?.key === col.key;
                    return (
                      <td
                        key={col.key}
                        className={cn(
                          "px-3",
                          compact ? "py-1.5" : "py-2.5",
                          col.align === "center" && "text-center",
                          col.align === "right" && "text-right",
                          col.editable && "cursor-pointer hover:bg-blue-50"
                        )}
                        onDoubleClick={() =>
                          col.editable && startEdit(row.id, col.key, val)
                        }
                      >
                        {isEditing && col.editable ? (
                          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                            {col.type === "select" && col.options ? (
                              <select
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value)}
                                className="text-xs border rounded px-1 py-0.5"
                                autoFocus
                              >
                                {col.options.map((opt) => (
                                  <option key={opt} value={opt}>
                                    {opt}
                                  </option>
                                ))}
                              </select>
                            ) : (
                              <input
                                type={col.type === "number" ? "number" : "text"}
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") saveEdit();
                                  if (e.key === "Escape") cancelEdit();
                                }}
                                className="text-xs border rounded px-1 py-0.5 w-full"
                                autoFocus
                              />
                            )}
                            <button onClick={saveEdit} className="p-0.5 text-green-600">
                              <Check className="w-3 h-3" />
                            </button>
                            <button onClick={cancelEdit} className="p-0.5 text-red-600">
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        ) : col.render ? (
                          col.render(val, row, rowIdx)
                        ) : (
                          <span className="truncate block max-w-[200px]">{String(val ?? "")}</span>
                        )}
                      </td>
                    );
                  })}
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onRowClick?.(row);
                        }}
                        className="p-1 rounded hover:bg-gray-100"
                        aria-label="View"
                      >
                        <Eye className="w-3 h-3 text-gray-400" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {pagination && totalPages > 1 && (
        <div className="flex items-center justify-between px-3 py-2 border-t border-gray-100 text-xs text-gray-500">
          <span>
            Showing {(currentPage - 1) * pageSize + 1}-
            {Math.min(currentPage * pageSize, sortedData.length)} of {sortedData.length}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-2 py-1 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
            >
              Prev
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const page = i + 1;
              return (
                <button
                  key={page}
                  onClick={() => setCurrentPage(page)}
                  className={cn(
                    "px-2 py-1 rounded border",
                    currentPage === page
                      ? "bg-blue-600 text-white border-blue-600"
                      : "border-gray-200 hover:bg-gray-50"
                  )}
                >
                  {page}
                </button>
              );
            })}
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-2 py-1 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export type { AdminDataTableProps, Column, BulkAction };
