"use client";

import { HistoryItem } from "@/lib/api";

interface HistoryTableProps {
  items: HistoryItem[];
  onSelect: (item: HistoryItem) => void;
}

export default function HistoryTable({ items, onSelect }: HistoryTableProps) {
  if (items.length === 0) {
    return <p className="py-8 text-center text-sm text-zinc-400">No predictions yet</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-zinc-500">
            <th className="pb-2 font-medium">Date</th>
            <th className="pb-2 font-medium">Model</th>
            <th className="pb-2 font-medium">Area</th>
            <th className="pb-2 font-medium">Year</th>
            <th className="pb-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.id}
              onClick={() => onSelect(item)}
              className="cursor-pointer border-b border-zinc-100 transition-colors hover:bg-zinc-50"
            >
              <td className="py-3 text-zinc-500">
                {new Date(item.created_at).toLocaleDateString()}
              </td>
              <td className="py-3 font-medium">{item.model_name}</td>
              <td className="py-3">
                {item.area_km2 ? `${item.area_km2.toFixed(2)} km²` : "—"}
              </td>
              <td className="py-3 text-zinc-500">{item.year || "—"}</td>
              <td className="py-3">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    item.status === "completed"
                      ? "bg-green-100 text-green-700"
                      : item.status === "failed"
                        ? "bg-red-100 text-red-700"
                        : "bg-yellow-100 text-yellow-700"
                  }`}
                >
                  {item.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
