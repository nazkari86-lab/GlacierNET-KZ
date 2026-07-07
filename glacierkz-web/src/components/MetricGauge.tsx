"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";

interface MetricGaugeProps {
  value: number;
  min?: number;
  max?: number;
  label?: string;
  unit?: string;
  size?: "sm" | "md" | "lg";
  showValue?: boolean;
  thresholds?: { value: number; color: string; label?: string }[];
  color?: string;
  className?: string;
  format?: (value: number) => string;
}

const SIZE_CONFIG = {
  sm: { width: 80, height: 80, strokeWidth: 6, fontSize: "text-xs", labelSize: "text-[9px]" },
  md: { width: 120, height: 120, strokeWidth: 8, fontSize: "text-lg", labelSize: "text-[10px]" },
  lg: { width: 160, height: 160, strokeWidth: 10, fontSize: "text-2xl", labelSize: "text-xs" },
} as const;

export default function MetricGauge({
  value,
  min = 0,
  max = 100,
  label,
  unit = "",
  size = "md",
  showValue = true,
  thresholds = [],
  color,
  className,
  format,
}: MetricGaugeProps) {
  const config = SIZE_CONFIG[size];
  const radius = (config.width - config.strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const angle = ((value - min) / (max - min)) * 270;
  const dashOffset = circumference - (circumference * angle) / 360;

  const computedColor = useMemo(() => {
    if (color) return color;
    for (const t of thresholds) {
      if (value >= t.value) return t.color;
    }
    return "#3b82f6";
  }, [value, thresholds, color]);

  const displayValue = format ? format(value) : value.toFixed(1);

  return (
    <div className={cn("flex flex-col items-center", className)}>
      <svg
        width={config.width}
        height={config.height}
        viewBox={`0 0 ${config.width} ${config.height}`}
      >
        <circle
          cx={config.width / 2}
          cy={config.height / 2}
          r={radius}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={config.strokeWidth}
          strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`}
          strokeLinecap="round"
          transform={`rotate(135 ${config.width / 2} ${config.height / 2})`}
        />
        <circle
          cx={config.width / 2}
          cy={config.height / 2}
          r={radius}
          fill="none"
          stroke={computedColor}
          strokeWidth={config.strokeWidth}
          strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          transform={`rotate(135 ${config.width / 2} ${config.height / 2})`}
          className="transition-all duration-500"
        />
        {showValue && (
          <text
            x={config.width / 2}
            y={config.height / 2 + 2}
            textAnchor="middle"
            dominantBaseline="central"
            className={cn("font-semibold fill-gray-900", config.fontSize)}
          >
            {displayValue}
            {unit && (
              <tspan className={cn("fill-gray-400", config.labelSize)}>
                {unit}
              </tspan>
            )}
          </text>
        )}
      </svg>
      {label && (
        <span className={cn("font-medium text-gray-700 mt-1", config.labelSize)}>{label}</span>
      )}
    </div>
  );
}

interface MetricGaugeBarProps {
  value: number;
  max?: number;
  label?: string;
  unit?: string;
  color?: string;
  showPercentage?: boolean;
  className?: string;
  format?: (value: number) => string;
}

export function MetricGaugeBar({
  value,
  max = 100,
  label,
  unit = "",
  color = "#3b82f6",
  showPercentage = true,
  className,
  format,
}: MetricGaugeBarProps) {
  const percent = Math.min((value / max) * 100, 100);
  const displayValue = format ? format(value) : value.toFixed(1);

  return (
    <div className={cn("w-full", className)}>
      {(label || showPercentage) && (
        <div className="flex items-center justify-between mb-1">
          {label && <span className="text-xs font-medium text-gray-700">{label}</span>}
          {showPercentage && (
            <span className="text-xs text-gray-500">
              {displayValue}{unit} ({percent.toFixed(0)}%)
            </span>
          )}
        </div>
      )}
      <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${percent}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

interface MetricGaugeMultiProps {
  items: Array<{
    label: string;
    value: number;
    max?: number;
    color?: string;
    unit?: string;
  }>;
  className?: string;
}

export function MetricGaugeMulti({ items, className }: MetricGaugeMultiProps) {
  return (
    <div className={cn("flex items-end gap-4 justify-center", className)}>
      {items.map((item, i) => (
        <MetricGauge
          key={i}
          value={item.value}
          min={0}
          max={item.max || 100}
          label={item.label}
          unit={item.unit}
          color={item.color}
        />
      ))}
    </div>
  );
}

const MetricGaugeCircular = MetricGauge;
export type { MetricGaugeProps, MetricGaugeBarProps, MetricGaugeMultiProps };
export { MetricGaugeCircular };
