"use client";

import React, { useMemo } from "react";

const BAR_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"];
const LINE_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];
const DONUT_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

interface ChartDataPoint {
  label: string;
  value: number;
  color?: string;
}

interface BarChartProps {
  data: ChartDataPoint[];
  height?: number;
  showLabels?: boolean;
  showValues?: boolean;
  animate?: boolean;
  horizontal?: boolean;
}

export function BarChart({
  data,
  height = 200,
  showLabels = true,
  showValues = true,
  animate = true,
  horizontal = false,
}: BarChartProps) {
  const max = useMemo(() => Math.max(...data.map((d) => d.value), 1), [data]);

  if (horizontal) {
    return (
      <div className="space-y-2" style={{ minHeight: height }}>
        {data.map((item, i) => {
          const pct = (item.value / max) * 100;
          const color = item.color || BAR_COLORS[i % BAR_COLORS.length];
          return (
            <div key={item.label} className="flex items-center gap-3">
              {showLabels && (
                <span className="text-xs text-gray-600 w-24 text-right truncate">{item.label}</span>
              )}
              <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
                <div
                  className={`h-full rounded-full flex items-center justify-end pr-2 ${animate ? "transition-all duration-700" : ""}`}
                  style={{ width: `${Math.max(pct, 2)}%`, backgroundColor: color }}
                >
                  {showValues && pct > 15 && (
                    <span className="text-xs font-medium text-white">{item.value}</span>
                  )}
                </div>
              </div>
              {showValues && pct <= 15 && (
                <span className="text-xs text-gray-500 w-12">{item.value}</span>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className="flex items-end gap-1" style={{ height }}>
      {data.map((item, i) => {
        const pct = (item.value / max) * 100;
        const color = item.color || BAR_COLORS[i % BAR_COLORS.length];
        return (
          <div key={item.label} className="flex-1 flex flex-col items-center gap-1">
            {showValues && (
              <span className="text-xs text-gray-600 font-medium">{item.value}</span>
            )}
            <div
              className={`w-full rounded-t-md ${animate ? "transition-all duration-500" : ""}`}
              style={{
                height: `${Math.max(pct, 2)}%`,
                backgroundColor: color,
                minHeight: 4,
              }}
            />
            {showLabels && (
              <span className="text-[10px] text-gray-500 truncate w-full text-center">{item.label}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

interface LineChartProps {
  data: { label: string; values: number[] }[];
  series?: { name: string; color: string }[];
  height?: number;
  showGrid?: boolean;
}

export function LineChart({ data, series, height = 200, showGrid = true }: LineChartProps) {
  const allValues = data.flatMap((d) => d.values);
  const max = Math.max(...allValues, 1);
  const min = Math.min(...allValues, 0);
  const range = max - min || 1;
  const seriesColors = series?.map((s) => s.color) || LINE_COLORS;

  const points = useMemo(() => {
    const numSeries = data[0]?.values.length || 0;
    return Array.from({ length: numSeries }, (_, si) => {
      return data.map((d, di) => {
        const x = (di / (data.length - 1 || 1)) * 100;
        const y = 100 - ((d.values[si] - min) / range) * 100;
        return `${x},${y}`;
      }).join(" ");
    });
  }, [data, range, min]);

  return (
    <div className="relative" style={{ height }}>
      {showGrid && (
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
          {[0, 25, 50, 75, 100].map((y) => (
            <line key={y} x1="0" y1={y} x2="100" y2={y} stroke="#f3f4f6" strokeWidth="0.5" />
          ))}
        </svg>
      )}
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
        {points.map((pts, i) => (
          <polyline
            key={i}
            points={pts}
            fill="none"
            stroke={seriesColors[i]}
            strokeWidth="0.8"
            strokeLinejoin="round"
          />
        ))}
      </svg>
      <div className="absolute bottom-0 left-0 right-0 flex justify-between px-1">
        {data.filter((_, i) => i % Math.ceil(data.length / 8) === 0 || i === data.length - 1).map((d) => (
          <span key={d.label} className="text-[9px] text-gray-400">{d.label}</span>
        ))}
      </div>
      {series && (
        <div className="flex gap-3 mt-2 justify-center">
          {series.map((s) => (
            <div key={s.name} className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: s.color }} />
              <span className="text-xs text-gray-600">{s.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface DonutChartProps {
  data: ChartDataPoint[];
  size?: number;
  innerRadius?: number;
  showLegend?: boolean;
}

export function DonutChart({ data, size = 160, innerRadius = 60, showLegend = true }: DonutChartProps) {
  const total = useMemo(() => data.reduce((s, d) => s + d.value, 0), [data]);
  const r = size / 2;
  const outerR = r - 4;
  const innerR = innerRadius;

  const arcs = useMemo(() => {
    let cumAngle = -Math.PI / 2;
    const result: Array<{ d: string; color: string; label: string; value: number; pct: string }> = [];
    for (let i = 0; i < data.length; i++) {
      const item = data[i];
      const angle = (item.value / total) * Math.PI * 2;
      const startAngle = cumAngle;
      cumAngle += angle;
      const endAngle = cumAngle;
      const color = item.color || DONUT_COLORS[i % DONUT_COLORS.length];

      const x1 = r + outerR * Math.cos(startAngle);
      const y1 = r + outerR * Math.sin(startAngle);
      const x2 = r + outerR * Math.cos(endAngle);
      const y2 = r + outerR * Math.sin(endAngle);
      const ix1 = r + innerR * Math.cos(endAngle);
      const iy1 = r + innerR * Math.sin(endAngle);
      const ix2 = r + innerR * Math.cos(startAngle);
      const iy2 = r + innerR * Math.sin(startAngle);

      const largeArc = angle > Math.PI ? 1 : 0;
      const d = `M ${x1} ${y1} A ${outerR} ${outerR} 0 ${largeArc} 1 ${x2} ${y2} L ${ix1} ${iy1} A ${innerR} ${innerR} 0 ${largeArc} 0 ${ix2} ${iy2} Z`;

      result.push({ d, color, label: item.label, value: item.value, pct: ((item.value / total) * 100).toFixed(1) });
    }
    return result;
  }, [data, total, innerR, outerR, r]);

  return (
    <div className="flex items-center gap-4">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {arcs.map((arc, i) => (
          <path key={i} d={arc.d} fill={arc.color} className="transition-all duration-300 hover:opacity-80" />
        ))}
        <text x={r} y={r - 6} textAnchor="middle" className="text-lg font-bold fill-gray-800">{total}</text>
        <text x={r} y={r + 10} textAnchor="middle" className="text-xs fill-gray-500">total</text>
      </svg>
      {showLegend && (
        <div className="space-y-1">
          {arcs.map((arc, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: arc.color }} />
              <span className="text-gray-600">{arc.label}</span>
              <span className="text-gray-400 ml-auto">{arc.pct}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
