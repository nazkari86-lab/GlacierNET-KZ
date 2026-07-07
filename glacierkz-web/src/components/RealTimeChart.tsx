"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
} from "recharts";
import { cn } from "@/lib/utils";
import { Pause, Play, Trash2, Download, RefreshCw } from "lucide-react";

interface DataPoint {
  timestamp: number;
  value: number;
  label?: string;
}

interface RealTimeChartProps {
  maxPoints?: number;
  refreshInterval?: number;
  yMin?: number;
  yMax?: number;
  title?: string;
  unit?: string;
  color?: string;
  fillColor?: string;
  thresholds?: { value: number; label: string; color: string }[];
  onDataFetch?: () => Promise<DataPoint[]>;
  className?: string;
  showControls?: boolean;
  showGrid?: boolean;
  variant?: "line" | "area";
}

export default function RealTimeChart({
  maxPoints = 100,
  refreshInterval = 2000,
  yMin,
  yMax,
  title,
  unit = "",
  color = "#3b82f6",
  fillColor = "rgba(59,130,246,0.1)",
  thresholds = [],
  onDataFetch,
  className,
  showControls = true,
  showGrid = true,
  variant = "line",
}: RealTimeChartProps) {
  const [isMounted, setIsMounted] = useState(false);
  const [data, setData] = useState<DataPoint[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const dataRef = useRef<DataPoint[]>([]);

  const addDataPoint = useCallback(
    (point: DataPoint) => {
      setData((prev) => {
        const next = [...prev, point];
        if (next.length > maxPoints) next.shift();
        dataRef.current = next;
        return next;
      });
      setLastUpdate(new Date());
    },
    [maxPoints]
  );

  const fetchData = useCallback(async () => {
    if (!onDataFetch) return;
    try {
      const points = await onDataFetch();
      points.forEach(addDataPoint);
    } catch {
      console.error("Failed to fetch chart data");
    }
  }, [onDataFetch, addDataPoint]);

  useEffect(() => {
    if (isPaused) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }
    intervalRef.current = setInterval(fetchData, refreshInterval);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPaused, refreshInterval, fetchData]);

  useEffect(() => {
    setIsMounted(true);
    fetchData();
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchData]);

  const handleClear = useCallback(() => {
    setData([]);
    dataRef.current = [];
  }, []);

  const handleExport = useCallback(() => {
    const csv = ["timestamp,value,label", ...data.map((d) => `${d.timestamp},${d.value},${d.label || ""}`)].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `chart-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [data]);

  const togglePause = useCallback(() => setIsPaused((p) => !p), []);

  const latestValue = data.length > 0 ? data[data.length - 1].value : 0;
  const avgValue = data.length > 0 ? data.reduce((s, d) => s + d.value, 0) / data.length : 0;
  const minValue = data.length > 0 ? Math.min(...data.map((d) => d.value)) : 0;
  const maxValue = data.length > 0 ? Math.max(...data.map((d) => d.value)) : 0;

  const formatTimestamp = (ts: number) => {
    const d = new Date(ts);
    return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
  };

  const ChartComponent = variant === "area" ? AreaChart : LineChart;

  return (
    <div className={cn("bg-white rounded-lg border border-gray-200 p-4", className)}>
      <div className="flex items-center justify-between mb-4">
        <div>
          {title && <h3 className="text-sm font-semibold text-gray-900">{title}</h3>}
          <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
            <span>
              Current: <span className="font-medium text-gray-900">{latestValue.toFixed(2)}{unit}</span>
            </span>
            <span>
              Avg: <span className="font-medium">{avgValue.toFixed(2)}{unit}</span>
            </span>
            <span>
              Min: <span className="font-medium">{minValue.toFixed(2)}{unit}</span>
            </span>
            <span>
              Max: <span className="font-medium">{maxValue.toFixed(2)}{unit}</span>
            </span>
          </div>
        </div>
        {showControls && (
          <div className="flex items-center gap-1.5">
            <button
              onClick={togglePause}
              className="p-1.5 rounded hover:bg-gray-100 transition-colors"
              aria-label={isPaused ? "Resume" : "Pause"}
            >
              {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            </button>
            <button
              onClick={fetchData}
              className="p-1.5 rounded hover:bg-gray-100 transition-colors"
              aria-label="Refresh"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleClear}
              className="p-1.5 rounded hover:bg-gray-100 transition-colors"
              aria-label="Clear data"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleExport}
              className="p-1.5 rounded hover:bg-gray-100 transition-colors"
              aria-label="Export CSV"
            >
              <Download className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      <div className="h-64 min-h-64 min-w-0">
        {isMounted ? (
          <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
            <ChartComponent
              data={data}
              margin={{ top: 5, right: 10, left: -10, bottom: 5 }}
            >
              {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />}
              <XAxis
                dataKey="timestamp"
                tickFormatter={formatTimestamp}
                tick={{ fontSize: 10, fill: "#9ca3af" }}
                tickLine={false}
                axisLine={{ stroke: "#e5e7eb" }}
              />
              <YAxis
                domain={yMin !== undefined && yMax !== undefined ? [yMin, yMax] : ["auto", "auto"]}
                tick={{ fontSize: 10, fill: "#9ca3af" }}
                tickLine={false}
                axisLine={{ stroke: "#e5e7eb" }}
              />
              <Tooltip
                labelFormatter={(label) => formatTimestamp(label as number)}
                contentStyle={{
                  backgroundColor: "white",
                  border: "1px solid #e5e7eb",
                  borderRadius: "6px",
                  fontSize: "12px",
                }}
                formatter={(value: unknown) => [`${Number(value).toFixed(2)}${unit}`, "Value"]}
              />
              {thresholds.map((t, i) => (
                <ReferenceLine
                  key={i}
                  y={t.value}
                  stroke={t.color}
                  strokeDasharray="4 4"
                  label={{ value: t.label, position: "right", fontSize: 10, fill: t.color }}
                />
              ))}
              {variant === "area" ? (
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={color}
                  fill={fillColor}
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              ) : (
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={color}
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              )}
            </ChartComponent>
          </ResponsiveContainer>
        ) : (
          <div className="h-full w-full rounded bg-gray-50" />
        )}
      </div>

      <div className="flex items-center justify-between mt-2 text-[10px] text-gray-400">
        <span>{data.length} points</span>
        <span>
          {isPaused ? "Paused" : "Live"} | Updated {lastUpdate.toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
}

export type { RealTimeChartProps, DataPoint };
